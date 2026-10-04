/* Owner posts ("From Chisme"): Goonie's own chisme in the feed (ownerposts.py serves GET /api/posts).
   • A "From Chisme" strip at the top of Chisme · All (every category), News, Sports, Events and Weather (that category):
     pinned posts first, then posts from the last few days (older ones behind "More from Chisme").
   • Tapping a post opens it in a sheet inside Chisme (photos with their credits, the text, where it happened with a
     Google Maps link and the OpenStreetMap map, the source); Share sends its own page, /p/<slug> (Open Graph preview).
   • /?post=<slug> (a shared link's "Open in Chisme", a notification) opens that post.
   • News posts stay straight: no emoji, no jokey styling (plain black + white card).
   Text only ever goes in with textContent / attributes (never innerHTML); links are http(s) only.
   Also used by the owner's composer (/stats/posts) for its live preview: window.__chismePosts.card(post). */
(function () {
  "use strict";
  var CAT = { news: ["News", ""], weather: ["Weather", "🌤️"], events: ["Events", "🎉"], sports: ["Sports", "🏀"], food: ["Food", "🌮"], other: ["Other", "👀"] };
  var SPOTS = [   // [view section, the element the strip goes before, which categories]
    ["#view-chisme", "#mq-gallery, #mix", null],
    ["#view-news", "#near", ["news"]],
    ["#view-sports", "#sports", ["sports"]],
    ["#view-events", "#events", ["events"]],
    ["#view-weather", "#weather", ["weather"]],
  ];
  var SHOW = 3, MAX = 10;
  var state = { posts: [], fresh: 72, at: 0, want: null };

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
  var httpUrl = function (u) { try { var x = new URL(u, location.origin); return /^https?:$/.test(x.protocol) ? x.href : ""; } catch (e) { return ""; } };
  var base = function () { var m = document.querySelector('meta[name="chisme-base"]'); var b = m && m.content && !/__PUBLIC_BASE__/.test(m.content) ? m.content : location.origin; return b.replace(/\/$/, ""); };
  var isNews = function (p) { return p.category === "news"; };

  // **bold** inside a line → <strong>, the rest as text
  function inline(s) {
    var out = [], re = /\*\*(.+?)\*\*/g, last = 0, m;
    while ((m = re.exec(s))) { if (m.index > last) out.push(s.slice(last, m.index)); out.push(h("strong", { text: m[1] })); last = re.lastIndex; }
    if (last < s.length) out.push(s.slice(last));
    return out;
  }
  // the same light formatting as ownerposts.body_blocks: blank line = paragraph, "- " = bullet, **bold**
  function renderBody(text) {
    var frag = document.createDocumentFragment(), para = [], items = [];
    function flushP() { if (para.length) { var p = h("p"); para.forEach(function (l, i) { if (i) p.append(h("br")); p.append.apply(p, inline(l)); }); frag.append(p); para = []; } }
    function flushU() { if (items.length) { var u = h("ul"); items.forEach(function (t) { var li = h("li"); li.append.apply(li, inline(t)); u.append(li); }); frag.append(u); items = []; } }
    String(text || "").split("\n").forEach(function (ln) {
      var s = ln.trim(), m;
      if (!s) { flushP(); flushU(); return; }
      if ((m = /^[-•*]\s+(.*)$/.exec(s)) && s.indexOf("**") !== 0) { flushP(); items.push(m[1]); return; }
      flushU(); para.push(s);
    });
    flushP(); flushU();
    return frag;
  }
  function ago(iso) {
    var t = Date.parse(iso); if (!t) return "";
    var s = (Date.now() - t) / 1000;
    if (s < 90) return "Just now";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + (Math.round(s / 3600) === 1 ? " hour ago" : " hours ago");
    return new Date(t).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "America/Chicago" });
  }
  function stamp(iso) {
    var t = Date.parse(iso); if (!t) return "";
    return new Date(t).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/Chicago" }) + " CT";
  }
  function badges(p, big) {
    var c = CAT[p.category] || CAT.other;
    return h("p", { class: "op-badges" },
      h("span", { class: "op-badge", text: "From Chisme" }),
      h("span", { class: "op-cat" }, !isNews(p) && c[1] ? h("span", { "aria-hidden": "true", text: c[1] + " " }) : null, c[0]),
      p.sponsored ? h("span", { class: "op-spon", text: "Sponsored" }) : null,   // paid post: always labeled (FTC)
      p.pinned ? h("span", { class: "op-pin", text: "Pinned" }) : null,
      big && p.status === "draft" ? h("span", { class: "op-draft", text: "Draft" }) : null);
  }

  // ---------- the feed card
  function card(p, opts) {
    opts = opts || {};
    var ph = (p.photos || [])[0], src = ph && httpUrl(ph.url);
    var a = h("a", { href: p.url || "#", class: "op-link", text: p.headline || "(headline)" });
    var c = h("article", { class: "op-card op-" + (CAT[p.category] ? p.category : "other") + (p.pinned ? " op-pinned" : "") + (p.sponsored ? " op-sponsored" : ""), "data-slug": p.slug || "" },
      badges(p, opts.preview),
      src ? h("figure", { class: "op-cimg" }, h("img", { src: src, alt: ph.alt || "", loading: "lazy", decoding: "async", width: ph.w || null, height: ph.h || null }),
        ph.credit ? h("figcaption", { text: ph.credit }) : null) : null,
      h("h3", { class: "op-h" }, a),
      p.summary || p.body ? h("p", { class: "op-sum", text: p.summary || p.body }) : null,
      h("p", { class: "op-meta" }, h("span", { text: p.created_at ? ago(p.created_at) : "Just now" }), p.location ? h("span", { class: "op-loc", text: p.location }) : null),
      h("div", { class: "op-acts" },
        h("button", { type: "button", class: "op-read", text: "Read more" }),
        h("button", { type: "button", class: "op-share", text: "Share" })));
    if (!opts.preview) {
      c.addEventListener("click", function (e) {
        if (e.target.closest(".op-share")) { e.preventDefault(); share(p); return; }
        if (e.target.closest("a.op-link") || e.target.closest(".op-read") || !e.target.closest("a, button")) { e.preventDefault(); openSheet(p, c); }
      });
    }
    return c;
  }

  // ---------- the full post, in a sheet
  var dlg = null, opener = null;
  function sheetEl() {
    if (dlg) return dlg;
    dlg = h("dialog", { class: "op-sheet", id: "op-sheet", "aria-labelledby": "op-sheet-h" });
    dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener("close", function () { if (opener && opener.focus) try { opener.focus({ preventScroll: true }); } catch (e) {} });
    document.body.append(dlg);
    return dlg;
  }
  function article(p) {
    var parts = [badges(p, true), h("h2", { class: "op-sh", id: "op-sheet-h", text: p.headline }),
      h("p", { class: "op-time", text: "Posted " + stamp(p.created_at) + (p.updated_at && Date.parse(p.updated_at) - Date.parse(p.created_at) > 120000 ? " · Updated " + stamp(p.updated_at) : "") })];
    (p.photos || []).forEach(function (ph, i) {
      var u = httpUrl(ph.url); if (!u) return;
      parts.push(h("figure", { class: "op-fig" + (i ? "" : " op-lead") }, h("img", { src: u, alt: ph.alt || "Photo " + (i + 1), loading: i ? "lazy" : null, decoding: "async", width: ph.w || null, height: ph.h || null }),
        ph.credit ? h("figcaption", { text: ph.credit }) : null));
    });
    var body = h("div", { class: "op-body" }); body.append(renderBody(p.body)); parts.push(body);
    if (p.location || p.maps_url) {
      var g = httpUrl(p.maps_url), w = h("div", { class: "op-where" }, h("p", null, h("strong", { text: "Where: " }), p.location || ""));
      if (g) w.append(h("p", null, h("a", { class: "op-gmaps orig-link", href: g, target: "_blank", rel: "noopener noreferrer", text: "Open in Google Maps ↗" })));
      if (p.map_image && httpUrl(p.map_image.url)) {
        w.append(h("a", { class: "op-map orig-link", href: g || "#", target: "_blank", rel: "noopener noreferrer", "aria-label": "Open the map in Google Maps" },
          h("img", { src: httpUrl(p.map_image.url), alt: "Map of " + (p.location || "the location"), width: p.map_image.w || 640, height: p.map_image.h || 320, loading: "lazy", decoding: "async" })),
          h("p", { class: "op-mapc", text: "Map © OpenStreetMap contributors" }));
      }
      parts.push(w);
    }
    var s = httpUrl(p.source_url);
    if (s || p.source_name) {
      var sp = h("p", { class: "op-src" }, h("strong", { text: "Source: " }));
      sp.append(s ? h("a", { href: s, rel: "noopener noreferrer nofollow", "data-title": p.headline, text: p.source_name || new URL(s).hostname.replace(/^www\./, "") }) : p.source_name);
      parts.push(sp);
    }
    return parts;
  }
  function openSheet(p, from) {
    var d = sheetEl(); opener = from || document.activeElement;
    var close = h("button", { type: "button", class: "op-x", "aria-label": "Close", on: { click: function () { d.close(); } } }, h("span", { "aria-hidden": "true", text: "×" }));
    var shareB = h("button", { type: "button", class: "op-share big", text: "Share this post", on: { click: function () { share(p); } } });
    var art = h("article", { class: "op-article op-" + p.category });
    art.append.apply(art, article(p));
    d.className = "op-sheet" + (isNews(p) ? " op-sheet-news" : "");
    d.replaceChildren(h("div", { class: "op-sbar" }, close), art, h("div", { class: "op-sfoot" }, shareB));
    if (!d.open) { try { d.showModal(); } catch (e) { d.setAttribute("open", ""); } }
    d.scrollTop = 0;
  }
  function toast(msg) {
    var t = document.getElementById("op-toast");
    if (!t) { t = h("div", { id: "op-toast", class: "op-toast", role: "status", "aria-live": "polite" }); document.body.append(t); }
    t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove("show"); }, 3200);
  }
  function share(p) {
    var url = base() + "/p/" + encodeURIComponent(p.slug);
    var data = { title: p.headline, url: url };
    if (navigator.share) { navigator.share(data).catch(function () {}); return; }
    (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(function () { toast("Link copied"); }, function () { prompt("Copy this link:", url); });
  }

  // ---------- the strips
  function forSpot(cats) {
    var now = Date.now(), fresh = state.fresh * 3600e3;
    var list = state.posts.filter(function (p) { return !cats || cats.indexOf(p.category) >= 0; });
    var top = list.filter(function (p) { return p.pinned || now - Date.parse(p.created_at) < fresh; });
    return { top: top, rest: list.filter(function (p) { return top.indexOf(p) < 0; }) };
  }
  function strip(view, before, cats) {
    var v = document.querySelector(view); if (!v) return;
    var old = v.querySelector(":scope > .op-strip"); if (old) old.remove();
    var g = forSpot(cats); if (!g.top.length && !g.rest.length) return;
    if (!g.top.length && cats) return;   // a category tab only shows its fresh / pinned posts
    var sec = h("section", { class: "card op-strip", "aria-label": "From Chisme" });
    var lst = h("div", { class: "op-list" });
    var all = g.top.concat(g.rest).slice(0, MAX), first = g.top.length ? g.top.slice(0, SHOW) : all.slice(0, 1);
    first.forEach(function (p) { lst.append(card(p)); });
    sec.append(lst);
    var more = all.filter(function (p) { return first.indexOf(p) < 0; });
    if (more.length) {
      var b = h("button", { type: "button", class: "op-more", text: "More from Chisme (" + more.length + ")" });
      b.onclick = function () { more.forEach(function (p) { lst.append(card(p)); }); b.remove(); };
      sec.append(h("div", { class: "op-more-w" }, b));
    }
    var at = v.querySelector(before.split(",").map(function (s) { return ":scope > " + s.trim(); }).join(", "));
    if (at) v.insertBefore(sec, at); else v.append(sec);
  }
  function render() { SPOTS.forEach(function (s) { strip(s[0], s[1], s[2]); }); }
  function load() {
    if (!document.querySelector("#view-chisme")) return Promise.resolve();
    return fetch("/api/posts", { credentials: "same-origin" }).then(function (r) { return r.ok || r.headers.get("X-Chisme-Offline") ? r.json() : { posts: state.posts }; })
      .then(function (j) { state.posts = Array.isArray(j.posts) ? j.posts : []; state.fresh = +j.fresh_hours || 72; state.at = Date.now(); render(); wanted(); })
      .catch(function () {});
  }
  function wanted() {
    if (!state.want) return;
    var slug = state.want; state.want = null;
    var hit = state.posts.find(function (p) { return p.slug === slug; });
    if (hit) return openSheet(hit);
    fetch("/api/posts/" + encodeURIComponent(slug)).then(function (r) { return r.json(); }).then(function (j) { if (j && j.post) openSheet(j.post); else toast("That post isn't here anymore."); }).catch(function () {});
  }
  function want(href) {
    try { var u = new URL(href, location.origin); var s = u.searchParams.get("post"); if (s && /^[a-z0-9][a-z0-9-]{2,95}$/.test(s)) { state.want = s; return true; } } catch (e) {}
    return false;
  }

  window.__chismePosts = { card: card, renderBody: renderBody, open: openSheet, reload: load, get posts() { return state.posts; } };
  if (!document.querySelector("#view-chisme")) return;   // the composer page only borrows card()
  if (want(location.href)) {
    var q = new URLSearchParams(location.search); q.delete("post");
    history.replaceState(history.state, "", location.pathname + (q.toString() ? "?" + q : "") + (location.hash || "#chisme"));
  }
  if (navigator.serviceWorker) navigator.serviceWorker.addEventListener("message", function (e) {
    if (e.data && typeof e.data.chismeOpen === "string" && want(e.data.chismeOpen)) { if (state.at) wanted(); }
  });
  load();
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible" && Date.now() - state.at > 4 * 60e3) load(); });
})();
