from anvil import *

from ._anvil_designer import CopyListTemplate
from ... import state


class CopyList(CopyListTemplate):
    """When the browser won't copy for us: the list in a box, selected, ready to copy by hand."""

    def __init__(self, text="", **properties):
        super().__init__(**properties)
        self.text_box.text = text
        state.set_control_attr(self.text_box, "readonly", "")
        state.set_control_attr(self.text_box, "aria-label", "Your shopping list")

    @handle("", "show")
    def form_show(self, **event_args):
        box = state.control(self.text_box)
        getattr(box, "focus")()
        getattr(box, "select")()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
