from datetime import datetime
import gc
from inspect import signature
import logging
import random
import subprocess
import threading
from typing import Annotated, Any, Callable, List, Literal, Optional
from langchain_core.tools.structured import StructuredTool
from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from langchain_deepseek import ChatDeepSeek
from scr.logging_db import DatabaseWriter
from scr.models import ActionModel, AgentState, AnswerModel, CreatePersonaModel, FriendInviteModel, ReflectionModel, ToolOutputModel, YesNoModel
from scr.selenium_functions import close_browser, configure_chrome, interact_with_modal, move_around, open_site, read_visible_messages, send_message, press_explore, press_share
from scr.setup import persona_config, config

logger = logging.getLogger(__name__)


def load_llm() -> BaseChatModel:
    """Load llm with params."""
    model_type = config.llm_config.model_type

    logger.info(f"Loading {model_type} LLM: {config.llm_config.model_name}")

    if model_type == "groq":
        return ChatGroq(
        model=config.llm_config.model_name, 
        temperature=config.llm_config.temperature
        )
    elif model_type == "local":
        return ChatOllama(
            model=config.llm_config.model_name, 
            temperature=config.llm_config.temperature
        )
    elif model_type == "gemini":
        return ChatGoogleGenerativeAI(
            model=config.llm_config.model_name,
            temperature=config.llm_config.temperature
        )
    elif model_type == "deepseek":
        return ChatDeepSeek(
            model=config.llm_config.model_name,
            temperature=config.llm_config.temperature,
            extra_body={"thinking": {"type": "disabled"}}
        )
    else:
        logger.error(f"Unknown model type: '{model_type}'. Expected 'groq' or 'local'.")
        raise


def create_persona(friend_invite: Optional[FriendInviteModel] = None,
                   verbose: Optional[bool] = None) -> CreatePersonaModel:
    
    def select_country_languages() -> tuple:
        country = random.choice(list(persona_config.countries.keys()))
        mother_language = persona_config.countries[country][1]
        languages = list(set(persona_config.languages_pool) - {mother_language})
        second_languages = random.sample(languages, k=random.randint(0, min(3, len(languages))))

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
        name = friend_invite.friends_name
        common_language_as_native = random.choice([True, False])
        if common_language_as_native:
            mother_language = friend_invite.common_language
        else:
            if second_languages:
                second_languages[random.randint(0, len(second_languages) - 1)] = friend_invite.common_language
            else:
                second_languages.append(friend_invite.common_language)


    also_speak_line = f"You also speak {', '.join(second_languages)}." if second_languages else ''

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

    persona = CreatePersonaModel(
        name=name,
        age=age,
        gender=gender,
        country=country,
        mother_language=mother_language,
        second_languages=second_languages,
        archetype=archetype,
        social_tendency=social_tendency,
        attention_span=attention_span,
        mood=mood,
        is_friend=is_friend,
        url=url,
        system_prompt=prompt_text
    )

    if verbose:
        logger.info(f"Persona created: {persona}")

    return persona


def register(_name: str, _type: Literal["node", "router", "tool"]):
        """Wrapper to add attributes to method."""
        def decorator(func: Callable):
            func._name = _name
            func._type = _type
            return func
        return decorator


def create_map(target, _type: str) -> dict:
    func_map = {}
    for name in dir(target):
        try:
            method = getattr(target, name)
            if callable(method) and hasattr(method, '_type') and getattr(method, '_type') == _type:
                func_map[getattr(method, '_name')] = method
        except Exception:
            continue
    return func_map



llm = load_llm()
_active_walkers = threading.Semaphore(config.walkers_config.active_walkers_limit)
_total_walkers = threading.Semaphore(config.walkers_config.total_walkers_limit)
_all_threads: list[threading.Thread] = []
_threads_lock = threading.Lock()

class VoidWalker():
    """Void Walker."""

    def __init__(self, 
                 friend_invite: Optional[FriendInviteModel] = None,
                 ) -> None:
        """Init Walker."""

        self.driver, self.wait = None, None
        self.tools = []
        self.node_map = {}
        self.router_map = {}

        self.time_limit_min = config.walkers_config.time_limit
        self.actions_limit = config.walkers_config.action_limit
        self.friends_limit =config.walkers_config.friends_limit
        self.verbose = config.walkers_config.verbose
        self.friend_invite = friend_invite

        self.moods = persona_config.moods


        self.state = AgentState()

        # Initialize DB writer with pool
        self.db = DatabaseWriter(self.state.session_id)
        self.db.init_pool()
        


        self.persona = create_persona(friend_invite=friend_invite,
                                      verbose=self.verbose)


        self.llm = llm.bind_tools(tools=self.tools)
        self.node_map = create_map(self, "node")
        self.router_map = create_map(self, "router")
        self.build_graph()


    def __str__(self) -> str:
        return str(self.state)
    

    def _make_tools(self) -> List[StructuredTool]:
        toolkit = WalkerTools(self.driver)
        tool_map = create_map(toolkit, "tool")

        return [
            StructuredTool.from_function(
                func=fn,
                name=name,
                description=fn.__doc__
            )
            for name, fn in tool_map.items()
        ]
    

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
        for key, val in create_map(self, "router").items():
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
    

    def _add_nodes(self) -> None:
        """Add nodes to builder."""
        for name, func in self.node_map.items():
            self.builder.add_node(name, func)
        if self.verbose:
            self.inspect_available()


    def walk(self) -> StateGraph | None:
        """Invoke graph."""
        if not _total_walkers.acquire(blocking=False):
            logger.info(f"Walker limit reached, {self.persona.name} won't walk.")
            return
        try:
            _active_walkers.acquire()
            _active_walkers.release()

            invoke_input = {
                "start_time": datetime.now(),
                "system_prompt": self.persona.system_prompt,
                "mood": self.persona.mood,
                "is_friend": self.persona.is_friend,
                "current_url": self.persona.url,
                "name": self.persona.name,
                "model_name": f"{config.llm_config.model_type}/{config.llm_config.model_name}",
                "model_temperature": config.llm_config.temperature
            }

            if self.friend_invite:
                invoke_input["friend_session_id"] = self.friend_invite.session_id

            response = self.graph.invoke(input=invoke_input)
            self.state = AgentState(**response)

            self.log_persona()
            self.db.flush(self.state)

            if self.verbose:
                logger.info(response)
            return response
        finally:
            _total_walkers.release()
                    

    def to_reflection_context(self, action: ActionModel) -> str:
        """"""
        lines = [f"You performed action: {action.name}"]
        if action.llm_prompt:
            lines.append(f"You considered: {action.llm_prompt}")
        if action.llm_response:
            lines.append(f"You decided: {action.llm_response.answer}")
            lines.append(f"Your reasoning: {action.llm_response.reason}")
        if action.function_result:
            lines.append(f"What happened: {action.function_result} ")
        return "\n".join(lines)


    def log_reflection(self, state: StateGraph, action: ActionModel) -> None:
        self.db.add("reflections", {
                "timestamp": datetime.now(),
                "action_name": state.actions[-1].name,
                "mood_before": state.mood,
                "mood_after": action.llm_response.mood or state.mood,
                "reflection": action.llm_response.reflection
            })
            

    def log_action(self, action: ActionModel) -> None:
        if action.name == "reflect":
            self.db.add("actions", {
            "name": action.name,
            "timestamp": datetime.now(),
            "llm_prompt": action.llm_prompt,
            "llm_answer": action.llm_response.mood,
            "llm_reason": action.llm_response.reflection,
            "function_result": action.function_result
        })

        elif action.name == 'select_action':
            self.db.add("actions", {
            "name": action.name,
            "timestamp": datetime.now(),
            "llm_prompt": action.llm_prompt,
            "llm_answer": action.llm_response.content,
            "llm_reason": None,
            "function_result": action.function_result
        })
            
        else:
            self.db.add("actions", {
            "name": action.name,
            "timestamp": datetime.now(),
            "llm_prompt": action.llm_prompt,
            "llm_answer": action.llm_response.answer if action.llm_response else None,
            "llm_reason": action.llm_response.reason if action.llm_response else None,
            "function_result": action.function_result
        })


    def log_persona(self) -> None:
            
        self.db.add("persona", {
            "timestamp": datetime.now(),
            "name": self.state.name,
            "age": self.persona.age,
            "gender": self.persona.gender,
            "country": self.persona.country,
            "mother_language": self.persona.mother_language,
            "second_languages": self.persona.second_languages,
            "archetype": self.persona.archetype,
            "social_tendency": self.persona.social_tendency,
            "attention_span": self.persona.attention_span,
            "mood": self.persona.mood,
            "is_friend": self.persona.is_friend,
            "system_prompt": self.persona.system_prompt
    })
    

    def log_tool(self, tool_output) -> None:
        if not self.db:
            return

        if tool_output.feedback:
            self.db.add("feedback", {
                "timestamp": datetime.now(),
                "feedback_text": tool_output.feedback
            })
        
        elif tool_output.friend_invite:
            self.db.add("invites", {
                "timestamp": datetime.now(),
                "name": tool_output.friend_invite.name,
                "friends_name": tool_output.friend_invite.friends_name,
                "common_language": tool_output.friend_invite.common_language,
                "shared_url": tool_output.friend_invite.shared_url,
                "message": tool_output.friend_invite.message,
                "friend_session_id": tool_output.friend_invite.friend_session_id
            })
        elif tool_output.message:
            self.db.add("messages", {
                "timestamp": datetime.now(),
                "message": tool_output.message,
                "reply_to": tool_output.reply_to,
                "tool_message": tool_output.tool_message,
                "last_read_messages": tool_output.visible_messages,
                "is_sent": tool_output.tool_message == config.status_config.send_message.on_success
            })

    @register(_type="router", _name="boolean_router")
    def true_false_router(self, state: AgentState) -> bool:
        """Router for True/False decisions."""
        return state.actions[-1].llm_response.answer
    

    @register(_type="router", _name="tool_router")
    def tool_router(self, state: AgentState) -> str:
        last = state.actions[-1].llm_response
        if hasattr(last, 'tool_calls') and last.tool_calls:
            return "execute_tool"
        return "close_website"
    
    
    @register(_type="router", _name="post_action_router")
    def post_action_router(self, state: AgentState) -> str:
        if state.exit_reason is not None:
            return "close_website"
        return "reflect"


    @register(_type="node", _name="decide_open_website")
    def decide_open_node(self, state: AgentState) -> dict:
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
        if response.answer == False:
            return {"actions": action,
                    "exit_reason": "not interested"}
        else:
            return {"actions": action}


    @register(_type="node", _name="initialize_tools")
    def initialize_tools_node(self, state: AgentState) -> dict:
        action = ActionModel(name=self.initialize_tools_node._name, timestamp=datetime.now())
        self.driver, self.wait = configure_chrome()
        self.tools = self._make_tools()
        self.llm = llm.bind_tools(tools=self.tools)
        return {"actions": action}


    @register(_type="node", _name="open_website")
    def open_site_node(self, state: AgentState) -> dict:
        """Node to open website."""
        
        action = ActionModel(name=self.open_site_node._name, timestamp=datetime.now())
        action.function_result = open_site(driver=self.driver, wait=self.wait, url=state.current_url)
        self.log_action(action)
        return {
            "actions": action
        }


    @register(_type="node", _name="close_website")
    def close_website_node(self, state: AgentState) -> dict:
        """Node to close website."""
        action = ActionModel(name=self.close_website_node._name, timestamp=datetime.now())

        action.function_result = close_browser(driver=self.driver)
        self.log_action(action)

        exit_reason = state.exit_reason if state.exit_reason else "decide to close"

        return {
            "actions": action,
            "end_time": datetime.now(),
            "exit_reason": exit_reason
        }
    

    @register(_type="node", _name="observe_website")
    def observe_site_node(self, state: AgentState) -> dict:
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
        self.log_action(action)

        return {
            "actions": action
        }


    @register(_type="node", _name="reflect")
    def reflect_node(self, state: AgentState) -> dict:
            action = ActionModel(name=self.reflect_node._name, timestamp=datetime.now())

            last_action = self.to_reflection_context(state.actions[-1])

            message = ""
            if state.reflection:
                message = f"Previous thoughts: {state.reflection}. "
            
            message += f"Current mood: {state.mood}.\n{last_action}\n"\
            "Reflect on what just happened in your persona's voice. "\
            "Update your internal monologue. If your mood shifted, note the new mood. "\
            f"Choose from: {self.moods}"

            response = self.call_llm(message=message, output_schema=ReflectionModel)

            action.llm_prompt = message
            action.llm_response = response

            self.log_reflection(state, action)
            self.log_action(action)

            return {
                "actions": action,
                "reflection": response.reflection,
                "mood": response.mood or state.mood
                }
    

    @register(_type="node", _name="select_action")
    def select_action_node(self, state: AgentState) -> dict:
        action = ActionModel(name=self.select_action_node._name, timestamp=datetime.now())

        EXCLUDED = {'reflect', 'select_action', 'initialize_tools', 'decide_open_website'}
        action_names = [a.name for a in state.actions if a.name not in EXCLUDED]
        history_line = f"Action history: {action_names}\n"
        recent = [a.name for a in state.actions if a.name not in EXCLUDED][-10:]
        counts = {}
        for name in recent:
            counts[name] = counts.get(name, 0) + 1

        warnings = [f"you've used '{name}' {count} times in your last 10 meaningful actions" 
                    for name, count in counts.items() if count >= 3]

        if warnings:
            history_line += f"Warning: {'; '.join(warnings)}. Try something different.\n"

        message = f"Current reflection: {state.reflection}\n" \
           f"Mood: {state.mood}\n" \
           + history_line + \
           f"Messages you can see: {state.last_read_messages}\n" \
           f"Windows you've opened: {state.opened_windows}\n" \
           f"Messages you sent: {'; '.join([m.message for m in state.sent_messages])}\n" \
           "Decide what to do next."

        response = self.call_llm(message=message)
        action.llm_prompt = message
        action.llm_response = response

        self.log_action(action)

        return {"actions": action}
 

    @register(_type="node", _name="check_conditions")
    def check_conditions_node(self, state: AgentState) -> dict:
        action = ActionModel(name=self.check_conditions_node._name, timestamp=datetime.now())
        elapsed = datetime.now() - state.start_time
        self.log_action(action)
        if len(state.actions) > self.actions_limit:
            return {"exit_reason": "action limit"}
        elif elapsed.total_seconds() >= self.time_limit_min * 60:
            return {"exit_reason": "time limit"}
        # TODO: add summarize
        else:
            return {}
    

    @register(_type="node", _name="execute_tool")
    def execute_tool_node(self, state: AgentState) -> dict:
        last = state.actions[-1].llm_response
        tool_call = last.tool_calls[0]
        tool = {t.name: t for t in self.tools}[tool_call['name']]
        tool_output = ToolOutputModel.model_validate_json(tool.invoke(tool_call['args']))
        action = ActionModel(name=tool_call['name'], 
                            timestamp=datetime.now(), 
                            function_result=tool_output.tool_message)
        
        sent_texts = {m.message for m in state.sent_messages}
        prev_messages = set(state.last_read_messages)
        message_history = sent_texts | prev_messages

        new_messages = [m for m in tool_output.visible_messages if m not in message_history]       

        if tool_output.friend_invite and len(state.invited_friends) < self.friends_limit:
            tool_output.friend_invite.name = state.name
            tool_output.friend_invite.session_id = state.session_id
            tool_output.friend_invite.common_language = random.choice(
                [self.persona.mother_language] + self.persona.second_languages)
            friend = VoidWalker(
                friend_invite=tool_output.friend_invite
            )
            tool_output.friend_invite.friend_session_id = friend.state.session_id
            thread = threading.Thread(target=friend.walk, daemon=True)
            with _threads_lock:
                _all_threads.append(thread)
            thread.start()

        
        
        self.log_tool(tool_output=tool_output)
        self.log_action(action)

        return {"actions": action,
                "last_read_messages": new_messages,
                "sent_messages": tool_output.to_sent_message(),
                "feedback": tool_output.feedback,
                "opened_windows": tool_output.window,
                "invited_friends": tool_output.to_friend_invite(),
                }


    def build_graph(self) -> Any:
        """Build graph."""
        self.builder = StateGraph(AgentState)
        self._add_nodes()

        self.builder.set_entry_point("decide_open_website")
        self.builder.add_conditional_edges("decide_open_website", 
                                      self.true_false_router, {
                                          True: "initialize_tools", 
                                          False: END})
        self.builder.add_edge("initialize_tools", "open_website")
        self.builder.add_edge("open_website", "observe_website")
        self.builder.add_edge("observe_website", "reflect")
        self.builder.add_edge("reflect", "select_action")
        self.builder.add_conditional_edges(
            "select_action", 
            self.tool_router, {
                "execute_tool": "execute_tool",
                "close_website": "close_website"
                })
        self.builder.add_edge("execute_tool", "check_conditions")
        self.builder.add_conditional_edges(
            "check_conditions", 
            self.post_action_router, {
                "close_website": "close_website",
                "reflect": "reflect"
            })
        self.builder.set_finish_point("close_website")
        self.graph = self.builder.compile(debug=self.verbose)

        if self.verbose:
            self.display_graph()


class WalkerTools:
    def __init__(self, driver) -> None:
        self.driver = driver
        

    @register(_type="tool", _name="send_message")
    def send_message(self, 
                    message: Annotated[str, 
                                        "The message you want to send to the void."]) -> ToolOutputModel:
            """Cast a message into the void. 
            Write something true to your persona, mood, and what you've observed. 
            Keep it short and human."""
            tool_output = ToolOutputModel()
            tool_output.visible_messages = read_visible_messages(self.driver)
            tool_output.tool_message = send_message(self.driver, message)
            tool_output.message = message
            
            return tool_output.model_dump_json()
    

    @register(_type="tool", _name="respond_to_message")
    def respond_to_message(self,
                           reply_to: Annotated[str, "Exact text of the message you are replying to."],
                           reply: Annotated[str, "Your reply. Keep it natural and in character."]) -> str:
        """Reply to a specific message you can see in the void."""
        tool_output = ToolOutputModel()
        tool_output.reply_to = reply_to
        tool_output.message = reply
        tool_output.visible_messages = read_visible_messages(self.driver)
        tool_output.tool_message = send_message(self.driver, reply)
        

        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="press_explore")
    def explore(self) -> str:
        """Teleport to a random location in the void. 
        Use when you want to discover new messages elsewhere."""        
        tool_output = ToolOutputModel()
        tool_output.tool_message = press_explore(self.driver)
        tool_output.visible_messages = read_visible_messages(self.driver)
            
        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="move_around")
    def move(self,
             dx: Annotated[int, "Horizontal distance. Negative moves left, positive moves right."],
             dy: Annotated[int, "Vertical distance. Negative moves up, positive moves down."]) -> str:
        """Drift from your current position to see nearby messages. 
        Small values for subtle movement, large for bigger jumps."""
        tool_output = ToolOutputModel()
        tool_output.tool_message = move_around(self.driver, dx, dy)
        tool_output.visible_messages = read_visible_messages(self.driver)
            
        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="open_window")
    def open_window(self, 
                    window: Annotated[Literal['about', 'support', 'terms'], "Panel to open."]) -> str:
        """Open one of the site's info panels and read its contents."""
        tool_output = ToolOutputModel()
        tool_output.tool_message = interact_with_modal(driver=self.driver, modal_name=window)
        tool_output.window = window
        tool_output.visible_messages = read_visible_messages(self.driver)

        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="send_feedback")
    def send_feedback(self, 
                      feedback: Annotated[str, "Your thoughts about the site. Speak as yourself."]) -> str:
        """Leave feedback about your experience on void-cast. Reflect honestly as your persona."""
        tool_output = ToolOutputModel()
        tool_output.feedback = feedback
        tool_output.tool_message = "Your thoughts have been noted."
        tool_output.visible_messages = read_visible_messages(self.driver)

        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="invite_friend")
    def invite_friend(self, 
                    friends_name: Annotated[str, "Name of someone you know. Can be real or made up—just pick any name."],
                    message: Annotated[str, "What you'd say to get them to join you here."]):
        """Call out to someone you know. 
        Even if they're not really there, the act of calling feels good."""
        url = press_share(self.driver)
        invite = FriendInviteModel(
            shared_url=url,
            message=message,
            friends_name=friends_name
        )
        tool_output = ToolOutputModel()
        tool_output.message = message
        tool_output.tool_message = "Your friend has been invited to the void."
        tool_output.visible_messages = read_visible_messages(self.driver)
        tool_output.friend_invite = invite

        return tool_output.model_dump_json()
    

    @register(_type="tool", _name="check_new_messages")
    def check_new_messages(self) -> str:
        """Look around and read any messages currently visible in the void. If you've already checked and seen nothing new, do something else instead."""
        tool_output = ToolOutputModel()
        messages = read_visible_messages(self.driver)
        tool_output.visible_messages = messages
        tool_output.tool_message = "You look around the void"

        return tool_output.model_dump_json()


def run_walkers(n: Optional[int] = 1):
    """Run walkers."""
    threads = []
    for _ in range(n):
        walker = VoidWalker()
        thread = threading.Thread(target=walker.walk, daemon=True)
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join()
    with _threads_lock:
        friend_threads = list(_all_threads)
    for t in friend_threads:
        t.join()
    gc.collect()
