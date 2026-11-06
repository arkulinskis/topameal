from anvil import *

from ... import state
from ._anvil_designer import NeverChipTemplate


class NeverChip(NeverChipTemplate):
    """A dinner Mom stopped suggesting (three noes). "Bring back" marks it to come back when they save; "Keep it off"
    undoes that. item = {key, name, page}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["name"].textContent = self.item["name"]
        self._show(False)

    def _show(self, gone):
        self.gone = gone
        self.chip.classes["gone"] = gone
        self.toggle_button.text = "Keep it off" if gone else "Bring back"
        self.toggle_button.role = ["btn", "btn-sm", "ic-x" if gone else "ic-undo"]
        state.set_control_attr(self.toggle_button, "aria-label", self.toggle_button.text + ": " + self.item["name"])

    @handle("toggle_button", "click")
    def toggle_button_click(self, **event_args):
        self._show(not self.gone)
        self.item["page"].toggle_never(self.item["key"], self.gone)
