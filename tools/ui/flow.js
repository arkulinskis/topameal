/* The main user journeys, run inside the real app (Anvil App Server) by tools/ui_test.py through tools/live/drive.mjs.
   Resolves to {ok, log}. Keep log lines ASCII (the Windows console). Ported from the JavaScript version's
   tools/preview/tests/flowtest.html: landing + peek, sign-up, Mom's plan (guesses, no / yes), the shopping list,
   cooking, the kitchen settings, too tired, sharing a kitchen (invite link, join as someone else, leave), sign out. */
(async function () {
  const log = [], t0 = Date.now();
  const say = (m) => log.push(((Date.now() - t0) / 1000).toFixed(1) + 's ' + m);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 20000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const vis = (e) => e && e.getBoundingClientRect().width > 0;
  const clean = (s) => s.textContent.trim().replace(/\s+/g, ' ');
  const byText = (sel, text) => $$(sel).find((e) => vis(e) && clean(e) === text);
  async function click(sel, text) {
    const el = await until(() => (text ? byText(sel, text) : $$(sel).find(vis)), sel + (text ? ' "' + text + '"' : ''));
    el.scrollIntoView({ block: 'center' });
    el.click();
    return el;
  }
  function type(input, value) {
    input.focus();
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  async function page(hash, ready, what) {
    if (location.hash !== hash) window.UI_READY = false;  // the old page stays until the router runs
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash && ready(), what || hash, 30000);
    await sleep(300);
  }
  const toasts = () => $$('.anvil-notification, [data-notify="container"]').map(clean).join(' | ');
  const ok = (cond, msg) => { if (!cond) throw new Error('FAILED: ' + msg); say('ok   ' + msg); };
  async function signUp(name, email) {
    await until(() => window.UI_READY && $$('.au-card input').length >= 2, 'auth page');
    if ($$('.au-card input').filter(vis).length < 3) await click('.au-card .ui-seg button', 'Create account');
    await until(() => $$('.au-card input').filter(vis).length >= 3, 'sign-up form');
    const inputs = $$('.au-card input[type=text], .au-card input[type=email], .au-card input[type=password]').filter(vis);
    type(inputs[0], name); type(inputs[1], email); type(inputs[2], 'Hb-' + Math.random().toString(36).slice(2) + '-Kq7');
    const tick = $('.au-card input[type=checkbox]');
    if (tick && !tick.checked) tick.click();
    await click('.anvil-role-btn-block button', 'Create account');
  }

  try {
    // ---- landing (visitors): hero, video, footer, peek at a week
    await page('#landing', () => $('.lp-hero'), 'landing');
    ok($('.lp-hero a[href="#auth/signup"]') && $('.lp-art svg'), 'landing: hero with the pan picture and a sign-up link');
    ok($('.ui-header .ui-btn.primary'), 'landing: Get started in the header');
    ok($('.ytf [aria-label^="Play the Topameal video"]') && $('.ytf a[href*="youtube.com/watch?v=Eex4sJbZDNg"]'), 'landing: the Watch section');
    ok($('.ui-footer [data-prepsto-open][href*="kpx5ewp"]') && $('.ui-footer [data-lk-open]') && $('.ui-footer a[href="https://arkvital.com"]') && $('.ui-footer a[href="https://addanapp.com"]'),
      'footer: Submit feedback, Privacy & Terms, arkvital.com, addanapp.com');
    await click('.anvil-role-ic-pan button', 'Peek at a week');
    await until(() => $$('.pk-item').length === 4, 'the sample week');
    ok(/The list \(\d+ things\)/.test($('.pk-shop').textContent), 'peek: four dinners and the list');
    await click('.anvil-modal-content button', 'Close');
    await until(() => !$('.pk-item'), 'peek closed');

    // ---- members-only page sends visitors to sign in, then back
    await page('#profile', () => true);
    await until(() => window.UI_READY && $$('.au-card input').length >= 2, 'redirected to sign in');
    ok(true, 'a members-only page asks visitors to sign in');
    await signUp('Flow Tester', 'flow' + Date.now() + '@example.com');
    await until(() => location.hash === '#profile' && window.UI_READY && $('.pf-grid'), 'back on the page they wanted', 40000);
    ok(true, 'sign-up: signed in and sent on to the page they asked for');
    ok($('.anvil-role-avatar button') && /FT/.test($('.anvil-role-avatar button').textContent), 'header: account button with initials');

    // ---- this week: Mom's plan, her guesses, say no, change your mind
    await page('#home', () => $$('.wk-card').length, 'home');
    ok($$('.wk-card').length === 4, 'a new member gets a 4-dinner plan straight away');
    ok(vis($('.tm-note')) && vis($('.wk-assume')), 'Mom says hello and lists her guesses');
    await click('.wk-assume button', "That's right");
    await until(() => !vis($('.wk-assume')), 'guesses hidden');
    ok(true, '"That\'s right" hides the guesses');
    const firstCard = $$('.wk-card')[0], refused = clean(firstCard.querySelector('.wk-title'));
    firstCard.querySelector('.anvil-role-wk-no button').click();
    await until(() => $$('.wk-chip').some((c) => c.textContent.includes(refused)), 'set aside');
    ok($$('.wk-card').length === 4 && !$$('.wk-title').some((t) => clean(t) === refused), 'saying no swaps the dinner and sets it aside');
    $$('.wk-chip').find((c) => c.textContent.includes(refused)).querySelector('button').click();
    await until(() => $$('.wk-title').some((t) => clean(t) === refused), 'brought back');
    ok($$('.wk-chip').filter(vis).length === 1, 'changing your mind brings it back (and sets the swap aside)');

    // ---- shopping list
    await click('.wk-hero a[href="#list"]');
    await until(() => location.hash === '#list' && window.UI_READY && $$('.sl-item').length > 5, 'the list');
    ok(true, 'the shopping list opens from the plan (' + $$('.sl-item').length + ' lines)');
    $$('.sl-item input')[0].click();
    await until(() => /^1 of/.test($('.sl-prog .ui-row span').textContent), 'progress moves');
    ok($$('.sl-item.on').length === 1, 'ticking a line moves the progress bar');
    await click('.sl-done button', "I've done the shopping");
    await until(() => location.hash === '#home' && window.UI_READY && vis($('.wk-hero a[href^="#cook/"]')), 'tonight');
    ok(/Let's cook/.test(document.body.textContent) && $$('.tm-flag.cook, .tm-flag.calm, .tm-flag.warn').length >= 3, "after shopping: tonight's dinner and cook-by days");

    // ---- cook it
    await click('.wk-hero a[href^="#cook/"]');
    await until(() => location.hash.indexOf('#cook/') === 0 && window.UI_READY && $$('.ck-step').length >= 4, 'cook page');
    ok($$('.ck-pill').length >= 2 && $$('.ck-li').length >= 3, 'the cook page shows dishes, ingredients and steps');
    $$('.ck-step')[1].click();
    ok($$('.ck-step')[1].classList.contains('done') && $$('.ck-step')[1].getAttribute('aria-pressed') === 'true', 'tapping a step ticks it');
    await click('.ck-end button', 'I cooked it');
    await until(() => location.hash === '#home' && window.UI_READY && $('.wk-card.done'), 'cooked');
    ok(true, '"I cooked it" marks the dinner done');

    // ---- your kitchen
    await page('#profile', () => $('.kc-step'), 'profile');
    await click('.anvil-role-kc-step-btn button', '+');
    await click('.kc-save button', 'Save my kitchen');
    await until(() => /changed|plan|Saved/i.test(toasts()), 'kitchen saved');
    ok($('.kc-step output').textContent === '3', 'kitchen saved (3 people)');
    type($('.pf-grid input'), 'Flow Tester Two');
    await click('.pf-grid .anvil-role-btn-primary button', 'Save');
    await until(() => /Flow Tester Two/.test($('.pf-head').textContent), 'name saved');
    ok(true, 'profile: name saved');

    // ---- too tired tonight
    await page('#home', () => $$('.wk-card').length, 'home again');
    await click('.wk-hero button', 'Too tired tonight');
    await until(() => /let's do|already the easiest/i.test(toasts()), 'too tired');
    ok(true, 'too tired: Mom moves the easiest dinner to tonight');

    // ---- share the kitchen
    await page('#list', () => $$('.sl-item').length, 'list again');
    await click('.sl-head button', 'Share');
    const link = await until(() => { const i = $('.tm-link input'); return i && /#join\//.test(i.value) && i.value; }, 'invite link');
    const code = link.split('#join/')[1];
    ok(code && code.length >= 6, 'Share shows the invite link');
    await click('.anvil-modal-content button', 'Done');
    await until(() => !$('.tm-link'), 'invite closed');

    // ---- light / dark switch, then sign out
    await click('.anvil-role-avatar button');
    await click('.ui-menu .ui-seg button', 'Dark');
    ok(document.documentElement.classList.contains('ui-dark'), 'menu: Dark switches the theme');
    await click('.ui-menu .ui-seg button', 'Auto');
    await click('.ui-menu button', 'Sign out');
    await until(() => location.hash === '#landing' && window.UI_READY && $('.ui-header .ui-btn.primary'), 'signed out');
    ok(true, 'sign out: back to the landing page as a visitor');

    // ---- the join page, signed out; a broken link; then a second person joins
    await page('#join/nope-nope-nope', () => vis($('.jn .ui-empty')), 'broken link');
    ok(true, 'a broken invite link says so');
    await page('#join/' + code, () => $$('.jn h1').some(vis), 'join page');
    ok(/Flow wants to share/.test($('.jn').textContent) && $$('.jn .anvil-role-btn-lg button').filter(vis).length === 2, 'signed out, the join page offers sign-up or sign-in');
    await click('.jn button', 'Create my account');
    await signUp('Ana Joiner', 'ana' + Date.now() + '@example.com');
    await until(() => location.hash === '#join/' + code && window.UI_READY && vis($('.jn .anvil-role-ic-heart button')), 'back on the join page', 40000);
    ok(/Join Flow's kitchen/.test($('.jn .anvil-role-ic-heart button').textContent), 'after sign-up they come straight back to join');
    await click('.jn .anvil-role-ic-heart button');
    await until(() => location.hash === '#home' && window.UI_READY && vis($('.wk-with')), 'joined');
    ok(/Shared with Flow/.test($('.wk-with').textContent), 'Ana joined: the plan says it is shared');
    await page('#list', () => $$('.sl-item').length, 'shared list');
    ok(vis($('.sl-with')) && $$('.sl-item .by').some((b) => /Flow got it/.test(b.textContent)), 'the shared list shows who got what');
    await page('#profile', () => vis($('.kc-house')), 'household');
    ok($$('.tm-person').filter(vis).length === 2 && vis(byText('.kc-house button', 'Leave this kitchen')), 'You shows the household and a Leave button');
    await click('.kc-house button', 'Leave this kitchen');
    await click('.anvil-modal-content button', 'Leave');
    await until(() => !vis(byText('.kc-house button', 'Leave this kitchen')), 'left');
    ok(true, 'Ana left and is back in her own kitchen');

    // ---- members can't open admin
    location.hash = '#admin';
    await sleep(2500);
    await until(() => window.UI_READY, 'router settled');
    ok(!$('.ad-stats'), 'non-admins are kept out of #admin');

    await click('.anvil-role-avatar button');
    await click('.ui-menu button', 'Sign out');
    await until(() => location.hash === '#landing' && window.UI_READY, 'signed out again');
    say('PASSED');
    return { ok: true, log: log };
  } catch (e) {
    say(String(e && e.message || e));
    return { ok: false, log: log };
  }
})();
