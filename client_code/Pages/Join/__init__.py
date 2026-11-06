import anvil.server
from anvil import *

from ._anvil_designer import JoinTemplate
from ... import router, state, tm


class Join(JoinTemplate):
    """#join/<code>: where an invite link lands. Anyone can open it (peek_invite: first names only). Signed out:
    create an account or sign in, then come straight back here. Signed in: "Join Sam's kitchen".
    Server: peek_invite (public), join_household (Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.code = args[0] if args else ""
        me = state.me()
        for part in (self.member_part, self.invite_part, self.failed_part):
            part.visible = False
        d: dict = anvil.server.call("peek_invite", self.code) if self.code else {"ok": False, "error": "This invite link is missing its code."}
        if not d.get("ok"):
            self.pan.visible = False
            self.failed_part.visible = True
            self.dom_nodes["failed_text"].textContent = d.get("error") or "This invite link doesn't work any more."
            state.set_attr(self.failed_link, "href", "#home" if me else "#landing")
            self.dom_nodes["failed_link_text"].textContent = "Back to this week" if me else "What is Topameal?"
            return
        name = d["owner"]
        if d.get("member"):
            self.member_part.visible = True
            self.dom_nodes["member_title"].textContent = "You're already in %s's kitchen" % name
            return
        self.invite_part.visible = True
        self.dom_nodes["invite_title"].textContent = "%s wants to share their kitchen" % name
        self.note.say(["%s's asked you to share dinners with them." % name,
                       "One plan, one shopping list, and whoever is at the shop ticks things off. Fewer arguments about dinner."])
        self.people.people = [{"name": x} for x in d["names"]]
        self.full_part.visible = bool(d.get("full"))
        self.dom_nodes["full_text"].textContent = "This kitchen is full. Ask %s to make some room." % name
        self.join_part.visible = bool(me) and not d.get("full")
        self.guest_part.visible = not me and not d.get("full")
        self.join_button.text = "Join %s's kitchen" % name

    def _auth(self, mode):
        router.remember_after(router.href("join", self.code))
        router.go("auth", mode)

    @handle("signup_button", "click")
    def signup_button_click(self, **event_args):
        self._auth("signup")

    @handle("signin_button", "click")
    def signin_button_click(self, **event_args):
        self._auth("")

    @handle("join_button", "click")
    def join_button_click(self, **event_args):
        r = state.call("join_household", self.code, tm.today())
        if r:
            tm.hearts()
            state.toast(r.get("note") or "Welcome in.", "ok")
            router.go("home")
