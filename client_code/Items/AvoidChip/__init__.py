from anvil import *

from ... import state
from ._anvil_designer import AvoidChipTemplate


class AvoidChip(AvoidChipTemplate):
    """One "Anything you don't eat?" choice: a toggle chip. item = {key, label, page}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.chip.text = self.item["label"]
        self._show(self.item["key"] in self.item["page"].k["avoid"])

    def _show(self, on):
        self.on = on
        self.chip.role = ["kc-chip", "on"] if on else ["kc-chip"]
        state.set_control_attr(self.chip, "aria-pressed", "true" if on else "false")

    @handle("chip", "click")
    def chip_click(self, **event_args):
        self._show(not self.on)
        self.item["page"].toggle_avoid(self.item["key"], self.on)
