from anvil import *
import anvil.js

from ._anvil_designer import WeekCardTemplate
from ... import router, state, tm


class WeekCard(WeekCardTemplate):
    """One dinner on This week. item = a slot card from get_week + i (its place) + fresh (just arrived: glows once).
    The whole card opens the cook page; "No thanks" raises x-no on the panel (the page asks Mom for a swap)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s, n = self.item, self.dom_nodes
        cooked = bool(s.get("cooked"))
        n["num"].innerHTML = '<i class="ic ic-check"></i>' if cooked else str(s["i"] + 1)
        n["title"].textContent = s["name"]
        state.set_attr(self.title_link, "href", router.href("cook", s["key"]))
        self.meta.topper = s
        kind, icon, text = tm.flag_for(s)
        n["flag"].className = "tm-flag " + kind
        n["flag_icon"].className = "ic ic-" + icon
        n["flag_text"].textContent = text
        self.no_button.visible = not cooked
        state.set_control_attr(self.no_button, "aria-label", "No thanks to " + s["name"])
        self.tip.visible = not cooked and bool(s.get("freeze"))
        n["tip_text"].textContent = "Freeze the %s when you get home. Move it to the fridge the night before." % s.get("perishable", "")
        self.card.classes["done"] = cooked
        self.card.classes["is-new"] = bool(s.get("fresh"))
        anvil.js.get_dom_node(self.card).style.animationDelay = "%dms" % min(s["i"] * 40, 240)

    def card_click(self, event):
        if event.target.closest("a, button"):
            return
        router.go("cook", self.item["key"])

    def fade(self, on):
        """Slide the card aside while Mom finds a swap (and back if that failed)."""
        st = anvil.js.get_dom_node(self.card).style
        st.opacity = ".35" if on else ""
        st.transform = "translateX(14px)" if on else ""

    @handle("no_button", "click")
    def no_button_click(self, **event_args):
        self.parent.raise_event("x-no", key=self.item["key"], card=self)
