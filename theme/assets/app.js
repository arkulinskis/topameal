/* core.js: the shared front-end engine (window.UI). Same in every app made from APP_MAKER/template;
   app-specific things live in web/app.js (brand, nav, footer) and web/pages/*.html (the pages).

   Pages:   UI.page(name, {title, nav, icon, auth, order, chrome}, mount)
              auth: null (anyone) | 'guest' (signed-out only) | 'user' | 'admin'
              nav: label for the header / phone tab bar (omit to keep it out of the menus)
              mount(view, ctx) draws into `view`; ctx = {args, me, go, api}. Return a Promise (the page
              is "ready" when it resolves) or {ready, destroy}. URLs are #name/arg1/arg2.
   Server:  UI.api(fn, ...args) -> Promise of the server function's return value. A reply of
              {ok: false, error} rejects with that message (shown as a toast unless you .catch it).
            UI.apiQuiet(fn, ...args) is the same without Anvil's loading spinner.
   Auth:    UI.auth('login'|'signup'|'reset'|'logout', {...}) -> Promise of {ok, me, message}
   Helpers: UI.esc, UI.icon, UI.toast, UI.modal, UI.confirm, UI.busy, UI.formData, UI.fmtDate, UI.ago,
            UI.store, UI.setTheme, UI.feedback, UI.go, UI.refresh
   Tests:   window.UI_READY is true when the current page has finished loading. */
(function () {
  'use strict';
  if (window.UI && window.UI.__v) return;
  var UI = window.UI = { __v: 1, pages: {}, me: null, config: { name: 'App', key: 'app', home: 'home', landing: 'landing' } };
  window.UI_READY = false;

  UI.configure = function (cfg) { Object.keys(cfg).forEach(function (k) { UI.config[k] = cfg[k]; }); };

  /* ------------------------------------------------------------------ small helpers */
  UI.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  UI.plural = function (n, one, many) { return n + ' ' + (n === 1 ? one : (many || one + 's')); };
  UI.initials = function (name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  };
  UI.fmtDate = function (iso, opts) {
    if (!iso) return '';
    var d = iso.length <= 10 ? new Date(iso + 'T12:00:00') : new Date(iso);
    return d.toLocaleDateString(undefined, opts || { day: 'numeric', month: 'short', year: 'numeric' });
  };
  UI.fmtDateTime = function (iso) {
    return iso ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
  };
  UI.ago = function (iso) {
    if (!iso) return '';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    var steps = [[60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year']], n = s / 60;
    for (var i = 0; i < steps.length; i++) {
      if (n < steps[i][0]) { n = Math.floor(n); return UI.plural(n, steps[i][1]) + ' ago'; }
      n = n / steps[i][0];
    }
    return '';
  };
  UI.store = {
    get: function (k, dflt) { try { var v = localStorage.getItem(UI.config.key + '.' + k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem(UI.config.key + '.' + k, JSON.stringify(v)); } catch (e) {} }
  };
  UI.formData = function (form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled) return;
      if (el.type === 'checkbox') out[el.name] = el.checked;
      else if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; }
      else out[el.name] = el.value;
    });
    return out;
  };
  /* Disable a button while a Promise runs; returns the Promise. */
  UI.busy = function (btn, promise) {
    if (!btn) return promise;
    btn.disabled = true; btn.classList.add('is-busy');
    var done = function () { btn.disabled = false; btn.classList.remove('is-busy'); };
    promise.then(done, done);
    return promise;
  };

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.7c2.2.6 3.5 2.4 3.5 5.3"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    bug: '<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5M9 5.5 7.5 4M15 5.5 16.5 4M7 13H3M21 13h-4M7.5 18l-3 2M16.5 18l3 2M7.5 9.5l-3-2M16.5 9.5l3-2"/>',
    bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13"/><path d="M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20v-4h-4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    pin: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    camera: '<path d="M4 8h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13.5" r="3.5"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>'
  };
  UI.ICONS = ICONS;
  UI.icon = function (name, cls) {
    return '<svg class="ui-ic ' + (cls || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || ICONS.sparkle) + '</svg>';
  };

  /* ------------------------------------------------------------------ toasts, modals */
  UI.toast = function (msg, kind) {
    var box = document.querySelector('.ui-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'ui ui-toasts'; box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'ui-toast' + (kind ? ' ' + kind : '');
    t.innerHTML = (kind === 'error' ? UI.icon('info') : kind === 'ok' ? UI.icon('check') : '') + '<span>' + UI.esc(msg) + '</span>';
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 300); }, kind === 'error' ? 6500 : 3200);
  };
  UI.modal = function (html, opts) {
    opts = opts || {};
    var prev = document.activeElement;
    var wrap = document.createElement('div');
    wrap.className = 'ui ui-modal-wrap';
    wrap.innerHTML = '<div class="ui-modal' + (opts.wide ? ' wide' : '') + '" role="dialog" aria-modal="true">' +
      '<button class="ui-btn ghost icon ui-modal-x" data-close aria-label="Close">' + UI.icon('x') + '</button>' + html + '</div>';
    document.body.appendChild(wrap);
    document.documentElement.classList.add('ui-modal-open');
    function key(e) { if (e.key === 'Escape') close(); }
    function close() {
      if (!wrap.parentNode) return;
      wrap.remove(); document.removeEventListener('keydown', key);
      if (!document.querySelector('.ui-modal-wrap')) document.documentElement.classList.remove('ui-modal-open');
      if (opts.onclose) opts.onclose();
      if (prev && prev.focus) prev.focus();
    }
    document.addEventListener('keydown', key);
    wrap.addEventListener('mousedown', function (e) { if (e.target === wrap) close(); });
    wrap.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) close(); });
    var first = wrap.querySelector('input, textarea, select');
    setTimeout(function () { (first || wrap.querySelector('.ui-modal')).focus && (first || wrap.querySelector('.ui-modal')).focus(); }, 30);
    return { el: wrap.querySelector('.ui-modal'), close: close };
  };
  UI.confirm = function (o) {
    o = typeof o === 'string' ? { title: o } : (o || {});
    return new Promise(function (resolve) {
      var answered = false;
      var m = UI.modal('<h2>' + UI.esc(o.title || 'Are you sure?') + '</h2>' + (o.text ? '<p class="muted">' + UI.esc(o.text) + '</p>' : '') +
        '<div class="ui-row end" style="margin-top:20px"><button class="ui-btn ghost" data-close>' + UI.esc(o.cancel || 'Cancel') + '</button>' +
        '<button class="ui-btn ' + (o.danger ? 'danger solid' : 'primary') + '" data-ok>' + UI.esc(o.ok || 'OK') + '</button></div>',
      { onclose: function () { if (!answered) resolve(false); } });
      m.el.querySelector('[data-ok]').onclick = function () { answered = true; m.close(); resolve(true); };
    });
  };

  /* ------------------------------------------------------------------ theme */
  UI.theme = function () { return UI.store.get('theme', 'auto'); };
  UI.applyTheme = function (t) {
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
    var dark = t === 'dark' || (t !== 'light' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('ui-dark', !!dark);
  };
  UI.setTheme = function (t) { UI.store.set('theme', t); UI.applyTheme(t); };
  UI.applyTheme(UI.theme());
  if (window.matchMedia) {
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { UI.applyTheme(UI.theme()); }); } catch (e) {}
  }

  /* ------------------------------------------------------------------ server bridge */
  var bridge = null;
  function send(kind, payload) {
    if (!bridge) return Promise.reject(new Error('The app is still starting.'));
    var out;
    try { out = bridge(kind, JSON.stringify(payload || {})); } catch (e) { return Promise.reject(e); }
    return Promise.resolve(out).then(function (r) {
      r = typeof r === 'string' ? JSON.parse(r) : (r || {});
      if (r.error) {
        var err = new Error(r.error); err.uiApi = true; err.denied = !!r.denied;
        if (r.detail) console.error(kind, payload && payload.fn, r.detail);
        if (r.reload) setTimeout(function () { location.reload(); }, 2500);
        throw err;
      }
      return r.result;
    });
  }
  function apiCall(quiet, fn, args) {
    return send('call', { fn: fn, args: args, quiet: quiet }).then(function (res) {
      if (res && typeof res === 'object' && res.ok === false) {
        var err = new Error(res.error || 'That didn\'t work.'); err.uiApi = true; err.expected = true; err.result = res;
        throw err;
      }
      return res;
    });
  }
  UI.api = function (fn) { return apiCall(false, fn, Array.prototype.slice.call(arguments, 1)); };
  UI.apiQuiet = function (fn) { return apiCall(true, fn, Array.prototype.slice.call(arguments, 1)); };
  /* Errors nobody caught become a toast, so a failed action is never silent. */
  window.addEventListener('unhandledrejection', function (e) {
    if (e.reason && e.reason.uiApi) { e.preventDefault(); UI.toast(e.reason.message, 'error'); }
  });

  /* Sign in / up / out. On success it navigates: to where the visitor was heading (UI.after) or home
     after signing in, to the landing page after signing out. */
  UI.auth = function (kind, payload) {
    return send(kind, payload || {}).then(function (r) {
      if (r && r.ok === false) { var err = new Error(r.error); err.uiApi = true; err.expected = true; throw err; }
      if (r && 'me' in r && (r.me || kind === 'logout')) {
        UI.me = r.me || null;
        var target = r.me ? (UI.after || '#' + UI.config.home) : '#' + UI.config.landing;
        UI.after = null;
        if (location.hash === target) route(); else location.hash = target;
      }
      return r;
    });
  };
  /* Update the signed-in user's details (e.g. a new name) and redraw the header, without reloading the page. */
  UI.setMe = function (me) {
    UI.me = me || null;
    if (shellRoot) renderChrome(current.name);
  };

  /* ------------------------------------------------------------------ pages and routing */
  UI.page = function (name, opts, mount) {
    if (typeof opts === 'function') { mount = opts; opts = {}; }
    opts.name = name; opts.mount = mount;
    UI.pages[name] = opts;
  };
  UI.allowed = function (p) {
    if (!p) return false;
    if (p.auth === 'user') return !!UI.me;
    if (p.auth === 'admin') return !!(UI.me && UI.me.is_admin);
    if (p.auth === 'guest') return !UI.me;
    return true;
  };
  UI.navPages = function () {
    return Object.keys(UI.pages).map(function (k) { return UI.pages[k]; })
      .filter(function (p) { return p.nav && UI.allowed(p) && (!p.when || p.when()); })
      .sort(function (a, b) { return (a.order || 50) - (b.order || 50); });
  };
  UI.parseHash = function () {
    var h = (location.hash || '').replace(/^#!?\/?/, '');
    var parts = h.split('?')[0].split('/').filter(function (x) { return x !== ''; }).map(decodeURIComponent);
    return { name: parts[0] || '', args: parts.slice(1) };
  };
  UI.hashFor = function (name) {
    var args = Array.prototype.slice.call(arguments, 1).filter(function (a) { return a != null && a !== ''; });
    return '#' + [name].concat(args.map(encodeURIComponent)).join('/');
  };
  UI.go = function (name) {
    var h = UI.hashFor.apply(null, arguments);
    if (location.hash === h) route(); else location.hash = h;
  };
  UI.refresh = function () { route(); };
  UI.after = null;  // where to go after signing in

  var shellRoot = null, view = null, current = { name: null, destroy: null }, routeSeq = 0;

  function defaultPage() { return UI.me ? UI.config.home : UI.config.landing; }

  function route() {
    var r = UI.parseHash(), name = r.name || defaultPage(), p = UI.pages[name];
    if (!p) { name = defaultPage(); p = UI.pages[name]; r.args = []; }
    if (p.auth === 'guest' && UI.me) { p = UI.pages[UI.config.home]; name = UI.config.home; r.args = []; }
    if ((p.auth === 'user' || p.auth === 'admin') && !UI.me) {
      UI.after = location.hash && location.hash !== '#' ? location.hash : null;
      p = UI.pages.auth; name = 'auth'; r.args = [];
    }
    if (p.auth === 'admin' && !(UI.me && UI.me.is_admin)) {
      UI.toast('That page is for admins only.', 'error');
      p = UI.pages[UI.config.home]; name = UI.config.home; r.args = [];
    }
    var seq = ++routeSeq;
    window.UI_READY = false;
    if (current.destroy) { try { current.destroy(); } catch (e) { console.error(e); } }
    current = { name: name, args: r.args, destroy: null };
    if (shellRoot) {
      shellRoot.className = 'ui ui-shell page-' + name + (UI.me ? ' signed-in' : ' signed-out') + (p.chrome === false ? ' no-chrome' : '');
      renderChrome(name);
    }
    // A fresh element for every page, so listeners a page adds to `view` never pile up.
    var fresh = view.cloneNode(false);
    view.parentNode.replaceChild(fresh, view);
    view = fresh;
    window.scrollTo(0, 0);
    document.title = (p.title ? (typeof p.title === 'function' ? p.title(r.args) : p.title) + ' · ' : '') + UI.config.name;
    var ctx = { name: name, args: r.args, me: UI.me, go: UI.go, api: UI.api, page: p };
    var out;
    try { out = p.mount(view, ctx); } catch (e) { console.error(e); out = Promise.reject(e); }
    var ready = out && typeof out.then === 'function' ? out : (out && out.ready) || Promise.resolve();
    if (out && out.destroy) current.destroy = out.destroy;
    Promise.resolve(ready).then(function () { if (seq === routeSeq) window.UI_READY = true; },
      function (e) {
        if (seq !== routeSeq) return;
        console.error(e);
        if (!view.innerHTML) view.innerHTML = '<div class="ui-wrap"><div class="ui-empty">' + UI.icon('info') +
          '<h3>This page didn\'t load</h3><p class="muted">' + UI.esc(e && e.message || 'Something went wrong.') + '</p>' +
          '<button class="ui-btn" onclick="UI.refresh()">Try again</button></div></div>';
        window.UI_READY = true;
      });
  }
  UI.current = function () { return current; };

  /* The shell's parts come from web/app.js: UI.shell = {header(me, active), footer(me), tabbar(me, active)} */
  function renderChrome(active) {
    var S = UI.shell || {};
    var hd = shellRoot.querySelector('[data-ui-header]'), ft = shellRoot.querySelector('[data-ui-footer]'), tb = shellRoot.querySelector('[data-ui-tabbar]');
    if (hd) hd.innerHTML = S.header ? S.header(UI.me, active) : '';
    if (ft) ft.innerHTML = S.footer ? S.footer(UI.me, active) : '';
    if (tb) tb.innerHTML = S.tabbar ? S.tabbar(UI.me, active) : '';
  }
  UI.renderChrome = function () { if (shellRoot) renderChrome(current.name); };

  /* Called by client_code/Main.py (and by the local harness) once the page is up. */
  UI.start = function (node, bridgeFn, bootJson) {
    bridge = bridgeFn;
    var boot = typeof bootJson === 'string' ? JSON.parse(bootJson || '{}') : (bootJson || {});
    UI.me = boot.me || null;
    var host = node && node.matches && node.matches('[data-ui-app]') ? node : (node && node.querySelector('[data-ui-app]')) || node || document.body;
    host.innerHTML = '<div class="ui ui-shell">' +
      '<header class="ui-header" data-ui-header></header>' +
      '<main class="ui-main" data-ui-view></main>' +
      '<footer class="ui-footer" data-ui-footer></footer>' +
      '<nav class="ui-tabbar" data-ui-tabbar aria-label="Main"></nav></div>';
    shellRoot = host.firstChild;
    view = host.querySelector('[data-ui-view]');
    if (UI.shell && UI.shell.wire) UI.shell.wire(shellRoot);
    window.addEventListener('hashchange', route);
    route();
  };

  /* ------------------------------------------------------------------ feedback form (footer + menu) */
  UI.feedback = function (kind) {
    var kinds = [['bug', 'Something\'s broken', 'bug'], ['idea', 'An idea', 'bulb'], ['question', 'A question', 'info'], ['other', 'Something else', 'chat']];
    var m = UI.modal('<h2>Send feedback</h2><p class="muted">Found a bug or have an idea? It goes straight to the people who make ' + UI.esc(UI.config.name) + '.</p>' +
      '<form class="ui-stack" data-fb>' +
      '<div class="ui-choices">' + kinds.map(function (k) {
        return '<label class="ui-choice"><input type="radio" name="kind" value="' + k[0] + '"' + ((kind || 'bug') === k[0] ? ' checked' : '') + '>' +
          '<span>' + UI.icon(k[2]) + UI.esc(k[1]) + '</span></label>';
      }).join('') + '</div>' +
      '<label class="ui-field"><span>What happened, or what would you like?</span><textarea name="message" rows="5" required minlength="5" placeholder="The more detail, the better."></textarea></label>' +
      (UI.me ? '' : '<label class="ui-field"><span>Your email <em>(optional, if you\'d like a reply)</em></span><input type="email" name="email" autocomplete="email"></label>') +
      '<p class="ui-hint">We also send the page you were on, your screen size and browser, to help us fix bugs.</p>' +
      '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + UI.icon('arrow') + 'Send</button></div></form>');
    var form = m.el.querySelector('[data-fb]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(form);
      var ctx = { page: location.hash || '#', screen: innerWidth + 'x' + innerHeight, browser: navigator.userAgent.slice(0, 280), theme: UI.theme() };
      UI.busy(form.querySelector('[type=submit]'), UI.api('submit_feedback', v.kind, v.message, v.email || null, ctx)).then(function () {
        m.close(); UI.toast('Thank you! Your message was sent.', 'ok');
      });
    });
    return m;
  };

  /* Shared clicks: [data-go="page/arg"], [data-feedback], [data-theme-set] anywhere in the app. */
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-go],[data-feedback],[data-theme-set]');
    if (!el) return;
    if (el.hasAttribute('data-go')) { e.preventDefault(); UI.go.apply(null, el.getAttribute('data-go').split('/')); }
    else if (el.hasAttribute('data-feedback')) { e.preventDefault(); UI.feedback(el.getAttribute('data-feedback') || null); }
    else if (el.hasAttribute('data-theme-set')) { e.preventDefault(); UI.setTheme(el.getAttribute('data-theme-set')); if (UI.shell && UI.shell.onTheme) UI.shell.onTheme(); }
  });
})();


/* app.js: this app's identity and frame: name, header, footer, phone tab bar.
   Pages live in web/pages/*.html. The engine (window.UI) is web/core.js. */
(function () {
  'use strict';
  UI.configure({
    name: 'Topameal',
    key: 'topameal',          // prefix for this app's browser storage
    tagline: 'Dinner, decided. With love.',   // footer line
    home: 'home',                // first page after signing in
    landing: 'landing'           // first page for visitors who aren't signed in
  });

  var esc = UI.esc;

  function brand() {
    return '<a class="ui-brand" href="#" data-go="' + (UI.me ? UI.config.home : UI.config.landing) + '" aria-label="' + esc(UI.config.name) + ' home">' +
      '<img src="_/theme/icon.svg" alt="" width="32" height="32"><span>' + esc(UI.config.name) + '</span></a>';
  }

  function themeSwitch() {
    var t = UI.theme();
    return '<div class="ui-seg" role="group" aria-label="Appearance">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
      return '<button type="button" data-theme-set="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
    }).join('') + '</div>';
  }

  function userMenu(me) {
    return '<div class="ui-menu" data-menu hidden>' +
      '<div class="ui-menu-head"><strong>' + esc(me.name) + '</strong><span class="muted small">' + esc(me.email) + '</span></div>' +
      '<a href="#profile" data-go="profile">' + UI.icon('user') + 'Your profile</a>' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<div class="ui-menu-block"><span class="small muted">Appearance</span>' + themeSwitch() + '</div>' +
      '<button type="button" data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button type="button" data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms</button>' +
      '<button type="button" data-signout>' + UI.icon('logout') + 'Sign out</button></div>';
  }

  UI.shell = {
    header: function (me, active) {
      var nav = UI.navPages();
      return '<div class="ui-header-in">' + brand() +
        (me ? '<nav class="ui-nav" aria-label="Main">' + nav.map(function (p) {
          return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
        }).join('') + '</nav>' : '') +
        '<div class="ui-header-right">' +
        (me ? '<button type="button" class="ui-avatar-btn" data-menu-toggle aria-label="Your account" aria-haspopup="true">' + esc(UI.initials(me.name)) + '</button>' + userMenu(me)
          : (active === 'auth' ? '' : '<a class="ui-btn ghost" href="#auth" data-go="auth">Sign in</a><a class="ui-btn primary" href="#auth/signup" data-go="auth/signup">Get started</a>')) +
        '</div></div>';
    },
    footer: function (me) {
      return '<div class="ui-footer-in"><div class="ui-footer-brand">' + brand() + '<p class="muted small">' + esc(UI.config.tagline) + '</p></div>' +
        '<div class="ui-footer-links">' +
        '<a href="#landing" data-go="landing">About</a>' +
        '<button type="button" data-feedback>Send feedback</button>' +
        '<button type="button" data-lk-open="overview">Privacy &amp; Terms</button>' +
        '</div><p class="ui-footer-legal small muted">© ' + new Date().getFullYear() + ' ' + esc(UI.config.name) + '</p></div>';
    },
    tabbar: function (me, active) {
      var nav = UI.navPages();
      if (!me || nav.length < 2) return '';
      return nav.slice(0, 4).map(function (p) {
        return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
      }).join('') + '<a href="#profile" class="' + (active === 'profile' ? 'on' : '') + '">' + UI.icon('user') + '<span>You</span></a>';
    },
    wire: function (root) {
      root.addEventListener('click', function (e) {
        var t = e.target.closest('[data-menu-toggle]');
        var menu = root.querySelector('[data-menu]');
        if (t && menu) { menu.hidden = !menu.hidden; t.setAttribute('aria-expanded', String(!menu.hidden)); return; }
        if (e.target.closest('[data-signout]')) { UI.auth('logout').then(function () { UI.toast('Signed out. See you soon!'); }); }
        if (menu && !menu.hidden && !e.target.closest('[data-menu] .ui-seg')) menu.hidden = true;
      });
      document.addEventListener('keydown', function (e) {
        var menu = root.querySelector('[data-menu]');
        if (e.key === 'Escape' && menu) menu.hidden = true;
      });
    },
    onTheme: function () {  // redraw the menu's Auto/Light/Dark buttons and keep the menu open
      var menu = document.querySelector('[data-menu]'), open = menu && !menu.hidden;
      UI.renderChrome();
      if (open) document.querySelector('[data-menu]').hidden = false;
    }
  };
})();


/* ===== _shared.html ===== */
(function () {
  var I = UI.ICONS;
  I.rice = '<path d="M3 12h18a9 8 0 0 1-18 0z"/><path d="M7.5 9.5c.5-1.6 2.4-3 4.5-3s4 1.4 4.5 3"/><path d="M10 8.2v.01M13 7.6v.01M14.8 8.6v.01"/>';
  I.pasta = '<path d="M3 13h18a9 7.5 0 0 1-18 0z"/><path d="M6 10c1.2-1.2 2.4 1.2 3.6 0s2.4 1.2 3.6 0 2.4 1.2 3.6 0 1.6.8 1.6.8"/><path d="M8 7c1.2-1.2 2.4 1.2 3.6 0s2.4 1.2 3.6 0"/>';
  I.potatoes = '<path d="M5.5 8.5C8 4.5 15 4 18.3 7.6c3 3.3 1.6 9.6-3.8 11.2-5 1.5-10.5-.4-11.2-4.4-.4-2.3.6-4.1 2.2-5.9z"/><path d="M10 10v.01M14.5 9.5v.01M12.5 14v.01"/>';
  I.pan = '<path d="M2.5 11.5h14v1.5a5 5 0 0 1-5 5h-4a5 5 0 0 1-5-5z"/><path d="M16.5 12.5h5"/><path d="M7 3.5c-1 1.4 1 2.2 0 4.5M11.5 3.5c-1 1.4 1 2.2 0 4.5"/>';
  I.cart = '<path d="M3 4h2.2l2.3 11h11L21 7.5H6.4"/><circle cx="9.5" cy="19.5" r="1.4"/><circle cx="17" cy="19.5" r="1.4"/>';
  I.bubbles = '<circle cx="8.5" cy="15" r="4.5"/><circle cx="16.5" cy="8.5" r="3"/><circle cx="18" cy="17" r="2"/>';
  I.snow = '<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9"/><path d="m9.5 4.5 2.5 2 2.5-2M9.5 19.5l2.5-2 2.5 2"/>';
  I.undo = '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>';
  I.week = '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/><path d="M12 17.2s-2.6-1.6-2.6-3.3a1.3 1.3 0 0 1 2.6-.5 1.3 1.3 0 0 1 2.6.5c0 1.7-2.6 3.3-2.6 3.3z"/>';
  I.fridge = '<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><path d="M6 10h12M9 6v1.5M9 13v2.5"/>';

  var esc = UI.esc;
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  var DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  var TM = window.TM = {
    today: function () { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); },
    date: function (iso) { return new Date(iso + 'T12:00:00'); },
    daysFrom: function (iso) { return Math.round((TM.date(iso) - TM.date(TM.today())) / 86400000); },
    day: function (iso) {
      var n = TM.daysFrom(iso);
      if (n === 0) return 'today';
      if (n === 1) return 'tomorrow';
      if (n === -1) return 'yesterday';
      if (n > 1 && n < 7) return DAYS[TM.date(iso).getDay()];
      return UI.fmtDate(iso, { weekday: 'short', day: 'numeric', month: 'short' });
    },
    cap: function (s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; },
    first: function (me) { return ((me && me.name) || 'love').split(' ')[0]; },
    greet: function (me) {
      var h = new Date().getHours(), n = TM.first(me);
      if (h < 5) return 'Still up, ' + n + '?';
      if (h < 12) return 'Morning, ' + n + '.';
      if (h < 17) return 'Hello, ' + n + '.';
      if (h < 21) return 'Evening, ' + n + '.';
      return 'It\'s late, ' + n + '.';
    },
    tier: function (n, label) {
      return '<span class="tm-tier" title="' + esc(label || '') + '" aria-label="Price: ' + esc(label || '') + '">' + '$$$'.slice(0, n) + '<i>' + '$$$'.slice(n) + '</i></span>';
    },
    meta: function (t, opts) {
      opts = opts || {};
      return '<div class="tm-meta">' +
        (opts.base === false ? '' : '<span>' + UI.icon(t.base) + 'over ' + esc(t.base) + '</span>') +
        '<span>' + UI.icon('clock') + t.minutes + ' min</span>' +
        '<span title="' + esc(t.dishes.join(', ')) + '">' + UI.icon('bubbles') + t.dish_count + ' to wash</span>' +
        TM.tier(t.tier, t.tier_label) + '</div>';
    },
    baseIcon: function (base, big) { return '<span class="tm-base ' + esc(base) + '"' + (big ? ' style="width:64px;height:64px"' : '') + '>' + UI.icon(base) + '</span>'; },
    /* How much of the base for n people (see BASES in Recipes.py). */
    baseAmount: function (base, n) {
      if (base === 'pasta') return (100 * n) + ' g of pasta';
      if (base === 'potatoes') return (2 * n) + ' medium potatoes';
      var cups = n / 2, whole = Math.floor(cups), half = cups - whole >= .5;
      return (whole ? whole : '') + (half ? '½' : '') + ' cup' + (cups > 1 ? 's' : '') + ' of rice';
    },
    note: function (lines, opts) {
      opts = opts || {};
      return '<div class="tm-note' + (opts.flat ? ' flat' : '') + '"' + (opts.attr || '') + '>' +
        (Array.isArray(lines) ? lines : [lines]).map(function (l, i) { return '<p' + (i ? ' class="small-hand"' : '') + '>' + l + '</p>'; }).join('') +
        (opts.actions ? '<div class="ui-row">' + opts.actions + '</div>' : '') +
        (opts.sign === false ? '' : '<span class="tm-sign">x Mom</span>') + '</div>';
    },
    hearts: function () {
      var box = document.createElement('div');
      box.className = 'tm-hearts'; box.setAttribute('aria-hidden', 'true');
      for (var i = 0; i < 18; i++) {
        var s = document.createElement('span');
        s.textContent = i % 4 === 3 ? '♡' : '♥';
        s.style.left = (5 + Math.random() * 90) + '%';
        s.style.fontSize = (16 + Math.random() * 22) + 'px';
        s.style.animationDelay = (Math.random() * .6) + 's';
        s.style.setProperty('--r', (Math.random() * 60 - 30) + 'deg');
        if (i % 3 === 1) s.style.color = 'var(--c-accent)';
        box.appendChild(s);
      }
      document.body.appendChild(box);
      setTimeout(function () { box.remove(); }, 3200);
    },
    pick: function (list) { return list[Math.floor(Math.random() * list.length)]; },
    list: function (words) {  // ["a", "b", "c"] -> "a, b and c"
      if (words.length < 2) return words.join('');
      return words.slice(0, -1).join(', ') + ' and ' + words[words.length - 1];
    },
    proud: ['Proud of you.', 'Look at you, feeding yourself properly.', 'That\'s my kid.', 'Well done, love. Now sit down and eat.',
            'See? You can do it.', 'Lovely. Soak the pan while you eat.']
  };
})();

/* ===== admin.html ===== */
(function () {
  var esc = UI.esc;
  var TABS = [['overview', 'Overview', 'grid'], ['kitchen', 'Kitchen', 'heart'], ['feedback', 'Feedback', 'inbox'], ['users', 'Users', 'users'], ['demo', 'Demo data', 'database']];

  UI.page('admin', { title: 'Admin', auth: 'admin' }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'overview';
    var fbFilter = 'new';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Admin</h1><p class="muted">Only admins see this page.</p></div></div>' +
      '<nav class="ui-tabs">' + TABS.map(function (t) {
        return '<a href="#admin/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + '</a>';
      }).join('') + '</nav><div data-body><div class="ui-skel"></div></div></div>';
    var body = view.querySelector('[data-body]');

    function overview() {
      return UI.api('admin_overview').then(function (d) {
        var stat = function (n, label, go) { return '<a class="ui-card ui-stat" href="#admin/' + go + '" style="text-decoration:none;color:inherit"><b>' + n + '</b><span>' + label + '</span></a>'; };
        body.innerHTML = '<div class="ad-stats">' + stat(d.users, 'people signed up', 'users') + stat(d.admins, UI.plural(d.admins, 'admin').replace(/^\d+ /, ''), 'users') +
          stat(d.feedback_new, 'new feedback', 'feedback') + stat(d.kitchens, 'kitchens set up', 'kitchen') + stat(d.cooked, 'dinners cooked', 'kitchen') + '</div>' +
          '<p class="muted small" style="margin-top:18px">Demo data is <b>' + esc(d.demo.state) + '</b> (' + d.demo.counts.users + ' demo people). Manage it in the Demo data tab.</p>';
      });
    }

    function feedback() {
      return UI.api('list_feedback', null).then(function (d) {
        var items = d.items.filter(function (i) { return fbFilter === 'all' || i.status === fbFilter; });
        body.innerHTML = '<div class="ui-row" style="margin-bottom:16px"><div class="ui-seg">' + [['new', 'New'], ['read', 'Read'], ['done', 'Done'], ['all', 'All']].map(function (f) {
          var n = f[0] === 'all' ? d.items.length : d.counts[f[0]];
          return '<button data-filter="' + f[0] + '" class="' + (fbFilter === f[0] ? 'on' : '') + '">' + f[1] + ' (' + n + ')</button>';
        }).join('') + '</div></div>' +
          (items.length ? '<div class="ad-fb">' + items.map(function (i) {
            var c = i.context || {};
            return '<div class="ui-item" data-id="' + esc(i.id) + '"><div class="meta"><span class="ui-badge ' + (i.kind === 'bug' ? 'bad' : i.kind === 'idea' ? 'brand' : '') + '">' + esc(i.kind_label) + '</span>' +
              '<b>' + esc(i.name) + '</b>' + (i.email ? '<a href="mailto:' + esc(i.email) + '">' + esc(i.email) + '</a>' : '') + '<span>' + esc(UI.fmtDateTime(i.created)) + '</span></div>' +
              '<p class="msg">' + esc(i.message) + '</p>' +
              '<div class="ctx">' + esc([c.page, c.screen, c.theme, c.browser].filter(Boolean).join(' · ')) + '</div>' +
              '<textarea data-note placeholder="Private note (only admins see it)">' + esc(i.note) + '</textarea>' +
              '<div class="ui-row" style="margin-top:10px">' + ['new', 'read', 'done'].map(function (s) {
                return '<button class="ui-btn sm' + (i.status === s ? ' primary' : '') + '" data-status="' + s + '">' + s[0].toUpperCase() + s.slice(1) + '</button>';
              }).join('') + '<span class="ui-spacer"></span><button class="ui-btn sm danger" data-del-fb>' + UI.icon('trash') + 'Delete</button></div></div>';
          }).join('') + '</div>'
            : '<div class="ui-empty">' + UI.icon('inbox') + '<h3>No ' + (fbFilter === 'all' ? '' : fbFilter + ' ') + 'messages</h3><p>Messages from the "Send feedback" form show up here.</p></div>');
      });
    }

    function users(query) {
      return UI.api('list_users', query || null).then(function (d) {
        body.innerHTML = '<form class="ui-row" data-search style="margin-bottom:14px"><input type="search" name="q" placeholder="Search by name or email" value="' + esc(query || '') + '" style="max-width:360px">' +
          '<button class="ui-btn" type="submit">' + UI.icon('search') + 'Search</button><span class="muted small">' + UI.plural(d.total, 'person', 'people') + '</span></form>' +
          '<table class="ad-users"><thead><tr><th>Name</th><th>Email</th><th>Joined</th><th>Admin</th><th>Active</th></tr></thead><tbody>' +
          d.users.map(function (u) {
            return '<tr data-id="' + esc(u.id) + '"><td><b>' + esc(u.name) + '</b></td><td class="email">' + esc(u.email) + '</td><td class="joined muted">' + esc(UI.fmtDate(u.joined)) + '</td>' +
              '<td><label class="ui-check"><input type="checkbox" data-admin' + (u.is_admin ? ' checked' : '') + '> Admin</label></td>' +
              '<td><label class="ui-check"><input type="checkbox" data-enabled' + (u.enabled ? ' checked' : '') + '> Active</label></td></tr>';
          }).join('') + '</tbody></table>';
      });
    }

    function demo() {
      return UI.api('admin_overview').then(function (d) {
        var c = d.demo.counts;
        body.innerHTML = '<div class="ui-card ui-narrow" style="margin:0"><h3>Demo data</h3>' +
          '<p class="muted">Example people and content, so the app never looks empty for the first visitors. Demo rows are flagged, so removing them never touches real data. Once removed, it stays removed until you load it again.</p>' +
          '<p>Status: <b>' + esc(d.demo.state) + '</b> · ' + Object.keys(c).map(function (k) { return c[k] + ' ' + esc(k); }).join(', ') + '</p>' +
          '<div class="ui-row"><button class="ui-btn primary" data-demo="load">' + UI.icon('refresh') + (d.demo.state === 'loaded' ? 'Reload demo data' : 'Load demo data') + '</button>' +
          '<button class="ui-btn danger" data-demo="remove">' + UI.icon('trash') + 'Remove demo data</button></div></div>';
      });
    }

    function kitchen() {
      return UI.api('admin_kitchen_stats').then(function (d) {
        var max = Math.max.apply(null, d.toppers.map(function (t) { return t.planned; }).concat([1]));
        body.innerHTML = '<div class="ad-stats" style="margin-bottom:22px">' +
          [[d.kitchens, 'kitchens'], [d.weeks, 'weekly plans'], [d.cooked, 'dinners cooked'], [d.nos, 'times someone said no']].map(function (s) {
            return '<div class="ui-card ui-stat"><b>' + s[0] + '</b><span>' + s[1] + '</span></div>';
          }).join('') + '</div>' +
          '<p class="muted small">Every topper in the catalogue (server_code/Recipes.py), most planned first. Lots of "no" means people skip it: reword it or swap it out. Demo households are counted too.</p>' +
          '<div class="ui-card" style="padding:8px 18px"><table class="ad-users ad-tp"><thead><tr><th>Topper</th><th>Planned</th><th>No</th><th>Cooked</th><th>Kind</th></tr></thead><tbody>' +
          d.toppers.map(function (t) {
            return '<tr><td><b>' + esc(t.name) + '</b><div class="ad-bar" aria-hidden="true"><i style="width:' + (100 * t.cooked / max) + '%;background:var(--c-good)"></i>' +
              '<i style="width:' + (100 * (t.planned - t.cooked) / max) + '%;background:var(--c-accent)"></i></div></td>' +
              '<td class="n">' + t.planned + '</td><td class="n no">' + t.no + '</td><td class="n ok">' + t.cooked + '</td>' +
              '<td class="meta small muted">' + esc(t.protein) + ' · over ' + esc(t.base) + ' · ' + '$$$'.slice(0, t.tier) + '</td></tr>';
          }).join('') + '</tbody></table></div>';
      });
    }

    var DRAW = { overview: overview, kitchen: kitchen, feedback: feedback, users: users, demo: demo };

    view.addEventListener('click', function (e) {
      var f = e.target.closest('[data-filter]');
      if (f) { fbFilter = f.getAttribute('data-filter'); feedback(); return; }
      var st = e.target.closest('[data-status]');
      if (st) {
        var card = st.closest('[data-id]');
        UI.api('set_feedback_status', card.getAttribute('data-id'), st.getAttribute('data-status'), card.querySelector('[data-note]').value).then(function () { UI.toast('Saved', 'ok'); feedback(); });
        return;
      }
      var del = e.target.closest('[data-del-fb]');
      if (del) {
        UI.confirm({ title: 'Delete this message?', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_feedback', del.closest('[data-id]').getAttribute('data-id')).then(feedback);
        });
        return;
      }
      var dm = e.target.closest('[data-demo]');
      if (dm) {
        var load = dm.getAttribute('data-demo') === 'load';
        UI.confirm({ title: load ? 'Load the demo data?' : 'Remove the demo data?', text: load ? 'Demo people and content are added (any old demo rows are replaced).' : 'Every demo row is deleted. Real data stays.', ok: load ? 'Load' : 'Remove', danger: !load })
          .then(function (yes) { if (yes) UI.busy(dm, UI.api(load ? 'demo_load' : 'demo_remove')).then(function () { UI.toast('Done', 'ok'); demo(); }); });
      }
    });
    view.addEventListener('change', function (e) {
      var row = e.target.closest('tr[data-id]');
      if (!row) return;
      var id = row.getAttribute('data-id'), box = e.target;
      var fn = box.hasAttribute('data-admin') ? 'set_admin' : box.hasAttribute('data-enabled') ? 'set_enabled' : null;
      if (fn) UI.api(fn, id, box.checked).then(function () { UI.toast('Saved', 'ok'); }, function (err) { box.checked = !box.checked; UI.toast(err.message, 'error'); });
    });
    view.addEventListener('submit', function (e) {
      if (e.target.matches('[data-search]')) { e.preventDefault(); users(UI.formData(e.target).q); }
    });
    return DRAW[tab]();
  });
})();

/* ===== auth.html ===== */
(function () {
  var esc = UI.esc;
  function pw(name, auto) {
    return '<div class="au-pw"><input type="password" name="' + name + '" autocomplete="' + auto + '" required minlength="8">' +
      '<button type="button" data-show>Show</button></div>';
  }
  UI.page('auth', { title: 'Sign in', auth: 'guest' }, function (view, ctx) {
    var mode = ['signup', 'reset'].indexOf(ctx.args[0]) >= 0 ? ctx.args[0] : 'login';
    function draw(msg, isErr) {
      var heading = { login: 'Welcome back', signup: 'Create your account', reset: 'Reset your password' }[mode];
      var sub = { login: 'Sign in to continue to ' + esc(UI.config.name) + '.', signup: 'It\'s free and takes a few seconds.',
        reset: 'We\'ll email you a link to choose a new password.' }[mode];
      view.innerHTML = '<div class="au-wrap"><div class="ui-card au-card">' +
        '<h1>' + heading + '</h1><p class="muted">' + sub + '</p>' +
        (mode !== 'reset' ? '<div class="ui-seg" role="tablist"><button type="button" data-mode="login" class="' + (mode === 'login' ? 'on' : '') + '">Sign in</button>' +
          '<button type="button" data-mode="signup" class="' + (mode === 'signup' ? 'on' : '') + '">Create account</button></div>' : '<div style="height:14px"></div>') +
        '<form class="ui-stack" data-form="' + mode + '" novalidate>' +
        (mode === 'signup' ? '<label class="ui-field"><span>Your name</span><input type="text" name="name" autocomplete="name" required maxlength="60"></label>' : '') +
        '<label class="ui-field"><span>Email</span><input type="email" name="email" autocomplete="email" required></label>' +
        (mode === 'login' ? '<label class="ui-field"><span>Password</span>' + pw('password', 'current-password') + '</label>' : '') +
        (mode === 'signup' ? '<label class="ui-field"><span>Password <em>(at least 8 characters)</em></span>' + pw('password', 'new-password') + '</label>' +
          (window.LegalKit ? '<div>' + LegalKit.consentField() + '</div>' : '') : '') +
        '<div data-msg role="alert"' + (msg ? ' class="' + (isErr ? 'ui-error' : 'ui-note') + '">' + esc(msg) : ' hidden>') + '</div>' +
        '<button class="ui-btn primary block" type="submit">' + { login: 'Sign in', signup: 'Create account', reset: 'Send the link' }[mode] + '</button></form>' +
        '<div class="au-links">' + (mode === 'login' ? '<a data-mode="reset">Forgot your password?</a>' : '<a data-mode="login">' + UI.icon('back') + ' Back to sign in</a>') +
        '<a href="#landing" data-go="landing">About ' + esc(UI.config.name) + '</a></div></div></div>';
      var first = view.querySelector('input');
      if (first && !msg) first.focus();
    }
    view.addEventListener('click', function (e) {
      var m = e.target.closest('[data-mode]');
      if (m) { e.preventDefault(); mode = m.getAttribute('data-mode'); history.replaceState(null, '', '#auth' + (mode === 'login' ? '' : '/' + mode)); draw(); return; }
      var s = e.target.closest('[data-show]');
      if (s) { var i = s.parentNode.querySelector('input'); i.type = i.type === 'password' ? 'text' : 'password'; s.textContent = i.type === 'password' ? 'Show' : 'Hide'; }
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target, v = UI.formData(form);
      var problem = !/^\S+@\S+\.\S+$/.test(v.email || '') ? 'Please enter a valid email address.'
        : mode !== 'reset' && (v.password || '').length < (mode === 'signup' ? 8 : 1) ? (mode === 'signup' ? 'Please choose a password of at least 8 characters.' : 'Please enter your password.')
        : mode === 'signup' && (v.name || '').trim().length < 2 ? 'Please tell us your name.' : null;
      if (problem) { say(problem, true); return; }
      if (mode === 'signup' && window.LegalKit && !LegalKit.consentChecked(form)) return;  // the kit shows its own message
      UI.busy(form.querySelector('[type=submit]'), UI.auth(mode, v)).then(function (r) {
        if (mode === 'reset' || (r && !r.me)) { mode = 'login'; draw(r && r.message, false); restore({ email: v.email }); }
        else UI.toast(mode === 'signup' ? 'Welcome to ' + UI.config.name + '!' : 'Welcome back!', 'ok');
      }, function (err) { say(err.message, true); });
    });
    function say(msg, isErr) {
      var box = view.querySelector('[data-msg]');
      box.className = isErr ? 'ui-error' : 'ui-note'; box.textContent = msg; box.hidden = false;
    }
    function restore(v) {
      ['name', 'email'].forEach(function (k) { var i = view.querySelector('[name=' + k + ']'); if (i && v[k]) i.value = v[k]; });
    }
    draw();
  });
})();

/* ===== cook.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('cook', { title: 'Cook', auth: 'user' }, function (view, ctx) {
    var key = ctx.args[0];
    if (!key) { UI.go('home'); return Promise.resolve(); }
    view.innerHTML = '<div class="ui-wrap ck ui-narrow"><div class="ui-skel" style="height:140px;margin-bottom:16px"></div><div class="ui-skel" style="height:320px"></div></div>';
    var D = null;

    function end() {
      if (!D.in_plan) return '<p class="muted">This one isn\'t on this week\'s plan.</p><a class="ui-btn" href="#home" data-go="home">Back to this week</a>';
      if (D.cooked) return '<span class="tm-flag ok" style="font-size:1rem;padding:8px 14px">' + UI.icon('heart') + 'Cooked ' + esc(TM.day(D.cooked)) + '</span>' +
        '<a class="ui-btn primary lg" href="#home" data-go="home">Back to this week</a>' +
        '<button class="ui-btn ghost sm" data-uncook>' + UI.icon('undo') + 'Actually, not yet</button>';
      return '<button class="ui-btn primary lg" data-cooked>' + UI.icon('heart') + 'I cooked it</button>' +
        '<p class="small muted">Leftovers? Lidded box, in the fridge within two hours, eaten within two days.</p>';
    }

    function draw() {
      var t = D.topper, b = D.base;
      document.title = t.name + ' · ' + UI.config.name;
      view.innerHTML = '<div class="ui-wrap ck ui-narrow">' +
        '<a class="ck-back" href="#home" data-go="home">' + UI.icon('back') + 'This week</a>' +
        '<div class="ck-title">' + TM.baseIcon(t.base, true) + '<div><h1>' + esc(t.name) + '</h1><p>' + esc(t.blurb) + '</p>' + TM.meta(t) +
        (t.also.length ? '<p class="small faint" style="margin:8px 0 0">Also lovely over ' + esc(TM.list(t.also)) + '.</p>' : '') + '</div></div>' +
        (D.cook_by && !D.cooked ? '<p><span class="tm-flag cook">' + UI.icon('clock') + 'Cook by ' + esc(TM.day(D.cook_by)) + '</span></p>' : '') +
        '<section class="ck-box"><h3>' + UI.icon('bubbles') + 'Get out ' + t.dish_count + ' things. That\'s all you\'ll wash.</h3>' +
        '<ul class="ck-dishes">' + t.dishes.map(function (d) { return '<li>' + esc(d) + '</li>'; }).join('') + '</ul></section>' +
        '<section class="ck-box"><h3>' + UI.icon('cart') + 'You\'ll need</h3><ul class="ck-ing">' +
        '<li>' + esc(TM.baseAmount(t.base, D.people)) + ' <span class="faint">(at home)</span></li>' +
        t.ingredients.map(function (i) { return '<li>' + esc(i) + '</li>'; }).join('') +
        '<li class="faint">oil, salt and pepper</li></ul></section>' +
        '<section class="ck-box"><h3>' + UI.icon('pan') + 'Steps</h3><ol class="ck-steps">' +
        '<li class="base"><span><b>' + esc(TM.cap(b.name)) + ' first.</b> ' + esc(TM.baseAmount(t.base, D.people)) + ' for ' + UI.plural(D.people, 'person', 'people') + '. ' + esc(b.how) + '</span></li>' +
        t.steps.map(function (s) { return '<li><span>' + esc(s) + '</span></li>'; }).join('') +
        '</ol><p class="ck-hint">Tap a step when it\'s done.</p></section>' +
        TM.note([esc(t.tip)]) +
        '<div class="ck-end">' + end() + '</div></div>';
    }

    view.addEventListener('click', function (e) {
      var li = e.target.closest('.ck-steps li');
      if (li) { li.classList.toggle('done'); return; }
      var b = e.target.closest('[data-cooked]');
      if (b) {
        UI.busy(b, UI.api('set_cooked', key, true, TM.today())).then(function (r) {
          TM.hearts();
          UI.toast(TM.pick(TM.proud), 'ok');
          UI.go('home');
        });
        return;
      }
      b = e.target.closest('[data-uncook]');
      if (b) UI.busy(b, UI.api('set_cooked', key, false, TM.today())).then(function () { D.cooked = null; draw(); });
    });

    return UI.api('get_cook', key, TM.today()).then(function (r) { D = r; draw(); });
  });
})();

/* ===== home.html ===== */
(function () {
  var esc = UI.esc;

  function flagFor(s, shopped) {
    if (s.cooked) return '<span class="tm-flag ok">' + UI.icon('heart') + 'Cooked ' + esc(TM.day(s.cooked)) + '</span>';
    if (s.past_best) return '<span class="tm-flag bad">' + UI.icon('info') + 'Past its best? Sniff test first</span>';
    if (s.cook_by) {
      var n = TM.daysFrom(s.cook_by);
      return '<span class="tm-flag ' + (n <= 0 ? 'warn' : 'cook') + '">' + UI.icon('clock') + (n <= 0 ? 'Cook it today' : 'Cook by ' + esc(TM.day(s.cook_by))) + '</span>';
    }
    if (s.keeps >= 30) return '<span class="tm-flag calm">' + UI.icon('check') + 'Keeps for ages</span>';
    return '<span class="tm-flag calm">' + UI.icon('fridge') + 'Keeps ' + s.keeps + ' day' + (s.keeps === 1 ? '' : 's') + '</span>';
  }

  function card(s, i, shopped, fresh) {
    var tip = '';
    if (!s.cooked && s.freeze) tip = '<p class="tip">' + UI.icon('snow') + '<span>Freeze the ' + esc(s.perishable) + ' when you get home. Move it to the fridge the night before.</span></p>';
    return '<article class="wk-card' + (s.cooked ? ' done' : '') + (fresh ? ' is-new' : '') + '" data-open="' + esc(s.key) + '" style="animation-delay:' + (i * 50) + 'ms">' +
      '<span class="num" aria-hidden="true">' + (s.cooked ? UI.icon('check') : i + 1) + '</span><div>' +
      '<h4>' + esc(s.name) + '</h4>' + TM.meta(s) +
      '<div class="flags">' + flagFor(s, shopped) +
      (s.cooked ? '' : '<button class="ui-btn ghost sm no" data-no="' + esc(s.key) + '" aria-label="No thanks to ' + esc(s.name) + '">' + UI.icon('x') + 'No thanks</button>') +
      '</div>' + tip + '</div></article>';
  }

  function hero(w, me) {
    var next = w.slots.filter(function (s) { return s.key === w.next; })[0];
    if (!next) return '';
    var shopped = !!w.shopped;
    if (!shopped) {
      var L = w.list;
      return '<section class="wk-hero"><div class="eyebrow">Step one</div><h2>Go shopping, once</h2>' +
        '<p class="blurb">' + UI.plural(L.total, 'thing') + ' for ' + UI.plural(w.totals.dinners, 'dinner') + ', in the order you walk the shop. ' +
        'Rice, pasta and potatoes you already have.</p>' +
        '<div class="ui-row"><a class="ui-btn primary lg" href="#list" data-go="list">' + UI.icon('cart') + 'Open my list</a>' +
        '<a class="ui-btn ghost" href="#cook/' + esc(next.key) + '" data-go="cook/' + esc(next.key) + '">Peek at the first recipe</a></div></section>';
    }
    var label = next.past_best ? 'Check this one first' : (next.cook_by && TM.daysFrom(next.cook_by) <= 0 ? 'Tonight, please' : 'Tonight');
    return '<section class="wk-hero"><div class="top">' + TM.baseIcon(next.base, true) + '<div><div class="eyebrow">' + esc(label) + '</div>' +
      '<h2>' + esc(next.name) + '</h2><p class="blurb">' + esc(next.blurb) + '</p>' + TM.meta(next) + '</div></div>' +
      '<div class="ui-row"><a class="ui-btn primary lg" href="#cook/' + esc(next.key) + '" data-go="cook/' + esc(next.key) + '">' + UI.icon('pan') + 'Let\'s cook</a></div></section>';
  }

  function momLine(w, me) {
    var next = w.slots.filter(function (s) { return s.key === w.next; })[0];
    var hi = TM.greet(me);
    if (w.all_done) return [hi + ' Every dinner cooked this week. I\'m so proud of you.'];
    var past = w.slots.filter(function (s) { return s.past_best && !s.cooked; })[0];
    if (past) return [hi + ' Check the ' + esc(past.perishable) + ' before you cook it, love.', 'If it smells off, bin it. Not worth a bad tummy.'];
    if (!w.shopped) {
      var lines = [hi + ' I\'ve sorted this week\'s dinners. All you have to do is the shopping.'];
      if (w.shared.length) lines.push('The ' + esc(TM.list(w.shared.slice(0, 3))) + ' go in more than one dinner, so nothing gets wasted.');
      else lines.push('Don\'t fancy one? Say no and I\'ll find another.');
      return lines;
    }
    if (next) return [hi + ' Tonight it\'s ' + esc(next.name.toLowerCase()) + '.', next.minutes + ' minutes and ' + next.dish_count + ' things to wash. You can do that.'];
    return [hi];
  }

  UI.page('home', { title: 'This week', nav: 'This week', icon: 'week', auth: 'user', order: 10 }, function (view, ctx) {
    var me = ctx.me, W = null, K = null, freshKey = null;
    view.innerHTML = '<div class="ui-wrap wk ui-narrow"><div class="ui-skel" style="height:120px;margin-bottom:20px"></div><div class="ui-skel" style="height:220px"></div></div>';

    function draw() {
      var w = W, k = K, shopped = !!w.shopped;
      var html = '<div class="ui-wrap wk ui-narrow">';
      html += TM.note(momLine(w, me));
      if (!k.confirmed) {
        html += '<div class="wk-assume" data-assume><p><b>I\'ve made a few guesses.</b> Tell me if I\'m wrong, otherwise carry on.</p><div class="facts">' +
          '<span class="ui-badge brand">' + UI.plural(k.people, 'person', 'people') + '</span>' +
          '<span class="ui-badge brand">' + k.nights + ' dinners a week</span>' +
          '<span class="ui-badge brand">' + esc(k.options.budget[k.budget - 1].label) + ' budget</span>' +
          '<span class="ui-badge">' + esc(TM.cap(TM.list(w.at_home))) + ' at home</span></div>' +
          '<div class="ui-row"><button class="ui-btn primary sm" data-confirm>' + UI.icon('check') + 'That\'s right</button>' +
          '<a class="ui-btn sm" href="#profile" data-go="profile">Change</a></div></div>';
      }
      if (w.all_done) {
        html += '<section class="wk-hero wk-done"><div class="big" aria-hidden="true">♥</div><h2>You fed yourself all week.</h2>' +
          '<p class="blurb" style="margin:0 auto 6px">' + UI.plural(w.story.cooked, 'dinner') + ' cooked with Topameal so far. Shall I plan the next week?</p>' +
          '<div class="ui-row" style="justify-content:center"><button class="ui-btn primary lg" data-fresh-now>' + UI.icon('sparkle') + 'Plan next week</button></div></section>';
      } else {
        html += hero(w, me);
      }
      if (w.slots.length) {
        html += '<div class="wk-head"><h3>' + (w.all_done ? 'This week' : 'In this order') + '</h3><span class="small muted">' +
          (shopped ? 'Shopped ' + esc(TM.day(w.shopped)) : 'Most perishable first') + '</span></div>' +
          '<div class="wk-list">' + w.slots.map(function (s, i) { return card(s, i, shopped, s.key === freshKey); }).join('') + '</div>';
        var T = w.totals;
        html += '<p class="wk-sum">' + UI.plural(T.dinners, 'dinner') + ' · ' + T.dishes + ' things to wash all week · roughly a ' +
          TM.tier(T.tier, T.tier_label) + ' <b>' + esc(T.tier_label.toLowerCase()) + '</b> week</p>';
      } else {
        html += '<div class="ui-empty">' + UI.icon('pan') + '<h3>Nothing fits, love</h3><p>With what you\'ve told me you don\'t eat, I\'ve run out of ideas. Loosen something in You?</p>' +
          '<a class="ui-btn" href="#profile" data-go="profile">Open my kitchen</a></div>';
      }
      if (w.nos.length) {
        html += '<section class="wk-tray"><div class="wk-head"><h3>Set aside</h3><span class="small muted">Changed your mind? Bring it back.</span></div><div class="chips">' +
          w.nos.map(function (n) {
            return '<span class="wk-chip"><span>' + esc(n.name) + '</span><button class="ui-btn sm" data-yes="' + esc(n.key) + '">' + UI.icon('undo') + 'Yes, this one</button></span>';
          }).join('') + '</div></section>';
      }
      if (!w.all_done && w.slots.length) {
        html += '<div class="wk-fresh"><button class="ui-btn ghost sm" data-fresh>' + UI.icon('refresh') + 'Start a whole new week</button></div>';
      }
      view.innerHTML = html + '</div>';
      freshKey = null;
    }

    function take(r) {
      W = r.week; K = r.kitchen;
      draw();
      if (r.note) UI.toast(r.note);
    }

    view.addEventListener('click', function (e) {
      var no = e.target.closest('[data-no]');
      if (no) {
        e.stopPropagation();
        var cardEl = no.closest('.wk-card');
        cardEl.style.transition = 'opacity .2s, transform .2s'; cardEl.style.opacity = '.35'; cardEl.style.transform = 'translateX(14px)';
        UI.busy(no, UI.api('say_no', no.getAttribute('data-no'), TM.today())).then(function (r) { freshKey = r.replaced_by; take(r); },
          function (err) { cardEl.style.opacity = ''; cardEl.style.transform = ''; throw err; });
        return;
      }
      var yes = e.target.closest('[data-yes]');
      if (yes) {
        freshKey = yes.getAttribute('data-yes');
        UI.busy(yes, UI.api('say_yes', freshKey, TM.today())).then(take);
        return;
      }
      if (e.target.closest('[data-confirm]')) {
        K.confirmed = true;
        var box = view.querySelector('[data-assume]'); if (box) box.remove();
        UI.apiQuiet('confirm_kitchen');
        UI.toast('Good. Leave it with me.');
        return;
      }
      if (e.target.closest('[data-fresh-now]')) {
        UI.busy(e.target.closest('[data-fresh-now]'), UI.api('new_plan', TM.today())).then(take);
        return;
      }
      if (e.target.closest('[data-fresh]')) {
        UI.confirm({ title: 'Start a whole new week?', text: 'I\'ll plan fresh dinners and a new list. This week\'s plan goes into the history.', ok: 'Yes, start fresh' })
          .then(function (ok) { if (ok) UI.api('new_plan', TM.today()).then(take); });
        return;
      }
      var open = e.target.closest('[data-open]');
      if (open && !e.target.closest('a,button')) UI.go('cook', open.getAttribute('data-open'));
    });

    return UI.api('get_week', TM.today()).then(function (r) { W = r.week; K = r.kitchen; draw(); });
  });
})();

/* ===== landing.html ===== */
(function () {
  var COPY = {
    hand: 'Don\'t worry, love.',
    title: 'You\'ve got rice. <em>I\'ve got the rest.</em>',
    lead: 'Topameal plans a week of quick one-pan toppers to pour over the rice, pasta and potatoes you already have. ' +
          'It writes the shopping list, tells you what to cook first so nothing spoils, and even counts the dishes. You don\'t choose anything. You just say no to what you don\'t fancy.',
    cta: 'Plan my week',
    proof: [['heart', 'Free'], ['pan', 'One big pan a night'], ['check', 'Nothing to decide']],
    stepsTitle: 'How it works',
    stepsLead: 'Three steps. Mom does the thinking.',
    steps: [['I pick your dinners', 'Three to seven toppers that share fresh ingredients, mix up the meat, and fit your budget. Don\'t fancy one? Tap no and I\'ll find another.'],
            ['You shop one list', 'Merged and sorted in the order you walk the shop, with the cupboard checks set apart. Tick as you go, or send it to whoever\'s shopping.'],
            ['Cook the right one first', 'Fish and mince first, sausages later, tins last. Every dinner gets a cook-by day, big simple steps, and a count of what you\'ll wash.']],
    featuresTitle: 'The rules I cook by',
    features: [['check', 'No choosing', 'Decision fatigue is real. I suggest, you only ever say no. And if you change your mind, it\'s one tap to bring it back.'],
               ['clock', 'Nothing goes off', 'Plans run most-perishable first. If something won\'t last until its night, I\'ll tell you to freeze it when you get home.'],
               ['heart', 'Less waste', 'Toppers that share the cream, the spinach or the peppers get planned together, so half a bag never dies in the fridge.'],
               ['bubbles', 'Dishes counted', 'Every recipe tells you what to get out, and that\'s all you\'ll wash. Some only need the pan and a spoon.'],
               ['star', 'Price tiers, not prices', 'Thrifty, comfortable or a little treat. You\'ll always know roughly what kind of week it is, without a calculator.'],
               ['sparkle', 'Shortcuts welcome', 'Garlic in a jar, pre-grated cheese, frozen shrimp straight into the pan. Cooking when you\'re tired should be easy.']],
    faq: [['Do I have to pick recipes?', 'No, and that\'s the point. I plan the week. If you don\'t fancy something, tap "No thanks" and I\'ll suggest something else that still fits the rest of the week.'],
          ['What if I say no to something by mistake?', 'It goes to "Set aside" at the bottom of your week. Tap "Yes, this one" and it comes straight back. Say no to the same dinner three times and I\'ll stop suggesting it (you can bring it back any time).'],
          ['Why rice, pasta and potatoes?', 'Because most kitchens already have them, they keep for ages, and anything good from a frying pan tastes great poured over them. You only shop for the topping.'],
          ['How accurate are the prices?', 'They are tiers, not prices: thrifty, comfortable or a little treat. Prices change by shop and by week, so I keep it simple.'],
          ['What about allergies?', 'Tell me what you don\'t eat in You (no pork, vegetarian, no nuts, no dairy and so on) and I\'ll leave those out. Always check labels yourself: I can\'t see what\'s in your shop\'s jars.'],
          ['Is it free?', 'Yes. No ads either.']],
    bandTitle: 'Let me take one thing off your plate.',
    bandLead: 'Dinner. I\'ll take dinner.'
  };

  function heroArt() {
    var chunk = function (x, y, r) { return '<rect x="' + x + '" y="' + y + '" width="34" height="24" rx="10" transform="rotate(' + r + ' ' + (x + 17) + ' ' + (y + 12) + ')" style="fill:#f1cb92;stroke:#d39b5c;stroke-width:2"/>'; };
    var tom = function (x, y) { return '<circle cx="' + x + '" cy="' + y + '" r="11" style="fill:#d83a2a"/><circle cx="' + (x - 3.5) + '" cy="' + (y - 4) + '" r="3" style="fill:#fff;opacity:.45"/>'; };
    var leaf = function (x, y, r) { return '<ellipse cx="' + x + '" cy="' + y + '" rx="13" ry="7" transform="rotate(' + r + ' ' + x + ' ' + y + ')" style="fill:#4f8a3a"/>'; };
    return '<div class="lp-art" aria-hidden="true"><svg class="pan" viewBox="0 0 440 400">' +
      '<defs><pattern id="lp-g" width="28" height="28" patternUnits="userSpaceOnUse"><rect width="28" height="28" style="fill:var(--c-surface)"/>' +
      '<rect width="14" height="28" style="fill:var(--c-brand);opacity:.22"/><rect width="28" height="14" style="fill:var(--c-brand);opacity:.22"/></pattern>' +
      '<radialGradient id="lp-s" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="#ec8a5e"/><stop offset=".7" stop-color="#c9532f"/><stop offset="1" stop-color="#a8401f"/></radialGradient></defs>' +
      '<rect x="40" y="36" width="360" height="330" rx="20" transform="rotate(-6 220 200)" style="fill:url(#lp-g)"/>' +
      '<path d="M300 268 L408 352" style="stroke:#2b201b;stroke-width:28;stroke-linecap:round"/>' +
      '<ellipse cx="206" cy="218" rx="132" ry="128" style="fill:#000;opacity:.12"/>' +
      '<circle cx="200" cy="200" r="130" style="fill:#2b201b"/><circle cx="200" cy="200" r="117" style="fill:#3d2e25"/>' +
      '<circle cx="200" cy="200" r="106" style="fill:url(#lp-s)"/>' +
      '<path d="M130 190c30-40 90-50 130-20M150 250c40 20 90 10 110-20" style="fill:none;stroke:#fbe7cc;stroke-width:7;stroke-linecap:round;opacity:.55"/>' +
      chunk(130, 150, -18) + chunk(205, 128, 12) + chunk(240, 200, -30) + chunk(150, 222, 22) + chunk(196, 250, -8) + chunk(178, 182, 40) +
      leaf(250, 160, 30) + leaf(130, 205, -40) + leaf(232, 258, 10) + leaf(165, 140, 70) + leaf(270, 228, -60) +
      tom(222, 176) + tom(140, 180) + tom(262, 252) + tom(186, 222) + tom(172, 268) +
      '<g class="steam" style="fill:none;stroke:var(--c-faint);stroke-width:5;stroke-linecap:round">' +
      '<path d="M160 70c-10-14 10-22 0-38"/><path d="M200 60c-10-14 10-22 0-38"/><path d="M240 70c-10-14 10-22 0-38"/></g></svg>' +
      '<div class="lp-list"><b>Mom\'s list ♥</b><span><s>chicken thighs</s></span><span>cherry tomatoes</span><span>baby spinach</span><span>cooking cream</span>' +
      '<span class="home">rice? you have it.</span></div>' +
      '<span class="lp-chip a">' + UI.icon('bubbles') + '5 things to wash</span>' +
      '<span class="lp-chip b">' + UI.icon('clock') + 'Cook by Wednesday</span></div>';
  }

  function peek() {
    var m = UI.modal('<h2>A week, planned</h2><p class="muted">A sample for two people. Yours is made fresh when you sign up.</p><div data-peek><div class="ui-skel" style="height:260px"></div></div>');
    UI.api('sample_week').then(function (d) {
      var esc = UI.esc, L = d.list, items = [];
      L.aisles.forEach(function (a) { if (a.key !== 'cupboard') a.items.forEach(function (i) { items.push(i.text.replace(/^1 /, '')); }); });
      m.el.querySelector('[data-peek]').innerHTML = '<div class="pk-list">' + d.slots.map(function (s, i) {
        return '<div class="pk-item">' + TM.baseIcon(s.base) + '<div><b>' + (i + 1) + '. ' + esc(s.name) + '</b>' + TM.meta(s, { base: true }) + '</div></div>';
      }).join('') + '</div>' +
        '<div class="pk-shop"><b>The list (' + L.total + ' things):</b> ' + esc(items.slice(0, 9).join(', ')) + (items.length > 9 ? ' and a few more' : '') + '.' +
        (d.shared.length ? ' The ' + esc(TM.list(d.shared.slice(0, 2))) + ' go in more than one dinner.' : '') + '</div>' +
        '<div class="ui-row end" style="margin-top:18px"><button class="ui-btn ghost" data-close>Close</button>' +
        '<a class="ui-btn primary" href="#auth/signup" data-go="auth/signup" data-close>' + esc(COPY.cta) + ' ' + UI.icon('arrow') + '</a></div>';
    });
  }

  UI.page('landing', { title: 'Dinner, decided' }, function (view, ctx) {
    var me = ctx.me, C = COPY, esc = UI.esc;
    var primary = me ? '<a class="ui-btn primary lg" href="#home" data-go="home">Open this week ' + UI.icon('arrow') + '</a>'
      : '<a class="ui-btn primary lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + ' ' + UI.icon('arrow') + '</a>' +
        '<button class="ui-btn lg" data-peek-open>' + UI.icon('pan') + 'Peek at a week</button>';
    view.innerHTML =
      '<section class="lp-hero"><div class="ui-wrap"><div>' +
        '<span class="lp-hand">' + esc(C.hand) + '</span><h1>' + C.title + '</h1><p class="lp-lead">' + esc(C.lead) + '</p>' +
        '<div class="lp-cta">' + primary + '</div>' +
        '<div class="lp-proof">' + C.proof.map(function (p) { return '<span>' + UI.icon(p[0]) + esc(p[1]) + '</span>'; }).join('') + '</div>' +
      '</div>' + heroArt() + '</div></section>' +
      '<section class="lp-section" id="how"><div class="ui-wrap"><div class="lp-head"><h2>' + esc(C.stepsTitle) + '</h2><p>' + esc(C.stepsLead) + '</p></div>' +
        '<div class="lp-steps">' + C.steps.map(function (s) { return '<div class="ui-card lp-step"><h3>' + esc(s[0]) + '</h3><p class="muted">' + esc(s[1]) + '</p></div>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><h2>' + esc(C.featuresTitle) + '</h2></div>' +
        '<div class="ui-grid">' + C.features.map(function (f) { return '<div class="ui-card lp-feature">' + UI.icon(f[0]) + '<h3>' + esc(f[1]) + '</h3><p>' + esc(f[2]) + '</p></div>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><h2>Questions</h2></div><div class="lp-faq">' +
        C.faq.map(function (q) { return '<details><summary>' + esc(q[0]) + '</summary><p>' + esc(q[1]) + '</p></details>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-band"><div><h2>' + esc(C.bandTitle) + '</h2><p>' + esc(C.bandLead) + '</p></div>' +
        (me ? '<a class="ui-btn lg" href="#home" data-go="home">Open this week</a>' : '<a class="ui-btn lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + '</a>') +
      '</div></div></section>';
    view.addEventListener('click', function (e) { if (e.target.closest('[data-peek-open]')) peek(); });
  });
})();

/* ===== list.html ===== */
(function () {
  var esc = UI.esc;
  var AISLE_ICONS = { meat: 'pan', veg: 'sparkle', fridge: 'fridge', freezer: 'snow', shelf: 'grid', cupboard: 'home' };

  UI.page('list', { title: 'Shopping list', nav: 'Shopping', icon: 'cart', auth: 'user', order: 20 }, function (view, ctx) {
    var W = null;
    view.innerHTML = '<div class="ui-wrap sl ui-narrow"><div class="ui-skel" style="height:90px;margin-bottom:16px"></div><div class="ui-skel" style="height:360px"></div></div>';

    function counts() {
      var all = view.querySelectorAll('.sl-item input'), on = view.querySelectorAll('.sl-item input:checked');
      return { total: all.length, done: on.length };
    }
    function progress() {
      var c = counts(), el = view.querySelector('.sl-prog');
      if (!el) return;
      el.querySelector('i').style.width = (c.total ? 100 * c.done / c.total : 0) + '%';
      el.querySelector('[data-count]').textContent = c.done + ' of ' + c.total + ' in the basket';
    }

    function draw() {
      var w = W, L = w.list, T = w.totals;
      var lines = ['Everything for ' + UI.plural(T.dinners, 'dinner') + ', for ' + UI.plural(w.people, 'person', 'people') + '.'];
      if (w.shared.length) lines.push('The ' + esc(TM.list(w.shared.slice(0, 3))) + ' go in more than one dinner. That\'s on purpose.');
      else lines.push('Roughly a ' + esc(T.tier_label.toLowerCase()) + ' week. Don\'t buy anything that\'s not on here.');
      var html = '<div class="ui-wrap sl ui-narrow"><div class="ui-page-head sl-head"><div><h1>Shopping list</h1>' +
        '<p class="muted">Roughly a ' + TM.tier(T.tier, T.tier_label) + ' <b>' + esc(T.tier_label.toLowerCase()) + '</b> week</p></div>' +
        '<button class="ui-btn sm" data-copy>' + UI.icon('copy') + 'Copy list</button></div>' +
        TM.note(lines) +
        '<p class="sl-home"><b>Already at home:</b> ' + esc(TM.list(w.at_home)) + '. I\'m assuming.</p>';
      if (!L.total) {
        view.innerHTML = html + '<div class="ui-empty">' + UI.icon('cart') + '<h3>Nothing to buy</h3><p>There are no dinners on this week\'s plan.</p>' +
          '<a class="ui-btn" href="#home" data-go="home">Back to this week</a></div></div>';
        return;
      }
      html += '<div class="sl-prog" aria-live="polite"><div class="ui-row between"><span data-count></span>' +
        (w.shopped ? '<span class="tm-flag ok">' + UI.icon('check') + 'Shopped ' + esc(TM.day(w.shopped)) + '</span>' : '') + '</div><div class="bar"><i></i></div></div>';
      html += L.aisles.map(function (a) {
        return '<section class="sl-aisle"><h3>' + UI.icon(AISLE_ICONS[a.key] || 'grid') + esc(a.label) + '</h3>' +
          (a.key === 'cupboard' ? '<p class="hint">Most kitchens have these. Have a look before you go, and only buy what\'s missing.</p>' : '') +
          '<div class="sl-items">' + a.items.map(function (it) {
            return '<label class="sl-item' + (it.checked ? ' on' : '') + '"><input type="checkbox" data-item="' + esc(it.key) + '"' + (it.checked ? ' checked' : '') + '>' +
              '<span class="box">' + UI.icon('check') + '</span><span><span class="what">' + esc(it.text) + '</span>' +
              '<span class="for">for ' + esc(TM.list(it.for)) + '</span>' +
              (it.perishable ? '<span class="tm-flag warn">' + UI.icon('fridge') + 'Fridge straight away · keeps ' + UI.plural(it.keeps, 'day') + '</span>' : '') +
              '</span></label>';
          }).join('') + '</div></section>';
      }).join('');
      html += '<div class="sl-done">' + (w.shopped
        ? '<p class="muted">Shopping done. Every dinner now has a cook-by day.</p><a class="ui-btn primary lg" href="#home" data-go="home">' + UI.icon('pan') + 'What\'s for tonight?</a>' +
          '<button class="ui-btn ghost sm" data-unshop>' + UI.icon('undo') + 'Actually, I haven\'t shopped yet</button>'
        : '<button class="ui-btn primary lg" data-shopped>' + UI.icon('check') + 'I\'ve done the shopping</button><p class="small muted">Then I\'ll tell you what to cook first, and by when.</p>') +
        '</div></div>';
      view.innerHTML = html;
      progress();
    }

    function asText() {
      var w = W, out = ['Topameal shopping list (' + UI.plural(w.totals.dinners, 'dinner') + ')', ''];
      w.list.aisles.forEach(function (a) {
        out.push(a.label.toUpperCase());
        a.items.forEach(function (it) {
          var on = view.querySelector('[data-item="' + it.key + '"]');
          out.push((on && on.checked ? '[x] ' : '[ ] ') + it.text);
        });
        out.push('');
      });
      out.push('At home already: ' + TM.list(w.at_home) + '.');
      return out.join('\n');
    }

    view.addEventListener('change', function (e) {
      var box = e.target.closest('[data-item]');
      if (!box) return;
      box.closest('.sl-item').classList.toggle('on', box.checked);
      progress();
      UI.apiQuiet('set_checked', box.getAttribute('data-item'), box.checked, TM.today()).catch(function (err) {
        box.checked = !box.checked; box.closest('.sl-item').classList.toggle('on', box.checked); progress(); throw err;
      });
      var c = counts();
      if (box.checked && c.done === c.total && !W.shopped) UI.toast('That\'s everything! Tap "I\'ve done the shopping" when you\'re home.', 'ok');
    });
    view.addEventListener('click', function (e) {
      var b = e.target.closest('[data-shopped]');
      if (b) {
        UI.busy(b, UI.api('set_shopped', true, TM.today())).then(function () {
          UI.toast('Well done, love. Fridge things in the fridge, then sit down.', 'ok');
          UI.go('home');
        });
        return;
      }
      b = e.target.closest('[data-unshop]');
      if (b) { UI.busy(b, UI.api('set_shopped', false, TM.today())).then(function (r) { W = r.week; draw(); }); return; }
      if (e.target.closest('[data-copy]')) {
        var text = asText();
        var done = function () { UI.toast('Copied. Paste it anywhere, or send it to whoever\'s shopping.', 'ok'); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fallback(text); });
        else fallback(text);
      }
    });
    function fallback(text) {
      var m = UI.modal('<h2>Your list</h2><p class="muted">Select it all and copy.</p><textarea rows="12" readonly style="font-size:.9rem">' + esc(text) + '</textarea>');
      var ta = m.el.querySelector('textarea'); ta.focus(); ta.select();
    }

    return UI.api('get_week', TM.today()).then(function (r) { W = r.week; draw(); });
  });
})();

/* ===== profile.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('profile', { title: 'You', auth: 'user' }, function (view, ctx) {
    var me = ctx.me;
    view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="pf-head"><span class="ui-avatar">' + esc(UI.initials(me.name)) + '</span>' +
      '<div><h1>' + esc(me.name) + '</h1><div class="muted">' + esc(me.email) + (me.joined ? ' · member since ' + esc(UI.fmtDate(me.joined, { month: 'long', year: 'numeric' })) : '') + '</div></div></div>' +
      '<form class="ui-card kc" data-kitchen style="margin-bottom:16px"><div class="ui-skel"></div></form>' +
      '<div class="pf-grid"><form class="ui-card ui-stack" data-name><h3>Your name</h3><label class="ui-field"><span>What should I call you?</span>' +
      '<input type="text" name="name" value="' + esc(me.name) + '" maxlength="60" required></label><button class="ui-btn primary" type="submit">Save</button></form>' +
      '<div class="ui-card ui-stack"><h3>Appearance</h3><p class="muted small">Follow your device, or pick one.</p><div data-theme-box></div>' +
      '<h3 style="margin-top:22px">Password</h3><p class="muted small">We\'ll email you a link to choose a new one.</p>' +
      '<button class="ui-btn" data-reset>' + UI.icon('mail') + 'Email me a reset link</button></div></div>' +
      '<div class="ui-card" style="margin-top:16px"><div class="pf-links">' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<button data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms, and your data</button>' +
      '<button data-signout-here>' + UI.icon('logout') + 'Sign out</button></div></div></div>';
    function themeBox() {
      var t = UI.theme();
      view.querySelector('[data-theme-box]').innerHTML = '<div class="ui-seg">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
        return '<button type="button" data-theme-pick="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
      }).join('') + '</div>';
    }
    themeBox();
    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-theme-pick]');
      if (t) { UI.setTheme(t.getAttribute('data-theme-pick')); themeBox(); UI.renderChrome(); return; }
      if (e.target.closest('[data-reset]')) {
        UI.busy(e.target.closest('[data-reset]'), UI.auth('reset', { email: me.email })).then(function (r) { UI.toast(r.message, 'ok'); });
      }
      if (e.target.closest('[data-signout-here]')) UI.auth('logout');
    });
    // ---- your kitchen
    var K = null, kbox = view.querySelector('[data-kitchen]');
    function picked() { return Array.prototype.map.call(kbox.querySelectorAll('[name=avoid]:checked'), function (x) { return x.value; }); }
    function stepper(name, label) {
      return '<div class="kc-step"><button type="button" class="ui-btn" data-step="' + name + ',-1" aria-label="Fewer ' + label + '">−</button><output data-out="' + name + '">' + K[name] + '</output>' +
        '<button type="button" class="ui-btn" data-step="' + name + ',1" aria-label="More ' + label + '">+</button></div>';
    }
    function kitchen() {
      var o = K.options;
      kbox.innerHTML = '<h2>Your kitchen</h2><p class="muted small">So I plan the right amount. I don\'t ask what you like: I suggest, you say no.</p>' +
        '<div class="kc-row first"><div><b>How many of you?</b><span class="small">I scale the shopping list.</span></div>' + stepper('people', 'people') + '</div>' +
        '<div class="kc-row"><div><b>Dinners a week</b><span class="small">The other nights: leftovers, or toast. No judgement.</span></div>' + stepper('nights', 'dinners') + '</div>' +
        '<div class="kc-row"><div><b>Budget</b><span class="small">A little treat lets in steak and salmon.</span></div><div class="ui-seg" role="group" aria-label="Budget">' +
        o.budget.map(function (b) { return '<button type="button" data-budget="' + b.key + '" class="' + (K.budget === b.key ? 'on' : '') + '">' + esc(b.label) + '</button>'; }).join('') + '</div></div>' +
        '<div class="kc-row"><div><b>Anything you don\'t eat?</b><span class="small">Only if you must. Always check labels for allergies.</span></div>' +
        '<div class="kc-avoid">' + o.avoid.map(function (a) {
          return '<label><input type="checkbox" name="avoid" value="' + esc(a.key) + '"' + (K.avoid.indexOf(a.key) >= 0 ? ' checked' : '') + '><span>' + esc(a.label) + '</span></label>';
        }).join('') + '</div></div>' +
        (K.never.length ? '<div class="kc-row"><div><b>I\'ve stopped suggesting</b><span class="small">You said no three times. Give one another chance?</span></div><div class="kc-never">' +
          K.never.map(function (n) {
            return '<span class="wk-chip' + (n.gone ? ' gone' : '') + '"><span>' + esc(n.name) + '</span><button type="button" class="ui-btn sm" data-forgive="' + esc(n.key) + '">' +
              (n.gone ? UI.icon('x') + 'Keep it off' : UI.icon('undo') + 'Bring back') + '</button></span>';
          }).join('') + '</div></div>' : '') +
        '<div class="ui-row end" style="margin-top:14px"><button class="ui-btn primary" type="submit">' + UI.icon('check') + 'Save my kitchen</button></div>';
    }
    kbox.addEventListener('click', function (e) {
      var st = e.target.closest('[data-step]');
      if (st) {
        var p = st.getAttribute('data-step').split(','), lim = p[0] === 'people' ? [1, 8] : [2, 7];
        K[p[0]] = Math.max(lim[0], Math.min(lim[1], K[p[0]] + Number(p[1])));
        kbox.querySelector('[data-out="' + p[0] + '"]').textContent = K[p[0]];
        return;
      }
      var bu = e.target.closest('[data-budget]');
      if (bu) {
        K.budget = Number(bu.getAttribute('data-budget'));
        kbox.querySelectorAll('[data-budget]').forEach(function (x) { x.classList.toggle('on', x === bu); });
        return;
      }
      var fg = e.target.closest('[data-forgive]');
      if (fg) {
        K.avoid = picked();
        K.never.forEach(function (n) { if (n.key === fg.getAttribute('data-forgive')) n.gone = !n.gone; });
        kitchen();
      }
    });
    kbox.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = { people: K.people, nights: K.nights, budget: K.budget, avoid: picked(),
        never: K.never.filter(function (n) { return !n.gone; }).map(function (n) { return n.key; }) };
      UI.busy(kbox.querySelector('[type=submit]'), UI.api('save_kitchen', data, TM.today())).then(function (r) {
        K = r.kitchen; kitchen(); UI.toast(r.note || 'Saved', 'ok');
      });
    });
    var ready = UI.api('get_kitchen').then(function (r) { K = r.kitchen; kitchen(); });

    view.querySelector('[data-name]').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(e.target);
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('update_profile', v.name)).then(function (r) {
        UI.setMe(r.me); ctx.me = r.me; UI.toast('Saved', 'ok');
        view.querySelector('.pf-head h1').textContent = r.me.name;
      });
    });
    return ready;
  });
})();
