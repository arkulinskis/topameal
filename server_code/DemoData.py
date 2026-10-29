"""Demo content, so the app never looks empty. Loaded automatically the first time anyone opens the app
(ensure_loaded), removed or reloaded from Admin -> Demo data. Removing it is remembered: it doesn't come back.

Demo users have is_demo=True and @example.com emails; they can't sign in (no password). Every demo row
is flagged is_demo=True, so remove() deletes exactly what load() added.
Demo households have a kitchen and a week or two of plans, so Admin -> Kitchen has something to show.
"""
import datetime as dt

from anvil.tables import app_tables

from . import common as C

DEMO_USERS = [
    ("Maya Chen", "maya.demo@example.com"),
    ("Theo Martin", "theo.demo@example.com"),
    ("Ines Ozola", "ines.demo@example.com"),
    ("Sam Okafor", "sam.demo@example.com"),
]
SHARED = [(3, 0)]   # (user index, joins the kitchen of user index): Sam shares Maya's kitchen
# Each demo household: (user index, people, nights, budget, avoid, weeks). A week is
# (days ago it started, [(topper key, cooked days after start or None)], [keys said no to], shopped days after start or None).
DEMO_KITCHENS = [
    (0, 1, 4, 2, [], [
        (9, [("lemon_salmon", 0), ("honey_garlic_chicken", 1), ("sausage_peppers", 3), ("tuna_tomato", 5)], ["beef_broccoli"], 0),
        (2, [("tuscan_chicken", 0), ("taco_beef", None), ("chorizo_chickpeas", None), ("red_lentil_dal", None)], ["shakshuka"], 0),
    ]),
    (1, 2, 5, 3, ["fish"], [
        (1, [("steak_bites", 0), ("butter_chicken", None), ("kielbasa_skillet", None), ("halloumi_veg", None), ("garlic_shrimp", None)],
         ["bacon_peas_pasta", "peanut_pork"], 0),
    ]),
    (2, 4, 3, 1, ["vegetarian"], [
        (3, [("mushroom_stroganoff", 0), ("black_bean_chili", 1), ("red_lentil_dal", 2)], [], 0),
    ]),
]
# Tables that hold demo rows (each has an is_demo column). Children before parents.
DEMO_TABLES = ["weeks", "kitchens"]


def state():
    return C.get_setting("demo", "never")  # "never" | "loaded" | "removed"


def ensure_loaded():
    """Call from the app's main data callables: loads the demo once, unless an admin removed it."""
    if state() == "never":
        load()


def load():
    remove(remember=False)
    users = []
    for name, email in DEMO_USERS:
        u = app_tables.users.get(email=email) or app_tables.users.add_row(email=email, enabled=False)
        u.update(display_name=name, is_demo=True, signed_up=C.now() - dt.timedelta(days=30))
        users.append(u)
    today = C.now().date()
    kitchens = {}
    for who, people, nights, budget, avoid, weeks in DEMO_KITCHENS:
        owner = users[who]
        kitchens[who] = app_tables.kitchens.add_row(owner=owner, people=people, nights=nights, budget=budget, avoid=avoid, never=[],
                                    no_counts={}, confirmed=True, created=C.now() - dt.timedelta(days=20), is_demo=True)
        for ago, slots, nos, shopped in weeks:
            start = today - dt.timedelta(days=ago)
            app_tables.weeks.add_row(
                kitchen=kitchens[who], owner=owner, started=start, is_demo=True, checked=[], updated=C.now(),
                created=C.now() - dt.timedelta(days=ago),
                shopped=None if shopped is None else start + dt.timedelta(days=shopped),
                slots=[{"key": k, "cooked": None if c is None else (start + dt.timedelta(days=c)).isoformat()} for k, c in slots],
                nos=[{"key": k, "by": None} for k in nos])
    for who, host in SHARED:
        users[who]["kitchen"] = kitchens[host]
    C.set_setting("demo", "loaded")
    return counts()


def remove(remember=True):
    for u in app_tables.users.search():   # real people who joined a demo kitchen go back to their own
        if u["kitchen"] is not None and u["kitchen"]["is_demo"]:
            u["kitchen"] = None
    for name in DEMO_TABLES:
        for r in getattr(app_tables, name).search(is_demo=True):
            r.delete()
    for u in app_tables.users.search(is_demo=True):
        u.delete()
    if remember:
        C.set_setting("demo", "removed")
    return counts()


def counts():
    out = {"users": len(app_tables.users.search(is_demo=True))}
    for name in DEMO_TABLES:
        out[name] = len(getattr(app_tables, name).search(is_demo=True))
    return out
