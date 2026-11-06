from anvil import *

from ._anvil_designer import ProfileTemplate
from ... import auth, router, state, tm

LIMITS = {"people": (1, 8), "nights": (2, 7)}


class Profile(ProfileTemplate):
    """#profile ("You"): your kitchen (how many, dinners a week, budget, what you don't eat, the never-again list:
    get_kitchen / save_kitchen), your household (who's in, invite, remove / leave), then the account: name, light/dark,
    password reset, Privacy & Terms, feedback, sign out."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.k: dict = {}
        self.gone: dict = {}  # never-again keys the member wants back (until they save)
        self._show_me()
        self._show_theme()
        state.set_control_attr(self.name_box, "autocomplete", "name")
        for name, label in (("people", "people"), ("nights", "dinners")):
            state.set_control_attr(getattr(self, name + "_minus"), "aria-label", "Fewer " + label)
            state.set_control_attr(getattr(self, name + "_plus"), "aria-label", "More " + label)
        self.house_people.on_remove = self._remove
        r = state.call("get_kitchen")
        if r:
            self.k = r["kitchen"]
            self._kitchen()
            self._house()

    # ---- you
    def _show_me(self):
        me, n = state.me(), self.dom_nodes
        n["initials"].textContent = state.initials(me.get("name"))
        n["name_title"].textContent = me.get("name") or ""
        joined = state.month_year(me.get("joined"))
        n["email_line"].textContent = (me.get("email") or "") + (" · member since " + joined if joined else "")
        self.name_box.text = me.get("name") or ""
        self.admin_link.visible = bool(me.get("is_admin"))

    def _show_theme(self):
        t = state.theme()
        for name, el in (("auto", self.theme_auto), ("light", self.theme_light), ("dark", self.theme_dark)):
            el.classes["on"] = name == t

    def theme_click(self, event):
        state.set_theme(event.currentTarget.getAttribute("data-theme-pick"))
        self._show_theme()

    # ---- your kitchen
    def _kitchen(self):
        k = self.k
        for name in ("people", "nights"):
            self.dom_nodes[name + "_out"].textContent = str(k[name])
        for b in k["options"]["budget"]:
            btn = getattr(self, "budget_%d" % b["key"])
            btn.text = b["label"]
        self._show_budget()
        self.avoid_panel.items = [dict(a, page=self) for a in k["options"]["avoid"]]
        self.never_row.visible = bool(k["never"])
        self.gone = {}
        self.never_panel.items = [dict(x, page=self) for x in k["never"]]

    def _show_budget(self):
        for n in (1, 2, 3):
            btn = getattr(self, "budget_%d" % n)
            on = self.k["budget"] == n
            btn.role = ["seg", "on"] if on else ["seg"]
            state.set_control_attr(btn, "aria-pressed", "true" if on else "false")

    def _step(self, name, by):
        lo, hi = LIMITS[name]
        self.k[name] = max(lo, min(hi, self.k[name] + by))
        self.dom_nodes[name + "_out"].textContent = str(self.k[name])

    @handle("people_minus", "click")
    def people_minus_click(self, **event_args):
        self._step("people", -1)

    @handle("people_plus", "click")
    def people_plus_click(self, **event_args):
        self._step("people", 1)

    @handle("nights_minus", "click")
    def nights_minus_click(self, **event_args):
        self._step("nights", -1)

    @handle("nights_plus", "click")
    def nights_plus_click(self, **event_args):
        self._step("nights", 1)

    def _budget(self, n):
        self.k["budget"] = n
        self._show_budget()

    @handle("budget_1", "click")
    def budget_1_click(self, **event_args):
        self._budget(1)

    @handle("budget_2", "click")
    def budget_2_click(self, **event_args):
        self._budget(2)

    @handle("budget_3", "click")
    def budget_3_click(self, **event_args):
        self._budget(3)

    def toggle_avoid(self, key, on):
        """Called by Items/AvoidChip."""
        avoid = [a for a in self.k["avoid"] if a != key]
        self.k["avoid"] = avoid + [key] if on else avoid

    def toggle_never(self, key, gone):
        """Called by Items/NeverChip: gone = bring it back when they save."""
        self.gone[key] = gone

    @handle("save_kitchen_button", "click")
    def save_kitchen_button_click(self, **event_args):
        k = self.k
        data = {"people": k["people"], "nights": k["nights"], "budget": k["budget"], "avoid": list(k["avoid"]),
                "never": [x["key"] for x in k["never"] if not self.gone.get(x["key"])]}
        r = state.call("save_kitchen", data, tm.today())
        if r:
            self.k = r["kitchen"]
            self._kitchen()
            self._house()
            state.toast(r.get("note") or "Saved", "ok")

    # ---- your household
    def _house(self):
        k = self.k
        owner = next((p for p in k["household"] if p.get("owner")), None)
        if k["shared"]:
            text = "You share one plan, one shopping list and these settings" + (
                "." if k["is_owner"] else " with %s." % (owner["name"].split(" ")[0] if owner else "them")) + " Everyone can tick things off."
        else:
            text = "Live with someone? Share your kitchen: one plan, one shopping list, and whoever is at the shop can tick things off."
        self.dom_nodes["house_text"].textContent = text
        self.house_people.visible = bool(k["shared"])
        self.house_people.removable = bool(k["is_owner"])
        self.house_people.people = k["household"]
        self.invite_button.text = "Invite someone else" if k["shared"] else "Share my kitchen"
        self.leave_button.visible = not k["is_owner"]

    def _remove(self, person):
        name = (person or {}).get("name") or "them"
        if confirm("They go back to their own plan. You can invite them again any time.", title="Take %s out of your kitchen?" % name,
                   buttons=[("Cancel", False), ("Take them out", True)], role="app-dialog"):
            r = state.call("remove_member", person["id"])
            if r:
                self.k = r["kitchen"]
                self._house()
                state.toast("Done.", "ok")

    @handle("invite_button", "click")
    def invite_button_click(self, **event_args):
        from ...Dialogs.Invite import Invite
        alert(Invite(), buttons=[], role="app-dialog", dismissible=True)

    @handle("leave_button", "click")
    def leave_button_click(self, **event_args):
        if confirm("You go back to your own plan and list. They keep theirs.", title="Leave this kitchen?",
                   buttons=[("Cancel", False), ("Leave", True)], role="app-dialog"):
            r = state.call("leave_household")
            if r:
                self.k = r["kitchen"]
                self._kitchen()
                self._house()
                state.toast(r.get("note") or "Done.", "ok")

    # ---- account
    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            state.toast("Tell me what to call you, love.", "error")
            return
        r = state.call("update_profile", name)
        if r:
            state.set_me(r["me"])
            self._show_me()
            state.toast("Saved", "ok")

    @handle("reset_button", "click")
    def reset_button_click(self, **event_args):
        r = auth.reset(state.me()["email"])
        state.toast(r["message"], "ok")

    def feedback_click(self, event):
        state.feedback()

    def sign_out_click(self, event):
        auth.sign_out()
        state.toast("Signed out. See you soon!")
        router.go("landing")
