from anvil import *

from ._anvil_designer import NoteTemplate


class Note(NoteTemplate):
    """Mom's handwritten note: one big line, an optional smaller one, signed x Mom."""

    def __init__(self, **properties):
        self._v: dict = {"line1": "", "line2": "", "sign": True}
        self._ready = False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if not self._ready:
            return
        self.l1.text = self._v["line1"]
        self.l2.text = self._v["line2"]
        self.l2.visible = bool(self._v["line2"])
        self.signature.visible = bool(self._v["sign"])

    def say(self, lines):
        """Show one or two lines at once."""
        lines = list(lines) + ["", ""]
        self._v["line1"], self._v["line2"] = lines[0], lines[1]
        self._draw()

    @property
    def line1(self):
        return self._v["line1"]

    @line1.setter
    def line1(self, value):
        self._v["line1"] = value or ""
        self._draw()

    @property
    def line2(self):
        return self._v["line2"]

    @line2.setter
    def line2(self, value):
        self._v["line2"] = value or ""
        self._draw()

    @property
    def sign(self):
        return self._v["sign"]

    @sign.setter
    def sign(self, value):
        self._v["sign"] = bool(value)
        self._draw()
