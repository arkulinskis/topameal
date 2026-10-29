"""The household's kitchen (settings) and its week: Mom's plan, the no-thanks tray, cooking, shopping,
"too tired tonight", and sharing the kitchen with the people you live with.

Tables: kitchens (one per owner; others join through users.kitchen), weeks (one row per plan, belonging to a
kitchen; the newest `created` is the current one). A user's kitchen is users.kitchen if they joined one,
otherwise their own (made on first use). Leaving sets users.kitchen back to None: their own plan returns.
Everyone in a household can see and change the plan, the list and the settings; only the owner removes people.
simpleObject columns are always reassigned whole (Anvil doesn't save changes made inside a list).
Every callable takes the browser's local date (`today`, YYYY-MM-DD) so "tonight" and cook-by dates match
the person's day; it is clamped to within 2 days of the server's date.
"""
import datetime as dt
import random
import secrets

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import DemoData
from . import Planner as P
from . import Recipes as R

DEFAULTS = {"people": 2, "nights": 4, "budget": 2}
PLAN_DAYS = 9          # a plan older than this is replaced by a fresh one when the member comes back
NEVER_AFTER = 3        # saying no to the same topper this many times puts it on the never list
MAX_MEMBERS = 8


def today_of(value):
    server = C.now().date()
    try:
        d = dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return server
    return d if abs((d - server).days) <= 2 else server


# ------------------------------------------------------------------------------------------- kitchen
def own_kitchen(user, create=True):
    k = app_tables.kitchens.get(owner=user)
    if k is None and create:
        k = app_tables.kitchens.add_row(owner=user, people=DEFAULTS["people"], nights=DEFAULTS["nights"],
                                        budget=DEFAULTS["budget"], avoid=[], never=[], no_counts={},
                                        confirmed=False, created=C.now(), is_demo=bool(user["is_demo"]))
    return k


def kitchen_row(user):
    """The kitchen this user cooks from: a household they joined, or their own."""
    return user["kitchen"] or own_kitchen(user)


def members(k):
    """Everyone sharing kitchen k: the owner first (if they still cook here), then who joined, oldest first."""
    owner = k["owner"]
    out = [owner] if owner is not None and owner["kitchen"] in (None, k) else []
    joined = sorted((u for u in app_tables.users.search(kitchen=k) if u != owner), key=lambda u: u["signed_up"] or C.now())
    return out + joined


def first_name(user):
    return C.name_of(user).split(" ")[0]


def kitchen_plain(k):
    return {"people": int(k["people"] or 2), "nights": int(k["nights"] or 4), "budget": int(k["budget"] or 2),
            "avoid": list(k["avoid"] or []), "never": list(k["never"] or [])}


def kitchen_dict(k, user=None):
    d = kitchen_plain(k)
    d["never"] = [{"key": key, "name": R.name_of(key)} for key in d["never"] if key in R.BY_KEY]
    d["confirmed"] = bool(k["confirmed"])
    d["options"] = {"avoid": [{"key": a, "label": label} for a, label in R.AVOID],
                    "budget": [{"key": n, "label": R.TIERS[n]} for n in (1, 2, 3)]}
    people = members(k)
    d["household"] = [{"id": u.get_id(), "name": C.name_of(u), "me": u == user, "owner": u == k["owner"]} for u in people]
    d["is_owner"] = user is not None and user == k["owner"]
    d["shared"] = len(people) > 1
    return d


# ------------------------------------------------------------------------------------------- weeks
def _weeks(k):
    return app_tables.weeks.search(tables.order_by("created", ascending=False), kitchen=k)


def _latest(k):
    """The current plan: the newest one made (two plans can start on the same day)."""
    return next(iter(_weeks(k)), None)


def _new_week(user, k, today, avoid_keys=()):
    kp = kitchen_plain(k)
    keys = P.pick(kp["nights"], kp, soft_exclude=avoid_keys)
    slots = P.order([{"key": key, "cooked": None} for key in keys])
    stamp, prev = C.now(), _latest(k)
    if prev is not None and prev["created"] is not None and stamp <= prev["created"]:
        stamp = prev["created"] + dt.timedelta(microseconds=1)   # the newest plan must sort first, even within one clock tick
    return app_tables.weeks.add_row(kitchen=k, owner=user, started=today, slots=slots, nos=[], checked={}, shopped=None,
                                    created=stamp, updated=C.now(), is_demo=bool(user["is_demo"]))


def current_week(user, k, today):
    w = _latest(k)
    if w is not None and (today - w["started"]).days <= PLAN_DAYS:
        return w
    last = [s["key"] for s in (w["slots"] if w else [])]
    return _new_week(user, k, today, last)


def week_dict(user, w, k, today):
    slots = list(w["slots"] or [])
    keys = [s["key"] for s in slots]
    cards = P.schedule(slots, today, w["shopped"])
    todo = [c for c in cards if not c["cooked"]]
    kp = kitchen_plain(k)
    history = list(_weeks(k))
    return {"id": w.get_id(), "started": C.iso(w["started"]), "shopped": C.iso(w["shopped"]),
            "slots": cards, "next": todo[0]["key"] if todo else None, "all_done": bool(cards) and not todo,
            "nos": [{"key": n["key"], "name": R.name_of(n["key"]), "auto": bool(n.get("auto"))}
                    for n in (w["nos"] or []) if n["key"] in R.BY_KEY],
            "list": P.shopping(keys, kp["people"], w["checked"]),
            "totals": P.totals(keys), "shared": P.shared(keys), "people": kp["people"],
            "at_home": R.AT_HOME,
            "story": {"weeks": len(history), "cooked": sum(len([s for s in (h["slots"] or []) if s.get("cooked")]) for h in history)}}


def _reply(user, w, k, today, note=None, **extra):
    out = {"week": week_dict(user, w, k, today), "kitchen": kitchen_dict(k, user), "note": note}
    out.update(extra)
    return C.ok(**out)


def _save(w, **cols):
    cols["updated"] = C.now()
    w.update(**cols)


def _find(slots, key, cooked=None):
    for i, s in enumerate(slots):
        if s["key"] == key and (cooked is None or bool(s.get("cooked")) == cooked):
            return i
    return None


@anvil.server.callable(require_user=True)
def get_week(today=None):
    """The home page: the current plan (made on the spot the first time, or when the last one is old)."""
    user = C.require_user()
    DemoData.ensure_loaded()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    return _reply(user, w, k, today)


@anvil.server.callable(require_user=True)
def say_no(key, today=None):
    """'Not this one': Mom puts it on the tray and suggests something else that fits."""
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    slots = [dict(s) for s in (w["slots"] or [])]
    i = _find(slots, key, cooked=False)
    if i is None:
        return C.fail("That one isn't waiting on this week's plan.")
    nos = [dict(n) for n in (w["nos"] or []) if n["key"] != key]
    counts = dict(k["no_counts"] or {})
    counts[key] = int(counts.get(key, 0)) + 1
    never = list(k["never"] or [])
    note = None
    if counts[key] >= NEVER_AFTER and key not in never:
        never.append(key)
        note = "That's three times you've said no to %s. I won't suggest it again. (Changed your mind? It's in You.)" % R.name_of(key)
    k.update(no_counts=counts, never=never)
    others = [s["key"] for j, s in enumerate(slots) if j != i]
    exclude = set(never) | {n["key"] for n in nos} | {key} | set(others)
    new = P.replacement(kitchen_plain(k), others, exclude)
    if new:
        slots[i] = {"key": new, "cooked": None}
        nos.append({"key": key, "by": new})
        note = note or random.choice(["Alright, love. How about %s instead?", "No problem. %s, then?",
                                      "Fair enough. Let's do %s instead.", "Say no more. %s it is."]) % R.name_of(new)
    else:
        slots.pop(i)
        nos.append({"key": key, "by": None})
        note = note or "That was the last idea I had that fits, so it's one dinner fewer this week."
    _save(w, slots=P.order(slots), nos=nos)
    return _reply(user, w, k, today, note, replaced_by=new)


@anvil.server.callable(require_user=True)
def say_yes(key, today=None):
    """Changed your mind: the topper comes back where its replacement is (which goes on the tray instead)."""
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    nos = [dict(n) for n in (w["nos"] or [])]
    entry = next((n for n in nos if n["key"] == key), None)
    if entry is None:
        return C.fail("I can't find that one on the tray.")
    nos = [n for n in nos if n["key"] != key]
    chain = {n["key"]: n.get("by") for n in nos}
    by, seen = entry.get("by"), set()
    while by in chain and by not in seen:
        seen.add(by)
        by = chain[by]
    slots = [dict(s) for s in (w["slots"] or [])]
    i = _find(slots, by, cooked=False) if by else None
    displaced = None
    if i is None and len(slots) >= P.MAX_NIGHTS:
        todo = [j for j, s in enumerate(slots) if not s.get("cooked")]
        i = todo[-1] if todo else None
    if i is not None:
        displaced = slots[i]["key"]
        slots[i] = {"key": key, "cooked": None}
        nos.append({"key": displaced, "by": key, "auto": True})
    else:
        slots.append({"key": key, "cooked": None})
    counts = dict(k["no_counts"] or {})
    counts[key] = max(0, int(counts.get(key, 0)) - 1)
    k.update(no_counts=counts, never=[x for x in (k["never"] or []) if x != key])
    _save(w, slots=P.order(slots), nos=nos)
    note = "%s is back on. " % R.name_of(key) + ("I set %s aside to make room." % R.name_of(displaced) if displaced
                                                 else "One more dinner this week, then.")
    return _reply(user, w, k, today, note)


@anvil.server.callable(require_user=True)
def set_cooked(key, flag=True, today=None):
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    slots = [dict(s) for s in (w["slots"] or [])]
    i = _find(slots, key, cooked=not flag)
    if i is None:
        i = _find(slots, key)
        if i is None:
            return C.fail("That one isn't on this week's plan.")
    slots[i]["cooked"] = today.isoformat() if flag else None
    _save(w, slots=P.order(slots))
    return _reply(user, w, k, today)


@anvil.server.callable(require_user=True)
def set_checked(item, flag=True, today=None):
    """Tick (or untick) a line on the shopping list. Quiet and small: the page keeps its own state."""
    user = C.require_user()
    if item not in R.GROCERIES:
        return C.fail("That isn't on the list.")
    today = today_of(today)
    w = current_week(user, kitchen_row(user), today)
    checked = P.ticks(w["checked"])
    checked.pop(item, None)
    if flag:
        checked[item] = first_name(user)
    _save(w, checked=checked)
    return C.ok(checked=len(checked))


@anvil.server.callable(require_user=True)
def get_ticks(today=None):
    """Polled by the shopping list while a household shops together: who ticked what, and whether it's done."""
    user = C.require_user()
    w = current_week(user, kitchen_row(user), today_of(today))
    return {"week": w.get_id(), "checked": P.ticks(w["checked"]), "shopped": C.iso(w["shopped"]),
            "slots": [s["key"] for s in (w["slots"] or [])]}


@anvil.server.callable(require_user=True)
def set_shopped(flag=True, today=None):
    """'I've done the shopping': from now on each dinner has a cook-by day."""
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    cols = {"shopped": today if flag else None}
    if flag:
        keys = [s["key"] for s in (w["slots"] or [])]
        ticked = P.ticks(w["checked"])
        name = first_name(user)
        cols["checked"] = {i["key"]: ticked.get(i["key"]) or name for a in P.shopping(keys, 2)["aisles"] for i in a["items"]}
    _save(w, **cols)
    return _reply(user, w, k, today)


@anvil.server.callable(require_user=True)
def new_plan(today=None):
    """A whole new week (the old one stays in the history)."""
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    if C.rate_limited("new_plan", 20, 3600):
        return C.fail("That's a lot of new plans in one hour. Let's stick with this one for now, love.")
    old = _latest(k)
    avoid = [s["key"] for s in (old["slots"] if old else [])]
    w = _new_week(user, k, today, avoid)
    return _reply(user, w, k, today, "Here's a fresh week. Same deal: say no to anything you don't fancy.")


@anvil.server.callable(require_user=True)
def get_cook(key, today=None):
    """Everything the cook page needs for one topper, scaled to the household."""
    user = C.require_user()
    t = R.BY_KEY.get(key)
    if t is None:
        return C.fail("I don't know that recipe.")
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    people = kitchen_plain(k)["people"]
    slots = list(w["slots"] or [])
    card = next((c for c in P.schedule(slots, today, w["shopped"]) if c["key"] == key), None)
    base = R.BASES[t["base"]]
    return C.ok(topper=dict(P.topper_card(t), steps=t["steps"], tip=t["tip"],
                            ingredients=[P.grocery_text(g, P.scaled(a, people, R.GROCERIES[g][4])) for g, a in t["ing"]]),
                base=dict(base, key=t["base"]), people=people, in_plan=card is not None,
                cooked=card["cooked"] if card else None, cook_by=card["cook_by"] if card else None)


@anvil.server.callable(require_user=True)
def get_kitchen():
    user = C.require_user()
    return C.ok(kitchen=kitchen_dict(kitchen_row(user), user))


@anvil.server.callable(require_user=True)
def save_kitchen(data, today=None):
    """Household settings. The current plan is refitted: dinners that no longer fit are swapped,
    and dinners are added or removed to match the number of nights (cooked ones always stay)."""
    user = C.require_user()
    if not isinstance(data, dict):
        return C.fail("Something went wrong with that form.")
    k = kitchen_row(user)
    cols = {"confirmed": True}
    for name, lo, hi in (("people", 1, 8), ("nights", 2, 7), ("budget", 1, 3)):
        if name in data:
            try:
                v = int(data[name])
            except (TypeError, ValueError):
                return C.fail("Please pick a number for %s." % name)
            if not lo <= v <= hi:
                return C.fail("%s has to be between %d and %d." % (name.capitalize(), lo, hi))
            cols[name] = v
    if "avoid" in data:
        allowed = {a for a, _ in R.AVOID}
        cols["avoid"] = sorted({a for a in (data["avoid"] or []) if a in allowed})
    if "never" in data:
        keep = set(data["never"] or [])
        cols["never"] = [x for x in (k["never"] or []) if x in keep]
        counts = dict(k["no_counts"] or {})
        for x in (k["never"] or []):
            if x not in keep:
                counts[x] = 0
        cols["no_counts"] = counts
    k.update(**cols)
    today = today_of(today)
    w = current_week(user, k, today)
    kp = kitchen_plain(k)
    slots = [dict(s) for s in (w["slots"] or [])]
    fits = [s for s in slots if s.get("cooked") or (R.is_allowed(R.BY_KEY[s["key"]], kp["avoid"], kp["budget"])
                                                    and s["key"] not in kp["never"])]
    cooked = len([s for s in fits if s.get("cooked")])
    while len(fits) > max(kp["nights"], cooked):
        last = max(j for j, s in enumerate(fits) if not s.get("cooked"))
        fits.pop(last)
    if len(fits) < kp["nights"]:
        nos = {n["key"] for n in (w["nos"] or [])}
        keys = P.pick(kp["nights"], kp, keep=[s["key"] for s in fits], exclude=nos)
        fits += [{"key": key, "cooked": None} for key in keys[len(fits):]]
    changed = [s["key"] for s in fits] != [s["key"] for s in slots]
    _save(w, slots=P.order(fits))
    note = "Thank you, love. I've changed this week's plan to match." if changed else "Noted, love. This week's plan still fits."
    return _reply(user, w, k, today, note)


@anvil.server.callable(require_user=True)
def confirm_kitchen():
    """'That's right': hides the first-visit note about Mom's assumptions."""
    user = C.require_user()
    kitchen_row(user)["confirmed"] = True
    return C.ok()


@anvil.server.callable
def sample_week():
    """A peek for visitors on the landing page: a plan for two, nothing saved."""
    kp = dict(DEFAULTS, avoid=[], never=[])
    keys = [s["key"] for s in P.order([{"key": key, "cooked": None} for key in P.pick(4, kp)])]
    return {"slots": [P.topper_card(R.BY_KEY[key]) for key in keys], "list": P.shopping(keys, 2),
            "totals": P.totals(keys), "shared": P.shared(keys), "at_home": R.AT_HOME}


@anvil.server.callable(require_user=True)
def too_tired(today=None):
    """"Too tired tonight": the easiest dinner left (fewest dishes, then quickest) moves to tonight."""
    user = C.require_user()
    today = today_of(today)
    k = kitchen_row(user)
    w = current_week(user, k, today)
    slots = [dict(s) for s in (w["slots"] or [])]
    todo = [s for s in slots if not s.get("cooked")]
    if len(todo) < 2:
        return _reply(user, w, k, today, "This is the last one, love. Or toast. Toast is dinner too.")
    current = todo[0]["key"]
    easy = P.easiest(todo)
    if easy == current:
        return _reply(user, w, k, today, "This is already the easiest one, love. Or toast. Toast is dinner too.")
    for s in slots:
        s.pop("pin", None)
        if s["key"] == easy and not s.get("cooked"):
            s["pin"] = today.isoformat()
    _save(w, slots=P.order(slots))
    t, was = R.BY_KEY[easy], R.BY_KEY[current]
    note = "Then let's do %s tonight. Only %d things to wash." % (t["name"].lower(), len(t["dishes"]) + 1)
    if w["shopped"] and R.keeps(was) <= 3:
        note += " Put the %s in the freezer now; it won't wait." % P.perishable_item(was)
    return _reply(user, w, k, today, note, tonight=easy)


# ------------------------------------------------------------------------------------------- household
def _code():
    return secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")


def _by_code(code):
    if not isinstance(code, str) or not 6 <= len(code) <= 40:
        return None
    return app_tables.kitchens.get(invite_code=code)


@anvil.server.callable(require_user=True)
def get_invite(fresh=False):
    """The invite code for the caller's household (made on first use). fresh=True makes a new one, so the
    old link stops working (owner only)."""
    user = C.require_user()
    k = kitchen_row(user)
    if fresh:
        if k["owner"] != user:
            return C.fail("Only %s can make a new link." % first_name(k["owner"]))
        k["invite_code"] = None
    if not k["invite_code"]:
        k["invite_code"] = _code()
    return C.ok(code=k["invite_code"], kitchen=kitchen_dict(k, user))


@anvil.server.callable
def peek_invite(code):
    """The join page: whose kitchen this link is for (first names only), before signing in or joining."""
    if C.rate_limited("peek_invite", 30, 3600):
        return C.fail("Too many tries. Please wait a little and open the link again.")
    k = _by_code(code)
    if k is None:
        return C.fail("This invite link doesn't work any more. Ask for a new one.")
    user = C.me()
    names = [first_name(u) for u in members(k)]
    return C.ok(owner=first_name(k["owner"]), names=names, full=len(names) >= MAX_MEMBERS,
                member=user is not None and kitchen_row(user) == k)


@anvil.server.callable(require_user=True)
def join_household(code, today=None):
    user = C.require_user()
    if C.rate_limited("join", 20, 3600):
        return C.fail("Too many tries. Please wait a little.")
    k = _by_code(code)
    if k is None:
        return C.fail("This invite link doesn't work any more. Ask for a new one.")
    if kitchen_row(user) == k:
        return C.ok(note="You're already in this kitchen.")
    if len(members(k)) >= MAX_MEMBERS:
        return C.fail("That kitchen is full (%d people)." % MAX_MEMBERS)
    user["kitchen"] = None if k["owner"] == user else k
    return C.ok(note="You're in. Same plan, same list, from now on.")


@anvil.server.callable(require_user=True)
def leave_household():
    """Back to your own kitchen and your own plan."""
    user = C.require_user()
    if user["kitchen"] is None:
        return C.fail("This is your own kitchen, love. You can't leave it.")
    user["kitchen"] = None
    return C.ok(kitchen=kitchen_dict(kitchen_row(user), user), note="Back in your own kitchen.")


@anvil.server.callable(require_user=True)
def remove_member(user_id):
    """The owner takes someone out of their kitchen (they go back to their own)."""
    me = C.require_user()
    k = kitchen_row(me)
    if k["owner"] != me:
        return C.fail("Only %s can do that." % first_name(k["owner"]))
    other = C.row_by_id(app_tables.users, user_id)
    if other is None or other == me or other["kitchen"] != k:
        return C.fail("That person isn't in your kitchen.")
    other["kitchen"] = None
    return C.ok(kitchen=kitchen_dict(k, me))


# ------------------------------------------------------------------------------------------- admin
def stats():
    """Which toppers get picked, refused and cooked, across every plan."""
    rows = {t["key"]: {"key": t["key"], "name": t["name"], "tier": t["tier"], "base": t["base"],
                       "protein": P.protein(t), "planned": 0, "no": 0, "cooked": 0} for t in R.TOPPERS}
    weeks = app_tables.weeks.search()
    for w in weeks:
        for s in (w["slots"] or []):
            if s["key"] in rows:
                rows[s["key"]]["planned"] += 1
                if s.get("cooked"):
                    rows[s["key"]]["cooked"] += 1
        for n in (w["nos"] or []):
            if n["key"] in rows and not n.get("auto"):
                rows[n["key"]]["no"] += 1
    out = sorted(rows.values(), key=lambda r: (-r["planned"], r["name"]))
    return {"toppers": out, "weeks": len(weeks), "kitchens": len(app_tables.kitchens.search()),
            "cooked": sum(r["cooked"] for r in out), "nos": sum(r["no"] for r in out)}


@anvil.server.callable(require_user=True)
def admin_kitchen_stats():
    C.require_admin()
    return stats()
