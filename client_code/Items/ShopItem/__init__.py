from anvil import *

from ._anvil_designer import ShopItemTemplate
from ... import tm


class ShopItem(ShopItemTemplate):
    """One line of the shopping list: a real tick box (keyboard and screen readers) drawn as Mom's round tick.
    item = {key, text, for, checked, by, keeps, perishable, page}. It registers itself in page.rows so the page can
    update it in place when someone else ticks it."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, n = self.item, self.dom_nodes
        self.page, self.key = it["page"], it["key"]
        n["what"].textContent = it["text"]
        n["for_text"].textContent = "for " + tm.words(it["for"])
        self.perish.visible = bool(it["perishable"])
        n["perish_text"].textContent = "Fridge straight away · keeps " + tm.plural(it["keeps"], "day")
        self.page.rows[self.key] = self
        n["box"].addEventListener("change", self._change)
        self.set(it["checked"], it.get("by"))

    def set(self, on, by):
        n = self.dom_nodes
        n["box"].checked = bool(on)
        self.row.classes["on"] = bool(on)
        n["by"].textContent = (by + " got it") if on and by and by != self.page.me else ""

    def short(self):
        """'2 red peppers' -> 'red peppers' (for "Sam got the red peppers")."""
        head, _, rest = self.item["text"].partition(" ")
        return rest if head.isdigit() and rest else self.item["text"]

    def _change(self, event):
        on = bool(self.dom_nodes["box"].checked)
        self.set(on, None)
        self.page.tick(self.key, on, self)
