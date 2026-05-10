from typing import Annotated, Literal

from src.models import FriendInviteModel, ToolOutputModel
from src.selenium.helpers import (
    get_current_url,
    interact_with_modal,
    move_around,
    press_explore,
    press_share,
    read_visible_messages,
    send_message,
)
from src.walker.utils import register


class WalkerTools:
    def __init__(self, driver) -> None:
        self.driver = driver


    @register(_type="tool", _name="send_message")
    def send_message(
        self,
        message: Annotated[str,
                           "The message you want to send to the void."]
        ) -> ToolOutputModel:
            """Cast a message into the void.
            Write something true to your persona, mood,
            and what you've observed. Keep it short and human."""
            tool_output = ToolOutputModel()
            tool_output.visible_messages = read_visible_messages(self.driver)
            tool_output.tool_message = send_message(self.driver, message)
            tool_output.message = message

            return tool_output.model_dump_json()


    @register(_type="tool", _name="respond_to_message")
    def respond_to_message(
        self,
        reply_to: Annotated[
            str,
            "Exact text of the message you are replying to."],
        reply: Annotated[
            str,
            "Your reply. Keep it natural and in character."]
            ) -> str:
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
        tool_output.current_url = get_current_url(self.driver)
        return tool_output.model_dump_json()


    @register(_type="tool", _name="move_around")
    def move(
        self,
        dx: Annotated[
            int,
            "Horizontal distance. Negative moves left, positive moves right."],
        dy: Annotated[
            int,
            "Vertical distance. Negative moves up, positive moves down."]
            ) -> str:
        """Drift from your current position to see nearby messages.
        Small values for subtle movement, large for bigger jumps."""
        tool_output = ToolOutputModel()
        tool_output.tool_message = move_around(self.driver, dx, dy)
        tool_output.visible_messages = read_visible_messages(self.driver)
        tool_output.current_url = get_current_url(self.driver)
        return tool_output.model_dump_json()


    @register(_type="tool", _name="open_window")
    def open_window(
        self,
        window: Annotated[
            Literal['about', 'support', 'terms'],
            "Panel to open."]
            ) -> str:
        """Open one of the site's info panels and read its contents."""
        tool_output = ToolOutputModel()
        tool_output.tool_message = interact_with_modal(driver=self.driver,
                                                       modal_name=window)
        tool_output.window = window
        tool_output.visible_messages = read_visible_messages(self.driver)

        return tool_output.model_dump_json()


    @register(_type="tool", _name="send_feedback")
    def send_feedback(
        self,
        feedback: Annotated[
            str,
            "Your thoughts about the site. Speak as yourself."]
            ) -> str:
        """
        Leave feedback about your experience on void-cast.
        Reflect honestly as your persona.
        """
        tool_output = ToolOutputModel()
        tool_output.feedback = feedback
        tool_output.tool_message = "Your thoughts have been noted."
        tool_output.visible_messages = read_visible_messages(self.driver)

        return tool_output.model_dump_json()


    @register(_type="tool", _name="invite_friend")
    def invite_friend(
        self,
        friends_name: Annotated[
            str,
            ("Name of someone you know. "
            "Can be real or made up—just pick any name.")],
        message: Annotated[
            str,
            "What you'd say to get them to join you here."]
            ) -> str:
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
        tool_output.current_url = url

        return tool_output.model_dump_json()


    @register(_type="tool", _name="check_new_messages")
    def check_new_messages(self) -> str:
        """
        Look around and read any messages currently visible in the void.
        If you've already checked and seen nothing new,
        do something else instead."""
        tool_output = ToolOutputModel()
        messages = read_visible_messages(self.driver)
        tool_output.visible_messages = messages
        tool_output.tool_message = "You look around the void"

        return tool_output.model_dump_json()
