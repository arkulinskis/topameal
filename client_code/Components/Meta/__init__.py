from anvil import *

from ._anvil_designer import MetaTemplate
from ... import tm


class Meta(MetaTemplate):
    """The facts row under a dinner (the old TM.meta): over rice, 25 min, 3 to wash, $$."""

    def __init__(self, **properties):
        self._t = None
        self._base = True
        self._ready = False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        t = self._t
        if not self._ready or not t:
            return
        n = self.dom_nodes
        n["base_part"].style.display = "" if self._base else "none"
        n["base_icon"].className = "ic ic-" + t["base"]
        n["base_text"].textContent = "over " + t["base"]
        n["minutes"].textContent = "%s min" % t["minutes"]
        n["dishes"].textContent = "%s to wash" % t["dish_count"]
        n["dishes_part"].setAttribute("title", ", ".join(t.get("dishes") or []))
        tm.set_tier(n["tier"], t["tier"], t.get("tier_label"))

    @property
    def topper(self):
        return self._t

    @topper.setter
    def topper(self, value):
        self._t = value
        self._draw()

    @property
    def show_base(self):
        return self._base

    @show_base.setter
    def show_base(self, value):
        self._base = bool(value)
        self._draw()
