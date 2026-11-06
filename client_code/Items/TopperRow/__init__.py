from anvil import *

from ._anvil_designer import TopperRowTemplate


class TopperRow(TopperRowTemplate):
    """One topper in Admin > Kitchen. item = {name, planned, no, cooked, protein, base, tier, max}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, n = self.item, self.dom_nodes
        n["name"].textContent = t["name"]
        n["planned"].textContent = str(t["planned"])
        n["no"].textContent = str(t["no"])
        n["cooked"].textContent = str(t["cooked"])
        n["kind"].textContent = "%s · over %s · %s" % (t["protein"], t["base"], "$$$"[:t["tier"]])
        n["bar_cooked"].style.width = "%.1f%%" % (100.0 * t["cooked"] / t["max"])
        n["bar_planned"].style.width = "%.1f%%" % (100.0 * (t["planned"] - t["cooked"]) / t["max"])
