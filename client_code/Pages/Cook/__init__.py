import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import CookTemplate
from ... import router, state, tm


class Cook(CookTemplate):
    """#cook/<topper key> (Operate): one topper, start to finish. What to get out (the dishes), the base first, the
    ingredients scaled to the household, big numbered steps you tap off (Items/Step), Mom's tip, then "I cooked it"
    (hearts, a proud toast, back to This week). An unknown key shows a friendly "I don't know that recipe".
    Server: get_cook, set_cooked (server_code/Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        self.d: dict = {}
        r = anvil.server.call("get_cook", self.key, tm.today()) if self.key else {"ok": False}
        ok = bool(r.get("ok"))
        self.missing.visible = not ok
        self.body.visible = ok
        if ok:
            self.d = r
            self._draw()

    def _draw(self):
        d, n = self.d, self.dom_nodes
        t, b, people = d["topper"], d["base"], d["people"]
        window.document.title = t["name"] + " · Topameal"
        tm.set_base(n["base"], t["base"], big=True)
        n["title"].textContent = t["name"]
        n["blurb"].textContent = t["blurb"]
        self.meta.topper = t
        self.also.visible = bool(t["also"])
        n["also_text"].textContent = "Also lovely over %s." % tm.words(t["also"])
        n["dishes_title"].textContent = "Get out %d things. That's all you'll wash." % t["dish_count"]
        self.dish_panel.items = [{"text": x} for x in t["dishes"]]
        amount = tm.base_amount(t["base"], people)
        self.ing_panel.items = ([{"text": amount, "note": "(at home)"}] + [{"text": x} for x in t["ingredients"]]
                                + [{"text": "oil, salt and pepper", "faint": True}])
        first = {"n": "0", "base": True, "lead": tm.cap(b["name"]) + " first.",
                 "text": "%s for %s. %s" % (amount, tm.plural(people, "person", "people"), b["how"])}
        self.step_panel.items = [first] + [{"n": str(i + 1), "text": s} for i, s in enumerate(t["steps"])]
        for panel, label in ((self.dish_panel, "Dishes"), (self.ing_panel, "Ingredients"), (self.step_panel, "Steps")):
            state.set_attr(panel, "role", "list")
            state.set_attr(panel, "aria-label", label)
        self.note.say([t["tip"]])
        self._draw_end()

    def _draw_end(self):
        d = self.d
        self.cookby.visible = bool(d["cook_by"]) and not d["cooked"]
        self.dom_nodes["cookby_text"].textContent = "Cook by " + tm.day(d["cook_by"]) if d["cook_by"] else ""
        self.end_off.visible = not d["in_plan"]
        self.end_done.visible = bool(d["in_plan"] and d["cooked"])
        self.end_todo.visible = bool(d["in_plan"] and not d["cooked"])
        self.dom_nodes["cooked_text"].textContent = "Cooked " + tm.day(d["cooked"]) if d["cooked"] else ""

    @handle("cooked_button", "click")
    def cooked_button_click(self, **event_args):
        if state.call("set_cooked", self.key, True, tm.today()):
            tm.hearts()
            state.toast(tm.pick(tm.PROUD), "ok")
            router.go("home")

    @handle("uncook_button", "click")
    def uncook_button_click(self, **event_args):
        if state.call("set_cooked", self.key, False, tm.today()):
            self.d["cooked"] = None
            self._draw_end()
