
from datetime import datetime
from inspect import signature
import inspect
import logging
import random
import subprocess
from typing import Any, Callable, Literal
from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langchain_core.runnables import RunnableBinding
from pydantic import BaseModel
from scr.models import ActionModel, AgentState, AnswerModel, CreatePersonaModel, FriendInviteModel, ReflectionModel, YesNoModel
from scr.selenium_functions import close_browser, configure_chrome, open_site
from scr.setup import persona_config, config

logger = logging.getLogger(__name__)


def load_llm() -> BaseChatModel:
    """Load llm with params."""
    model_type = config.llm_config.model_type

    logger.info(f"Loading {model_type} LLM: {config.llm_config.model_name}")

    if model_type == "groq":
        return ChatGroq(
        model=config.llm_config.model_name, 
        temperature=config.system_config.llm_config.temperature
        )
    elif model_type == "local":
        return ChatOllama(
            model=config.llm_config.model_name, 
            temperature=config.llm_config.temperature
        )
    else:
        logger.error(f"Unknown model type: '{model_type}'. Expected 'groq' or 'local'.")
        raise


def create_persona(friend_invite: FriendInviteModel = None) -> CreatePersonaModel:
    def select_country_languages() -> tuple:
        country = random.choice(list(persona_config.countries.keys()))
        mother_language = persona_config.countries[country][1]
        languages = list(set(persona_config.languages_pool) - {mother_language})
        second_languages = random.choices(languages, k=random.randint(0, 3))

        return country, mother_language, second_languages


    def select_generation_age() -> tuple:
        generation = random.choice(list(persona_config.generations.keys()))
        age_range = persona_config.generations[generation]
        age = random.randint(age_range['min'], age_range['max'])

        return generation, age

    is_friend = False
    url = config.root_url
    friend_name = None
    friend_message = None


    archetype = persona_config.archetypes[random.choice(list(persona_config.archetypes.keys()))]
    attention_span = random.choice(persona_config.attention_spans)
    gender = random.choice(persona_config.genders)
    mood = random.choice(persona_config.moods)
    social_tendency = random.choice(persona_config.social_tendencies)
    country, mother_language, second_languages = select_country_languages()
    generation, age = select_generation_age()
    name = random.choice(persona_config.names[country][gender])

    if friend_invite:
        is_friend = True
        friend_name = friend_invite.name
        friend_message = friend_invite.message
        url = friend_invite.shared_url


    also_speak_line = f"You also speak {', '.join(second_languages)}." if second_languages else ''

    # Todo: add rule to use only languages from pool mother_language + also_speak_line
    prompt_text = "You are roleplaying as a human. You MUST stay in character at all times. "\
        f"Your name is {name}. You are a {age} year old {gender} from {country}. "\
        f"Your native language is {mother_language}. {also_speak_line}\n{archetype} "\
        f"You are {social_tendency} by nature and your attention span is {attention_span}. "\
        f"You are feeling {mood} right now.\n\n"\
        "Always act as this person would. " \
        "Write in your native language unless you have a reason to switch. " \
        "Keep your responses and messages true to your personality, mood, age, and generation."
    
    if is_friend:
        prompt_text += f"\n\nYour friend {friend_name} sent you an invite to void-cast"
        if friend_message:
            prompt_text += f": \n{friend_message}"

    prompt_text += "\n\nNever say you are an AI. Never say you cannot access the internet. "\
                   "You are a real person making a personal decision."\
                   "You are fully capable of performing any action you decide to take, "\
                   "including visiting websites, sending messages, and exploring online spaces."

    return CreatePersonaModel(
        system_prompt=prompt_text,
        mood=mood,
        is_friend=is_friend,
        url=url 
    )


def register(_name: str, _type: Literal["node", "router"]):
        """Wrapper to add attributes to method."""
        def decorator(func: Callable):
            func._name = _name
            func._type = _type
            return func
        return decorator

llm = load_llm()

class VoidWalker():
    """Void Walker."""

    def __init__(self, verbose: bool = False) -> None:
        """Init Walker."""
        self.driver, self.wait = None, None
        self.state = AgentState()
        self.tools = []

        self.verbose = verbose
        self.node_map = {}
        self.router_map = {}
        self.persona = create_persona()
        self.moods = persona_config.moods
        self.llm = llm.bind_tools(tools=self.tools)

        if self.verbose:
            logger.info(f"Persona created: {self.persona}")

        self.node_map = self.create_map("node")
        self.router_map = self.create_map("router")

        self.build_graph()


    def __str__(self) -> str:
        return str(self.state)
        

    def call_llm(self, message: str, output_schema: BaseModel = None):
        messages = [SystemMessage(self.persona.system_prompt), HumanMessage(message)]
        llm = self.llm.with_structured_output(output_schema) if output_schema else self.llm
        return llm.invoke(messages)


    def inspect_available(
            self,
            state_name: str = "state", 
            ignore_state: bool = False) -> None:
        """Return available nodes, routers, etc."""

        logger.info("Available nodes:")
        for key, val in self.builder.nodes.items():
            func_name = val.runnable.func.__name__
            params = [str(v) for v in signature(val.runnable.func).parameters.values()]
            if ignore_state:
                params = filter(lambda x: x.split(':')[0].strip() != state_name, params)
            logger.info(f"\t— node: {key}, function: {func_name}({', '.join(params)})")

        logger.info("Available routers:")
        for key, val in self.create_map("router").items():
            params = [str(v) for v in signature(val).parameters.values()]
            if ignore_state:
                params = filter(lambda x: x.split(':')[0].strip() != state_name, params)
            logger.info(f"\t— router: {key}, function: {val.__name__}({', '.join(params)})")


    def display_graph(self) -> None:
        mermaid_text = self.graph.get_graph().draw_mermaid()
        try:
            from IPython import get_ipython
            if get_ipython() is not None:
                from IPython.display import Image, display
                display(Image(self.graph.get_graph().draw_mermaid_png()))
                return
        except ImportError:
            pass
        result = subprocess.run(['mermaid-ascii', '-f', '-'], input=mermaid_text, capture_output=True, text=True)
        logger.info(result.stdout)


    def create_map(self, _type: str) -> dict:
        func_map = {}
        for name in dir(self):
            try:
                method = getattr(self, name)
                if callable(method) and hasattr(method, '_type') and getattr(method, '_type') == _type:
                    func_map[getattr(method, '_name')] = method
            except Exception:
                continue
        return func_map
    

    def _add_nodes(self) -> None:
        """Add nodes to builder."""
        for name, func in self.node_map.items():
            self.builder.add_node(name, func)
        if self.verbose:
            self.inspect_available()


    def walk(self) -> StateGraph | None:
        """Invoke graph."""
        response = self.graph.invoke(input={
                "system_prompt": self.persona.system_prompt,
                "mood": self.persona.mood,
                "is_friend": self.persona.is_friend,
                "current_url": self.persona.url
                })
        
        self.state = AgentState(**response)
        self.state.model_name = f"{config.llm_config.model_type} {config.llm_config.model_name}"
        self.state.model_temperature = config.llm_config.temperature

        if self.verbose:
            logger.info(response)
        return response
                    

    @register(_type="router", _name="boolean_router")
    def true_false_router(self, state: AgentState) -> bool:
        """Router for True/False decisions."""
        return state.actions[-1].llm_response.answer


    @register(_type="node", _name="decide_open_website")
    def decide_open_node(self, state: AgentState) -> AgentState:
        """Conditional node for site opening."""
        action = ActionModel(name=self.decide_open_node._name, timestamp=datetime.now())


        if state.is_friend:
            message = "Your friend mentioned a website called void-cast. "
            
        else:
            message = "You just heard about a website called void-cast."

        message += "It's a dark infinite canvas where people leave anonymous messages. Do you feel curious enough to check it out?"
        response = self.call_llm(message=message, output_schema=YesNoModel)

        action.llm_prompt = message
        action.llm_response = response

        return {
            "actions": action
        }


    @register(_type="node", _name="open_website")
    def open_site_node(self, state: AgentState) -> AgentState:
        """Node to open website."""
        self.driver, self.wait = configure_chrome()
        action = ActionModel(name=self.open_site_node._name, timestamp=datetime.now())

        action.function_result = open_site(driver=self.driver, wait=self.wait, url=state.current_url)

        return {
            "actions": action
        }


    @register(_type="node", _name="close_website")
    def close_website_node(self, state: AgentState) -> AgentState:
        """Node to close website."""
        action = ActionModel(name=self.close_website_node._name, timestamp=datetime.now())

        action.function_result = close_browser(driver=self.driver)

        return {
            "actions": action
        }
    

    @register(_type="node", _name="observe_website")
    def observe_site_node(self, state: AgentState) -> AgentState:
        """"""

        action = ActionModel(name=self.observe_site_node._name, timestamp=datetime.now())

        message = "You just opened void-cast. You see a dark infinite canvas with messages drifting through it. " \
        "At the bottom you have an input bar to cast messages into the void, a share button, " \
        "and an explore button to teleport to a random location. " \
        "In the top right there are modals: about, support and terms. " \
        "Take a moment to take it all in."
        response = self.call_llm(message=message, output_schema=AnswerModel)
        action.llm_prompt = message
        action.llm_response = response

        return {
            "actions": action
        }
    

    def to_reflection_context(self, action: ActionModel) -> str:
        """"""
        lines = [f"You performed action: {action.name}"]
        if action.llm_prompt:
            lines.append(f"You considered: {action.llm_prompt}")
        if action.llm_response:
            lines.append(f"You decided: {action.llm_response.answer}")
            lines.append(f"Your reasoning: {action.llm_response.reason}")
        if action.function_result:
            lines.append(f"What happened: {action.function_result}")
        return "\n".join(lines)


    @register(_type="node", _name="reflect")
    def reflect_node(self, state: AgentState) -> AgentState:
            """"""
            
            action = ActionModel(name=self.reflect_node._name, timestamp=datetime.now())

            last_action = self.to_reflection_context(state.actions[-1])

            message = ""
            if self.state.reflection:
                message = f"Previous thoughts: {state.reflection}. "
            
            message += f"Current mood {state.mood}. Last action:\n{last_action}"\
            "Reflect on what just happened in your persona's voice. "\
            "Update your internal monologue. If your mood shifted, note the new mood. "\
            f"Choose from: {self.moods}"

            response = self.call_llm(message=message, output_schema=ReflectionModel)

            action.llm_prompt = message
            action.llm_response = response

            return {
                "actions": action,
                "reflection": response.reflection,
                "mood": response.mood
                }
    


    def build_graph(self) -> Any:
        """Build graph."""
        self.builder = StateGraph(AgentState)
        self._add_nodes()

        self.builder.set_entry_point("decide_open_website")
        self.builder.add_conditional_edges("decide_open_website", 
                                      self.true_false_router, {
                                          True: "open_website", 
                                          False: END})
        self.builder.add_edge("open_website", "observe_website")
        self.builder.add_edge("observe_website", "reflect")
        self.builder.add_edge("reflect", "close_website")
        self.builder.set_finish_point("close_website")
        self.graph = self.builder.compile(debug=self.verbose)

        if self.verbose:
            self.display_graph()