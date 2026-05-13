"""Pydantic models."""

import textwrap
from datetime import datetime
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# -----------------------------------------------
# Congiguration Models
# -----------------------------------------------
class StatusMessageModel(BaseModel):
    """Model for selenuim functions status."""
    on_success: str = 'OK'
    on_fail: str = 'Failed'


class StatusConfigModel(BaseModel):
    """Model for status configurations."""
    configure_chrome: Optional[StatusMessageModel] = StatusMessageModel()
    open_site: Optional[StatusMessageModel] = StatusMessageModel()
    close_browser: Optional[StatusMessageModel] = StatusMessageModel()
    press_explore: Optional[StatusMessageModel] = StatusMessageModel()
    press_share: Optional[StatusMessageModel] = StatusMessageModel()
    input_message: Optional[StatusMessageModel] = StatusMessageModel()
    press_submit: Optional[StatusMessageModel] = StatusMessageModel()
    validate_cast_input: Optional[StatusMessageModel] = StatusMessageModel()
    send_message: Optional[StatusMessageModel] = StatusMessageModel()
    clear_input: Optional[StatusMessageModel] = StatusMessageModel()
    read_visible_messages: Optional[StatusMessageModel] = StatusMessageModel()
    check_available_modals: Optional[StatusMessageModel] = StatusMessageModel()
    open_modal: Optional[StatusMessageModel] = StatusMessageModel()
    close_modal: Optional[StatusMessageModel] = StatusMessageModel()
    read_modal_content: Optional[StatusMessageModel] = StatusMessageModel()
    interact_with_modal: Optional[StatusMessageModel] = StatusMessageModel()
    move_around: Optional[StatusMessageModel] = StatusMessageModel()


class LLMConfigModel(BaseModel):
    """Model for LLM configurations."""
    model_type: Literal["local", "groq", "gemini", "deepseek"] = "local"
    temperature: Optional[float] = 0.5
    model_name: Optional[str] = "llama3.2:3b"


class WalkerConfigModel(BaseModel):
    """Model for VoidWalker configurations."""
    verbose: Optional[bool] = False
    action_limit: Optional[int] = 50
    friends_limit: Optional[int] = 1
    active_walkers_limit: Optional[int] = 3
    total_walkers_limit: Optional[int] = 5
    time_limit: Optional[int] = 10


class ConfigModel(BaseModel):
    """Model for configurations."""
    root_url: str = "https://void-cast.fly.dev/"
    status_config: Optional[StatusConfigModel] = StatusConfigModel()
    wait_timeout: Optional[int] = 10
    site_description: Optional[str] = ""
    llm_config: Optional[LLMConfigModel] = LLMConfigModel()
    walkers_config: Optional[WalkerConfigModel] = WalkerConfigModel()


class PersonaConfigModel(BaseModel):
    """LLM Persona Model."""
    archetypes: dict
    moods: list
    social_tendencies: list
    attention_spans: list
    generations: dict
    countries: dict
    languages_pool: list
    genders: list
    names: dict


# -----------------------------------------------
# VoidWalker Models
# -----------------------------------------------

# ~~~~~~~~~~~~~~~~~~ Persona ~~~~~~~~~~~~~~~~~~
class CreatePersonaModel(BaseModel):
    """Persona model."""
    name: str
    age: int
    gender: str
    country: str
    mother_language: str
    second_languages: Optional[list[str]] = []
    archetype: str
    archetype_description: str
    generation: str
    social_tendency: str
    attention_span: str
    mood: str
    is_friend: bool
    url: str
    system_prompt: str
    friend_message: Optional[str] = None
    friend_name: Optional[str] = None

    def __str__(self) -> str:
        lines = self.system_prompt.split('\n')
        header = '\n'.join(lines[:6])
        wrapped = textwrap.fill(
            header,
            width=80,
            break_long_words=False,
            break_on_hyphens=False)
        return (
            f"\n\n{wrapped}\n"
            f"Mood: {self.mood}\n"
            f"Friend: {self.is_friend}\n"
            f"URL: {self.url}\n\n")


# ~~~~~~~~~~~~~~~~~~ LLM response schemas ~~~~~~~~~~~~~~~~~~

class YesNoModel(BaseModel):
    """LLM Answer model for binary questions."""
    answer: bool = Field(
        description="Decision: true to proceed, false to decline")
    reason: str = Field(description="Please explain your decision")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())

class AnswerModel(BaseModel):
    """Basic LLM Answer model."""
    answer: str = Field(description="The answer or decision made")
    reason: str = Field(description="The reasoning behind the answer")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())

class SelectToolModel(BaseModel):
    """LLM Answer model for tool selection."""
    answer: str = Field(description="Next action:")
    reason: str = Field(description="The reasoning behind the answer")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())

class ReflectionModel(BaseModel):
    """LLM Answer model for reflection node."""
    reflection: str = Field(
        description=(
            "Your inner monologue after the action, "
            "written in your persona's voice"))
    mood: str = Field(description="Your current mood after reflecting")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())

class GenderPrediction(BaseModel):
    """Predicted gender from a given name."""
    gender: Literal["male", "female"] = Field(
        description="The predicted gender of the name")
    confidence: float = Field(
        description="Confidence score between 0 and 1")

# ~~~~~~~~~~~~~~~~~~ State attributes ~~~~~~~~~~~~~~~~~~

class ActionModel(BaseModel):
    """Action model for graph."""
    name: str
    timestamp: datetime
    llm_prompt: Optional[str] = None
    llm_response: Optional[
        Union[YesNoModel, AnswerModel, ReflectionModel]] = None
    function_result: Optional[str] = None

    def __str__(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.__dict__.items())

    @field_validator('llm_response', mode='before')
    @classmethod
    def validate_llm_response(cls, v) -> AnswerModel:
        if not isinstance(v, dict) or not v:
            return v
        if 'answer' in v and isinstance(v['answer'], bool):
            return YesNoModel(**v)
        if 'reflection' in v:
            return ReflectionModel(**v)
        return AnswerModel(**v)


class FriendInviteModel(BaseModel):
    """Friend invite model."""
    name: Optional[str] = None
    friends_name: Optional[str] = None
    friend_session_id: Optional[str] = None
    shared_url: str
    message: str
    common_language: Optional[str] = None
    session_id: Optional[str] = None


class SentMessageModel(BaseModel):
    """Send message model."""
    message: str
    reply_to: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ~~~~~~~~~~~~~~~~~~ Reducers ~~~~~~~~~~~~~~~~~~

def add_actions(
        left: list[ActionModel],
        right: list[ActionModel] | ActionModel) -> list[ActionModel]:
    """Reducer to add new actions."""
    if isinstance(right, list):
        return left + right
    return left + [right]

def append_str(
        left: list[str],
        right: str | list[str]) -> list[str]:
    """Reduced to add new string or a list of strings."""
    if right is None:
        return left
    if isinstance(right, str):
        return left + [right]
    return left + right


def append_message(
        left: list[SentMessageModel],
        right: Optional[SentMessageModel]) -> list[SentMessageModel]:
    """Reduced to append new message."""
    if right is None or not right.message:
        return left
    return left + [right]


def append_friend(
        left: list[FriendInviteModel],
        right: Optional[FriendInviteModel]) -> list[FriendInviteModel]:
    """Reducer to append new frien invites."""
    if right is None:
        return left
    return left + [right]


# ~~~~~~~~~~~~~~~~~~ Tool output ~~~~~~~~~~~~~~~~~~

class ToolOutputModel(BaseModel):
    """Tool output model."""
    reply_to: Optional[str] = None
    message: Optional[str] = None
    tool_message: Optional[str] = None
    current_url: Optional[str] = None
    visible_messages: Optional[List[str]] = []
    window: Optional[str] = None
    friend_invite: Optional[FriendInviteModel] = None
    feedback: Optional[str] = None

    def to_sent_message(self) -> SentMessageModel | None:
        if not self.message:
            return None
        return SentMessageModel(message=self.message,
                                reply_to=self.reply_to)


    def to_friend_invite(self) -> FriendInviteModel | None:
        if not self.friend_invite:
            return None
        return self.friend_invite



# ~~~~~~~~~~~~~~~~~~ Agent State ~~~~~~~~~~~~~~~~~~

class AgentState(BaseModel):
    """LLM Agent State."""

    # Session
    session_id: Optional[str] = None
    parent_session_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    model_name: Optional[str] = None
    model_temperature: Optional[float] = None

    # Persona
    name: Optional[str] = None
    mood: Optional[str] = None
    system_prompt: Optional[str] = None

    # Position
    initial_url: Optional[str] = None
    current_url: Optional[str] = None

    # Reasoning
    exit_reason: Optional[str] = None
    summary: Optional[str] = None
    reflection: Optional[str] = None
    feedback: Annotated[list[str], append_str] = []

    # Social
    is_friend: Optional[bool] = None
    invited_friends: Annotated[list[FriendInviteModel], append_friend] = []

    # Messages
    sent_messages: Annotated[list[SentMessageModel], append_message] = []
    last_read_messages: List[str] = []

    # Actions
    actions: Annotated[list[ActionModel], add_actions] = []
    opened_windows: Annotated[list[str], append_str] = []
    learned_map: Annotated[list[str], append_str]

    def __str__(self) -> str:
        lines = []
        separator = '─' * 60
        for k, v in self.__dict__.items():
            if isinstance(v, list):
                lines.append(f"\n{k}:")
                for item in v:
                    indented = (
                        "\n".join(f"  {line}"
                                  for line in str(item).splitlines()))
                    lines.append(indented)
                    lines.append("  " + "·" * 40)
            else:
                lines.append(f"{k}: {v}")
                lines.append(separator)
        return "\n".join(lines)


    @field_validator('actions', mode='before')
    @classmethod
    def validate_actions(cls, v) -> list:
        return [ActionModel(**a) if isinstance(a, dict) else a for a in v]
