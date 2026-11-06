import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import ShoppingTemplate
from ... import router, state, tm


class Shopping(ShoppingTemplate):
    """#list ("Shopping", Operate): the week's list, merged and grouped in the order you walk the shop
    (Items/Aisle > Items/ShopItem). Ticks save quietly (set_checked); Copy list; Share opens Dialogs/Invite; "I've done
    the shopping" starts the cook-by days. In a shared kitchen the page checks other people's ticks every 6 s
    (get_ticks, quiet) and updates the rows in place, with "Sam got it".
    Server: get_week, set_checked, set_shopped, get_ticks (server_code/Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.w: dict = {}
        self.k: dict = {}
        self.rows: dict = {}     # grocery key -> its Items/ShopItem (registered by the item)
        self.on: dict = {}       # grocery key -> ticked?
        self.pending: dict = {}  # grocery key -> ticks still being saved (polling leaves those alone)
        self.me = tm.first(state.me())
        self.timer = None
        self.list_keys = ""
        r = state.call("get_week", tm.today())
        if r:
            self._take(r)

    @handle("", "hide")
    def form_hide(self, **event_args):
        self._stop()

    def _stop(self):
        if self.timer is not None:
            window.clearInterval(self.timer)
            self.timer = None

    def _take(self, r):
        self.w, self.k = r["week"], r["kitchen"]
        self.list_keys = ",".join(s["key"] for s in self.w["slots"])
        self._draw()
        self._stop()
        if self.k["shared"] and not self.w["shopped"]:
            self.timer = window.setInterval(self._poll, 6000)

    def _draw(self):
        w, k, n = self.w, self.k, self.dom_nodes
        lst, t = w["list"], w["totals"]
        tm.set_tier(n["tier"], t["tier"], t["tier_label"])
        n["tier_word"].textContent = t["tier_label"].lower()
        others = [p["name"].split(" ")[0] for p in k["household"] if not p.get("me")]
        self.with_line.visible = bool(k["shared"])
        n["with_text"].textContent = "Shopping together with %s. Ticks show up for everyone." % tm.words(others)
        lines = ["Everything for %s, for %s." % (tm.plural(t["dinners"], "dinner"), tm.plural(w["people"], "person", "people"))]
        if w["shared"]:
            lines.append("The %s go in more than one dinner. That's on purpose." % tm.words(w["shared"][:3]))
        else:
            lines.append("Roughly a %s week. Don't buy anything that's not on here." % t["tier_label"].lower())
        self.note.say(lines)
        n["home_text"].textContent = tm.words(w["at_home"]) + "."
        has = lst["total"] > 0
        self.empty_part.visible = not has
        self.list_part.visible = has
        if not has:
            return
        self.on = {it["key"]: bool(it["checked"]) for a in lst["aisles"] for it in a["items"]}
        self.rows = {}
        self.shopped_flag.visible = bool(w["shopped"])
        n["shopped_text"].textContent = "Shopped " + tm.day(w["shopped"]) if w["shopped"] else ""
        self.aisle_panel.items = [dict(a, page=self) for a in lst["aisles"]]
        self.done_shopped.visible = bool(w["shopped"])
        self.done_todo.visible = not w["shopped"]
        self._progress()

    def _progress(self):
        total = len(self.on)
        done = len([v for v in self.on.values() if v])
        n = self.dom_nodes
        n["count"].textContent = "%d of %d in the basket" % (done, total)
        n["bar"].style.transform = "scaleX(%.4f)" % ((done / float(total)) if total else 0)
        n["bar_box"].setAttribute("aria-valuemax", str(total))
        n["bar_box"].setAttribute("aria-valuenow", str(done))
        return done, total

    # ---- ticks (called by Items/ShopItem)
    def tick(self, key, on, row):
        self.on[key] = on
        self._progress()
        self.pending[key] = self.pending.get(key, 0) + 1
        saved = False
        try:
            r = anvil.server.call_s("set_checked", key, on, tm.today())
            saved = not (isinstance(r, dict) and r.get("ok") is False)
            if not saved:
                state.toast(r.get("error") or "That tick didn't save.", "error")
        except anvil.server.AppOfflineError:
            state.toast("You're offline, so that tick didn't save.", "error")
        finally:
            self.pending[key] -= 1
            if not self.pending[key]:
                del self.pending[key]
        if not saved:
            self.on[key] = not on
            row.set(not on, None)
            self._progress()
            return
        done, total = self._progress()
        if on and done == total and not self.w["shopped"]:
            state.toast("That's everything! Tap \"I've done the shopping\" when you're home.", "ok")

    def _poll(self):
        """Shared kitchens: pick up other people's ticks without redrawing the page."""
        if window.document.hidden or not self.w:
            return
        try:
            t = anvil.server.call_s("get_ticks", tm.today())
        except Exception:
            return
        if t["week"] != self.w["id"] or ",".join(t["slots"]) != self.list_keys or bool(t["shopped"]) != bool(self.w["shopped"]):
            try:
                self._take(anvil.server.call_s("get_week", tm.today()))
            except Exception:
                pass
            return
        fresh = []
        for key, row in self.rows.items():
            if key in self.pending:
                continue
            by = t["checked"].get(key)
            on = key in t["checked"]
            if on and not self.on.get(key) and by and by != self.me:
                fresh.append("%s got the %s" % (by, row.short()))
            self.on[key] = on
            row.set(on, by if on else None)
        self._progress()
        if fresh and len(fresh) <= 2:
            state.toast(". ".join(fresh) + ".")

    # ---- buttons
    def _as_text(self):
        w = self.w
        out = ["Topameal shopping list (%s)" % tm.plural(w["totals"]["dinners"], "dinner"), ""]
        for a in w["list"]["aisles"]:
            out.append(a["label"].upper())
            for it in a["items"]:
                out.append(("[x] " if self.on.get(it["key"]) else "[ ] ") + it["text"])
            out.append("")
        out.append("At home already: %s." % tm.words(w["at_home"]))
        return "\n".join(out)

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        text = self._as_text()

        def fallback():
            from ...Dialogs.CopyList import CopyList
            alert(CopyList(text=text), buttons=[], role="app-dialog", dismissible=True)

        tm.copy_text(text, lambda: state.toast("Copied. Paste it anywhere, or send it to whoever's shopping.", "ok"), fallback)

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        from ...Dialogs.Invite import Invite
        alert(Invite(), buttons=[], role="app-dialog", dismissible=True)

    @handle("shopped_button", "click")
    def shopped_button_click(self, **event_args):
        if state.call("set_shopped", True, tm.today()):
            state.toast("Well done, love. Fridge things in the fridge, then sit down.", "ok")
            router.go("home")

    @handle("unshop_button", "click")
    def unshop_button_click(self, **event_args):
        r = state.call("set_shopped", False, tm.today())
        if r:
            self._take(r)
