from anvil import *

from ._anvil_designer import PersonTemplate
from ... import state


class Person(PersonTemplate):
    """One name chip in Components/People. item = {id, name, me, owner, removable}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p = self.item
        n = self.dom_nodes
        n["initials"].textContent = state.initials(p.get("name"))
        n["name"].textContent = p.get("name") or ""
        tag = "you" if p.get("me") else ("started it" if p.get("owner") else "")
        n["tag"].textContent = tag
        n["tag"].style.display = "" if tag else "none"
        self.remove_button.visible = bool(p.get("removable"))
        if p.get("removable"):
            state.set_control_attr(self.remove_button, "aria-label", "Remove " + (p.get("name") or ""))

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-remove", person=self.item)
