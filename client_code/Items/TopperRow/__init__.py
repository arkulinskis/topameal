from anvil import *

from ._anvil_designer import TopperRowTemplate


class TopperRow(TopperRowTemplate):
    """One topper in Admin > Kitchen. item = {name, planned, no, cooked, loved, nope, protein, base, tier, max}.
    loved / nope = what households said after cooking it (Everyone ate it / Not again)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        t, n = self.item, self.dom_nodes
        n["name"].textContent = t["name"]
        n["planned"].textContent = str(t["planned"])
        n["no"].textContent = str(t["no"])
        n["cooked"].textContent = str(t["cooked"])
        said = []
        if t.get("loved"):
            said.append("%d favourite%s" % (t["loved"], "" if t["loved"] == 1 else "s"))
        if t.get("nope"):
            said.append("%d not again" % t["nope"])
        n["kind"].textContent = " · ".join(["%s" % t["protein"], "over %s" % t["base"], "$$$"[:t["tier"]]] + said)
        n["bar_cooked"].style.width = "%.1f%%" % (100.0 * t["cooked"] / t["max"])
        n["bar_planned"].style.width = "%.1f%%" % (100.0 * (t["planned"] - t["cooked"]) / t["max"])
