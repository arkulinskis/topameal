import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import CookTemplate
from ... import router, state, tm


# What Mom says about a verdict given earlier (a fresh answer gets rate_dinner's own note).
SAID = {"loved": "One of my favourites now. It'll come back now and then.",
        "nope": "I won't make you cook that again. (It's in You if you change your mind.)"}


class Cook(CookTemplate):
    """#cook/<topper key> (Operate): one topper, start to finish. What to get out (the dishes), the base first, the
    ingredients scaled to the household, big numbered steps you tap off (Items/Step), Mom's tip, then "I cooked it"
    (hearts, a proud toast). Once cooked: "How did it go down?" with Everyone ate it (a favourite: it comes back now
    and then) / Not again (Mom stops suggesting it; Bring back in You), Mom's reply and a small Undo.
    An unknown key shows a friendly "I don't know that recipe".
    Server: get_cook, set_cooked, rate_dinner (server_code/Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        self.d: dict = {}
        r = anvil.server.call("get_cook", self.key, tm.today()) if self.key else {"ok": False}
        ok = bool(r.get("ok"))
        self.missing.visible = not ok
        self.body.visible = ok
        state.live(self.reply)
        if ok:
            self.d = r
            self.reply.text = SAID.get(r.get("verdict") or "", "")
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
        self._draw_verdict()

    def _draw_verdict(self):
        v = self.d.get("verdict")
        self.loved_button.role = ["btn", "btn-sm", "ic-heart", "ck-v"] + (["on"] if v == "loved" else [])
        self.nope_button.role = ["btn", "btn-ghost", "btn-sm", "ic-x", "ck-v", "ck-nope"] + (["on"] if v == "nope" else [])
        state.set_control_attr(self.loved_button, "aria-pressed", "true" if v == "loved" else "false")
        state.set_control_attr(self.nope_button, "aria-pressed", "true" if v == "nope" else "false")
        self.undo_button.visible = bool(v)
        state.set_control_attr(self.undo_button, "aria-label", "Undo how it went")
        self.reply_box.visible = bool(self.reply.text)

    def _rate(self, verdict):
        r = state.call("rate_dinner", self.key, verdict, tm.today())
        if r:
            self.d["verdict"] = r.get("verdict")
            self.reply.text = r.get("note") or ""
            self._draw_verdict()

    @handle("loved_button", "click")
    def loved_button_click(self, **event_args):
        self._rate(None if self.d.get("verdict") == "loved" else "loved")

    @handle("nope_button", "click")
    def nope_button_click(self, **event_args):
        self._rate(None if self.d.get("verdict") == "nope" else "nope")

    @handle("undo_button", "click")
    def undo_button_click(self, **event_args):
        self._rate(None)
        state.focus(self.loved_button)

    @handle("cooked_button", "click")
    def cooked_button_click(self, **event_args):
        if state.call("set_cooked", self.key, True, tm.today()):
            tm.hearts()
            state.toast(tm.pick(tm.PROUD), "ok")
            self.d["cooked"], self.d["verdict"] = tm.today(), None
            self.reply.text = ""
            self._draw_end()
            state.focus(self.loved_button)  # the next question, for keyboards and screen readers

    @handle("uncook_button", "click")
    def uncook_button_click(self, **event_args):
        if state.call("set_cooked", self.key, False, tm.today()):
            self.d["cooked"], self.d["verdict"] = None, None
            self.reply.text = ""
            self._draw_end()
