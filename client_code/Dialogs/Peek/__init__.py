import anvil.server
from anvil import *

from ._anvil_designer import PeekTemplate
from ... import tm


class Peek(PeekTemplate):
    """The landing page's "Peek at a week": a sample plan for two from the public sample_week() (nothing is saved).
    Closes with "signup" when they press Plan my week, else None."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.body.visible = False

    @handle("", "show")
    def form_show(self, **event_args):
        d = anvil.server.call("sample_week")
        self.rows.items = [dict(s, n=i + 1) for i, s in enumerate(d["slots"])]
        items = [i["text"][2:] if i["text"].startswith("1 ") else i["text"]
                 for a in d["list"]["aisles"] if a["key"] != "cupboard" for i in a["items"]]
        self.dom_nodes["shop_head"].textContent = "The list (%d things):" % d["list"]["total"]
        text = ", ".join(items[:9]) + (" and a few more" if len(items) > 9 else "") + "."
        if d["shared"]:
            text += " The %s go in more than one dinner." % tm.words(d["shared"][:2])
        self.dom_nodes["shop_text"].textContent = text
        self.wait.visible = False
        self.body.visible = True

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("signup_button", "click")
    def signup_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="signup")
