from anvil import *
from anvil.js import window

from ._anvil_designer import InviteTemplate
from ... import state, tm


class Invite(InviteTemplate):
    """"Share your kitchen" (the old TM.invite): the invite link (get_invite), Copy / Send it with..., who's in the
    kitchen now, and for the owner "Make a new link" (the old one stops working)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.body.visible = False
        state.set_control_attr(self.link_box, "readonly", "")
        state.set_control_attr(self.link_box, "aria-label", "Invite link")
        self.share_button.visible = tm.can_share()

    @handle("", "show")
    def form_show(self, **event_args):
        r = state.call("get_invite")
        if r:
            self._draw(r)

    def _draw(self, r):
        loc = window.location
        self.link_box.text = loc.origin + loc.pathname + "#join/" + r["code"]
        k = r["kitchen"]
        self.in_part.visible = bool(k["shared"])
        self.people.people = k["household"]
        self.new_part.visible = bool(k["is_owner"])
        self.wait.visible = False
        self.body.visible = True

    def _select(self):
        box = state.control(self.link_box)
        getattr(box, "focus")()
        getattr(box, "select")()

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        tm.copy_text(self.link_box.text, lambda: state.toast("Link copied. Send it to them however you like.", "ok"), self._select)

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        tm.share("Share my kitchen on Topameal", "Join my kitchen on Topameal: same dinners, same shopping list.", self.link_box.text)

    @handle("new_button", "click")
    def new_button_click(self, **event_args):
        r = state.call("get_invite", True)
        if r:
            self._draw(r)
            state.toast("New link made. The old one no longer works.", "ok")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
