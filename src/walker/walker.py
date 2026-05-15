"""Void Walker."""

import logging
import random
import subprocess
import threading
import uuid
from collections import Counter
from datetime import datetime
from inspect import signature
from typing import List, Optional

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools.structured import StructuredTool
from langgraph.graph import StateGraph
from pydantic import BaseModel

from src.db.db_writer import DatabaseWriter
from src.models import (
    ActionModel,
    AgentState,
    AnswerModel,
    FriendInviteModel,
    ReflectionModel,
    SummaryModel,
    ToolOutputModel,
    YesNoModel,
)
from src.selenium.helpers import (
    close_browser,
    configure_chrome,
    open_site,
    read_visible_messages,
)
from src.setup import config, lessons_config, persona_config
from src.walker.persona import create_persona
from src.walker.tools import WalkerTools
from src.walker.utils import (
    create_map,
    load_llm,
    publish_current_url,
    publish_session,
    publish_state,
    register,
    remove_session,
)

logger = logging.getLogger(__name__)


llm = load_llm()
_active_walkers = threading.Semaphore(
    config.walkers_config.active_walkers_limit)
_total_walkers = threading.Semaphore(
    config.walkers_config.total_walkers_limit)
_all_threads: list[threading.Thread] = []
_threads_lock = threading.Lock()


class VoidWalker():
    """Void Walker."""

    def __init__(self,
                 friend_invite: Optional[FriendInviteModel] = None,
                 ) -> None:
        """Init Walker."""

        self.driver, self.wait = None, None
        self.state = None
        self.tools = []
        self.node_map = {}
        self.router_map = {}

        self.time_limit_min = config.walkers_config.time_limit
        self.actions_limit = config.walkers_config.action_limit
        self.friends_limit = config.walkers_config.friends_limit
        self.verbose = config.walkers_config.verbose
        self.friend_invite = friend_invite

        self.moods = persona_config.moods


        self.session_id = uuid.uuid1().hex

        # Initialize DB writer with pool
        self.db = DatabaseWriter()
        self.db.init_pool()



        self.persona = create_persona(friend_invite=friend_invite,
                                      verbose=self.verbose)


        self.llm = llm.bind_tools(tools=self.tools)
        self.node_map = create_map(self, "node")
        self.router_map = create_map(self, "router")
        self.build_graph()


    def __str__(self) -> str:
        """Define print style."""
        return str(self.state)


    def _make_tools(self) -> List[StructuredTool]:
        """Create structured tools."""
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


    def call_llm(self,
                 message: str,
                 output_schema: BaseModel = None) -> AIMessage | BaseModel:
        """Call llm with system prompt and message."""
        mood = self.state.mood if self.state else self.persona.mood
        messages = [
            SystemMessage(self.persona.system_prompt),
            SystemMessage(f"You are feeling {mood} right now."),
            HumanMessage(message)]
        llm = (self.llm.with_structured_output(output_schema)
               if output_schema
               else self.llm)
        return llm.invoke(messages)


    def inspect_available(
            self,
            state_name: str = "state",
            ignore_state: bool = False) -> None:
        """Return available nodes, routers and tools."""

        logger.info("Available nodes:")
        for key, val in self.builder.nodes.items():
            func_name = val.runnable.func.__name__
            params = [
                str(v)
                for v in signature(val.runnable.func).parameters.values()]
            if ignore_state:
                params = filter(
                    lambda x: x.split(':')[0].strip() != state_name, params)
            logger.info(
                f"\t— node: {key}, function: {func_name}({', '.join(params)})")

        logger.info("Available routers:")
        for key, val in create_map(self, "router").items():
            params = [str(v) for v in signature(val).parameters.values()]
            if ignore_state:
                params = filter(
                    lambda x: x.split(':')[0].strip() != state_name, params)
            p = ', '.join(params)
            logger.info(f"\t— router: {key}, function: {val.__name__}({p})")

        logger.info("Available tools:")
        for key, val in create_map(self, "tool").items():
            params = [str(v) for v in signature(val).parameters.values()]
            if ignore_state:
                params = filter(
                    lambda x: x.split(':')[0].strip() != state_name, params)
            p = ', '.join(params)
            logger.info(f"\t— router: {key}, function: {val.__name__}({p})")


    def display_graph(self) -> None:
        """Draw VoidWalker's graph."""
        mermaid_text = self.graph.get_graph().draw_mermaid()
        try:
            from IPython import get_ipython
            if get_ipython() is not None:
                from IPython.display import Image, display
                display(Image(self.graph.get_graph().draw_mermaid_png()))
                return
        except ImportError:
            pass
        result = subprocess.run(['mermaid-ascii', '-f', '-'],
                                input=mermaid_text,
                                capture_output=True,
                                text=True)
        logger.info(result.stdout)


    def _add_nodes(self) -> None:
        """Add nodes to builder."""
        for name, func in self.node_map.items():
            self.builder.add_node(name, func)
        if self.verbose:
            self.inspect_available()


    def walk(self) -> None:
        """Invoke graph."""
        if not _total_walkers.acquire(blocking=False):
            logger.info(
                f"Walker limit reached, {self.persona.name} won't walk.")
            return

        invoke_input = {
                "session_id": self.session_id,
                "start_time": datetime.now(),
                "system_prompt": self.persona.system_prompt,
                "mood": self.persona.mood,
                "is_friend": self.persona.is_friend,
                "initial_url": self.persona.url,
                "current_url": self.persona.url,
                "name": self.persona.name,
                "model_name":
            f"{config.llm_config.model_type}/{config.llm_config.model_name}",
                "model_temperature": config.llm_config.temperature
            }
        if self.friend_invite:
            invoke_input['parent_session_id'] = self.friend_invite.session_id

        try:
            logger.info(f"Start walker with session_id: {self.session_id[:8]}")
            _active_walkers.acquire()
            try:
                publish_session(session_id=self.session_id)
                publish_current_url(session_id=self.session_id,
                                    current_url=self.persona.url)
                response = self.graph.invoke(input=invoke_input)
                remove_session(session_id=self.session_id)
                self.state = AgentState(**response)
                self.log_persona()
                self.db.flush(self.state)
                if self.verbose:
                    logger.info(response)
            finally:
                _active_walkers.release()
        finally:
            _total_walkers.release()


    def to_reflection_context(self, action: ActionModel) -> str:
        """Create reflection context."""
        lines = [f"You performed action: {action.name}"]
        if action.llm_prompt:
            lines.append(f"You considered: {action.llm_prompt}")
        if action.llm_response:
            lines.append(f"You decided: {action.llm_response.answer}")
            lines.append(f"Your reasoning: {action.llm_response.reason}")
        if action.function_result:
            lines.append(f"What happened: {action.function_result} ")
        return "\n".join(lines)


    def to_lesson(self, tool_name: str, tool_output: ToolOutputModel) -> set:
        """Add lesson based on tool result."""
        lessons = set()
        if tool_name == "open_window":
            lessons.add(lessons_config[tool_output.window])
        elif tool_name == "move_around":
            lessons.add(lessons_config["move_around"])
        elif tool_name == "press_explore":
            lessons.add(lessons_config["press_explore"])
        elif tool_name == "invite_friend":
            lessons.add(lessons_config["invite_friend"])
        elif tool_name in {"respond_to_message", "send_message"}:
            lessons.add(lessons_config["messages"])
            on_success = config.status_config.send_message.on_success
            if (tool_output.tool_message != on_success):
                error = ("message_frequency_limit"
                         if "too many" in tool_output.tool_message
                         else "message_char_limit")
                lessons.add(lessons_config[error])
        return lessons


    def log_reflection(self, state: StateGraph, action: ActionModel) -> None:
        """Add reflection to db queue."""
        self.db.add("reflections", {
                "timestamp": datetime.now(),
                "action_name": state.actions[-1].name,
                "mood_before": state.mood,
                "mood_after": action.llm_response.mood or state.mood,
                "reflection": action.llm_response.reflection
            })


    def log_action(self, action: ActionModel) -> None:
        """Add action to db queue."""
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
            "llm_answer": (action.llm_response.answer if action.llm_response
                           else None),
            "llm_reason": (action.llm_response.reason if action.llm_response
                           else None),
            "function_result": action.function_result
        })


    def log_persona(self) -> None:
        """Add persona to db queue."""

        self.db.add("persona", {
            "timestamp": datetime.now(),
            "name": self.state.name,
            "age": self.persona.age,
            "generation": self.persona.generation,
            "gender": self.persona.gender,
            "country": self.persona.country,
            "mother_language": self.persona.mother_language,
            "second_languages": self.persona.second_languages,
            "archetype": self.persona.archetype,
            "archetype_description": self.persona.archetype_description,
            "social_tendency": self.persona.social_tendency,
            "attention_span": self.persona.attention_span,
            "mood": self.persona.mood,
            "is_friend": self.persona.is_friend,
            "system_prompt": self.persona.system_prompt
    })


    def log_tool(self, tool_output) -> None:
        """Add tool to db queue."""
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
                "friend_session_id":
                    tool_output.friend_invite.friend_session_id
            })
        elif tool_output.message:
            self.db.add("messages", {
                "timestamp": datetime.now(),
                "message": tool_output.message,
                "reply_to": tool_output.reply_to,
                "tool_message": tool_output.tool_message,
                "last_read_messages": tool_output.visible_messages,
                "is_sent":
    tool_output.tool_message == config.status_config.send_message.on_success
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
        action = ActionModel(name=self.decide_open_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        if state.is_friend:
            message = (
                f"Your friend {self.persona.friend_name} "
                "sent you an invite to void-cast. "
                f"They wrote: \n{self.persona.friend_message}")
        else:
            message = "You just heard about a website called void-cast."

        message += (
            "It's a dark infinite canvas "
            "where people leave anonymous messages. "
            "Do you feel like check it out?")
        response = self.call_llm(message=message, output_schema=YesNoModel)
        action.llm_prompt = message
        action.llm_response = response
        self.log_action(action)
        if not response.answer:
            return {"actions": action,
                    "exit_reason": "not interested"}
        else:
            return {"actions": action}


    @register(_type="node", _name="initialize_tools")
    def initialize_tools_node(self, state: AgentState) -> dict:
        """Node to initialize browser and llm tools."""
        action = ActionModel(name=self.initialize_tools_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)


        self.driver, self.wait = configure_chrome()
        self.tools = self._make_tools()
        self.llm = llm.bind_tools(tools=self.tools)
        return {"actions": action}


    @register(_type="node", _name="open_website")
    def open_site_node(self, state: AgentState) -> dict:
        """Node to open website."""
        action = ActionModel(name=self.open_site_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        action.function_result = open_site(driver=self.driver,
                                           wait=self.wait,
                                           url=state.initial_url)
        self.log_action(action)
        return {
            "actions": action,
            "last_read_messages": read_visible_messages(self.driver)
        }


    @register(_type="node", _name="close_website")
    def close_website_node(self, state: AgentState) -> dict:
        """Node to close website and browser."""
        action = ActionModel(name=self.close_website_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        action.function_result = close_browser(driver=self.driver)
        self.log_action(action)

        exit_reason = (state.exit_reason if state.exit_reason
                       else "decide to close")

        return {
            "actions": action,
            "end_time": datetime.now(),
            "exit_reason": exit_reason
        }


    @register(_type="node", _name="observe_website")
    def observe_site_node(self, state: AgentState) -> dict:
        """Node to give Walker context about website."""
        action = ActionModel(name=self.observe_site_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        message = (
            "You just opened void-cast. "
            "You see a dark infinite canvas "
            "with messages drifting through it. "
            "At the bottom you have an input bar to cast messages "
            "into the void, a share button, "
            "and an explore button to teleport to a random location. "
            "In the top right there are modals: about, support and terms. "
            "Take a moment to take it all in.")
        response = self.call_llm(message=message, output_schema=AnswerModel)
        action.llm_prompt = message
        action.llm_response = response
        self.log_action(action)

        return {
            "actions": action
        }


    @register(_type="node", _name="reflect")
    def reflect_node(self, state: AgentState) -> dict:
            """Reflection node where Walker can change it's mood."""
            action = ActionModel(name=self.reflect_node._name,
                                 timestamp=datetime.now())
            publish_state(session_id=state.session_id, state=state)

            last_action = self.to_reflection_context(state.actions[-1])

            message = ""
            if state.reflection:
                message = f"Previous thoughts: {state.reflection}. "

            message += (
                f"Current mood: {state.mood}.\n{last_action}\n"
                "Reflect on what just happened in your persona's voice. "
                "Update your internal monologue. "
                "If your mood shifted, note the new mood. "
                f"Choose from: {self.moods}")

            response = self.call_llm(message=message,
                                     output_schema=ReflectionModel)

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
        """Select next tool/action node."""
        action = ActionModel(name=self.select_action_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        EXCLUDED = {'reflect', 'select_action',
                    'initialize_tools', 'decide_open_website'}
        action_names = [
            a.name for a in state.actions if a.name not in EXCLUDED]

        recent = action_names[-10:]
        counts = {}
        for name in recent:
            counts[name] = counts.get(name, 0) + 1

        msgs = '; '.join([
            f'(reply to: {m.reply_to}\nmessage: "{m.message}")' if m.reply_to
            else f'(message: "{m.message})"\n'
            for m in state.sent_messages])
        friends = ', '.join([
            invite.friends_name for invite in state.invited_friends])

        warnings = [
            (f"you've used '{name}' {count} "
             "times in your last 10 meaningful actions")
            for name, count in counts.items() if count >= 3]

        warnings = (f"\n\nWarning: {'; '.join(warnings)}. "
                    "Try something different.") if warnings else ""

        lessons = "\n".join(state.learned_lessons)
        friend = (
            ("Friend that invited you:"
             f"{self.persona.friend_name} - {self.persona.friend_message}\n")
            if state.is_friend
            else "")
        message = (
            "LESSONS YOU'VE LEARNED:\n\n"
            f"{lessons}"
            "CURRENT STATE:\n\n"
            f"- Action history: [{action_names}]\n"
            f"- Messages you can see: {state.last_read_messages}\n"
            f"- Messages you've sent: [{msgs}]\n"
            f"- Windows you've opened: {state.opened_windows}\n"
            f"- Friends you've invited: {friends}\n"
            f"{friend}"
            f"- Current reflection: {state.reflection}\n\n"
            "Decide what to do next.")

        message += warnings


        response = self.call_llm(message=message)
        action.llm_prompt = message
        action.llm_response = response

        self.log_action(action)

        return {"actions": action}


    @register(_type="node", _name="check_conditions")
    def check_conditions_node(self, state: AgentState) -> dict:
        """Node to check exit conditions."""
        action = ActionModel(name=self.check_conditions_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        elapsed = datetime.now() - state.start_time
        n_actions = len(state.actions)
        self.log_action(action)
        logger.info(
                f"{self.actions_limit - n_actions} till action limit for "
                f"walker {self.session_id[:8]}.")
        if n_actions > self.actions_limit:
            return {"exit_reason": "action limit"}
        elif elapsed.total_seconds() >= self.time_limit_min * 60:
            return {"exit_reason": "time limit"}
        else:
            return {}


    @register(_type="node", _name="execute_tool")
    def execute_tool_node(self, state: AgentState) -> dict:
        """Execute selected tool."""
        last = state.actions[-1].llm_response

        tool_call = last.tool_calls[0]
        tool = {t.name: t for t in self.tools}[tool_call['name']]

        tool_output = tool.invoke(tool_call['args'])

        tool_output = ToolOutputModel.model_validate_json(tool_output)


        action = ActionModel(
            name=tool_call['name'],
            timestamp=datetime.now(),
            function_result=tool_output.tool_message)

        publish_state(session_id=state.session_id, state=state)
        publish_current_url(
            session_id=self.session_id,
            current_url=tool_output.current_url or state.current_url)

        if (
            tool_output.friend_invite
            and not state.is_friend
            and len(state.invited_friends) < self.friends_limit):

            tool_output.friend_invite.name = state.name
            tool_output.friend_invite.session_id = state.session_id
            tool_output.friend_invite.common_language = random.choice(
                [self.persona.mother_language] + self.persona.second_languages)
            friend = VoidWalker(
                friend_invite=tool_output.friend_invite
            )
            tool_output.friend_invite.friend_session_id = friend.session_id
            thread = threading.Thread(target=friend.walk, daemon=False)
            with _threads_lock:
                _all_threads.append(thread)
            thread.start()



        self.log_tool(tool_output=tool_output)
        self.log_action(action)

        return {"actions": action,
                "last_read_messages": tool_output.visible_messages,
                "sent_messages": tool_output.to_sent_message(),
                "feedback": tool_output.feedback,
                "opened_windows": tool_output.window,
                "invited_friends": tool_output.to_friend_invite(),
                "current_url": tool_output.current_url or state.current_url,
                "learned_lessons": self.to_lesson(tool_name=tool_call['name'],
                                                  tool_output=tool_output)
                }


    @register(_type="node", _name="summarize")
    def summarize_node(self, state: AgentState) -> dict:
        """Summarize on exit node."""
        action = ActionModel(name=self.summarize_node._name,
                             timestamp=datetime.now())
        publish_state(session_id=state.session_id, state=state)

        invited_friends = [f.friends_name for f in state.invited_friends]

        skip_actions = {"summarize",
                        "initialize_tools",
                        'select_action',
                        'reflect',
                        'check_conditions'}
        actions = [a.name for a in state.actions if a.name not in skip_actions]
        actions = ', '.join([f"{k} ({v}x)"
                             for k, v in Counter(actions).items()])
        last_action = state.actions[-1]

        question = (
            "Why did you choose to leave?"
            if state.exit_reason == 'decide to close'
            else
            "Why are you leaving? (The void ended your time.)")

        message = (
            f"Your session is ending. Reflect on your time in the void.\n\n"
            f"Facts:\n"
            f"- Messages sent: {[m.message for m in state.sent_messages]}\n"
            f"- Windows opened: {state.opened_windows}\n"
            f"- Friends invited: {invited_friends}\n"
            f"- Actions you took: {actions}\n"
            f"- Exit reason: {state.exit_reason}\n\n"
            "Write a short summary answering:\n"
            "What you actually did (factual, 2-3 sentences). "
            "How it felt, in your own voice (personal, 2-3 sentences). "
            f"{question}\n"
            "Keep it honest and true to your persona.")

        if state.exit_reason == "not interested":
            message = (
                "You chose not to enter the void."
                f"You considered: {last_action.llm_prompt}"
                f"You decided: {last_action.llm_response.answer}"
                f"Your reasoning: {last_action.llm_response.reason}"
                "Answer these question:"
                "- How did you feel when you saw the void?"
                "- Why did you reject it?"
                )

        response = self.call_llm(message=message, output_schema=SummaryModel)
        action.llm_prompt = message
        action.llm_response = response
        self.log_action(action)

        return {
            "actions": action,
            "summary": response.answer
        }


    def build_graph(self) -> None:
        """Build graph."""
        self.builder = StateGraph(AgentState)
        self._add_nodes()

        self.builder.set_entry_point("decide_open_website")
        self.builder.add_conditional_edges("decide_open_website",
                                      self.true_false_router, {
                                          True: "initialize_tools",
                                          False: "summarize"})
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
        self.builder.add_edge("close_website", "summarize")
        self.builder.set_finish_point("summarize")
        self.graph = self.builder.compile(debug=self.verbose)

        if self.verbose:
            self.display_graph()


