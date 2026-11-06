from anvil import *

from ._anvil_designer import PeekRowTemplate
from ... import tm


class PeekRow(PeekRowTemplate):
    """One dinner in the Peek dialog. item = a topper card + n (its number)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        tm.set_base(self.dom_nodes["base"], self.item["base"])
        self.dom_nodes["title"].textContent = "%d. %s" % (self.item["n"], self.item["name"])
        self.meta.topper = self.item
