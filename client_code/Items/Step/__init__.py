from anvil import *

from ._anvil_designer import StepTemplate


class Step(StepTemplate):
    """One cooking step: a big button you tap when it's done (it fades and gets a tick). item = {n, text, lead?, base?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        n, it = self.dom_nodes, self.item
        n["n"].textContent = it["n"]
        n["lead"].textContent = it.get("lead") or ""
        n["text"].textContent = it["text"]
        if it.get("base"):
            n["btn"].classList.add("base")
        n["btn"].addEventListener("click", self._toggle)

    def _toggle(self, event):
        b = self.dom_nodes["btn"]
        on = not b.classList.contains("done")
        b.classList.toggle("done", on)
        b.setAttribute("aria-pressed", "true" if on else "false")
        self.dom_nodes["n"].textContent = "✓" if on else self.item["n"]
