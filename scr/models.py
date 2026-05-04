from datetime import datetime
from typing import Annotated, List, Literal, Optional, Any, Set
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
    model_type: Literal["local", "groq"] = "local"
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


class AnswerModel(BaseModel):
    answer: str = Field(description="The answer or decision made")
    reason: str = Field(description="The reasoning behind the answer")


class ActionModel(BaseModel):
    name: str
    timestamp: datetime
    llm_prompt: str | None = None
    llm_response: YesNoModel | AnswerModel | None = None
    function_result: str | None = None


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
        import textwrap
        lines = self.system_prompt.split('\n')
        header = '\n'.join(lines[:6])
        wrapped = textwrap.fill(header, width=80, break_long_words=False, break_on_hyphens=False)
        return f"\n\n{wrapped}\nMood: {self.mood}\nFriend: {self.is_friend}\nURL: {self.url}\n\n"

class FriendInviteModel(BaseModel):
    name: str
    url: str
    message: Optional[str] = None


def add_actions(left: list[ActionModel], right: list[ActionModel] | ActionModel | dict) -> list[ActionModel]:
    """Reducer to add new actions."""
    if isinstance(right, dict):
        right = ActionModel(**right)
    if isinstance(right, list):
        return left + [ActionModel(**r) if isinstance(r, dict) else r for r in right]
    return left + [right]

class AgentState(BaseModel):
    """LLM Agent State."""

    # Session
    session_id: str = Field(default_factory=lambda: uuid.uuid1().hex)
    start_time: datetime = Field(default_factory=datetime.now)

    # Position 
    current_url: str = ""
    shared_url: str | None = None
    
    # Reasoning
    summary: str | None = None
    thoughts: str | None = None

    # Persona
    mood: str = "curious"
    system_prompt: str = ""

    # Social
    is_friend: bool = False
    friend_messages: list[FriendMessageModel] = []
    invited_friends: list[FriendInviteModel] = []

    # Messages
    last_read_messages: List[str] = []
    focused_message: str | None = None
    outstanding_messages: List[str] = []
    outstanding_history: Set[str] | None = Field(default_factory=set)

    # Actions
    actions: Annotated[list[Any], add_actions] = []