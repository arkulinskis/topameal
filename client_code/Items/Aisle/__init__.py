from anvil import *

from ._anvil_designer import AisleTemplate
from ... import state, tm


HINTS = {
    "cupboard": "Most kitchens have these. Have a look before you go, and only buy what's missing.",
    "home": "You bought these on an earlier shop and there's usually some left. Tick what you've still got.",
}


class Aisle(AisleTemplate):
    """One aisle of the shopping list. item = {key, label, items, page}. The cupboard and "Probably still at home"
    (key "home": jars and bunches from an earlier shop) groups get a hint: look before you buy."""

    def __init__(self, **properties):
        super().__init__(**properties)
        a = self.item
        self.dom_nodes["icon"].className = "ic ic-" + tm.AISLE_ICONS.get(a["key"], "grid")
        self.dom_nodes["label"].textContent = a["label"]
        self.hint.visible = a["key"] in HINTS
        self.dom_nodes["hint_text"].textContent = HINTS.get(a["key"], "")
        state.set_attr(self.item_panel, "role", "list")
        state.set_attr(self.item_panel, "aria-label", a["label"])
        self.item_panel.items = [dict(it, page=a["page"]) for it in a["items"]]
