# Topameal

Topameal is a grocery-list maker for people with decision fatigue. It assumes you have rice, pasta and potatoes at home, picks a week of quick one-pan "toppers" (meats and sauces made in a big frying pan, then poured over the base), writes one merged shopping list, orders the week so nothing spoils, gives price tiers instead of prices, and counts the dishes you'll wash. It never asks what you like: Mom suggests, you only say no (and can change your mind). The voice and look are a loving mother's kitchen. Built on [Anvil](https://anvil.works).

- **App repo:** github.com/arkulinskis/topameal (branch `master`). Anvil pulls `master`.
- **Live:** https://topameal.com

## What it does

**For visitors:** a landing page ("You've got rice. I've got the rest.") with a frying-pan illustration, how it works,
Mom's rules, FAQ, and **Peek at a week**: a real sample plan + list for two, made on the spot, nothing saved.
Sign-up with email and password or Google, a feedback form, and the Privacy & Terms page.

**For members** (three tabs on a phone: This week, Shopping, You):
- **This week** (`#home`): made automatically on the first visit, with Mom's guesses (2 people, 4 dinners, comfortable
  budget) shown once with "That's right" / "Change". Mom's handwritten note greets you and says the one thing to do next.
  Before shopping: a "Go shopping, once" card. After: a **Tonight** card with "Let's cook" and **Too tired tonight**
  (the easiest dinner left, fewest dishes then quickest, moves to tonight; if what it bumps won't keep, Mom says freeze it).
  The dinners are listed most perishable first, each with base, minutes, dishes to wash, price tier ($ / $$ / $$$), and
  "Keeps N days" (before shopping) or "Cook by Thursday" (after). A freezer tip appears when a dinner is planned after its
  meat would go off; "Past its best? Sniff test first" when it's late. Household favourites wear a little heart flag,
  "A favourite".
- **Send this week:** a button beside "Start a whole new week" opens the phone's share sheet (Copy on a computer) with
  "My dinners this week, sorted by Topameal: ..." and a link `#week/<key>.<key>...`. Whoever opens it (no account
  needed) sees Mom's note ("Someone thinks you'd like this week"), the dinners, the totals and a short list summary.
  Visitors get **Cook this week** (sign up, then straight back); members get **Make this my week**: the sent dinners
  become their plan (the old one stays in the history), and any that don't suit their kitchen (vegetarian, no pork,
  over budget, stopped...) are swapped, marked "I'd swap this one" beforehand and named in Mom's toast.
- **Still at home from last week:** jars, bunches and bags bought on an earlier shop (the "one covers the week" groceries:
  curry paste, salsa, cheese bags, garlic, herbs, cupboard things) that are still within their keep days move to a last
  list group, **Probably still at home** ("bought Sun 16 Nov · check before you buy"; ticking means "got it / have it").
  Mom plans new weeks leaning towards toppers that use them up, and her note says so ("You should still have salsa from
  last time. The taco beef & beans will use it up."). Short-keep things (a 5-day parsley) drop out; packs that get used up
  never move there.
- **No thanks** on any dinner: Mom swaps in another that fits the rest of the week (shared ingredients, different protein).
  The refused one goes to **Set aside**; "Yes, this one" brings it back in its replacement's place (the replacement is set
  aside, so nothing is lost). Say no to the same topper three times and Mom stops suggesting it.
- **Shopping** (`#list`): one merged list in walking order (meat counter, fruit & veg, fridge, freezer, shelves, then
  "Check your cupboard first"), quantities scaled to the household, which dinners each line is for, "Fridge straight away"
  on the perishables, tick as you go (saved), **Copy list** to send to someone, **I've done the shopping** (starts the cook-by
  days; undoable).
- **Cook** (`#cook/<key>`): what to get out ("That's all you'll wash"), the base first with amounts for the household,
  ingredients scaled, big tappable steps, Mom's tip, **I cooked it** (hearts float up, Mom is proud). Then **How did it go
  down?**: **Everyone ate it** (a favourite: it comes back now and then, never two weeks running) or **Not again** (Mom
  stops suggesting it; it's in You with Bring back), with Mom's reply and a small Undo.
- **Shared household:** "Share my kitchen" (You, or Share on the list) gives an invite link `#join/<code>`. Whoever opens it
  (signing up first if needed) joins: one plan, one list, one set of settings. The list picks up other people's ticks every
  few seconds while open and shows "Sam got it" (and a toast for new ones). The owner can remove people and make a new link;
  others can leave, which brings their own plan back. Up to 8 people. "Shared with …" shows on This week.
- When every dinner is cooked: "You fed yourself all week" and **Plan next week** (avoids last week's dinners).
  "Start a whole new week" at the bottom any time.
- **You** (`#profile`): Your kitchen (people 1-8, dinners 2-7, budget, things you don't eat: vegetarian, no pork/beef/
  chicken/fish/shellfish/dairy/nuts, nothing spicy; the "stopped suggesting" list with Bring back). Saving refits the
  current plan. Then name, appearance, password, privacy, sign out.

**The catalogue** (`server_code/Recipes.py`): 34 toppers (chicken, beef, pork, seafood, vegetarian), 62 groceries with aisle,
keep-for days and "sum" or "one" (one jar covers the week), 3 bases. Shortcuts on purpose: jarred garlic, grated cheese,
frozen shrimp. Eleven toppers are vegetarian and seven of those have no dairy (lentil bolognese, egg-fried rice, sticky
tofu, lemony white beans, chickpea ratatouille, mild coconut chickpea curry, red lentil dal), so a vegetarian, no-dairy
or thrifty vegetarian kitchen gets a real rotation instead of the same few dinners.

**For admins** (`#admin`; your admin email (App Secret `admin_emails`) becomes an admin on first sign-in):
- **Kitchen:** every topper with how often it's planned, refused and cooked, plus favourites and "not again" after
  cooking (spot the ones people skip).
- **Feedback inbox:** New / Read / Done, private notes.
- **Users:** search, make admin, disable an account.
- **Demo data:** three demo households with plans (Sam shares Maya's kitchen), so the Kitchen stats aren't empty; remove or reload it.

## Setting it up in Anvil (once)

1. In the Anvil editor: **Create app → Clone from GitHub**, and paste `https://github.com/arkulinskis/topameal`.
2. **Users** service: email + password and "Continue with Google", sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **your admin email** (App Secret `admin_emails`) straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [YouTube embeds](https://developers.google.com/youtube/player_parameters) | Outside web service | Plays a YouTube video inside the page (the privacy-friendlier youtube-nocookie address). |
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Caveat, Fraunces, Nunito |

**Built into the browser:** localStorage.

**Anvil platform:** Anvil, Anvil Data Tables, Anvil Email, Anvil JS bridge (anvil.js), Anvil Secrets, Anvil Users, Anvil Google service, Anvil HTTP, Anvil timezones (anvil.tz).

**Build and test tools (not shipped):** axe-core, Node.js, Headless Chrome (DevTools Protocol), PyYAML.

<!-- libraries:end -->

## Working on it

See `APP_MAP.md` (the code map) and `.claude/skills/topameal/SKILL.md`. In short:

```
python tools/check.py                            # Anvil's validator, JS syntax, asset hashes, server tests → ALL CHECKS PASSED
python -I tools/ui_test.py                       # the app in the Anvil App Server (Docker) + headless Chrome → ALL UI TESTS PASSED
git push origin master                           # deploy: Anvil pulls master
```

## Project layout

Native Anvil Forms (since 2026-11-07):

```
client_code/    startup.py, router.py (pages), state.py, tm.py (Mom's little helpers), Layouts/Shell, Pages/ (Landing, Auth,
                Home, Shopping, Cook, Week, Join, Profile, Admin), Items/, Components/, Dialogs/
server_code/    Recipes.py (catalogue), Planner.py (Mom's rules, pure), Kitchen.py (callables), common.py, Accounts.py,
                Admin.py, DemoData.py, Feedback.py, legal_server.py, seo_routes.py, AppStatus.py, SchemaCheck.py
theme/assets/   app.css (tokens, pages, role layer), icons.css, app-kit.js, theme.css (spinner), icons
tools/          check.py, ui_test.py + ui/ (flow, phone, admin, a11y, design), live/drive.mjs, testing/ (server tests + Anvil mock)
```
