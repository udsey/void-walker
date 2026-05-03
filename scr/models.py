from typing import List, Optional, Any
from pydantic import BaseModel


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


class ConfigModel(BaseModel):
    root_url: str = "https://void-cast.fly.dev/"
    status_config: Optional[StatusConfigModel] = None
    wait_timeout: Optional[int] = 10

    def model_post_init(self, __context: Any) -> None:
        if self.status_config is None:
            self.status_config = StatusConfigModel()