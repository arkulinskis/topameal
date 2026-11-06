"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced,
and the reply must be JSON (a datetime or a row in a reply fails here, like it would break the page).
Add tests for every new server function: the happy path, bad input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)


def call(name, *args):
    r = anvil.server.call(name, *args)
    json.dumps(r)  # strict: must be JSON-able
    return r


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def ok(r, msg=""):
    assert isinstance(r, dict) and r.get("ok"), (msg, r)
    return r


def bad(r, msg=""):
    assert isinstance(r, dict) and r.get("ok") is False and r.get("error"), (msg, r)
    return r


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("arkulinskis@gmail.com", "The Admin")
ana = person("ana@example.com", "Ana")
bob = person("bob@example.com")

as_user(None)
assert call("get_me") is None
assert denied("update_profile", "X")
as_user(admin)
assert call("get_me")["is_admin"] is True, "ADMIN_EMAILS become admins on first sign-in"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana" and me["is_admin"] is False
assert ana["last_seen"] is not None
as_user(bob)
assert call("get_me")["name"] == "Bob", "a name comes from the email when none is set"
bad(call("update_profile", " x "))
assert ok(call("update_profile", "  Bob   Stone "))["me"]["name"] == "Bob Stone"

# ---------------------------------------------------------------------------------- feedback
as_user(None)
bad(call("submit_feedback", "bug", "hi"))
ok(call("submit_feedback", "bug", "The button is broken", "guest@example.com", {"page": "#home", "evil": "x" * 9999}))
fb = T.feedback.search()[0]
assert fb["name"] == "Guest" and fb["email"] == "guest@example.com" and "evil" not in fb["context"] and fb["status"] == "new"
for i in range(4):
    ok(call("submit_feedback", "idea", "Idea number %d" % i))
bad(call("submit_feedback", "idea", "One too many this hour"), "rate limit")
as_user(ana)
ok(call("submit_feedback", "nonsense-kind", "Signed-in feedback"))
assert T.feedback.get(message="Signed-in feedback")["kind"] == "other"
assert denied("list_feedback")
as_user(admin)
lst = call("list_feedback")
assert lst["counts"]["new"] == 6 and len(lst["items"]) == 6
fid = lst["items"][0]["id"]
ok(call("set_feedback_status", fid, "done", "Fixed it"))
assert call("list_feedback", "done")["items"][0]["note"] == "Fixed it"
bad(call("set_feedback_status", fid, "weird"))
bad(call("set_feedback_status", "nope", "done"))
ok(call("delete_feedback", fid))
assert len(call("list_feedback")["items"]) == 5

# ---------------------------------------------------------------------------------- admin
as_user(ana)
for fn, args in [("admin_overview", ()), ("list_users", ()), ("set_admin", (bob.get_id(), True)), ("demo_load", ()), ("demo_remove", ())]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["users"] == 3 and ov["admins"] == 1 and ov["feedback_new"] == 5 and ov["kitchens"] == 0
assert len(call("list_users")["users"]) == 3 and len(call("list_users", "bob")["users"]) == 1
ok(call("set_admin", bob.get_id(), True))
assert bob["is_admin"] is True
bad(call("set_admin", admin.get_id(), False), "can't remove your own admin")
ok(call("set_enabled", bob.get_id(), False))
assert bob["enabled"] is False
bad(call("set_enabled", admin.get_id(), False))
ok(call("set_enabled", bob.get_id(), True))
ok(call("set_admin", bob.get_id(), False))
assert bob["is_admin"] is False

# ---------------------------------------------------------------------------------- the catalogue
R, P = M["Recipes"], M["Planner"]
assert len(R.TOPPERS) >= 20 and len(R.BY_KEY) == len(R.TOPPERS), "unique topper keys"
for t in R.TOPPERS:
    assert t["base"] in R.BASES and all(b in R.BASES for b in t["also"]), t["key"]
    assert all(g in R.GROCERIES for g, _ in t["ing"]), t["key"]
    assert all(d in R.DISHES and d != "pot" for d in t["dishes"]) and "pan" in t["dishes"], t["key"]
    assert t["tier"] in (1, 2, 3) and 3 <= len(t["steps"]) <= 6 and t["tip"], t["key"]
    assert len([p for p in R.PROTEINS if p in t["tags"]]) == 1, "exactly one protein tag: " + t["key"]
    assert not any(h in [g for g, _ in t["ing"]] for h in R.AT_HOME), t["key"]
assert all(g[2] in dict(R.AISLES) and g[4] in ("sum", "one") for g in R.GROCERIES.values())
used = {g for t in R.TOPPERS for g, _ in t["ing"]}
assert used == set(R.GROCERIES), "unused groceries: %s" % (set(R.GROCERIES) - used)
for avoid in [[a] for a, _ in R.AVOID]:
    assert len(P.candidates({"avoid": avoid, "budget": 3}, set())) >= 4, "enough toppers without %s" % avoid

# ---------------------------------------------------------------------------------- the planner (pure)
import random  # noqa: E402
kit = {"people": 2, "nights": 4, "budget": 2, "avoid": [], "never": []}
for seed in range(40):
    keys = P.pick(4, kit, rng=random.Random(seed))
    assert len(keys) == 4 and len(set(keys)) == 4
    assert all(R.BY_KEY[k]["tier"] <= 2 for k in keys), "budget respected"
    prots = [P.protein(R.BY_KEY[k]) for k in keys]
    assert len(set(prots)) >= 3, "Mom mixes up the proteins: %s" % prots
veg = P.pick(5, dict(kit, avoid=["vegetarian"]))
assert veg and all("veg" in R.BY_KEY[k]["tags"] for k in veg)
assert "tuscan_chicken" not in P.pick(7, dict(kit, never=["tuscan_chicken"], budget=3))
ordered = P.order([{"key": "tuna_tomato", "cooked": None}, {"key": "lemon_salmon", "cooked": None}, {"key": "sausage_peppers", "cooked": "2026-01-01"}])
assert [s["key"] for s in ordered] == ["sausage_peppers", "lemon_salmon", "tuna_tomato"], "cooked first, then most perishable"
lst = P.shopping(["tuscan_chicken", "sausage_mushroom_cream"], 2)
flat = {i["key"]: i for a in lst["aisles"] for i in a["items"]}
assert flat["cream"]["text"].startswith("2 cartons") and flat["garlic"]["text"].startswith("1 jar"), "sum vs one"
assert flat["spinach"]["for"] == ["Creamy Tuscan chicken", "Creamy sausage & mushroom"]
assert [a["key"] for a in lst["aisles"]] == [k for k, _ in R.AISLES if k in {a["key"] for a in lst["aisles"]}], "walking order"
assert P.shopping(["tuscan_chicken"], 4)["aisles"][0]["items"][0]["text"].startswith("2 packs"), "scales with people"
assert P.shopping(["tuscan_chicken"], 1)["aisles"][0]["items"][0]["text"].startswith("1 pack")
assert "baby spinach" in P.shared(["tuscan_chicken", "sausage_mushroom_cream"])
d0 = dt.date(2026, 3, 2)
sch = P.schedule([{"key": "tuna_tomato", "cooked": None}, {"key": "sausage_peppers", "cooked": None}, {"key": "x", "cooked": None},
                  {"key": "honey_garlic_chicken", "cooked": None}], d0)
assert len(sch) == 3 and sch[0]["cook_by"] is None, "unknown keys are skipped; no cook-by before shopping"
sch = P.schedule([{"key": "tuna_tomato", "cooked": None}, {"key": "sausage_peppers", "cooked": None}, {"key": "honey_garlic_chicken", "cooked": None}], d0, d0)
assert sch[2]["freeze"] and sch[2]["perishable"] == "boneless chicken thighs", "chicken planned for day 3 of 2: freeze tip"
assert sch[1]["cook_by"] == "2026-03-06" and sch[0]["cook_by"] is None, "cook-by from the shopping day; tins keep"
assert P.schedule([{"key": "lemon_salmon", "cooked": None}], d0 + dt.timedelta(days=2), d0)[0]["past_best"]

# ---------------------------------------------------------------------------------- demo data + the kitchen
today = now.date().isoformat()
as_user(None)
assert denied("get_week", today) and denied("say_no", "x") and denied("get_kitchen") and denied("save_kitchen", {})
sample = call("sample_week")
assert len(sample["slots"]) == 4 and sample["list"]["total"] > 4, "visitors can peek at a sample week"
assert not T.weeks.search(), "the sample saves nothing"

as_user(ana)
r = ok(call("get_week", today))
assert M["DemoData"].state() == "loaded" and T.weeks.search(is_demo=True), "demo loads on first visit"
w, k = r["week"], r["kitchen"]
assert k["people"] == 2 and k["nights"] == 4 and k["confirmed"] is False, "Mom assumes, the member corrects"
assert len(w["slots"]) == 4 and w["next"] == w["slots"][0]["key"] and not w["shopped"]
assert w["list"]["total"] > 5 and w["at_home"][:3] == ["rice", "pasta", "potatoes"]
keeps = [s["keeps"] for s in w["slots"]]
assert keeps == sorted(keeps), "most perishable first"
assert ok(call("get_week", "garbage"))["week"]["id"] == w["id"], "a bad date falls back to the server's"
assert ok(call("get_week", "1999-01-01"))["week"]["id"] == w["id"], "a far-off date is ignored"
ok(call("confirm_kitchen"))
assert call("get_kitchen")["kitchen"]["confirmed"] is True

# say no, then change your mind
first = w["slots"][0]["key"]
r = ok(call("say_no", first, today))
w2, repl = r["week"], r["replaced_by"]
assert first not in [s["key"] for s in w2["slots"]] and len(w2["slots"]) == 4 and r["replaced_by"] and r["note"]
assert [n["key"] for n in w2["nos"]] == [first]
bad(call("say_no", first, today), "can't refuse what isn't planned")
bad(call("say_no", "nonsense", today))
r = ok(call("say_yes", first, today))
w3 = r["week"]
assert first in [s["key"] for s in w3["slots"]] and len(w3["slots"]) == 4, "it comes back in its replacement's place"
assert [(n["key"], n["auto"]) for n in w3["nos"]] == [(repl, True)], "the replacement is set aside, not lost"
bad(call("say_yes", "nonsense", today))
# three noes and it's off the list for good
target = w3["slots"][-1]["key"]
T.kitchens.get(owner=ana)["no_counts"] = {target: 2}   # two noes on earlier weeks (a no then a yes cancels out)
r = ok(call("say_no", target, today))
assert target in [n["key"] for n in r["kitchen"]["never"]] and "three times" in r["note"]
assert target not in [s["key"] for s in r["week"]["slots"]]

# cooking and shopping
wk = call("get_week", today)["week"]
key0 = wk["slots"][0]["key"]
cook = ok(call("get_cook", key0, today))
assert cook["in_plan"] and cook["topper"]["steps"] and cook["topper"]["ingredients"] and cook["base"]["how"] and cook["people"] == 2
bad(call("get_cook", "nope", today))
assert ok(call("get_cook", "red_lentil_dal" if key0 != "red_lentil_dal" else "shakshuka", today))["in_plan"] in (True, False)
item = wk["list"]["aisles"][0]["items"][0]["key"]
assert ok(call("set_checked", item, True, today))["checked"] == 1
assert ok(call("set_checked", item, True, today))["checked"] == 1, "ticking twice doesn't double up"
bad(call("set_checked", "not-a-thing", True, today))
r = ok(call("set_shopped", True, today))
assert r["week"]["shopped"] == today and r["week"]["list"]["done"] == r["week"]["list"]["total"], "shopping done ticks everything"
assert all(s["cook_by"] or s["keeps"] >= 30 for s in r["week"]["slots"]), "every dinner gets a cook-by day"
r = ok(call("set_cooked", key0, True, today))
assert r["week"]["slots"][0]["cooked"] == today and r["week"]["next"] != key0
bad(call("say_no", key0, today), "cooked dinners can't be refused")
r = ok(call("set_cooked", key0, False, today))
assert not any(s["cooked"] for s in r["week"]["slots"])
bad(call("set_cooked", "nope", True, today))
for s in call("get_week", today)["week"]["slots"]:
    r = ok(call("set_cooked", s["key"], True, today))
assert r["week"]["all_done"] and r["week"]["story"]["cooked"] == len(r["week"]["slots"])

# a new week avoids last week's dinners
old_keys = {s["key"] for s in r["week"]["slots"]}
r = ok(call("new_plan", today))
assert r["week"]["id"] != wk["id"] and not (old_keys & {s["key"] for s in r["week"]["slots"]})
assert r["week"]["story"]["weeks"] == 2

# kitchen settings refit the plan
bad(call("save_kitchen", "nope"))
bad(call("save_kitchen", {"people": 0}))
bad(call("save_kitchen", {"nights": "lots"}))
r = ok(call("save_kitchen", {"people": 3, "nights": 3, "budget": 1, "avoid": ["vegetarian", "made-up"], "never": []}, today))
k, w = r["kitchen"], r["week"]
assert k["people"] == 3 and k["avoid"] == ["vegetarian"] and k["never"] == [], "unknown avoid options are dropped; never list cleared"
assert len(w["slots"]) == 3 and all("veg" in R.BY_KEY[s["key"]]["tags"] and s["tier"] == 1 for s in w["slots"]), "plan refitted"
assert w["people"] == 3
r = ok(call("save_kitchen", {"nights": 6, "avoid": [], "budget": 3}, today))
assert len(r["week"]["slots"]) == 6

# someone else's data stays theirs
as_user(bob)
bw = ok(call("get_week", today))["week"]
assert bw["id"] != r["week"]["id"] and bw["story"]["weeks"] == 1
as_user(ana)
assert ok(call("get_week", today))["week"]["id"] == r["week"]["id"]

# admin
assert denied("admin_kitchen_stats")
as_user(admin)
st = call("admin_kitchen_stats")
assert st["weeks"] >= 4 and st["kitchens"] >= 5 and st["cooked"] >= 1 and len(st["toppers"]) == len(R.TOPPERS)
assert call("admin_overview")["kitchens"] >= 2

# demo data on and off
ok(call("demo_remove"))
assert M["DemoData"].state() == "removed" and not T.weeks.search(is_demo=True) and not T.kitchens.search(is_demo=True)
assert not T.users.search(is_demo=True) and T.weeks.search(owner=ana), "removing demo data keeps real data"
as_user(ana)
call("get_week", today)
assert M["DemoData"].state() == "removed", "removed demo data doesn't come back by itself"
as_user(admin)
ok(call("demo_load"))
n = len(T.weeks.search(is_demo=True))
ok(call("demo_load"))
assert len(T.weeks.search(is_demo=True)) == n, "reloading replaces the demo instead of doubling it"

# ---------------------------------------------------------------------------------- households
as_user(ana)
inv = ok(call("get_invite"))
code = inv["code"]
assert inv["kitchen"]["is_owner"] and not inv["kitchen"]["shared"] and len(code) >= 8
assert ok(call("get_invite"))["code"] == code, "the same link until a new one is made"
as_user(None)
pk = ok(call("peek_invite", code))
assert pk["owner"] == "Ana" and pk["names"] == ["Ana"] and pk["member"] is False
assert "example.com" not in json.dumps(pk), "the join page never shows emails"
bad(call("peek_invite", "not-a-real-code"))
bad(call("peek_invite", None))
assert denied("join_household", code) and denied("get_invite") and denied("too_tired")
as_user(bob)
bob_week = call("get_week", today)["week"]["id"]
assert ok(call("peek_invite", code))["member"] is False
ok(call("join_household", code))
assert ok(call("peek_invite", code))["member"] is True
bw = call("get_week", today)["week"]
as_user(ana)
aw = call("get_week", today)["week"]
assert bw["id"] == aw["id"] and bw["id"] != bob_week, "a household shares one plan"
as_user(bob)
hk = call("get_kitchen")["kitchen"]
assert hk["shared"] and [m["name"] for m in hk["household"]] == ["Ana", "Bob Stone"] and not hk["is_owner"]
assert "email" not in json.dumps(hk["household"])
item = bw["list"]["aisles"][0]["items"][0]["key"]
ok(call("set_checked", item, True, today))
as_user(ana)
assert call("get_ticks", today)["checked"][item] == "Bob", "ticks remember who ticked them"
flat = {i["key"]: i for a in call("get_week", today)["week"]["list"]["aisles"] for i in a["items"]}
assert flat[item]["by"] == "Bob" and flat[item]["checked"]
ok(call("save_kitchen", {"people": 4}, today))
as_user(bob)
assert call("get_kitchen")["kitchen"]["people"] == 4, "settings are shared too"
bad(call("get_invite", True), "only the owner makes a new link")
bad(call("remove_member", ana.get_id()), "only the owner removes people")
assert ok(call("get_invite"))["code"] == code, "anyone in the household can share the link"
as_user(ana)
bad(call("leave_household"), "you can't leave your own kitchen")
bad(call("remove_member", admin.get_id()), "not in the kitchen")
bad(call("remove_member", "nope"))
assert not ok(call("remove_member", bob.get_id()))["kitchen"]["shared"]
as_user(bob)
assert call("get_week", today)["week"]["id"] == bob_week, "removed: back to their own plan"
ok(call("join_household", code))
r = ok(call("leave_household"))
assert not r["kitchen"]["shared"] and call("get_week", today)["week"]["id"] == bob_week
bad(call("leave_household"))
as_user(ana)
new = ok(call("get_invite", True))["code"]
assert new != code
assert "already" in ok(call("join_household", new))["note"]
as_user(bob)
bad(call("join_household", code), "the old link stops working")
# the demo household, and removing demo data frees real people from demo kitchens
maya, sam = T.users.get(email="maya.demo@example.com"), T.users.get(email="sam.demo@example.com")
assert sam["kitchen"] == T.kitchens.get(owner=maya), "demo: Sam shares Maya's kitchen"
bob["kitchen"] = sam["kitchen"]
as_user(admin)
ok(call("demo_remove"))
assert bob["kitchen"] is None
as_user(bob)
assert call("get_week", today)["week"]["id"] == bob_week
as_user(admin)
ok(call("demo_load"))

# ---------------------------------------------------------------------------------- too tired tonight
as_user(ana)
w = call("get_week", today)["week"]
todo = [s for s in w["slots"] if not s["cooked"]]
expect = min(todo, key=lambda s: (s["dish_count"], s["minutes"], todo.index(s)))["key"]
r = ok(call("too_tired", today))
if expect == w["next"]:
    assert "already" in r["note"]
else:
    assert r["tonight"] == expect and r["week"]["next"] == expect and "wash" in r["note"]
wrow = T.weeks.get_by_id(w["id"])
wrow["slots"] = [{"key": "lemon_salmon", "cooked": None}, {"key": "tuna_tomato", "cooked": None}]
wrow["shopped"] = now.date()
r = ok(call("too_tired", today))
assert r["week"]["next"] == "tuna_tomato" and "freezer" in r["note"], "tired: the tin one tonight, freeze the salmon"
r = ok(call("say_no", "lemon_salmon", today))
assert r["week"]["next"] == "tuna_tomato", "tonight's pick stays first"
ok(call("set_cooked", "tuna_tomato", True, today))
r = ok(call("too_tired", today))
assert "last one" in r["note"]

# ---------------------------------------------------------------------------------- Privacy & Terms
if "legal_server" in M:
    as_user(ana)
    st = call("legal_state")
    assert st["signedIn"] and st["accepted_version"] is None
    ok(call("legal_accept", st["version"], "signup"))
    assert ana["legal_source"] == "signup" and call("legal_state")["accepted_version"] == st["version"]

# ---------------------------------------------------------------------------------- every callable is covered by a permission check
# A callable that changes data without require_user / a C.require_* check is a security hole. List the public ones here.
PUBLIC = {"get_me", "submit_feedback", "sample_week", "peek_invite", "legal_state", "legal_accept"}
for name, (f, need) in sorted(anvil.server.CALLABLES.items()):
    if name in PUBLIC:
        continue
    assert need, "%s is callable by anyone: add require_user=True (or list it in PUBLIC in test_server.py)" % name

print("ALL OK (%d server functions)" % len(anvil.server.CALLABLES))
