from anvil import *

from ._anvil_designer import PillTemplate


class Pill(PillTemplate):
    """A dish to get out, as a little pill. item = {text}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["text"].textContent = self.item["text"]
