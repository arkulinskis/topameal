from anvil import *

from ._anvil_designer import HomeTemplate
from ... import router, state, tm


class Home(HomeTemplate):
    """#home ("This week", Operate): Mom's plan for the member. Her note, who it's shared with, the first-visit guesses,
    then one hero (go shopping / tonight's dinner / all done), the dinners in spoilage order (Items/WeekCard, one
    "No thanks" each: Mom swaps it), the set-aside tray (Items/TrayChip: change your mind) and "Start a whole new week".
    Server: get_week, say_no, say_yes, confirm_kitchen, new_plan, too_tired (server_code/Kitchen.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.w: dict = {}
        self.k: dict = {}
        self.fresh = None  # the dinner that just arrived (it glows once)
        self.week_panel.add_event_handler("x-no", self._no)
        self.tray_panel.add_event_handler("x-yes", self._yes)
        r = state.call("get_week", tm.today())
        if r:
            self._take(r, toast=False)

    def _take(self, r, toast=True):
        self.w, self.k = r["week"], r["kitchen"]
        self._draw()
        if toast and r.get("note"):
            state.toast(r["note"])

    # ---- drawing
    def _mom(self, w, nxt):
        hi = tm.greet(state.me())
        if w["all_done"]:
            return [hi + " Every dinner cooked this week. I'm so proud of you."]
        past = next((s for s in w["slots"] if s.get("past_best") and not s.get("cooked")), None)
        if past:
            return [hi + " Check the %s before you cook it, love." % past["perishable"], "If it smells off, bin it. Not worth a bad tummy."]
        if not w["shopped"]:
            second = ("The %s go in more than one dinner, so nothing gets wasted." % tm.words(w["shared"][:3]) if w["shared"]
                      else "Don't fancy one? Say no and I'll find another.")
            return [hi + " I've sorted this week's dinners. All you have to do is the shopping.", second]
        if nxt:
            return [hi + " Tonight it's %s." % nxt["name"].lower(),
                    "%d minutes and %d things to wash. You can do that." % (nxt["minutes"], nxt["dish_count"])]
        return [hi]

    def _draw(self):
        w, k, n = self.w, self.k, self.dom_nodes
        nxt = next((s for s in w["slots"] if s["key"] == w["next"]), None)
        self.note.say(self._mom(w, nxt))

        others = [p["name"].split(" ")[0] for p in k["household"] if not p.get("me")]
        self.with_line.visible = bool(k["shared"])
        n["with_text"].textContent = "Shared with %s. Same plan, same list." % tm.words(others)

        self.assume_box.visible = not k["confirmed"]
        n["f_people"].textContent = tm.plural(k["people"], "person", "people")
        n["f_nights"].textContent = "%d dinners a week" % k["nights"]
        n["f_budget"].textContent = k["options"]["budget"][k["budget"] - 1]["label"] + " budget"
        n["f_home"].textContent = tm.cap(tm.words(w["at_home"])) + " at home"

        done, shopped = w["all_done"], bool(w["shopped"])
        self.done_hero.visible = done
        self.shop_hero.visible = bool(nxt) and not done and not shopped
        self.tonight_hero.visible = bool(nxt) and not done and shopped
        if done:
            n["done_text"].textContent = "%s cooked with Topameal so far. Shall I plan the next week?" % tm.plural(w["story"]["cooked"], "dinner")
        elif nxt and not shopped:
            n["shop_text"].textContent = "%s for %s, in the order you walk the shop. Rice, pasta and potatoes you already have." % (
                tm.plural(w["list"]["total"], "thing"), tm.plural(w["totals"]["dinners"], "dinner"))
            state.set_attr(self.peek_link, "href", router.href("cook", nxt["key"]))
        elif nxt:
            today_due = bool(nxt.get("cook_by")) and tm.days_from(nxt["cook_by"]) <= 0
            label = "Check this one first" if nxt.get("past_best") else ("Tonight, please" if today_due else "Tonight")
            n["t_title"].textContent = "%s: %s" % (label, nxt["name"])
            n["t_blurb"].textContent = nxt["blurb"]
            tm.set_base(n["t_base"], nxt["base"], big=True)
            self.t_meta.topper = nxt
            state.set_attr(self.cook_link, "href", router.href("cook", nxt["key"]))
            self.tired_button.visible = len([s for s in w["slots"] if not s.get("cooked")]) > 1

        has = bool(w["slots"])
        self.plan_part.visible = has
        self.empty_part.visible = not has
        if has:
            n["plan_title"].textContent = "This week" if done else "In this order"
            n["plan_sub"].textContent = ("Shopped " + tm.day(w["shopped"])) if shopped else "Most perishable first"
            self.week_panel.items = [dict(s, i=i, fresh=s["key"] == self.fresh) for i, s in enumerate(w["slots"])]
            t = w["totals"]
            n["sum_text"].textContent = "%s · %d things to wash all week · roughly a" % (tm.plural(t["dinners"], "dinner"), t["dishes"])
            tm.set_tier(n["sum_tier"], t["tier"], t["tier_label"])
            n["sum_word"].textContent = t["tier_label"].lower()
        self.tray_part.visible = bool(w["nos"])
        self.tray_panel.items = w["nos"]
        self.fresh_part.visible = has and not done
        self.fresh = None

    # ---- actions
    def _no(self, key=None, card=None, **event_args):
        if card is not None:
            card.fade(True)
        r = state.call("say_no", key, tm.today())
        if r:
            self.fresh = r.get("replaced_by")
            self._take(r)
        elif card is not None:
            card.fade(False)

    def _yes(self, key=None, **event_args):
        r = state.call("say_yes", key, tm.today())
        if r:
            self.fresh = key
            self._take(r)

    @handle("tired_button", "click")
    def tired_button_click(self, **event_args):
        r = state.call("too_tired", tm.today())
        if r:
            self.fresh = r.get("tonight")
            self._take(r)

    @handle("confirm_button", "click")
    def confirm_button_click(self, **event_args):
        self.k["confirmed"] = True
        self.assume_box.visible = False
        state.call_quiet("confirm_kitchen")
        state.toast("Good. Leave it with me.")

    @handle("fresh_now_button", "click")
    def fresh_now_button_click(self, **event_args):
        r = state.call("new_plan", tm.today())
        if r:
            self._take(r)

    @handle("fresh_button", "click")
    def fresh_button_click(self, **event_args):
        if confirm("I'll plan fresh dinners and a new list. This week's plan goes into the history.",
                   title="Start a whole new week?", buttons=[("Cancel", False), ("Yes, start fresh", True)], role="app-dialog"):
            r = state.call("new_plan", tm.today())
            if r:
                self._take(r)
