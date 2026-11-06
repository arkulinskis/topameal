from anvil import *

from ._anvil_designer import IngredientTemplate


class Ingredient(IngredientTemplate):
    """One line of "You'll need". item = {text, note?, faint?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["text"].textContent = self.item["text"]
        self.dom_nodes["note"].textContent = self.item.get("note") or ""
        if self.item.get("faint"):
            self.dom_nodes["text"].className = "faint"
