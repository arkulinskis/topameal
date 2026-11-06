from anvil import *

from ._anvil_designer import TrayChipTemplate
from ... import state


class TrayChip(TrayChipTemplate):
    """A dinner on the set-aside tray. item = {key, name, auto}. "Yes, this one" raises x-yes (it comes back)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["name"].textContent = self.item["name"]
        state.set_control_attr(self.yes_button, "aria-label", "Yes, this one: " + self.item["name"])

    @handle("yes_button", "click")
    def yes_button_click(self, **event_args):
        self.parent.raise_event("x-yes", key=self.item["key"])
