"""Mom's planning brain: which toppers this week, in which order, and the shopping list.

Pure functions on plain data (no tables), so they are easy to test. Kitchen.py stores the results.
  kitchen  = {"people": 2, "nights": 4, "budget": 2, "avoid": [...], "never": [...]}
  slot     = {"key": "tuscan_chicken", "cooked": None | "YYYY-MM-DD"}
How Mom picks: toppers that share fresh ingredients (less waste, cheaper), different proteins and bases
(variety), cheaper tiers unless treats are allowed, fewer dishes, and a little luck. She also leans towards toppers
that use up what's probably still at home from earlier weeks (`have`, see leftovers()) and the household's
favourites (`loved`: dinners rated "Everyone ate it"), which come back now and then but never two weeks running
when there's enough else (last week's dinners are soft-excluded).
Order: cooked first, then the most perishable first (fish, mince, chicken ... tins last).
"""
import datetime as dt
import math
import random

from . import Recipes as R

FRESH_DAYS = 14   # ingredients that keep less than this are the ones worth sharing between dinners
MAX_NIGHTS = 7
HOME_AISLE = ("home", "Probably still at home")   # the list's last group: jars and bunches bought on an earlier shop
HAVE_BONUS = 1.0     # per ingredient probably still at home (cupboard things count less: everyone has those)
HAVE_CUPBOARD = 0.3
LOVED_BONUS = 2.0    # a household favourite


def protein(t):
    return next((p for p in R.PROTEINS if p in t["tags"]), "veg")


def ingredient_keys(t):
    return {k for k, _ in t["ing"]}


def candidates(kitchen, exclude):
    return [t for t in R.TOPPERS if t["key"] not in exclude
            and R.is_allowed(t, kitchen.get("avoid"), kitchen.get("budget", 2))]


def score(t, chosen, budget, rng, have=(), loved=()):
    s = rng.random() * 3.0
    for k in ingredient_keys(t) & set(have or ()):
        s += HAVE_CUPBOARD if R.GROCERIES[k][2] == "cupboard" else HAVE_BONUS
    if t["key"] in (loved or ()):
        s += LOVED_BONUS
    have, proteins, bases = set(), [], []
    for c in chosen:
        have |= ingredient_keys(c)
        proteins.append(protein(c))
        bases.append(c["base"])
    for k in ingredient_keys(t) & have:
        aisle, keeps = R.GROCERIES[k][2], R.GROCERIES[k][3]
        s += 0.4 if aisle == "cupboard" else (2.0 if keeps <= FRESH_DAYS else 0.8)
    s -= 4.0 * proteins.count(protein(t))
    s -= 1.5 * bases.count(t["base"])
    s -= (0.8 if budget < 3 else 0.2) * (t["tier"] - 1)
    s -= 0.25 * len(t["dishes"])
    return s


def pick(n, kitchen, keep=(), exclude=(), soft_exclude=(), rng=None, have=(), loved=()):
    """Up to n topper keys: the `keep` ones first, then Mom's choices. `soft_exclude` (e.g. last week's
    toppers) is avoided unless there aren't enough others. `have`: grocery keys probably still at home;
    `loved`: the household's favourite topper keys (both only nudge the score)."""
    rng = rng or random.Random()
    n = max(0, min(int(n), MAX_NIGHTS))
    chosen = [R.BY_KEY[k] for k in keep if k in R.BY_KEY]
    hard = set(exclude) | set(kitchen.get("never") or []) | {t["key"] for t in chosen}
    pool = candidates(kitchen, hard | set(soft_exclude))
    if len(pool) < n - len(chosen):
        pool = candidates(kitchen, hard)
    while len(chosen) < n and pool:
        best = max(pool, key=lambda t: score(t, chosen, kitchen.get("budget", 2), rng, have, loved))
        chosen.append(best)
        pool.remove(best)
    return [t["key"] for t in chosen]


def replacement(kitchen, others, exclude, rng=None, have=(), loved=()):
    """One new topper that goes well with `others`, or None."""
    got = pick(len(others) + 1, kitchen, keep=others, exclude=exclude, rng=rng, have=have, loved=loved)
    return got[-1] if len(got) > len(others) else None


def order(slots):
    """Cooked first (as they were), then tonight's pick ("too tired"), then the rest most-perishable first."""
    done = [s for s in slots if s.get("cooked")]
    todo = [s for s in slots if not s.get("cooked")]
    todo.sort(key=lambda s: (0 if s.get("pin") else 1, R.keeps(R.BY_KEY[s["key"]]) if s["key"] in R.BY_KEY else 999))
    return done + todo


def short_name(gkey, plural=False):
    one, many = R.GROCERIES[gkey][0], R.GROCERIES[gkey][1]
    text = many if plural else one
    if " of " in text:
        text = text.split(" of ", 1)[1]
    return text.split(" (")[0]


def scaled(amount, people, mode):
    if mode == "one":
        return 1
    return max(1, int(math.ceil(amount * people / 2.0 - 1e-9)))


def grocery_text(gkey, qty):
    one, many = R.GROCERIES[gkey][0], R.GROCERIES[gkey][1]
    return "%d %s" % (qty, one if qty == 1 else many)


def ticks(value):
    """The week's ticked lines as {grocery key: first name of who ticked it} (older rows stored a list)."""
    if isinstance(value, dict):
        return dict(value)
    return {k: "" for k in (value or [])}


def leftovers(past, today):
    """What's probably still at home from earlier shops: {grocery key: 'YYYY-MM-DD' it was bought}.
    `past` = [(shopped date, grocery keys bought that week)], any order. Only "one" groceries count (a jar, a bunch,
    a bag: one covers a week, so some is usually left); "sum" groceries get used up. A grocery drops out once its
    keep days have passed (shopped + keeps - 1 < today), so a 5-day bunch of parsley goes, a jar of curry paste stays.
    If a week ticked something that was probably still at home then, the older date stands: ticking it meant
    "I have it", not "I bought a new one", so its keep days don't start again."""
    bought = {}
    for shopped, keys in sorted(((d, ks) for d, ks in past if d is not None), key=lambda x: x[0]):
        for g in keys or ():
            info = R.GROCERIES.get(g)
            if info is None or info[4] != "one":
                continue
            prev = bought.get(g)
            if prev is not None and prev + dt.timedelta(days=info[3] - 1) >= shopped:
                continue
            bought[g] = shopped
    return {g: d.isoformat() for g, d in bought.items() if d + dt.timedelta(days=R.GROCERIES[g][3] - 1) >= today}


def shopping(keys, people, checked=(), home=None):
    """The merged list for these toppers, grouped by aisle in walking order. `checked`: ticks() dict or a list.
    `home`: leftovers() of earlier weeks; those lines move to a last group, "Probably still at home", with `since`."""
    acc, order_seen = {}, []
    for key in keys:
        t = R.BY_KEY.get(key)
        if not t:
            continue
        for g, amount in t["ing"]:
            if g not in acc:
                acc[g] = {"amount": 0.0, "for": []}
                order_seen.append(g)
            acc[g]["amount"] += amount
            if t["name"] not in acc[g]["for"]:
                acc[g]["for"].append(t["name"])
    checked = ticks(checked)
    home = home or {}
    aisles, total, done = [], 0, 0
    for aisle, label in R.AISLES + [HOME_AISLE]:
        items = []
        for g in order_seen:
            one, many, a, keeps, mode = R.GROCERIES[g]
            if (HOME_AISLE[0] if g in home else a) != aisle:
                continue
            qty = scaled(acc[g]["amount"], people, mode)
            items.append({"key": g, "text": grocery_text(g, qty), "for": acc[g]["for"], "checked": g in checked,
                          "by": checked.get(g) or None, "keeps": keeps, "perishable": keeps <= 3 and g not in home,
                          "since": home.get(g)})
        items.sort(key=lambda i: (i["keeps"], i["text"]) if aisle == "meat" else (str(i["text"]).split(" ", 1)[1],))
        if items:
            total += len(items)
            done += len([i for i in items if i["checked"]])
            aisles.append({"key": aisle, "label": label, "items": items})
    return {"aisles": aisles, "total": total, "done": done}


def home_notes(keys, home):
    """For Mom's note: groceries on this week's list that are probably still at home, the most telling first
    (a jar only one or two toppers use beats the garlic everything uses; cupboard things are left out).
    [{"key": "salsa", "name": "salsa", "dinner": "Taco beef & beans"}]."""
    uses = {}
    for t in R.TOPPERS:
        for g in ingredient_keys(t):
            uses[g] = uses.get(g, 0) + 1
    out, seen = [], set()
    for key in keys:
        t = R.BY_KEY.get(key)
        if not t:
            continue
        for g, _ in t["ing"]:
            if g in (home or {}) and R.GROCERIES[g][2] != "cupboard" and g not in seen:
                seen.add(g)
                out.append({"key": g, "name": short_name(g), "dinner": t["name"], "uses": uses.get(g, 0)})
    out.sort(key=lambda o: (o["uses"], o["name"]))
    return [{"key": o["key"], "name": o["name"], "dinner": o["dinner"]} for o in out]


def shared(keys):
    """Fresh ingredients that go into two or more of these toppers (Mom likes to point these out)."""
    count = {}
    for key in keys:
        for g in ingredient_keys(R.BY_KEY[key]):
            count[g] = count.get(g, 0) + 1
    out = [g for g, n in count.items() if n >= 2 and R.GROCERIES[g][2] != "cupboard" and R.GROCERIES[g][3] <= FRESH_DAYS]
    out.sort(key=lambda g: (-count[g], g))
    return [short_name(g, plural=R.GROCERIES[g][4] == "sum" and " of " not in R.GROCERIES[g][0]) for g in out]


def perishable_item(t):
    g = min((k for k, _ in t["ing"]), key=lambda k: R.GROCERIES[k][3])
    return short_name(g, plural=True)


def dish_list(t):
    return [R.DISHES[d] for d in t["dishes"]] + [R.DISHES["pot"]]


def topper_card(t):
    """What a page needs to show a topper (no steps)."""
    return {"key": t["key"], "name": t["name"], "blurb": t["blurb"], "base": t["base"], "also": t["also"],
            "tier": t["tier"], "tier_label": R.TIERS[t["tier"]], "minutes": t["minutes"],
            "dishes": dish_list(t), "dish_count": len(t["dishes"]) + 1, "keeps": R.keeps(t),
            "perishable": perishable_item(t), "tags": [x for x in t["tags"] if x in ("spicy", "nuts")]}


def schedule(slots, today, shopped=None):
    """Cards for the slots, with cook-by dates once shopped, and a freezer tip when a dinner is planned
    after its shopping would go off. Dinners are assumed one a day, in order, from today (or the shop day)."""
    out, pos = [], 0
    start = max(today, shopped) if shopped else today
    for s in slots:
        t = R.BY_KEY.get(s["key"])
        if not t:
            continue
        card = topper_card(t)
        card.update(cooked=s.get("cooked"), cook_by=None, planned=None, freeze=False, past_best=False)
        if not s.get("cooked"):
            k = card["keeps"]
            planned = start + dt.timedelta(days=pos)
            card["planned"] = planned.isoformat()
            base_day = shopped or today
            if k < 30:
                cook_by = base_day + dt.timedelta(days=k - 1)
                card["freeze"] = planned > cook_by and k <= 3
                if shopped:
                    card["cook_by"] = cook_by.isoformat()
                    card["past_best"] = today > cook_by
            pos += 1
        out.append(card)
    return out


def easiest(slots):
    """For "too tired tonight": the uncooked slot with the fewest dishes, then the fewest minutes."""
    todo = [s for s in slots if not s.get("cooked") and s["key"] in R.BY_KEY]
    if not todo:
        return None
    return min(todo, key=lambda s: (len(R.BY_KEY[s["key"]]["dishes"]), R.BY_KEY[s["key"]]["minutes"], todo.index(s)))["key"]


def tier_of(keys):
    tiers = [R.BY_KEY[k]["tier"] for k in keys if k in R.BY_KEY]
    if not tiers:
        return 1
    return int(round(sum(tiers) / float(len(tiers)) + 1e-9))


def totals(keys):
    ts = [R.BY_KEY[k] for k in keys if k in R.BY_KEY]
    tier = tier_of(keys)
    return {"dinners": len(ts), "dishes": sum(len(t["dishes"]) + 1 for t in ts), "minutes": sum(t["minutes"] for t in ts),
            "tier": tier, "tier_label": R.TIERS[tier]}
