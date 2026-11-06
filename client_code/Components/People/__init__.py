from anvil import *

from ._anvil_designer import PeopleTemplate


class People(PeopleTemplate):
    """The household's name chips (the old TM.people). `on_remove(person)` is called by the remove buttons."""

    def __init__(self, **properties):
        self._people: list = []
        self._removable = False
        self.on_remove = None
        self._ready = False
        super().__init__(**properties)
        self.panel.add_event_handler("x-remove", self._remove)
        self._ready = True
        self._draw()

    def _draw(self):
        if self._ready:
            self.panel.items = [dict(p, removable=self._removable and not p.get("me")) for p in (self._people or [])]

    def _remove(self, person=None, **event_args):
        if self.on_remove is not None:
            self.on_remove(person)

    @property
    def people(self):
        return self._people

    @people.setter
    def people(self, value):
        self._people = list(value or [])
        self._draw()

    @property
    def removable(self):
        return self._removable

    @removable.setter
    def removable(self, value):
        self._removable = bool(value)
        self._draw()
