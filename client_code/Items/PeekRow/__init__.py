from anvil import *

from ._anvil_designer import PeekRowTemplate
from ... import tm


class PeekRow(PeekRowTemplate):
    """One dinner in the Peek dialog and on a sent week (Pages/Week). item = a topper card + n (its number)
    + swap (Pages/Week, signed in: why Mom would swap it for this kitchen, e.g. "you don't eat pork")."""

    def __init__(self, **properties):
        super().__init__(**properties)
        tm.set_base(self.dom_nodes["base"], self.item["base"])
        self.dom_nodes["title"].textContent = "%d. %s" % (self.item["n"], self.item["name"])
        self.meta.topper = self.item
        swap = self.item.get("swap")
        self.swap.visible = bool(swap)
        self.dom_nodes["swap_text"].textContent = "I'd swap this one, since %s." % swap if swap else ""
