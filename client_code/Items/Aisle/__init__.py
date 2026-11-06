from anvil import *

from ._anvil_designer import AisleTemplate
from ... import state, tm


class Aisle(AisleTemplate):
    """One aisle of the shopping list. item = {key, label, items, page}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        a = self.item
        self.dom_nodes["icon"].className = "ic ic-" + tm.AISLE_ICONS.get(a["key"], "grid")
        self.dom_nodes["label"].textContent = a["label"]
        self.hint.visible = a["key"] == "cupboard"
        state.set_attr(self.item_panel, "role", "list")
        state.set_attr(self.item_panel, "aria-label", a["label"])
        self.item_panel.items = [dict(it, page=a["page"]) for it in a["items"]]
