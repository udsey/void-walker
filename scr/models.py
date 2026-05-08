from datetime import datetime
import textwrap
from typing import Annotated, List, Literal, Optional, Any, Set, Union
from langchain.messages import AnyMessage
from pydantic import BaseModel, Field, field_validator
from langchain_core.prompts import ChatPromptTemplate
from selenium.webdriver import Chrome
from selenium.webdriver.support.wait import WebDriverWait
import uuid


class StatusMessageModel(BaseModel):
    on_success: str = 'OK'
    on_fail: str = 'Failed'


class StatusConfigModel(BaseModel):
    configure_chrome: Optional[StatusMessageModel] = None
    open_site: Optional[StatusMessageModel] = None
    close_browser: Optional[StatusMessageModel] = None
    press_explore: Optional[StatusMessageModel] = None
    press_share: Optional[StatusMessageModel] = None
    input_message: Optional[StatusMessageModel] = None
    press_submit: Optional[StatusMessageModel] = None
    validate_cast_input: Optional[StatusMessageModel] = None
    send_message: Optional[StatusMessageModel] = None
    clear_input: Optional[StatusMessageModel] = None
    read_visible_messages: Optional[StatusMessageModel] = None
    check_available_modals: Optional[StatusMessageModel] = None
    open_modal: Optional[StatusMessageModel] = None
    close_modal: Optional[StatusMessageModel] = None
    read_modal_content: Optional[StatusMessageModel] = None
    interact_with_modal: Optional[StatusMessageModel] = None
    move_around: Optional[StatusMessageModel] = None
    

    def model_post_init(self, __context: Any) -> None:
        for field in StatusConfigModel.model_fields:
            if getattr(self, field) is None:
                setattr(self, field, StatusMessageModel())

class LLMConfigModel(BaseModel):
    model_type: Literal["local", "groq", "gemini", "deepseek"] = "local"
    temperature: Optional[float] = 1
    model_name: Optional[str] = "llama3.2:3b"
    
class ConfigModel(BaseModel):
    root_url: str = "https://void-cast.fly.dev/"
    status_config: Optional[StatusConfigModel] = None
    wait_timeout: Optional[int] = 10
    site_description: Optional[str] = ""
    llm_config: Optional[LLMConfigModel] = None

    def model_post_init(self, __context: Any) -> None:
        if self.status_config is None:
            self.status_config = StatusConfigModel()
        if self.site_description is None:
            self.site_description = ""
        if self.llm_config is None:
            self.llm_config = LLMConfigModel()


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
    names: Optional[dict] = {}


class YesNoModel(BaseModel):
    answer: bool = Field(description="Decision: true to proceed, false to decline")
    reason: str = Field(description="Please explain your decision")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())


class AnswerModel(BaseModel):
    answer: str = Field(description="The answer or decision made")
    reason: str = Field(description="The reasoning behind the answer")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())

class SelectToolModel(BaseModel):
    answer: str = Field(description="Next action:")
    reason: str = Field(description="The reasoning behind the answer")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())




class ReflectionModel(BaseModel):
    reflection: str = Field(description="Your inner monologue after the action, written in your persona's voice")
    mood: str = Field(description=f"Your current mood after reflecting")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())


class SelectOutstandingModel(BaseModel):
    messages: list = Field(description="Select outstanding messages based on your mood.")
    reason: str = Field(description="The reasoning behind the answer")

    def __str__(self) -> str:
        space = " " * 14
        return f"\n{space}".join(f"{k}: {v}" for k, v in self.__dict__.items())


class ActionModel(BaseModel):
    name: str
    timestamp: datetime
    llm_prompt: str | None = None
    llm_response: Optional[Union[YesNoModel, AnswerModel, ReflectionModel]] = None
    function_result: str | None = None

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


class FriendMessageModel(BaseModel):
    name: str
    message: str


class FriendInviteModel(BaseModel):
    name: str
    shared_url: str
    message: str

class CreatePersonaModel(BaseModel):
    system_prompt: str
    mood: str
    is_friend: bool
    url: str

    def __str__(self) -> str:
        lines = self.system_prompt.split('\n')
        header = '\n'.join(lines[:6])
        wrapped = textwrap.fill(header, width=80, break_long_words=False, break_on_hyphens=False)
        return f"\n\n{wrapped}\nMood: {self.mood}\nFriend: {self.is_friend}\nURL: {self.url}\n\n"


class SentMessageModel(BaseModel):
    message: str
    reply_to: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


def add_actions(left: list[ActionModel], right: list[ActionModel] | ActionModel) -> list[ActionModel]:
    """Reducer to add new actions."""
    if isinstance(right, list):
        return left + right
    return left + [right]

def append_str(left: list[str], right: str | list[str]) -> list[str]:
    if right is None:
        return left
    if isinstance(right, str):
        return left + [right]
    return left + right


def append_message(left: list[SentMessageModel], right: SentMessageModel | None) -> list[SentMessageModel]:
    if right is None or not right.message:
        return left
    return left + [right]



class AgentState(BaseModel):
    """LLM Agent State."""

    # Session
    session_id: str = Field(default_factory=lambda: uuid.uuid1().hex)
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    model_name: str | None = None
    model_temperature: float | None = None

    # Position 
    current_url: str = ""
    shared_url: str | None = None
    
    # Reasoning
    exit_reason: Optional[str] = None
    summary: str | None = None
    reflection: str | None = None
    feedback: Annotated[list[str], append_str] = []

    # Persona
    mood: str = "curious"
    system_prompt: str = ""

    # Social
    is_friend: bool = False
    friend_messages: list[FriendMessageModel] = []
    invited_friends: list[FriendInviteModel] = []

    # Messages
    sent_messages: Annotated[list[SentMessageModel], append_message] = []
    last_read_messages: List[str] = []
    focused_message: str | None = None
    outstanding_messages: List[str] = []
    outstanding_history: Set[str] | None = Field(default_factory=set)

    # Actions
    actions: Annotated[list[ActionModel], add_actions] = []
    opened_windows: Annotated[list[str], append_str] = []

    def __str__(self) -> str:
        lines = []
        separator = '─' * 60
        for k, v in self.__dict__.items():
            if isinstance(v, list):
                lines.append(f"\n{k}:")
                for item in v:
                    indented = "\n".join(f"  {line}" for line in str(item).splitlines())
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
    

class ToolOutputModel(BaseModel):
    reply_to: Optional[str] = None
    message: Optional[str] = None
    tool_message: Optional[str] = None
    visible_messages: Optional[List[str]] = []
    window: Optional[str] = None
    friend_invite: Optional[FriendInviteModel] = None
    feedback: Optional[str] = None

    def to_sent_message(self) -> SentMessageModel | None:
        if not self.message:
            return None
        return SentMessageModel(message=self.message, 
                                reply_to=self.reply_to)