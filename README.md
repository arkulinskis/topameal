# Topameal

Topameal is a grocery-list maker for people with decision fatigue. It assumes you have rice, pasta and potatoes at home, picks a week of quick one-pan "toppers" (meats and sauces made in a big frying pan, then poured over the base), writes one merged shopping list, orders the week so nothing spoils, gives price tiers instead of prices, and counts the dishes you'll wash. It never asks what you like: Mom suggests, you only say no (and can change your mind). The voice and look are a loving mother's kitchen. Built on [Anvil](https://anvil.works).

- **App repo:** github.com/arkulinskis/topameal (branch `master`). Anvil pulls `master`.
- **Live:** not published yet (planned: topameal.anvil.app or a custom domain).

## What it does

**For visitors:** a landing page ("You've got rice. I've got the rest.") with a frying-pan illustration, how it works,
Mom's rules, FAQ, and **Peek at a week**: a real sample plan + list for two, made on the spot, nothing saved.
Sign-up with email and password, a feedback form, and the Privacy & Terms page.

**For members** (three tabs on a phone: This week, Shopping, You):
- **This week** (`#home`): made automatically on the first visit, with Mom's guesses (2 people, 4 dinners, comfortable
  budget) shown once with "That's right" / "Change". Mom's handwritten note greets you and says the one thing to do next.
  Before shopping: a "Go shopping, once" card. After: a **Tonight** card with "Let's cook" and **Too tired tonight**
  (the easiest dinner left, fewest dishes then quickest, moves to tonight; if what it bumps won't keep, Mom says freeze it).
  The dinners are listed most perishable first, each with base, minutes, dishes to wash, price tier ($ / $$ / $$$), and
  "Keeps N days" (before shopping) or "Cook by Thursday" (after). A freezer tip appears when a dinner is planned after its
  meat would go off; "Past its best? Sniff test first" when it's late.
- **No thanks** on any dinner: Mom swaps in another that fits the rest of the week (shared ingredients, different protein).
  The refused one goes to **Set aside**; "Yes, this one" brings it back in its replacement's place (the replacement is set
  aside, so nothing is lost). Say no to the same topper three times and Mom stops suggesting it.
- **Shopping** (`#list`): one merged list in walking order (meat counter, fruit & veg, fridge, freezer, shelves, then
  "Check your cupboard first"), quantities scaled to the household, which dinners each line is for, "Fridge straight away"
  on the perishables, tick as you go (saved), **Copy list** to send to someone, **I've done the shopping** (starts the cook-by
  days; undoable).
- **Cook** (`#cook/<key>`): what to get out ("That's all you'll wash"), the base first with amounts for the household,
  ingredients scaled, big tappable steps, Mom's tip, **I cooked it** (hearts float up, Mom is proud).
- **Shared household:** "Share my kitchen" (You, or Share on the list) gives an invite link `#join/<code>`. Whoever opens it
  (signing up first if needed) joins: one plan, one list, one set of settings. The list picks up other people's ticks every
  few seconds while open and shows "Sam got it" (and a toast for new ones). The owner can remove people and make a new link;
  others can leave, which brings their own plan back. Up to 8 people. "Shared with …" shows on This week.
- When every dinner is cooked: "You fed yourself all week" and **Plan next week** (avoids last week's dinners).
  "Start a whole new week" at the bottom any time.
- **You** (`#profile`): Your kitchen (people 1-8, dinners 2-7, budget, things you don't eat: vegetarian, no pork/beef/
  chicken/fish/shellfish/dairy/nuts, nothing spicy; the "stopped suggesting" list with Bring back). Saving refits the
  current plan. Then name, appearance, password, privacy, sign out.

**The catalogue** (`server_code/Recipes.py`): 25 toppers (chicken, beef, pork, seafood, vegetarian), 60 groceries with aisle,
keep-for days and "sum" or "one" (one jar covers the week), 3 bases. Shortcuts on purpose: jarred garlic, grated cheese,
frozen shrimp.

**For admins** (`#admin`; arkulinskis@gmail.com becomes an admin on first sign-in):
- **Kitchen:** every topper with how often it's planned, refused and cooked (spot the ones people skip).
- **Feedback inbox:** New / Read / Done, private notes.
- **Users:** search, make admin, disable an account.
- **Demo data:** three demo households with plans (Sam shares Maya's kitchen), so the Kitchen stats aren't empty; remove or reload it.

## Setting it up in Anvil (once)

1. In the Anvil editor: **Create app → Clone from GitHub**, and paste `https://github.com/arkulinskis/topameal`.
2. **Users** service: email + password, sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **arkulinskis@gmail.com** straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Caveat, Fraunces, Nunito |

**Built into the browser:** Web Share, localStorage, Clipboard.

**Anvil platform:** Anvil, Anvil Data Tables, Anvil JS bridge (anvil.js), Anvil Users.

**Build and test tools (not shipped):** Node.js, Headless Chrome (DevTools Protocol), PyYAML.

<!-- libraries:end -->

## Working on it

See `.claude/skills/topameal/SKILL.md`. In short:

```
python -I tools/check.py --ui                    # syntax, server tests, headless UI tests → ALL CHECKS PASSED
python -I tools/preview/devserver.py 8765        # the app on in-memory data: http://localhost:8765/  (?as=ana#home, ?as=admin#admin)
python tools/deploy.py                           # dry run (needs PyYAML, so no -I)
python tools/deploy.py --push "Message"          # deploy: commit + push to GitHub, Anvil pulls it
```

## Project layout

```
web/            the interface: core.js/core.css (shared engine + design tokens), app.js (header, footer), pages/*.html
client_code/    Main.py (the only Anvil form: bridge to the server, sign-in), legal.py
server_code/    common.py, Accounts.py, Feedback.py, Admin.py, DemoData.py, legal_server.py,
                Recipes.py (catalogue), Planner.py (Mom's rules, pure), Kitchen.py (callables)
assets/         icon.svg + generated PNG icons, pictures (served at _/theme/<name>)
tools/          sync_to_anvil.py (settings + table schema), deploy.py, check.py, preview/ (dev server, UI tests, screenshots), testing/
```
