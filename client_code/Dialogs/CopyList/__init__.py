from anvil import *

from ._anvil_designer import CopyListTemplate
from ... import state


class CopyList(CopyListTemplate):
    """When the browser won't copy for us: the text in a box, selected, ready to copy by hand. Used for the shopping
    list (Pages/Shopping) and the "Send this week" link (Pages/Home, title="Your week's link")."""

    def __init__(self, text="", title="Your list", **properties):
        super().__init__(**properties)
        self.text_box.text = text
        self.dom_nodes["title"].textContent = title
        state.set_control_attr(self.text_box, "readonly", "")
        state.set_control_attr(self.text_box, "aria-label", "Your shopping list" if title == "Your list" else title)

    @handle("", "show")
    def form_show(self, **event_args):
        box = state.control(self.text_box)
        getattr(box, "focus")()
        getattr(box, "select")()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
