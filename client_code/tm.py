"""Topameal's small helpers (the Python version of the old window.TM): dates in Mom's words, base amounts, price tiers,
lists in plain English, the hearts when you've cooked, copy/share. Pages and items import it as `from .. import tm`.

    tm.today()                  the browser's local date 'YYYY-MM-DD' (every member callable takes it)
    tm.day(iso)                 'today', 'tomorrow', 'Thursday', 'Mon 3 Nov'
    tm.words(["a", "b", "c"])   'a, b and c'
    tm.set_tier(node, n, label) '$$' + a faded '$' in a <span class="tm-tier"> DOM node
    tm.set_base(node, base)     the round rice/pasta/potatoes badge in a <span class="tm-base"> DOM node
    tm.hearts()                 hearts float up the screen (skipped with reduced motion)
"""
import random

from anvil.js import window

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SHORT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PROUD = ["Proud of you.", "Look at you, feeding yourself properly.", "That's my kid.",
         "Well done, love. Now sit down and eat.", "See? You can do it.", "Lovely. Soak the pan while you eat."]
AISLE_ICONS = {"meat": "pan", "veg": "sparkle", "fridge": "fridge", "freezer": "snow", "shelf": "grid", "cupboard": "home"}


def _pad(n):
    return ("0" if n < 10 else "") + str(n)


def today():
    d = window.Date()
    return "%d-%s-%s" % (d.getFullYear(), _pad(d.getMonth() + 1), _pad(d.getDate()))


def _date(iso):
    return window.Date(iso[:10] + "T12:00:00")


def days_from(iso):
    return int(round((_date(iso).getTime() - _date(today()).getTime()) / 86400000.0))


def day(iso):
    if not iso:
        return ""
    n = days_from(iso)
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    if n == -1:
        return "yesterday"
    d = _date(iso)
    if 1 < n < 7:
        return DAYS[d.getDay()]
    return "%s %d %s" % (SHORT_DAYS[d.getDay()], d.getDate(), MONTHS[d.getMonth()])


def cap(s):
    return s[:1].upper() + s[1:] if s else s


def first(me):
    return ((me or {}).get("name") or "love").split(" ")[0]


def greet(me):
    h, n = window.Date().getHours(), first(me)
    if h < 5:
        return "Still up, %s?" % n
    if h < 12:
        return "Morning, %s." % n
    if h < 17:
        return "Hello, %s." % n
    if h < 21:
        return "Evening, %s." % n
    return "It's late, %s." % n


def words(items):
    items = list(items)
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def plural(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def base_amount(base, n):
    """How much of the base for n people (BASES in Recipes.py)."""
    if base == "pasta":
        return "%d g of pasta" % (100 * n)
    if base == "potatoes":
        return "%d medium potatoes" % (2 * n)
    cups = n / 2.0
    whole, half = int(cups), cups - int(cups) >= .5
    return "%s%s cup%s of rice" % (whole or "", "½" if half else "", "s" if cups > 1 else "")


def pick(options):
    return random.choice(options)


def flag_for(s):
    """(kind, icon, text) for a dinner's little flag on This week (the old flagFor)."""
    if s.get("cooked"):
        return "ok", "heart", "Cooked " + day(s["cooked"])
    if s.get("past_best"):
        return "bad", "info", "Past its best? Sniff test first"
    if s.get("cook_by"):
        n = days_from(s["cook_by"])
        return ("warn" if n <= 0 else "cook"), "clock", ("Cook it today" if n <= 0 else "Cook by " + day(s["cook_by"]))
    if s["keeps"] >= 30:
        return "calm", "check", "Keeps for ages"
    return "calm", "fridge", "Keeps %d day%s" % (s["keeps"], "" if s["keeps"] == 1 else "s")


def set_tier(node, n, label):
    """'$$' strong + '$' faded, read out as 'Price: Comfortable'."""
    node.innerHTML = "$$$"[:n] + "<i>" + "$$$"[n:] + "</i>"
    node.setAttribute("title", label or "")
    node.setAttribute("role", "img")
    node.setAttribute("aria-label", "Price: " + (label or ""))


def set_base(node, base, big=False):
    node.className = "tm-base " + base + (" big" if big else "")
    node.innerHTML = '<i class="ic ic-%s"></i>' % base
    node.setAttribute("aria-hidden", "true")


def hearts():
    """Hearts rise up the screen for a moment (the old TM.hearts). Decorative: hidden from screen readers."""
    if window.UI.reducedMotion():
        return
    doc = window.document
    make = getattr(doc, "createElement")
    box = make("div")
    box.className = "tm-hearts"
    box.setAttribute("aria-hidden", "true")
    for i in range(18):
        s = make("span")
        s.textContent = "♡" if i % 4 == 3 else "♥"
        s.style.left = "%.1f%%" % (5 + random.random() * 90)
        s.style.fontSize = "%dpx" % (16 + random.random() * 22)
        s.style.animationDelay = "%.2fs" % (random.random() * .6)
        s.style.setProperty("--r", "%ddeg" % (random.random() * 60 - 30))
        if i % 3 == 1:
            s.style.color = "var(--c-accent)"
        box.appendChild(s)
    getattr(doc, "body").appendChild(box)
    window.setTimeout(lambda: box.remove(), 3200)


def copy_text(text, done, fallback):
    """Copy to the clipboard; done() on success, fallback() when the browser won't (old browsers, no permission)."""
    clip = getattr(window.navigator, "clipboard", None)
    if clip is None:
        fallback()
        return
    try:
        clip.writeText(text).then(lambda _=None: done(), lambda _=None: fallback())
    except Exception:
        fallback()


def can_share():
    return getattr(window.navigator, "share", None) is not None


def share(title, text, url):
    try:
        getattr(window.navigator, "share")({"title": title, "text": text, "url": url}).catch(lambda _=None: None)
    except Exception:
        pass
