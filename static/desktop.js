/* v49.14: Chisme as a desktop website (screens 1024 px and wider). Phones and narrow windows keep the app exactly as it
   is: this file does nothing there (except the optional "Chisme moved" note for installed users, see moved()).
   On wide screens it turns the app into a site, reusing the app's own parts (tabs, story cards, reader, settings):
     • a top nav: the logo, the 4 tabs (the app's own buttons), ⚙️ Settings and "Get the app"
     • the homepage (the Chisme tab): a hero (QR code, Add to Home Screen steps, "coming soon to the stores"), the latest
       chisme as a multi-column grid, and a sidebar: weather, the local sponsor spot, Juegos, ¿Y la dieta?, the
       App Store goal card
     • the reader as a side panel (desktop.css), Chisme's own pages (About, Support, Privacy, Terms) open in it too
     • a footer on every page, a Settings switch for 21+ sponsors
   Built from server data only (textContent / attributes, never innerHTML with outside text). The server side is website.py. */
(function () {
  "use strict";
  var MIN = 1024, MQ = window.matchMedia("(min-width: " + MIN + "px)"), d = document.documentElement;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var C = function () { return window.__chisme || null; }, R = function () { return window.__chismeReader || null; };
  var AGE_KEY = "chisme-21plus", MOVED_KEY = "chisme-moved-x";
  var lsGet = function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } };
  var lsSet = function (k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} };
  var reduced = function () { return d.classList.contains("reduce-motion") || window.matchMedia("(prefers-reduced-motion: reduce)").matches; };

  // h("a", { class: "x", href: "/", text: "Hi", on: { click: fn } }, child, …): text and attributes only
  function h(tag, props) {
    var n = document.createElement(tag), p = props || {};
    Object.keys(p).forEach(function (k) {
      var v = p[k];
      if (v == null || v === false) return;
      if (k === "text") n.textContent = v;
      else if (k === "on") Object.keys(v).forEach(function (ev) { n.addEventListener(ev, v[ev]); });
      else n.setAttribute(k, v === true ? "" : String(v));
    });
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      (Array.isArray(c) ? c : [c]).forEach(function (x) { if (x != null && x !== false) n.append(x.nodeType ? x : document.createTextNode(String(x))); });
    }
    return n;
  }
  function fill(n) { var a = Array.prototype.slice.call(arguments, 1).filter(function (x) { return x != null && x !== false; }); n.replaceChildren.apply(n, a); return n; }
  var emo = function (e) { return h("span", { "aria-hidden": "true", text: e }); };

  var SITE = { base: location.origin, goal: { title: "Help get Chisme on the App Store", amount: 99, url: "https://buymeacoffee.com/Chismoso", raised: null }, moved: { on: false } };
  var siteReady = null;
  function loadSite() {
    if (!siteReady) siteReady = fetch("/api/site").then(function (r) { return r.json(); }).then(function (j) { if (j && j.goal) SITE = j; return SITE; }).catch(function () { return SITE; });
    return siteReady;
  }

  // ---------------------------------------------------------------- helpers shared by the widgets
  var nodes = [];   // everything this file adds: shown only in desktop mode
  var mark = function (n) { nodes.push(n); return n; };
  var navH = function () { var t = $("#tabs"); return t ? t.offsetHeight : 0; };
  function scrollToEl(el, focusEl) {
    if (!el) return;
    var y = el.getBoundingClientRect().top + window.scrollY - navH() - 14;
    window.scrollTo({ top: Math.max(0, y), behavior: reduced() ? "instant" : "smooth" });
    if (focusEl) { if (!focusEl.hasAttribute("tabindex")) focusEl.setAttribute("tabindex", "-1"); focusEl.focus({ preventScroll: true }); }
  }
  function go(view, opts) { var c = C(); if (c && c.goView) c.goView(view, opts || {}); }
  function goHome(then) {
    var c = C(), on = c && ["chisme", "news", "sports", "events"].indexOf(c.view) >= 0 && c.view === "chisme";
    if (!on) go("chisme", { instant: true });
    setTimeout(then || function () { window.scrollTo({ top: 0, behavior: reduced() ? "instant" : "smooth" }); }, on ? 0 : 60);
  }
  var q = function () { var c = C(), l = c && c.loc; return l && l.lat != null ? "lat=" + (+l.lat).toFixed(2) + "&lon=" + (+l.lon).toFixed(2) : "lat=29.42&lon=-98.49"; };
  var dietaName = function () { var l = $('#tabs .tab[data-view="antojos"] .tab-l'); return (l && l.textContent.trim()) || "¿Y la dieta?"; };

  // Chisme's own pages (About, Support, Privacy, Terms) open in the reader panel too (house rule: every link stays inside)
  function openPage(href, title, opener) {
    var r = R(), u = new URL(href, location.origin);
    if (!r || !r.play) { location.href = u.pathname + u.search + u.hash; return; }
    u.searchParams.set("embed", "1");
    r.play({ url: u.origin + u.pathname, title: title, source: "Chisme", reader: true, frame: true, frameUrl: u.href, kind: "page" }, opener, { noSave: true });
    var k = $("#player-kind"), n = $("#player-note"), o = $("#player-orig");
    if (k) k.textContent = "📄 Chisme";
    if (n) n.hidden = true;
    if (o) o.hidden = true;
    var dlg = $("#player");
    if (dlg) {
      dlg.classList.add("dk-page");
      dlg.addEventListener("close", function () { dlg.classList.remove("dk-page"); }, { once: true });
    }
  }
  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button > 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || !d.classList.contains("dk")) return;
    var a = e.target.closest && e.target.closest("a[data-dk-page]");
    if (!a) return;
    e.preventDefault();
    openPage(a.getAttribute("href"), a.getAttribute("data-title") || a.textContent.trim(), a);
  });

  // ---------------------------------------------------------------- 1. the top nav (the app's own tab bar, widened)
  var settingsHome = null;
  function buildNav() {
    var inner = $("#tabs .tabs-inner");
    if (!inner) return;
    var logo = mark(h("a", { class: "dk-logo", href: "/", "aria-label": "Chisme home", on: { click: function (e) { if (e.metaKey || e.ctrlKey) return; e.preventDefault(); goHome(); } } },
      h("img", { src: "/static/icons/icon-192.png", alt: "", width: 40, height: 40, decoding: "async" }), h("span", { class: "dk-word", text: "Chisme" })));
    inner.prepend(logo);
    var get = h("button", { type: "button", class: "dk-get", id: "dk-get", on: { click: function () { goHome(function () { var c = $("#dk-getapp"); scrollToEl(c, $("#dk-getapp-t")); if (c) { c.classList.remove("dk-flash"); void c.offsetWidth; c.classList.add("dk-flash"); } }); } } },
      emo("📲"), " Get the app");
    var end = mark(h("div", { class: "dk-navend" }, h("span", { class: "dk-set-slot" }), get));
    inner.append(end);
    var skip = mark(h("a", { class: "dk-skip", href: "#mix", text: "Skip to the latest chisme", on: { click: function (e) { e.preventDefault(); goHome(function () { scrollToEl($("#mix"), $("#mix-title")); }); } } }));
    document.body.prepend(skip);
  }
  function moveSettings(intoNav) {   // the header's Settings button (the Chisme bubble) sits in the nav on desktop
    var b = $("#settings-btn"), slot = $(".dk-set-slot");
    if (!b || !slot) return;
    if (intoNav) {
      if (!settingsHome) settingsHome = { parent: b.parentNode, next: b.nextSibling };
      if (!$(".dk-set-l", b)) b.append(h("span", { class: "dk-set-l" }, emo("⚙️"), " Settings"));
      slot.append(b);
    } else if (settingsHome && b.parentNode === slot) {
      settingsHome.parent.insertBefore(b, settingsHome.next && settingsHome.next.parentNode === settingsHome.parent ? settingsHome.next : null);
    }
  }

  // ---------------------------------------------------------------- 2. the homepage hero
  function buildHero(view) {
    var hero = mark(h("section", { class: "dk-hero", id: "dk-hero", "aria-labelledby": "dk-hero-t" },
      h("div", { class: "dk-hero-copy" },
        h("p", { class: "dk-hola" }, h("img", { src: "/static/mascot/avatar-128.webp?art=3", alt: "Tía Chismosa, Chisme's mascot", width: 64, height: 64, decoding: "async" }), h("span", { text: "¡Hola, metiche!" })),
        h("h1", { class: "dk-hero-t", id: "dk-hero-t", text: "Chisme, the community for los metiches" }),
        h("p", { class: "dk-pitch", text: "San Antonio's news, sports, events, weather, food and games in one free app. Something to do while you're bored in the waiting room at your doctor's appointment." }),
        h("div", { class: "dk-hero-cta" },
          h("a", { class: "dk-btn primary", href: "#mix", on: { click: function (e) { e.preventDefault(); scrollToEl($("#mix"), $("#mix-title")); } } }, "Start chismeando ", emo("👀")),
          h("a", { class: "dk-btn", href: "/about", "data-dk-page": "", "data-title": "About Chisme", text: "About Chisme" }))),
      h("div", { class: "dk-getapp", id: "dk-getapp", role: "region", "aria-labelledby": "dk-getapp-t" },
        h("h2", { id: "dk-getapp-t", tabindex: "-1", text: "Open it on your phone" }),
        h("div", { class: "dk-qr-row" },
          h("img", { class: "dk-qr", src: "/qr.svg", width: 148, height: 148, alt: "QR code that opens Chisme on your phone", decoding: "async" }),
          h("ol", { class: "dk-steps" },
            h("li", {}, "Point your phone's camera at the code."),
            h("li", {}, h("b", { text: "iPhone:" }), " in Safari, tap Share ", emo("⬆️"), ", then ", h("b", { text: "Add to Home Screen" }), "."),
            h("li", {}, h("b", { text: "Android:" }), " in Chrome, tap ⋮, then ", h("b", { text: "Add to Home screen" }), "."))),
        h("p", { class: "dk-soon" }, emo("✨ "), "Coming soon to the App Store and Google Play."))));
    view.prepend(hero);
  }

  // ---------------------------------------------------------------- 3. the layout: main column + sidebar
  var mainCol = null, side = null;
  function wrap() {
    var view = $("#view-chisme");
    if (!view || !mainCol) return;
    if (mainCol.parentNode !== view) view.append(mainCol, side);
    Array.prototype.slice.call(view.children).forEach(function (c) { if (c !== mainCol && c !== side && c.id !== "dk-hero") mainCol.append(c); });
  }
  function unwrap() {
    var view = $("#view-chisme");
    if (!view || !mainCol || mainCol.parentNode !== view) return;
    while (mainCol.firstChild) view.insertBefore(mainCol.firstChild, mainCol);
    mainCol.remove(); side.remove();   // the phone layout gets its own DOM back, exactly
  }

  // ---------------------------------------------------------------- 4. sidebar widgets
  function widget(id, title, sub) {
    var head = h("div", { class: "dk-w-head" }, h("h2", { id: id + "-t", text: title }), sub ? h("span", { class: "dk-w-sub", id: id + "-sub", text: sub }) : null);
    return h("section", { class: "dk-w", id: id, "aria-labelledby": id + "-t" }, head);
  }
  function moreBtn(text, view, extra) {
    return h("button", { type: "button", class: "dk-more", on: { click: function () { go(view, extra); window.scrollTo({ top: 0, behavior: "instant" }); } } }, text, emo(" →"));
  }
  // 4a. weather (the same /api/weather the Weather tab uses; the server and the service worker cache it)
  var wxKey = "", wxBox = null;
  var f = function (c) { return c == null ? null : Math.round(c * 9 / 5 + 32); };
  function loadWx(force) {
    var key = q();
    if (!force && key === wxKey) return;
    wxKey = key;
    fetch("/api/weather?" + key).then(function (r) { return r.json(); }).then(renderWx).catch(function () { renderWx(null); });
  }
  function renderWx(w) {
    var body = $(".dk-wx-body", wxBox);
    if (!w || w.supported === false || !w.forecast) { body.replaceChildren(h("p", { class: "dk-dim", text: w && w.message ? w.message : "The weather will show up here in a moment." })); return; }
    var cur = w.current || {}, fc = w.forecast || [], now = fc[0] || {};
    var t = f(cur.temp_c) != null ? f(cur.temp_c) : now.temperature, txt = cur.text || now.shortForecast || "";
    var sub = $("#dk-wx-sub"); if (sub) sub.textContent = (w.location && w.location.city) || "";
    var nowRow = h("div", { class: "dk-wx-now" },
      cur.icon || now.icon ? h("img", { src: cur.icon || now.icon, alt: "", width: 64, height: 64, loading: "lazy", referrerpolicy: "no-referrer" }) : null,
      h("span", { class: "dk-wx-temp", text: t != null ? t + "°" : "–" }), h("span", { class: "dk-wx-txt", text: txt }));
    var next = h("ul", { class: "dk-wx-next", "aria-label": "Coming up" }, fc.slice(0, 3).map(function (p) {
      return h("li", {}, h("b", { text: p.name }), h("span", { class: "dk-wx-t", text: p.temperature + "°" }), h("span", { class: "dk-wx-s", text: p.shortForecast }));
    }));
    var al = (w.alerts || [])[0];
    var alert = al ? h("button", { type: "button", class: "dk-wx-alert", on: { click: function () { go("weather", { scrollTo: "alerts" }); } } }, emo("⚠️ "), al.event || al.headline || "Weather alert", emo(" →")) : null;
    fill(body, nowRow, alert, next);
  }
  function buildWx() {
    wxBox = widget("dk-wx", "Weather", "");
    $("h2", wxBox).prepend(emo("🌤️ "));
    wxBox.append(h("div", { class: "dk-wx-body", "aria-live": "polite" }, h("p", { class: "dk-dim", text: "Checking the sky…" })), moreBtn("Forecast & radar", "weather"));
    return wxBox;
  }
  // 4b. the local sponsor spot (data/sponsors.json via GET /api/sponsors; beer / ice-house spots only with 21+ on)
  var spBox = null;
  var over21 = function () { return lsGet(AGE_KEY) === "1"; };
  function pick(list) {
    var tot = list.reduce(function (t, s) { return t + (s.weight || 1); }, 0), r = Math.random() * tot;
    for (var i = 0; i < list.length; i++) { r -= list[i].weight || 1; if (r < 0) return list[i]; }
    return list[list.length - 1];
  }
  function loadSponsors() {
    return fetch("/api/sponsors?adult=" + (over21() ? 1 : 0)).then(function (r) { return r.json(); })
      .then(function (j) { renderSponsor((j && j.sponsors) || []); }).catch(function () { renderSponsor([]); });
  }
  function renderSponsor(list) {
    list = list.filter(function (s) { return s && s.name && s.url && (!s.adult || over21()); });
    var by = h("p", { class: "dk-sp-by", id: "dk-sp-t", text: "This chisme brought to you by…" });
    if (!list.length) {
      spBox.className = "dk-w dk-sponsor dk-house";
      spBox.dataset.sponsor = "";
      fill(spBox, by, h("p", { class: "dk-sp-name", text: "Your business here" }),
        h("p", { class: "dk-sp-line", text: "Reach local metiches. Put your taquería, shop or ice house in front of San Antonio while they're chismeando." }),
        h("a", { class: "dk-btn", href: "/support#advertise", "data-dk-page": "", "data-title": "Support & contact" }, "Ask about a sponsor spot ", emo("→")));
      return;
    }
    var s = pick(list);
    spBox.className = "dk-w dk-sponsor" + (s.adult ? " dk-adult" : "");
    spBox.dataset.sponsor = s.id;
    var img = s.image ? h("img", { class: "dk-sp-img", src: s.image, alt: s.alt || s.name, loading: "lazy", decoding: "async", referrerpolicy: "no-referrer" }) : null;
    if (img) img.onerror = function () { img.remove(); };
    fill(spBox, h("div", { class: "dk-sp-top" }, by, h("span", { class: "dk-sp-tag", text: "Sponsored" })), img,
      h("p", { class: "dk-sp-name", text: s.name }), s.area ? h("p", { class: "dk-sp-area" }, emo("📍 "), s.area) : null,
      s.tagline ? h("p", { class: "dk-sp-line", text: s.tagline }) : null,
      s.adult ? h("p", { class: "dk-sp-21", text: "21+ · Please drink responsibly." }) : null,
      h("a", { class: "dk-btn primary", href: s.url, rel: "sponsored noopener", "data-title": s.name, "aria-label": s.cta + " (sponsored)" }, s.cta, emo(" →")));
  }
  function buildSponsor() {
    spBox = h("section", { class: "dk-w dk-sponsor", id: "dk-sponsor", "aria-labelledby": "dk-sp-t" }, h("p", { class: "dk-sp-by", id: "dk-sp-t", text: "This chisme brought to you by…" }));
    return spBox;
  }
  // 4c. Juegos (the games juegos.js / juan.js list)
  var GAME_HASH = { juan: "#juan", loteria: "#chismeria" };
  function openGame(id) {
    var hsh = GAME_HASH[id] || "#juegos";
    if (location.hash === hsh) window.dispatchEvent(new HashChangeEvent("hashchange"));
    else location.hash = hsh;
    setTimeout(function () { try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {} window.scrollTo({ top: 0, behavior: "instant" }); }, 0);
  }
  function buildGames() {
    var box = widget("dk-games", "Juegos", "For when the chisme's slow");
    $("h2", box).prepend(emo("🎲 "));
    var games = (window.ChismeJuegos && window.ChismeJuegos.GAMES) || [];
    box.append(h("ul", { class: "dk-games" }, games.map(function (g) {
      return h("li", {}, h("button", { type: "button", class: "dk-game", "data-game": g.id, on: { click: function () { openGame(g.id); } } },
        h("span", { class: "dk-game-emo", "aria-hidden": "true", text: g.emoji || "🎲" }), h("span", {}, h("b", { text: g.name }), h("small", { text: g.blurb || "" }))));
    })), moreBtn("All the games", "juegos"));
    return box;
  }
  // 4d. ¿Y la dieta? (3 of the latest local food reviews; they play in the reader panel)
  var foodBox = null, foodKey = "";
  function loadFood() {
    var key = q();
    if (key === foodKey) return;
    foodKey = key;
    fetch("/api/food?" + key).then(function (r) { return r.json(); }).then(function (j) {
      var items = ((j && j.items) || []).filter(function (i) { return i && i.video && i.image && i.title; }).slice(0, 3);
      var ul = $(".dk-food", foodBox);
      if (!items.length) { ul.replaceChildren(h("li", { class: "dk-dim", text: "The food reviews are on their way." })); return; }
      ul.replaceChildren.apply(ul, items.map(function (it) {
        var b = h("button", { type: "button", class: "dk-food-i", on: { click: function () { var r = R(); if (r && r.play) r.play(it, b); else go("antojos"); } } },
          h("span", { class: "dk-food-th" }, h("img", { src: it.image, alt: "", loading: "lazy", decoding: "async", referrerpolicy: "no-referrer", width: 120, height: 68 }), h("span", { class: "dk-food-play", "aria-hidden": "true", text: "▶" })),
          h("span", { class: "dk-food-txt" }, h("b", { text: it.title }), h("small", { text: it.creator || it.outlet || "" })));
        return h("li", {}, b);
      }));
    }).catch(function () {});
  }
  function buildFood() {
    foodBox = widget("dk-dieta", dietaName(), "Fresh from local food creators");
    $("h2", foodBox).prepend(emo("🌮 "));
    foodBox.append(h("ul", { class: "dk-food" }, h("li", { class: "dk-dim", text: "Asking the foodies where to eat…" })), moreBtn("More food", "antojos"));
    return foodBox;
  }
  // 4e. Buy Me a Coffee: "Help get Chisme on the App Store, $99"
  function buildGoal() {
    var g = SITE.goal;
    var box = h("section", { class: "dk-w dk-goal", id: "dk-goal", "aria-labelledby": "dk-goal-t" },
      h("h2", { id: "dk-goal-t" }, emo("☕ "), g.title + ", $" + g.amount),
      h("p", { text: "Putting Chisme in the App Store costs $" + g.amount + " a year. A coffee helps get it there." }),
      h("div", { class: "dk-goal-bar", hidden: true }),
      h("a", { class: "dk-btn bmc", href: g.url, target: "_blank", rel: "noopener noreferrer" }, emo("☕ "), "Buy Chisme a coffee"),
      h("p", { class: "dk-fine", text: "Tips go to the Chisme creator; not a charity, not tax-deductible, unlocks nothing." }));
    loadSite().then(function (s) {
      var gg = s.goal || g, bar = $(".dk-goal-bar", box);
      if (gg.raised == null || !bar) return;
      var pct = Math.max(0, Math.min(100, Math.round(gg.raised / gg.amount * 100)));
      bar.hidden = false;
      bar.replaceChildren(h("div", { class: "dk-goal-track", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": gg.amount, "aria-valuenow": gg.raised, "aria-label": "Raised so far" },
        h("span", { class: "dk-goal-fill", style: "width:" + pct + "%" })), h("p", { class: "dk-goal-n", text: "$" + gg.raised + " of $" + gg.amount + " raised" }));
    });
    return box;
  }

  // ---------------------------------------------------------------- 5. the footer (on every desktop page)
  function buildFooter() {
    var foot = $("footer.foot");
    if (!foot) return;
    var link = function (href, text) { return h("li", {}, h("a", { href: href, "data-dk-page": "", "data-title": text, text: text })); };
    var nav = mark(h("nav", { class: "dk-foot", "aria-label": "Chisme pages" },
      h("div", { class: "dk-foot-brand" }, h("img", { src: "/static/icons/icon-192.png", alt: "", width: 44, height: 44, loading: "lazy" }),
        h("div", {}, h("p", { class: "dk-foot-name", text: "Chisme" }), h("p", { class: "dk-foot-tag", text: "Chisme, the community for los metiches. Made in San Antonio, Texas." }))),
      h("ul", { class: "dk-foot-links" },
        h("li", {}, h("a", { href: "/", text: "Home", on: { click: function (e) { if (e.metaKey || e.ctrlKey) return; e.preventDefault(); goHome(); } } })),
        link("/about", "About"), link("/support", "Support & contact"), link("/privacy", "Privacy Policy"), link("/terms", "Terms of Use"),
        h("li", {}, h("button", { type: "button", class: "linkish dk-foot-get", text: "Get the app", on: { click: function () { var g = $("#dk-get"); if (g) g.click(); } } }))),
      h("p", { class: "dk-foot-tip" }, h("a", { class: "dk-foot-bmc", href: SITE.goal.url, target: "_blank", rel: "noopener noreferrer" }, emo("☕ "), SITE.goal.title + ", $" + SITE.goal.amount))));
    foot.prepend(nav);
  }

  // ---------------------------------------------------------------- 6. Settings: 21+ sponsors (desktop only, where sponsors show)
  function buildSettings() {
    var anchor = $("#set-privacy");
    if (!anchor) return;
    var input = h("input", { type: "checkbox", role: "switch", id: "set-21", "aria-describedby": "set-21-note" });
    input.checked = over21();
    input.addEventListener("change", function () { lsSet(AGE_KEY, input.checked ? "1" : null); loadSponsors(); });
    var fs = mark(h("fieldset", { class: "set-group", id: "set-sponsors" }, h("legend", { text: "Local sponsors" }),
      h("label", { class: "switch" }, input, h("span", { text: "I'm 21 or older: include beer and ice-house sponsors" })),
      h("p", { class: "set-note", id: "set-21-note", text: "Sponsored spots are always labeled Sponsored. Saved on this device only." })));
    anchor.parentNode.insertBefore(fs, anchor);
  }

  // ---------------------------------------------------------------- enter / leave desktop mode
  var built = false, timers = [];
  function build() {
    built = true;
    var view = $("#view-chisme");
    buildNav();
    if (view) {
      buildHero(view);
      mainCol = mark(h("div", { class: "dk-main" }));
      side = mark(h("aside", { class: "dk-side", "aria-label": "More from Chisme" }));
      side.append(buildWx(), buildSponsor(), buildGames(), buildFood(), buildGoal());
      view.append(mainCol, side);
    }
    buildFooter();
    buildSettings();
  }
  function tick() { if (d.classList.contains("dk")) { loadWx(); loadFood(); } }
  function enter() {
    if (!built) build();
    nodes.forEach(function (n) { n.hidden = false; });
    wrap(); moveSettings(true);
    d.classList.add("dk");
    var l = $("#dk-dieta-t"); if (l) l.replaceChildren(emo("🌮 "), dietaName());
    loadWx(); loadFood(); loadSponsors(); loadSite();
    if (!timers.length) timers.push(setInterval(tick, 20000), setInterval(function () { loadWx(true); }, 10 * 60000));
    window.dispatchEvent(new Event("resize"));   // the app re-measures the nav (--tabs-h) and the map
  }
  function leave() {
    if (!built) return;
    d.classList.remove("dk");
    unwrap(); moveSettings(false);
    nodes.forEach(function (n) { n.hidden = true; });
    timers.forEach(clearInterval); timers = [];
    window.dispatchEvent(new Event("resize"));
  }
  function start() {
    if (MQ.matches) enter();
    var onChange = function () { if (MQ.matches) enter(); else leave(); };
    if (MQ.addEventListener) MQ.addEventListener("change", onChange); else if (MQ.addListener) MQ.addListener(onChange);
    document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") tick(); });
    moved();
  }

  // ---------------------------------------------------------------- the domain move: "Chisme moved" (MOVED_BANNER=1)
  // Installs and push subscriptions belong to the web address, so installed users on the old one are asked (gently,
  // dismissible, back after 3 days) to add Chisme again from the new one. Any screen size; never in a browser tab.
  function moved() {
    var standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    if (!standalone) return;
    var x = +lsGet(MOVED_KEY) || 0;
    if (x && Date.now() - x < 3 * 864e5) return;
    loadSite().then(function (s) {
      if (!s.moved || !s.moved.on || $("#moved-banner")) return;
      var host = s.moved.host || "the new address", to = s.moved.to;
      var bar = h("div", { id: "moved-banner", class: "moved-banner wrap", role: "region", "aria-label": "Chisme moved",
        style: "margin-top:12px" },
        h("div", { style: "display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:12px 14px;border-radius:14px;background:#000;color:#fff;border:3px solid #00C9CD;box-shadow:0 4px 0 #EF426F;font-size:.95rem;line-height:1.35" },
          h("p", { style: "margin:0;flex:1 1 16em;font-weight:700" }, h("b", { text: "Chisme moved to " + host + "! " }),
            "Open it there and add it to your Home Screen again, so you keep getting updates and alerts."),
          h("a", { href: to, id: "moved-go", style: "display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:12px;background:#00C9CD;color:#000;font-weight:900;text-decoration:none",
            on: { click: function (e) { e.preventDefault(); window.open(to, "_blank", "noopener"); } } }, "Open " + host),
          h("button", { type: "button", id: "moved-x", style: "min-height:44px;border-radius:12px;background:transparent;color:#fff;border:2px solid #fff",
            on: { click: function () { lsSet(MOVED_KEY, String(Date.now())); bar.remove(); } } }, "Later")));
      var after = $("#offline-banner") || $("#views");
      if (after && after.parentNode) after.parentNode.insertBefore(bar, after.nextSibling); else document.body.prepend(bar);
    });
  }

  window.__chismeDesk = { get on() { return d.classList.contains("dk"); }, openPage: openPage, reloadSponsors: loadSponsors, moved: moved, MIN: MIN };
  if (window.__chismeBooted || document.readyState !== "loading") start();
  else document.addEventListener("DOMContentLoaded", start);
})();
