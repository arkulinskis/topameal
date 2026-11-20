import anvil.server
from anvil import *

from ._anvil_designer import WeekTemplate
from ... import router, state, tm


class Week(WeekTemplate):
    """#week/<key>.<key>... : a week someone sent with "Send this week" on This week. Anyone can open it (peek_week:
    the dinners, totals and the list for two; nothing saved). Visitors get "Cook this week" (sign up, then straight back
    here); members get "Make this my week" (adopt_week: their current plan goes into the history, and dinners that
    don't suit their kitchen are swapped, each marked "I'd swap this one" here first). A broken or cut-short link shows
    a friendly empty state with "Peek at a week" (visitors) or "Back to this week" (members).
    Server: peek_week (public), adopt_week (Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.code = args[0] if args else ""
        self.d: dict = {}
        self.body.visible = False
        self.failed_part.visible = False
        me = state.me()
        d: dict = (anvil.server.call("peek_week", self.code) if self.code
                   else {"ok": False, "error": "This link is missing its dinners."})
        self.wait.visible = False
        if not d.get("ok"):
            self.failed_part.visible = True
            self.dom_nodes["failed_text"].textContent = (d.get("error") or "That link doesn't work.") + " Here's a fresh idea instead."
            self.peek_button.visible = not me
            self.home_link.visible = bool(me)
            return
        self.d = d
        self._draw(bool(me))

    def _draw(self, member):
        d, n = self.d, self.dom_nodes
        self.body.visible = True
        swaps = [s for s in d["slots"] if s.get("swap")]
        if member and len(swaps) == 1:
            line2 = "I'd swap %s for you, since %s. The rest is ready to go." % (swaps[0]["name"].lower(), swaps[0]["swap"])
        elif member and swaps:
            line2 = "I'd swap %d of these to suit your kitchen. The rest is ready to go." % len(swaps)
        else:
            line2 = "%s for two, most perishable first. Rice, pasta and potatoes you already have." % tm.cap(tm.plural(len(d["slots"]), "dinner"))
        self.note.say(["Someone thinks you'd like this week. I've done the list too.", line2])

        self.rows.items = [dict(s, n=i + 1) for i, s in enumerate(d["slots"])]
        state.set_attr(self.rows, "role", "list")
        state.set_attr(self.rows, "aria-label", "The dinners")
        t = d["totals"]
        n["sum_text"].textContent = "%s · %d things to wash all week · roughly a" % (tm.plural(t["dinners"], "dinner"), t["dishes"])
        tm.set_tier(n["sum_tier"], t["tier"], t["tier_label"])
        n["sum_word"].textContent = t["tier_label"].lower()

        items = [i["text"][2:] if i["text"].startswith("1 ") else i["text"]
                 for a in d["list"]["aisles"] if a["key"] != "cupboard" for i in a["items"]]
        n["shop_head"].textContent = "The list (%d things):" % d["list"]["total"]
        text = ", ".join(items[:9]) + (" and a few more" if len(items) > 9 else "") + "."
        if d["shared"]:
            text += " The %s go in more than one dinner." % tm.words(d["shared"][:2])
        n["shop_text"].textContent = text

        self.member_part.visible = member
        self.guest_part.visible = not member
        n["member_fine"].textContent = ("Your current plan goes into the history. Same deal after: say no to anything you don't fancy."
                                        if d.get("has_plan") else "I'll write your shopping list straight away.")

    @handle("adopt_button", "click")
    def adopt_button_click(self, **event_args):
        if self.d.get("has_plan") and not confirm(
                "I'll make these dinners your plan and write a new list. This week's plan goes into the history.",
                title="Make this your week?", buttons=[("Cancel", False), ("Yes, make it mine", True)], role="app-dialog"):
            return
        r = state.call("adopt_week", self.code, tm.today())
        if r:
            tm.hearts()
            state.toast(r.get("note") or "This is your week now.", "ok")
            router.go("home")

    @handle("cook_button", "click")
    def cook_button_click(self, **event_args):
        router.remember_after(router.href("week", self.code))
        router.go("auth", "signup")

    @handle("peek_button", "click")
    def peek_button_click(self, **event_args):
        from ...Dialogs.Peek import Peek
        if alert(Peek(), buttons=[], role="app-dialog", dismissible=True) == "signup":
            router.go("auth", "signup")
