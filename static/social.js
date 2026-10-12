/* Chisme social, part 1 (the /social app + the owner's /stats/social moderation queue). Plain DOM, no framework.
   Every bit of user text goes in with textContent (never innerHTML). Words: a "Chisme" (never a post), "Homies". */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const MODE = document.body.dataset.mode || "app";
  const view = $("#view");
  let CFG = null, ME = null, BUSY = false;

  function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "text") n.textContent = v;
      else if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (k === "style" && typeof v === "object") Object.assign(n.style, v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return n;
  }
  const clear = (n) => { while (n.firstChild) n.firstChild.remove(); return n; };

  async function api(path, opts = {}) {
    const o = { method: opts.method || "GET", headers: {}, credentials: "same-origin" };
    if (opts.body !== undefined) {
      if (opts.raw) { o.body = opts.body; o.headers["Content-Type"] = opts.type || "application/octet-stream"; }
      else { o.body = JSON.stringify(opts.body); o.headers["Content-Type"] = "application/json"; }
    }
    let r, d = {};
    try { r = await fetch(path, o); d = await r.json().catch(() => ({})); }
    catch (e) { return { ok: false, error: "You look offline. Try again when you're back." }; }
    if (!r.ok && !d.error) d.error = "Something went wrong. Try again.";
    d.status = r.status;
    return d;
  }
  function toast(msg, ms = 2600) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, ms);
  }
  const ago = (iso) => {
    const s = Math.max(1, (Date.now() - Date.parse(iso)) / 1000);
    if (s < 60) return "now"; if (s < 3600) return Math.floor(s / 60) + "m"; if (s < 86400) return Math.floor(s / 3600) + "h";
    if (s < 604800) return Math.floor(s / 86400) + "d";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  // ------------------------------------------------ the sheet (bottom dialog)
  let sheetBack = null;
  function sheet(title, body, onClose) {
    $("#sheet-title").textContent = title;
    clear($("#sheet-body")).append(body);
    $("#sheet").hidden = false; document.body.classList.add("locked");
    sheetBack = onClose || null;
    setTimeout(() => { const f = $("#sheet-body").querySelector("input,textarea,button,select"); f && f.focus({ preventScroll: true }); }, 30);
  }
  function closeSheet() { $("#sheet").hidden = true; document.body.classList.remove("locked"); const f = sheetBack; sheetBack = null; f && f(); }
  $("#sheet-x").addEventListener("click", closeSheet);
  $("#sheet").addEventListener("click", (e) => { if (e.target.id === "sheet") closeSheet(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#sheet").hidden) closeSheet(); });

  // ------------------------------------------------ the bot check (Turnstile, else a quick math question)
  function botBox() {
    const box = el("div", { class: "bot" }, el("p", { class: "bot-copy", text: (CFG && CFG.bot_copy) || "Prove you ain't a bot, cuh 🤖" }));
    box.value = () => ({});
    if (CFG && CFG.turnstile && window.turnstile) {
      const slot = el("div", { class: "ts" }); box.append(slot);
      let token = "";
      setTimeout(() => { window.turnstile.render(slot, { sitekey: CFG.turnstile, callback: (t) => { token = t; }, theme: "light" }); }, 0);
      box.value = () => ({ turnstile: token });
    } else if (CFG && CFG.challenge) {
      const ch = CFG.challenge;
      const inp = el("input", { inputmode: "numeric", autocomplete: "off", maxlength: "3", "aria-label": ch.question, placeholder: "Answer" });
      box.append(el("label", { class: "row" }, el("span", { text: ch.question }), inp));
      box.value = () => ({ challenge: { id: ch.id, answer: inp.value } });
    }
    box.append(el("input", { name: "website", class: "hp", tabindex: "-1", autocomplete: "off", "aria-hidden": "true" }));
    return box;
  }
  async function freshChallenge() { const c = await api("/api/social/config"); if (c.ok) CFG = c; }

  function field(label, attrs) { const i = el(attrs.tag || "input", attrs); return [el("label", { class: "fld" }, el("span", { text: label }), i), i]; }
  function form(onSubmit, ...kids) {
    const err = el("p", { class: "err", role: "alert", hidden: true });
    const f = el("form", { class: "form", novalidate: true }, err, ...kids);
    f.addEventListener("submit", async (e) => {
      e.preventDefault(); if (BUSY) return; BUSY = true; err.hidden = true;
      const btn = f.querySelector("button[type=submit]"); btn && (btn.disabled = true);
      try { const m = await onSubmit(); if (m) { err.textContent = m; err.hidden = false; } }
      finally { BUSY = false; btn && (btn.disabled = false); }
    });
    return f;
  }

  // ------------------------------------------------ accounts
  function signIn() {
    const [fe, email] = field("Email", { type: "email", autocomplete: "email", required: true });
    const [fp, pw] = field("Password", { type: "password", autocomplete: "current-password", required: true });
    let bot = null;
    const botSlot = el("div");
    const f = form(async () => {
      const d = await api("/api/social/login", { method: "POST", body: { email: email.value, password: pw.value, ...(bot ? bot.value() : {}) } });
      if (d.ok) { await loadMe(); location.hash = "#feed/sananto"; toast("Welcome back, metiche 👋"); return; }
      if (d.next === "verify") { verifyView(email.value); return; }
      if (d.need_bot || d.bot) { await freshChallenge(); bot = botBox(); clear(botSlot).append(bot); }
      return d.error;
    }, fe, fp, botSlot, el("button", { class: "btn pink wide", type: "submit", text: "Sign in" }));
    if (CFG && CFG.turnstile) { bot = botBox(); botSlot.append(bot); }
    const prov = (CFG && CFG.providers || []).map((p) => el("a", { class: "btn ghost wide", href: "/api/social/oauth/" + p, text: p === "apple" ? " Sign in with Apple" : "Sign in with Google" }));
    page("Sign in", el("section", { class: "card auth" },
      el("h1", { text: "Welcome back 👋" }), el("p", { class: "sub", text: "Sign in to see the chisme from your Homies." }), f, ...prov,
      el("p", { class: "links" }, el("a", { href: "#forgot", text: "Forgot password?" }), " · ", el("a", { href: "#signup", text: "New here? Join Chisme" }))));
  }

  function signUp() {
    const [fn, name] = field("Display name", { maxlength: "40", autocomplete: "name", required: true });
    const [fu, user] = field("@username", { maxlength: "20", autocapitalize: "none", autocomplete: "username", pattern: "[a-z0-9_]{3,20}", required: true });
    const [fe, email] = field("Email (never shown to anyone)", { type: "email", autocomplete: "email", required: true });
    const [fb, bday] = field("Birthday (you must be 18 or older)", { type: "date", required: true, max: new Date().toISOString().slice(0, 10) });
    const [fp, pw] = field("Password (8+ characters)", { type: "password", autocomplete: "new-password", minlength: "8", required: true });
    const [fp2, pw2] = field("Confirm password", { type: "password", autocomplete: "new-password", required: true });
    const tos = el("input", { type: "checkbox", required: true });
    const bot = botBox();
    const f = form(async () => {
      const d = await api("/api/social/signup", { method: "POST", body: { display_name: name.value, username: user.value, email: email.value,
        birthday: bday.value, password: pw.value, password2: pw2.value, tos: tos.checked, ...bot.value() } });
      if (d.ok) { verifyView(email.value, d.message); return; }
      if (d.under_age) { page("Not yet", el("section", { class: "card auth" }, el("h1", { text: "Chisme is 18+ 🤙" }), el("p", { text: d.error }))); return; }
      if (d.bot) { await freshChallenge(); signUp(); toast(d.error, 4000); return; }
      return d.error;
    }, fn, fu, fe, fb, fp, fp2,
      el("label", { class: "chk" }, tos, el("span", {}, "I agree to the ", el("a", { href: "/terms", target: "_blank", text: "Terms" }), " and the ",
        el("a", { href: "/privacy", target: "_blank", text: "Privacy Policy" }), ".")),
      bot, el("button", { class: "btn pink wide", type: "submit", text: "Join Chisme 🌶️" }));
    page("Join", el("section", { class: "card auth" }, el("h1", { text: "Join Chisme" }),
      el("p", { class: "sub", text: "Your Homies, your city, your chisme. Your email stays private; we only use it to send your 6-digit code." }), f,
      el("p", { class: "links" }, el("a", { href: "#signin", text: "Already in? Sign in" }))));
  }

  function verifyView(emailAddr, msg) {
    const [fc, code] = field("6-digit code", { inputmode: "numeric", autocomplete: "one-time-code", maxlength: "6", pattern: "[0-9]{6}", required: true });
    const f = form(async () => {
      const d = await api("/api/social/verify", { method: "POST", body: { email: emailAddr, code: code.value } });
      if (d.ok) { await loadMe(); location.hash = "#edit"; toast("You're in! 🎉 Make your profile yours."); return; }
      return d.error;
    }, fc, el("button", { class: "btn pink wide", type: "submit", text: "Confirm" }));
    const again = el("button", { type: "button", class: "linkish", text: "Send a new code", onclick: async () => {
      const d = await api("/api/social/resend", { method: "POST", body: { email: emailAddr } }); toast(d.message || d.error); } });
    const dev = CFG && CFG.dev_outbox ? el("button", { type: "button", class: "linkish", text: "(dev) fill the code", onclick: async () => {
      const d = await api("/api/social/dev/outbox?email=" + encodeURIComponent(emailAddr)); code.value = d.code || ""; } }) : null;
    page("Check your email", el("section", { class: "card auth" }, el("h1", { text: "Check your email 📬" }),
      el("p", { class: "sub", text: msg || "We sent a 6-digit code to your email." }), el("p", { class: "small", text: emailAddr }), f, el("p", { class: "links" }, again, dev)));
  }

  function forgot() {
    const [fe, email] = field("Email", { type: "email", autocomplete: "email", required: true });
    const bot = botBox();
    const f = form(async () => {
      const d = await api("/api/social/forgot", { method: "POST", body: { email: email.value, ...bot.value() } });
      if (!d.ok) { if (d.bot) await freshChallenge(); return d.error; }
      const [fc, code] = field("6-digit code", { inputmode: "numeric", maxlength: "6", autocomplete: "one-time-code" });
      const [fp, pw] = field("New password", { type: "password", autocomplete: "new-password" });
      const [fp2, pw2] = field("Confirm new password", { type: "password", autocomplete: "new-password" });
      page("New password", el("section", { class: "card auth" }, el("h1", { text: "Pick a new password" }), el("p", { class: "sub", text: d.message }),
        form(async () => {
          const r = await api("/api/social/reset", { method: "POST", body: { email: email.value, code: code.value, password: pw.value, password2: pw2.value } });
          if (r.ok) { await loadMe(); location.hash = "#feed/sananto"; toast(r.message); return; }
          return r.error;
        }, fc, fp, fp2, el("button", { class: "btn pink wide", type: "submit", text: "Save password" }))));
    }, fe, bot, el("button", { class: "btn pink wide", type: "submit", text: "Send me a code" }));
    page("Forgot password", el("section", { class: "card auth" }, el("h1", { text: "Forgot your password?" }),
      el("p", { class: "sub", text: "No stress. We'll email you a 6-digit code." }), f));
  }

  async function loadMe() {
    const d = await api("/api/social/me");
    ME = d.ok ? d.me : null;
    if (ME) ME.can_upload = !!d.can_upload;
    $("#dot-alerts").hidden = !(d.unread > 0);
    $("#dot-req").hidden = !(d.requests > 0);
    if (ME) document.documentElement.style.setProperty("--accent", ME.accent_hex || "#00C9CD");
    return ME;
  }
  function needMe() { if (ME) return true; location.hash = "#signin"; return false; }
  function page(title, ...kids) { document.title = title + " · Chisme"; clear(view).append(...kids); view.focus({ preventScroll: true }); window.scrollTo(0, 0); }

  // ------------------------------------------------ a Chisme card
  const AUD = { everyone: "🌎 Everyone", homies: "🤝 Homies Only", me: "🔒 Only Me" };
  function avatar(u, size = 44) {
    const a = el("span", { class: "av", style: { width: size + "px", height: size + "px", borderColor: (CFG && CFG.accents[u.accent]) || "#00C9CD" } });
    if (u.photo) a.append(el("img", { src: u.photo, alt: "", width: size, height: size, loading: "lazy" }));
    else a.append(el("span", { class: "av-i", text: (u.name || u.username || "?").trim().charAt(0).toUpperCase() }));
    return a;
  }
  function richText(t) {
    const p = el("p", { class: "txt" });
    String(t || "").split(/([#@][\w]{1,40})/u).forEach((part) => {
      if (/^#\w/u.test(part)) p.append(el("a", { href: "#tag/" + encodeURIComponent(part.slice(1).toLowerCase()), class: "tag", text: part }));
      else if (/^@[A-Za-z0-9_]{3,20}$/.test(part)) p.append(el("a", { href: "#u/" + part.slice(1).toLowerCase(), class: "mention", text: part }));
      else p.append(part);
    });
    return p;
  }
  function card(c, opts = {}) {
    const a = c.author;
    const art = el("article", { class: "chisme card" + (c.meme ? " meme" : "") + (c.hidden ? " is-hidden" : ""), "data-id": c.id,
      style: { "--acc": (CFG && CFG.accents[a.accent]) || "#00C9CD" } });
    art.append(el("header", { class: "by" },
      el("a", { href: "#u/" + a.username, class: "who" }, avatar(a), el("span", {}, el("b", { text: a.name }), el("small", {}, "@" + a.username + " · " + ago(c.created_at),
        a.fresh ? el("em", { class: "new", text: "new here" }) : null))),
      opts.pinned ? el("span", { class: "pin", text: "📌 Pinned" }) : null,
      c.audience !== "everyone" ? el("span", { class: "aud", text: AUD[c.audience] }) : null,
      el("button", { type: "button", class: "more", "aria-label": "More options", text: "⋯", onclick: () => moreMenu(c) })));
    if (c.hidden) art.append(el("p", { class: "note", text: "Hidden while our team checks some reports. Only you can see it." }));
    if (c.meme) art.append(el("span", { class: "meme-badge", text: "😂 MEME" }));
    if (c.text) art.append(richText(c.text));
    if (c.photos.length) {
      const g = el("div", { class: "photos n" + c.photos.length });
      c.photos.forEach((p) => g.append(el("img", { src: p.url, alt: "", width: p.w || 600, height: p.h || 600, loading: "lazy", decoding: "async" })));
      art.append(g);
    }
    c.videos.forEach((v) => art.append(el("video", { class: "vid", src: v.url, poster: v.poster || null, controls: true, playsinline: true, preload: "metadata",
      width: v.w || 720, height: v.h || 1280 })));
    if (c.clip) art.append(clipCard(c.clip));
    const bar = el("div", { class: "react" });
    Object.entries(CFG.reactions).forEach(([k, emo]) => {
      const b = el("button", { type: "button", class: "rx" + (c.mine[k] ? " on" : ""), "aria-pressed": c.mine[k] ? "true" : "false",
        "aria-label": { like: "Love", laugh: "Laugh", wow: "Wow", chile: "Give a Chile" }[k] + ", " + c.counts[k] },
        el("span", { "aria-hidden": "true", text: emo }), el("span", { text: c.counts[k] || "" }));
      b.addEventListener("click", async () => {
        if (!needMe()) return;
        b.classList.add("pop"); setTimeout(() => b.classList.remove("pop"), 400);
        const d = await api(`/api/social/chismes/${c.id}/react`, { method: "POST", body: { kind: k } });
        if (d.ok) art.replaceWith(card(d.chisme, opts)); else toast(d.error);
      });
      bar.append(b);
    });
    bar.append(el("a", { class: "rx", href: "#c/" + c.id, "aria-label": "Comments, " + c.counts.comments }, el("span", { "aria-hidden": "true", text: "💬" }), el("span", { text: c.counts.comments || "" })));
    bar.append(el("button", { type: "button", class: "rx", "aria-label": "Share", onclick: () => share(c) }, el("span", { "aria-hidden": "true", text: "↗" }), el("span", { text: "Share" })));
    bar.append(el("button", { type: "button", class: "rx save" + (c.mine.saved ? " on" : ""), "aria-label": c.mine.saved ? "Saved" : "Save", onclick: async () => {
      if (!needMe()) return;
      const d = await api(`/api/social/chismes/${c.id}/save`, { method: "POST", body: {} });
      if (d.ok) { art.replaceWith(card(d.chisme, opts)); toast(d.chisme.mine.saved ? "Saved 🔖" : "Unsaved"); }
    } }, el("span", { "aria-hidden": "true", text: "🔖" })));
    art.append(bar);
    return art;
  }
  function clipCard(clip) {
    const box = el("div", { class: "clip" });
    const play = el("button", { type: "button", class: "clip-play", "aria-label": "Play " + (clip.title || "this ChismeTV clip") },
      clip.thumb ? el("img", { src: clip.thumb, alt: "", loading: "lazy" }) : el("span", { class: "clip-tt", text: "🎬" }), el("span", { class: "play", text: "▶" }));
    play.addEventListener("click", () => {
      const f = el("iframe", { src: clip.embed, title: clip.title || "ChismeTV clip", allow: "autoplay; encrypted-media; picture-in-picture", allowfullscreen: true, loading: "lazy" });
      play.replaceWith(f);
    });
    box.append(el("span", { class: "clip-tag", text: "📺 ChismeTV" }), play, el("p", { class: "clip-t" }, el("b", { text: clip.title || "A ChismeTV clip" }), clip.creator ? " · " + clip.creator : ""));
    return box;
  }
  async function share(c) {
    if (!c.share_url) { toast(c.audience === "homies" ? "Homies-only Chismes stay with your Homies 🤝" : "Only you can see this one 🔒"); return; }
    const url = location.origin + c.share_url;
    const text = (c.text || "Look at this chisme 👀").slice(0, 120);
    if (navigator.share) { try { await navigator.share({ title: "Chisme", text, url }); return; } catch (e) { if (e && e.name === "AbortError") return; } }
    try { await navigator.clipboard.writeText(url); toast("Link copied. Go spread the chisme 😏"); } catch (e) { toast(url, 5000); }
  }
  function moreMenu(c) {
    const items = [];
    if (c.own) {
      items.push(el("button", { type: "button", class: "item", text: ME && ME.pinned_id === c.id ? "📌 Unpin from my profile" : "📌 Pin to my profile", onclick: async () => {
        const d = await api("/api/social/profile", { method: "PATCH", body: { pinned_id: ME.pinned_id === c.id ? null : c.id } });
        closeSheet(); if (d.ok) { ME = { ...ME, ...d.profile }; toast(d.profile.pinned_id ? "Pinned 📌" : "Unpinned"); route(); } else toast(d.error);
      } }));
      items.push(el("button", { type: "button", class: "item danger", text: "🗑️ Delete this Chisme", onclick: async () => {
        if (!confirm("Delete this Chisme for good?")) return;
        const d = await api("/api/social/chismes/" + c.id, { method: "DELETE" }); closeSheet();
        if (d.ok) { document.querySelectorAll(`[data-id="${c.id}"]`).forEach((n) => n.remove()); toast("Deleted."); } else toast(d.error);
      } }));
    } else {
      items.push(el("button", { type: "button", class: "item", text: "🚩 Report this Chisme", onclick: () => reportSheet("chisme", c.id) }));
      items.push(el("button", { type: "button", class: "item", text: "©️ Report copyright", onclick: () => reportSheet("chisme", c.id, "copyright") }));
      items.push(el("button", { type: "button", class: "item danger", text: "🚫 Block @" + c.author.username, onclick: () => blockSheet(c.author.username) }));
    }
    items.push(el("button", { type: "button", class: "item", text: "↗ Share", onclick: () => { closeSheet(); share(c); } }));
    sheet("Options", el("div", { class: "menu" }, ...items));
  }
  function reportSheet(kind, id, preset) {
    if (!needMe()) return;
    const reasons = Object.entries(CFG.reasons);
    let pick = preset || "";
    const list = el("div", { class: "reasons", role: "radiogroup", "aria-label": "What's wrong?" });
    const details = el("textarea", { maxlength: "500", rows: "2", placeholder: "Anything else? (optional)" });
    const dm = el("p", { class: "small", hidden: pick !== "copyright" }, "Is it your work? After this, send a full takedown notice on the ",
      el("a", { href: "/dmca", text: "copyright (DMCA) form" }), " so we can remove it for good.");
    reasons.forEach(([k, label]) => {
      const r = el("label", { class: "reason" }, el("input", { type: "radio", name: "why", value: k, checked: k === pick }), el("span", { text: label }));
      r.querySelector("input").addEventListener("change", () => { pick = k; dm.hidden = k !== "copyright"; });
      list.append(r);
    });
    const f = form(async () => {
      if (!pick) return "Pick what's wrong.";
      const d = await api("/api/social/report", { method: "POST", body: { kind, id, reason: pick, details: details.value } });
      if (!d.ok) return d.error;
      closeSheet(); toast(d.message, 4500);
      if (d.hidden) document.querySelectorAll(`[data-id="${id}"]`).forEach((n) => n.remove());
    }, list, dm, details, el("button", { type: "submit", class: "btn pink wide", text: "Send report" }));
    sheet(preset === "copyright" ? "Report copyright" : "What's wrong?", el("div", {}, el("p", { class: "small", text: "Reports are private. They never see who sent one." }), f));
  }
  function blockSheet(username) {
    if (!needMe()) return;
    sheet("Block @" + username + "?", el("div", {},
      el("p", { text: "They won't see your profile or Chismes, can't send you Homie requests, and won't be told. If you're Homies, that ends too." }),
      el("button", { type: "button", class: "btn pink wide", text: "Block", onclick: async () => {
        const d = await api("/api/social/block/" + username, { method: "POST", body: { on: true } });
        closeSheet(); toast(d.message || d.error, 4000); if (d.ok) location.hash = "#feed/sananto";
      } })));
  }

  // ------------------------------------------------ feeds
  const EMPTY = {
    homies: "No chisme from your Homies yet. Find your people in 🤝 Homies.",
    sananto: "San Anto's quiet... too quiet. Be the first to spill. 🌶️",
    trending: "Nothing's trending yet. Give a Chile 🌶️ to what you love.",
    memes: "No memes yet?! Post one with #memes and get the 😂 rolling.",
  };
  async function feed(tab) {
    document.querySelectorAll("#feedtabs a").forEach((a) => {
      a.setAttribute("aria-current", a.dataset.tab === tab ? "page" : "false");
      if (a.dataset.tab === tab) a.scrollIntoView({ inline: "nearest", block: "nearest" });
    });
    const list = el("div", { class: "list" }, el("p", { class: "loading", text: "Getting the chisme..." }));
    const head = {
      homies: ["🤝 Homies", "Chismes from your confirmed Homies."], sananto: ["🌶️ San Anto", "Public chisme from around San Antonio."],
      trending: ["🔥 Trending", "What everybody's reacting to right now. New faces get a fair shot."],
      memes: ["😂 Memes", "The funniest stuff on Chisme. Tag yours #memes."],
    }[tab];
    page(head[0], el("section", { class: "feed-head" }, el("h1", { text: head[0] }), el("p", { class: "sub", text: head[1] })), list);
    if (tab === "homies" && !ME) { clear(list).append(guestCard()); return; }
    const d = await api("/api/social/feed?tab=" + tab);
    clear(list);
    if (!d.ok) { list.append(el("p", { class: "err", text: d.error })); return; }
    if (!d.chismes.length) list.append(el("p", { class: "empty", text: EMPTY[tab] }));
    d.chismes.forEach((c) => list.append(card(c)));
    if (!ME) list.prepend(guestCard());
  }
  function guestCard() {
    return el("div", { class: "card guest" }, el("b", { text: "Get in on the chisme 👀" }), el("p", { text: "Join to react, comment and post your own Chismes." }),
      el("a", { class: "btn pink", href: "#signup", text: "Join Chisme" }), " ", el("a", { class: "btn ghost", href: "#signin", text: "Sign in" }));
  }
  async function tagView(tag) {
    const d = await api("/api/social/feed?tab=sananto");
    const items = (d.chismes || []).filter((c) => (c.hashtags || []).includes(tag));
    page("#" + tag, el("section", { class: "feed-head" }, el("h1", { text: "#" + tag })), el("div", { class: "list" },
      items.length ? items.map((c) => card(c)) : el("p", { class: "empty", text: "Nothing with #" + tag + " yet." })));
  }
  async function oneView(id) {
    const d = await api("/api/social/chismes/" + id);
    if (!d.ok) { page("Not here", el("p", { class: "empty", text: d.error })); return; }
    const list = el("div", { class: "comments" });
    const box = el("textarea", { maxlength: "500", rows: "2", placeholder: "Say something..." , "aria-label": "Write a comment" });
    const f = form(async () => {
      if (!needMe()) return;
      const r = await api(`/api/social/chismes/${id}/comments`, { method: "POST", body: { text: box.value } });
      if (!r.ok) return r.error;
      box.value = ""; list.append(commentRow(r.comment));
    }, box, el("button", { type: "submit", class: "btn pink", text: "Comment 💬" }));
    page("Chisme", card(d.chisme), el("h2", { class: "h2", text: "Comments" }), list, ME ? f : guestCard());
    const cm = await api(`/api/social/chismes/${id}/comments`);
    (cm.comments || []).forEach((x) => list.append(commentRow(x)));
    if (!(cm.comments || []).length) list.append(el("p", { class: "empty small", text: "No comments yet. Say something funny. 😂" }));
  }
  function commentRow(x) {
    const row = el("div", { class: "comment", "data-id": x.id }, avatar(x.author, 32),
      el("div", {}, el("b", { text: x.author.name }), el("small", { text: " @" + x.author.username + " · " + ago(x.created_at) }), richText(x.text)));
    const actions = el("div", { class: "c-act" });
    if (x.can_delete) actions.append(el("button", { type: "button", class: "linkish", text: "Delete", onclick: async () => {
      const d = await api("/api/social/comments/" + x.id, { method: "DELETE" }); if (d.ok) row.remove(); } }));
    if (!x.own) actions.append(el("button", { type: "button", class: "linkish", text: "Report", onclick: () => reportSheet("comment", x.id) }));
    row.append(actions);
    return row;
  }

  // ------------------------------------------------ profiles
  async function profileView(username, tab = "chismes") {
    const d = await api(`/api/social/u/${encodeURIComponent(username)}?tab=${tab}`);
    if (!d.ok) { page("Not here", el("p", { class: "empty", text: d.error })); return; }
    const p = d.profile, acc = p.accent_hex || "#00C9CD";
    const banner = el("div", { class: "banner", style: { background: p.banner ? `center/cover no-repeat url("${p.banner}")` : `linear-gradient(135deg, ${acc}, #FF1A7F 55%, #FF6A0B)` } });
    const btns = el("div", { class: "p-btns" });
    if (p.relation === "me") {
      btns.append(el("a", { class: "btn acc", href: "#edit", text: "✏️ Edit profile" }), el("a", { class: "btn ghost", href: "#settings", text: "⚙️" , "aria-label": "Settings" }));
    } else if (ME) {
      const label = { homies: "🤝 HOMIES", requested: "⏳ Asked", incoming: "🤝 YEAH, HOMIE", none: "🤝 HOMIE" }[p.relation];
      btns.append(el("button", { type: "button", class: "btn acc", text: label, disabled: p.relation === "requested", onclick: () => homieOrNah(p) }));
      btns.append(el("button", { type: "button", class: "btn ghost", "aria-label": "More", text: "⋯", onclick: () => sheet("@" + p.username, el("div", { class: "menu" },
        el("button", { type: "button", class: "item", text: "🚩 Report @" + p.username, onclick: () => reportSheet("user", p.username) }),
        el("button", { type: "button", class: "item danger", text: "🚫 Block @" + p.username, onclick: () => blockSheet(p.username) }),
        p.relation === "homies" ? el("button", { type: "button", class: "item", text: "Stop being Homies", onclick: async () => {
          await api("/api/social/homies/" + p.username, { method: "POST", body: { action: "unhomie" } }); closeSheet(); route(); } }) : null)) }));
    } else btns.append(el("a", { class: "btn acc", href: "#signup", text: "🤝 HOMIE" }));
    const tabs = el("nav", { class: "ptabs", "aria-label": "Profile" }, ...["chismes", "photos", "videos"].map((t) =>
      el("a", { href: `#u/${p.username}/${t}`, "aria-current": t === tab ? "page" : "false", text: t.toUpperCase() })));
    const list = el("div", { class: "list" });
    if (d.pinned) list.append(card(d.pinned, { pinned: true }));
    d.chismes.forEach((c) => list.append(card(c)));
    if (!d.chismes.length && !d.pinned) list.append(el("p", { class: "empty", text: tab === "chismes" ? "No Chismes yet." : "Nothing here yet." }));
    page(p.name, el("section", { class: "profile", style: { "--acc": acc } }, banner,
      el("div", { class: "p-top" }, avatar(p, 96), btns),
      el("h1", { class: "p-name", text: p.name }), el("p", { class: "p-user", text: "@" + p.username }),
      p.area ? el("p", { class: "p-area", text: "📍 " + p.area + " • San Antonio" }) : null,
      p.bio ? richText(p.bio) : null,
      el("p", { class: "p-counts" }, el("b", { text: String(p.homies) }), " HOMIES 🤝",
        p.relation !== "me" && p.mutual_homies ? el("span", {}, " · ", el("b", { text: String(p.mutual_homies) }), " Mutual Homies") : null),
      p.under_review ? el("p", { class: "note", text: "Your profile is being reviewed after some reports. You can still use Chisme." }) : null, tabs), list);
  }
  function homieOrNah(p) {
    if (p.relation === "homies") { toast("Y'all are already Homies 🤝"); return; }
    const go = async (action) => {
      const d = await api("/api/social/homies/" + p.username, { method: "POST", body: { action } });
      closeSheet();
      if (!d.ok) { toast(d.error); return; }
      toast(action === "nah" ? "Got it. Nobody gets told. ✋" : d.relation === "homies" ? "Y'all are Homies now 🤝" : "Homie request sent 🤝");
      route();
    };
    sheet("KNOW THIS PERSON?", el("div", { class: "hon" },
      el("div", { class: "hon-who" }, avatar(p, 72), el("div", {}, el("b", { text: p.name }), el("p", { class: "small", text: "@" + p.username + (p.area ? " · 📍 " + p.area : "") }),
        el("p", { class: "small", text: `${p.homies} Homies · ${p.mutual_homies} Mutual Homies` }))),
      p.bio ? el("p", { text: p.bio }) : null,
      el("a", { href: "#u/" + p.username, class: "small", text: "See their Chismes, photos and videos", onclick: closeSheet }),
      el("div", { class: "hon-btns" },
        el("button", { type: "button", class: "btn acc big", text: "🤝 HOMIE", onclick: () => go("homie") }),
        el("button", { type: "button", class: "btn ghost big", text: "✋ NAH", onclick: () => go("nah") })),
      el("p", { class: "small", text: "NAH is private. They'll never know." })));
  }

  // ------------------------------------------------ photo + video squeeze on the phone (the server cleans them again)
  async function squeezePhoto(file, edge = 2048) {
    let bmp;
    try { bmp = await createImageBitmap(file, { imageOrientation: "from-image" }); }
    catch (e) {
      bmp = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("bad")); i.src = URL.createObjectURL(file); })
        .catch(() => null);
    }
    if (!bmp) throw new Error("That photo can't be read. Try a JPEG or PNG.");
    const w = bmp.width, h = bmp.height, k = Math.min(1, edge / Math.max(w, h));
    const cv = document.createElement("canvas"); cv.width = Math.round(w * k); cv.height = Math.round(h * k);
    cv.getContext("2d").drawImage(bmp, 0, 0, cv.width, cv.height);   // redrawn pixels only: EXIF / GPS never leave the phone
    const blob = await new Promise((res) => cv.toBlob(res, "image/jpeg", 0.85));
    if (!blob) throw new Error("That photo can't be read.");
    if (blob.size > 8 * 1024 * 1024) throw new Error("That photo is too big (8 MB max).");
    return blob;
  }
  function videoInfo(file) {
    return new Promise((res) => {
      const v = document.createElement("video"); v.preload = "metadata"; v.muted = true;
      v.onloadedmetadata = () => { res({ s: v.duration, w: v.videoWidth, h: v.videoHeight }); URL.revokeObjectURL(v.src); };
      v.onerror = () => res(null); v.src = URL.createObjectURL(file);
    });
  }
  async function squeezeVideo(file, info, onTick) {
    // Big or over 720p: re-record it at 720p on the phone first (MediaRecorder), so the upload is small. If the phone
    // can't, the original goes up (40 MB max) and the server re-encodes it either way, dropping all metadata.
    const big = file.size > 18 * 1024 * 1024 || Math.min(info.w, info.h) > 720;
    if (!big || !window.MediaRecorder || !HTMLCanvasElement.prototype.captureStream) return file;
    const type = ["video/mp4;codecs=avc1", "video/webm;codecs=vp9", "video/webm"].find((t) => MediaRecorder.isTypeSupported(t));
    if (!type) return file;
    try {
      const v = document.createElement("video"); v.src = URL.createObjectURL(file); v.muted = true; v.playsInline = true;
      await v.play(); v.pause(); v.currentTime = 0;
      const k = Math.min(1, 720 / Math.min(info.w, info.h));
      const cv = document.createElement("canvas"); cv.width = Math.round(info.w * k / 2) * 2; cv.height = Math.round(info.h * k / 2) * 2;
      const ctx = cv.getContext("2d"), stream = cv.captureStream(30);
      const rec = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 1800000 }), parts = [];
      rec.ondataavailable = (e) => e.data.size && parts.push(e.data);
      const done = new Promise((r) => { rec.onstop = r; });
      rec.start(500); await v.play();
      await new Promise((r) => { const step = () => { if (v.ended || v.currentTime >= 60) { r(); return; } ctx.drawImage(v, 0, 0, cv.width, cv.height);
        onTick && onTick(v.currentTime / Math.min(60, info.s)); requestAnimationFrame(step); }; step(); });
      rec.stop(); await done; URL.revokeObjectURL(v.src);
      const out = new Blob(parts, { type: type.split(";")[0] });
      return out.size && out.size < file.size ? out : file;
    } catch (e) { return file; }
  }
  async function upload(blob, kind) {
    return api("/api/social/upload?kind=" + kind, { method: "POST", raw: true, body: blob, type: blob.type || "application/octet-stream" });
  }

  // ------------------------------------------------ edit profile (customization)
  function editView() {
    if (!needMe()) return;
    const st = { photo: undefined, banner: undefined, accent: ME.accent };
    const prevBanner = el("div", { class: "banner edit", style: { background: ME.banner ? `center/cover url("${ME.banner}")` : "linear-gradient(135deg, var(--accent), #FF1A7F 55%, #FF6A0B)" } },
      el("button", { type: "button", class: "chip-btn", text: "📷 Change cover", onclick: media(() => $("#pick-banner").click()) }));
    const prevAv = el("div", { class: "av-edit" }, avatar(ME, 96), el("button", { type: "button", class: "chip-btn", text: "📷 Photo", onclick: media(() => $("#pick-avatar").click()) }));
    const wire = (inputId, kind, key, apply) => {
      const inp = $(inputId);
      inp.onchange = async () => {
        const f = inp.files[0]; inp.value = ""; if (!f) return;
        toast("Uploading...");
        try {
          const d = await upload(await squeezePhoto(f, kind === "avatar" ? 1024 : 2048), kind);
          if (!d.ok) { toast(d.error, 4000); return; }
          st[key] = d.name; apply(d.url); toast("Looking good 😎");
        } catch (e) { toast(e.message); }
      };
    };
    wire("#pick-avatar", "avatar", "photo", (u) => { const a = prevAv.querySelector(".av"); clear(a).append(el("img", { src: u, alt: "" })); });
    wire("#pick-banner", "banner", "banner", (u) => { prevBanner.style.background = `center/cover url("${u}")`; });
    const [fn, name] = field("Display name", { maxlength: "40", value: ME.name });
    const [fu, user] = field("@username", { maxlength: "20", value: ME.username, autocapitalize: "none" });
    const [fb, bio] = field("Bio", { tag: "textarea", maxlength: "160", rows: "3" }); bio.value = ME.bio || "";
    const count = el("small", { class: "count", text: `${bio.value.length}/160` }); bio.addEventListener("input", () => { count.textContent = `${bio.value.length}/160`; });
    const area = el("select", { "aria-label": "Part of town" }, el("option", { value: "", text: "Don't show" }), ...CFG.areas.map((a) => el("option", { value: a, text: a, selected: ME.area_choice === a })));
    const sw = el("div", { class: "swatches", role: "radiogroup", "aria-label": "Theme accent" });
    Object.entries(CFG.accents).forEach(([k, hex]) => {
      const b = el("button", { type: "button", class: "sw" + (k === st.accent ? " on" : ""), role: "radio", "aria-checked": k === st.accent ? "true" : "false",
        "aria-label": k, style: { background: hex }, onclick: () => {
          st.accent = k; sw.querySelectorAll(".sw").forEach((n) => { n.classList.toggle("on", n === b); n.setAttribute("aria-checked", n === b ? "true" : "false"); });
          document.documentElement.style.setProperty("--accent", hex);
        } });
      sw.append(b);
    });
    const f = form(async () => {
      const body = { display_name: name.value, username: user.value, bio: bio.value, area: area.value || null, accent: st.accent };
      if (st.photo !== undefined) body.photo = st.photo;
      if (st.banner !== undefined) body.banner = st.banner;
      const d = await api("/api/social/profile", { method: "PATCH", body });
      if (!d.ok) return d.error;
      await loadMe(); toast("Saved ✅"); location.hash = "#u/" + d.profile.username;
    }, fn, fu, fb, count, el("label", { class: "fld" }, el("span", { text: "📍 Part of town (optional)" }), area),
      el("div", { class: "fld" }, el("span", { text: "Theme accent (the Fiesta palette)" }), sw),
      el("p", { class: "small", text: "Pin a Chisme from its ⋯ menu to keep it at the top of your profile." }),
      el("button", { type: "submit", class: "btn pink wide", text: "Save profile" }));
    page("Edit profile", el("section", { class: "profile editing" }, prevBanner, prevAv), el("section", { class: "card" }, el("h1", { text: "Make it yours ✨" }), f));
  }

  // ------------------------------------------------ ➕ CHISME: the menu + the composer
  const SOON = "Photo and video uploads are coming soon 📸 Text Chismes work right now.";
  const media = (fn) => () => { if (!ME.can_upload) { toast(SOON, 3500); return; } fn(); };
  function plusMenu() {
    if (!needMe()) return;
    const opt = (emo, label, fn) => el("button", { type: "button", class: "item big", onclick: () => { closeSheet(); fn(); } }, el("span", { "aria-hidden": "true", text: emo }), " " + label);
    sheet("➕ CHISME", el("div", { class: "menu grid" },
      opt("📸", "Take Photo", media(() => composer({ pick: "#cam-photo" }))), opt("🖼️", "Upload Photo", media(() => composer({ pick: "#pick-photo" }))),
      opt("🎥", "Record Video", media(() => composer({ pick: "#cam-video" }))), opt("📁", "Upload Video", media(() => composer({ pick: "#pick-video" }))),
      opt("📺", "Repost a ChismeTV clip", () => composer({ clip: true })), opt("😂", "Post a Meme", () => composer({ meme: true, pick: ME.can_upload ? "#pick-photo" : null })),
      opt("✏️", "Text Chisme", () => composer({})), ME.can_upload ? null : el("p", { class: "note soon", text: SOON })));
  }
  function composer(o = {}) {
    if (!needMe()) return;
    const st = { photos: [], video: null, clip: null, meme: !!o.meme, audience: (ME.privacy && ME.privacy.default_audience) || "everyone" };
    const text = el("textarea", { class: "big-txt", maxlength: "2000", rows: "4", placeholder: "WHAT'S THE CHISME? 👀", "aria-label": "What's the chisme?" });
    const media = el("div", { class: "c-media" });
    const status = el("p", { class: "small", role: "status" });
    const drawMedia = () => {
      clear(media);
      st.photos.forEach((p, i) => media.append(el("figure", { class: "thumb" }, el("img", { src: p.url, alt: "" }),
        el("button", { type: "button", class: "rm", "aria-label": "Remove photo", text: "✕", onclick: () => { st.photos.splice(i, 1); drawMedia(); } }))));
      if (st.video) media.append(el("figure", { class: "thumb vid" }, el("video", { src: st.video.url, poster: st.video.poster, muted: true, playsinline: true, controls: true }),
        el("figcaption", { text: `🎥 ${st.video.seconds}s · ${st.video.w}×${st.video.h}` }),
        el("button", { type: "button", class: "rm", "aria-label": "Remove video", text: "✕", onclick: () => { st.video = null; drawMedia(); } })));
      if (st.clip) media.append(el("div", { class: "thumb clipthumb" }, clipCard(st.clip), el("button", { type: "button", class: "rm", "aria-label": "Remove clip", text: "✕", onclick: () => { st.clip = null; drawMedia(); } })));
    };
    const addPhotos = async (files) => {
      for (const f of [...files].slice(0, CFG.max_photos - st.photos.length)) {
        status.textContent = "Shrinking + cleaning your photo (no location data)...";
        try {
          const d = await upload(await squeezePhoto(f), "chisme");
          if (!d.ok) { toast(d.error, 4000); continue; }
          st.photos.push(d); st.video = null; drawMedia();
        } catch (e) { toast(e.message); }
      }
      status.textContent = "";
    };
    const addVideo = async (f) => {
      const info = await videoInfo(f);
      if (!info) { toast("That video can't be read on this phone. Try MP4."); return; }
      if (info.s > CFG.max_video_s + 0.5) { toast(`Videos can be ${CFG.max_video_s} seconds max. Trim it first ✂️`, 4000); return; }
      status.textContent = "Squeezing your video to 720p...";
      const blob = await squeezeVideo(f, info, (x) => { status.textContent = `Squeezing your video... ${Math.round(x * 100)}%`; });
      if (blob.size > 40 * 1024 * 1024) { status.textContent = ""; toast("That video is too big (40 MB max). Try a shorter one."); return; }
      status.textContent = "Uploading + cleaning (no location data)...";
      const d = await upload(blob, "video");
      status.textContent = "";
      if (!d.ok) { toast(d.error, 4000); return; }
      st.video = d; st.photos = []; drawMedia();
    };
    const wire = (id, fn) => { const i = $(id); i.onchange = () => { const fs = [...i.files]; i.value = ""; fs.length && fn(fs); }; };
    wire("#pick-photo", addPhotos); wire("#cam-photo", addPhotos);
    wire("#pick-video", (fs) => addVideo(fs[0])); wire("#cam-video", (fs) => addVideo(fs[0]));
    const tools = el("div", { class: "tools" },
      el("button", { type: "button", class: "tool", "aria-label": "Add photos", text: "🖼️", onclick: media(() => $("#pick-photo").click()) }),
      el("button", { type: "button", class: "tool", "aria-label": "Take a photo", text: "📸", onclick: media(() => $("#cam-photo").click()) }),
      el("button", { type: "button", class: "tool", "aria-label": "Add a video", text: "🎥", onclick: media(() => $("#pick-video").click()) }),
      el("button", { type: "button", class: "tool", "aria-label": "Repost a ChismeTV clip", text: "📺", onclick: () => clipPicker((c) => { st.clip = c; drawMedia(); }) }));
    const memeT = el("input", { type: "checkbox", checked: st.meme }); memeT.addEventListener("change", () => { st.meme = memeT.checked; });
    const aud = el("div", { class: "aud-pick", role: "radiogroup", "aria-label": "WHO CAN SEE THIS?" });
    Object.entries(AUD).forEach(([k, label]) => {
      const b = el("button", { type: "button", role: "radio", class: "audb" + (k === st.audience ? " on" : ""), "aria-checked": k === st.audience ? "true" : "false", text: label,
        onclick: () => { st.audience = k; aud.querySelectorAll(".audb").forEach((n) => { n.classList.toggle("on", n === b); n.setAttribute("aria-checked", n === b ? "true" : "false"); }); } });
      aud.append(b);
    });
    const f = form(async () => {
      const d = await api("/api/social/chismes", { method: "POST", body: { text: text.value, photos: st.photos.map((p) => p.name),
        video: st.video && st.video.name, clip: st.clip && { id: st.clip.id, title: st.clip.title, creator: st.clip.creator }, meme: st.meme, audience: st.audience } });
      if (!d.ok) return d.error;
      toast("Chisme posted 🌶️"); location.hash = st.meme ? "#feed/memes" : "#c/" + d.chisme.id;
    }, text, media, status, tools, el("label", { class: "chk" }, memeT, el("span", { text: "😂 It's a meme (shows in Memes)" })),
      el("p", { class: "lbl", text: "WHO CAN SEE THIS?" }), aud, el("button", { type: "submit", class: "btn pink wide big", text: "POST CHISME 🌶️" }));
    page("New Chisme", el("section", { class: "card composer" }, el("div", { class: "c-who" }, avatar(ME, 40), el("b", { text: ME.name })), f));
    if (o.pick) setTimeout(() => $(o.pick).click(), 50);
    if (o.clip) clipPicker((c) => { st.clip = c; drawMedia(); });
    composer.state = st; composer.draw = drawMedia;
  }
  async function clipPicker(done) {
    const link = el("input", { type: "url", placeholder: "Paste a ChismeTV, YouTube or TikTok link", "aria-label": "Clip link" });
    const list = el("div", { class: "clips" }, el("p", { class: "small", text: "Loading ChismeTV..." }));
    const pickId = (id, title, creator) => { closeSheet(); done({ id, title: title || "", creator: creator || "",
      thumb: /^\d+$/.test(id) ? null : `https://i.ytimg.com/vi/${id}/hqdefault.jpg`, embed: /^\d+$/.test(id) ? `https://www.tiktok.com/player/v1/${id}` : `https://www.youtube-nocookie.com/embed/${id}?playsinline=1` }); };
    sheet("📺 Repost a ChismeTV clip", el("div", {}, form(async () => {
      const v = link.value.trim();
      const m = v.match(/[?&]reel=([\w-]{11}|\d{15,20})/) || v.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/) || v.match(/tiktok\.com\/.*?(\d{15,20})/);
      if (!m) return "That isn't a ChismeTV, YouTube or TikTok link.";
      pickId(m[1]);
    }, link, el("button", { type: "submit", class: "btn acc", text: "Use this link" })), list));
    const d = await api("/api/food");
    clear(list);
    const items = [...(d.items || []), ...(d.world || [])].filter((it) => it.video && it.url).slice(0, 12);
    if (!items.length) list.append(el("p", { class: "small", text: "Couldn't load ChismeTV right now. Paste a link instead." }));
    items.forEach((it) => {
      const m = String(it.url).match(/(?:v=|shorts\/|youtu\.be\/|embed\/)([\w-]{11})/) || String(it.url).match(/video\/(\d{15,20})/);
      if (!m) return;
      list.append(el("button", { type: "button", class: "clip-row", onclick: () => pickId(m[1], it.title, it.creator) },
        el("img", { src: /^\d+$/.test(m[1]) ? (it.image || "") : `https://i.ytimg.com/vi/${m[1]}/default.jpg`, alt: "", loading: "lazy" }),
        el("span", {}, el("b", { text: it.title || "ChismeTV clip" }), el("small", { text: it.creator || "" }))));
    });
  }

  // ------------------------------------------------ Homies, alerts, settings
  async function homiesView() {
    if (!needMe()) return;
    const reqs = el("div", { class: "list" }), sugg = el("div", { class: "list" });
    page("Homies", el("section", { class: "feed-head" }, el("h1", { text: "🤝 Homies" }), el("p", { class: "sub", text: "Mutual only. Both of y'all have to say yeah." })),
      el("h2", { class: "h2", text: "Homie requests" }), reqs, el("h2", { class: "h2", text: "People you might know" }), sugg);
    const [r, s] = await Promise.all([api("/api/social/requests"), api("/api/social/suggestions")]);
    const row = (p, incoming) => el("div", { class: "card person" }, el("a", { href: "#u/" + p.username, class: "who" }, avatar(p, 52),
      el("span", {}, el("b", { text: p.name }), el("small", { text: "@" + p.username + (p.mutual_homies ? ` · ${p.mutual_homies} Mutual Homies` : "") }))),
      el("button", { type: "button", class: "btn acc", text: incoming ? "Review" : "Homie or Nah?", onclick: () => homieOrNah(p) }));
    (r.requests || []).forEach((p) => reqs.append(el("div", {}, el("p", { class: "small notif", text: `${p.name} says you're Homies. 🤝` }), row(p, true))));
    if (!(r.requests || []).length) reqs.append(el("p", { class: "empty small", text: "No requests right now." }));
    (s.people || []).forEach((p) => sugg.append(row(p, false)));
    if (!(s.people || []).length) sugg.append(el("p", { class: "empty small", text: "No suggestions yet. Invite your people to Chisme." }));
  }
  async function alertsView() {
    if (!needMe()) return;
    const d = await api("/api/social/notifications");
    $("#dot-alerts").hidden = true;
    page("Alerts", el("section", { class: "feed-head" }, el("h1", { text: "🔔 Alerts" })), el("div", { class: "list" },
      (d.notifications || []).length ? d.notifications.map((n) => el("a", { class: "card notif-row" + (n.read ? "" : " unread"),
        href: n.kind === "homie_request" ? "#homies" : n.chisme_id ? "#c/" + n.chisme_id : "#u/" + n.actor.username },
        avatar(n.actor, 40), el("span", {}, n.text, el("small", { text: " · " + ago(n.created_at) })))) : el("p", { class: "empty", text: "All quiet. For now. 👀" })));
  }
  async function settingsView() {
    if (!needMe()) return;
    const pv = ME.privacy || {};
    const sel = (key, label, opts) => { const s = el("select", { "aria-label": label }, ...opts.map(([v, t]) => el("option", { value: v, text: t, selected: pv[key] === v })));
      s.addEventListener("change", async () => { const d = await api("/api/social/profile", { method: "PATCH", body: { privacy: { [key]: s.value } } }); toast(d.ok ? "Saved ✅" : d.error); if (d.ok) loadMe(); });
      return el("label", { class: "fld" }, el("span", { text: label }), s); };
    const blocked = el("div", { class: "list" });
    const del = el("input", { placeholder: "Type DELETE", autocapitalize: "characters", "aria-label": "Type DELETE to confirm" });
    page("Settings", el("section", { class: "card" }, el("h1", { text: "⚙️ Settings" }), el("p", { class: "small", text: "Signed in as @" + ME.username + (ME.email_hint ? " (" + ME.email_hint + ")" : "") }),
      el("h2", { class: "h2", text: "Privacy" }),
      sel("default_audience", "New Chismes go to", [["everyone", "🌎 Everyone"], ["homies", "🤝 Homies Only"], ["me", "🔒 Only Me"]]),
      sel("area", "Who sees my part of town", [["everyone", "Everyone"], ["homies", "Homies"], ["nobody", "Nobody"]]),
      sel("homies_list", "Who sees my Homies list", [["everyone", "Everyone"], ["homies", "Homies"], ["me", "Only me"]]),
      sel("requests", "Who can send Homie requests", [["everyone", "Everyone"], ["mutuals", "People with mutual Homies"]]),
      el("h2", { class: "h2", text: "Blocked" }), blocked,
      el("h2", { class: "h2", text: "Safety" }), el("p", {}, el("a", { href: "/dmca", text: "©️ Report copyright (DMCA)" })),
      el("button", { type: "button", class: "btn ghost wide", text: "Sign out", onclick: async () => { await api("/api/social/logout", { method: "POST", body: {} }); ME = null; location.hash = "#signin"; } }),
      el("h2", { class: "h2 danger", text: "Delete my account" }),
      el("p", { class: "small", text: "This deletes your profile, every Chisme, photo, video, comment and reaction, right now. It can't be undone." }),
      form(async () => {
        const d = await api("/api/social/account/delete", { method: "POST", body: { confirm: del.value.trim() } });
        if (!d.ok) return d.error;
        ME = null; page("Bye", el("section", { class: "card auth" }, el("h1", { text: "Account deleted" }), el("p", { text: d.message })));
      }, del, el("button", { type: "submit", class: "btn danger wide", text: "Delete my account for good" }))));
    const b = await api("/api/social/blocked");
    (b.people || []).forEach((p) => blocked.append(el("div", { class: "person slim" }, el("span", { text: p.name + " @" + p.username }),
      el("button", { type: "button", class: "linkish", text: "Unblock", onclick: async () => { await api("/api/social/block/" + p.username, { method: "POST", body: { on: false } }); settingsView(); } }))));
    if (!(b.people || []).length) blocked.append(el("p", { class: "small", text: "Nobody. Peace and love. ✌️" }));
  }

  // ------------------------------------------------ the owner's moderation queue (/stats/social)
  async function modView() {
    const d = await api("/stats/social/queue");
    if (!d.ok) { page("Moderation", el("p", { class: "err", text: d.error })); return; }
    const act = async (kind, id, action) => { const r = await api("/stats/social/action", { method: "POST", body: { kind, id, action } }); toast(r.ok ? "Done ✅" : r.error); if (r.ok) modView(); };
    const items = d.items.map((g) => el("article", { class: "card mod" + (g.status === "hidden" ? " auto" : "") },
      el("header", { class: "mod-h" }, el("b", { text: { chisme: "Chisme", comment: "Comment", user: "Profile" }[g.kind] }),
        el("span", { class: "pill", text: `${g.count} report${g.count === 1 ? "" : "s"}` }),
        g.status === "hidden" || g.status === "flagged" ? el("span", { class: "pill pink", text: "Auto-hidden" }) : null),
      g.author ? el("p", { class: "small", text: `${g.author.name} @${g.author.username}` }) : null,
      el("p", { class: "mod-prev", text: g.preview || "(no text)" }),
      (g.media || []).length ? el("div", { class: "photos n1" }, el("img", { src: g.media[0], alt: "Reported media", class: "blur", onclick: (e) => e.target.classList.toggle("blur") })) : null,
      el("p", { class: "small", text: Object.entries(g.reasons).map(([k, n]) => `${k} ×${n}`).join(" · ") }),
      ...g.details.slice(0, 3).map((t) => el("p", { class: "small quote", text: "“" + t + "”" })),
      el("div", { class: "mod-btns" },
        el("button", { type: "button", class: "btn ghost", text: "✅ Keep it up", onclick: () => act(g.kind, g.id, "restore") }),
        el("button", { type: "button", class: "btn pink", text: "🗑️ Take it down", onclick: () => act(g.kind, g.id, "remove") }),
        el("button", { type: "button", class: "btn danger", text: "⛔ Ban account", onclick: () => confirm("Ban this account? Their email can't sign up again.") && act(g.kind, g.author ? g.id : g.id, "ban") }))));
    const dm = d.dmca.map((x) => el("article", { class: "card mod" }, el("header", { class: "mod-h" }, el("b", { text: "DMCA notice" }), el("span", { class: "pill", text: ago(x.created_at) })),
      el("p", { class: "small", text: "From " + x.claimant_name }), el("p", { class: "mod-prev", text: x.work }), el("p", { class: "small quote", text: x.urls }),
      el("div", { class: "mod-btns" }, el("button", { type: "button", class: "btn pink", text: "Remove the content", onclick: () => act("dmca", x.id, "removed") }),
        el("button", { type: "button", class: "btn ghost", text: "Reject + restore", onclick: () => act("dmca", x.id, "rejected") }))));
    page("Moderation", el("section", { class: "feed-head" }, el("h1", { text: "🛡️ Moderation queue" }),
      el("p", { class: "sub", text: `Things with ${3}+ reports hide themselves until you decide. Most reported first.` }),
      d.csam_unreported ? el("p", { class: "err", text: `⚠️ ${d.csam_unreported} scanner match(es) held. File the required NCMEC CyberTipline report.` }) : null),
      el("div", { class: "list" }, items.length ? items : el("p", { class: "empty", text: "Queue's empty. Chisme's behaving. 😇" })),
      dm.length ? el("h2", { class: "h2", text: "Copyright (DMCA)" }) : null, el("div", { class: "list" }, dm));
  }

  // ------------------------------------------------ router
  async function route() {
    if (!$("#sheet").hidden) closeSheet();
    if (MODE === "mod") { document.body.classList.add("mod-mode"); return modView(); }
    const h = decodeURIComponent(location.hash.slice(1) || "feed/sananto"), [a, b, c] = h.split("/");
    document.querySelectorAll("#bottom [data-nav]").forEach((n) => n.setAttribute("aria-current", n.dataset.nav === (a === "u" && ME && b === ME.username ? "me" : a) ? "page" : "false"));
    document.body.classList.toggle("on-feed", a === "feed");
    if (a === "feed") return feed(["homies", "sananto", "trending", "memes"].includes(b) ? b : "sananto");
    if (a === "u" && b) return profileView(b, ["photos", "videos"].includes(c) ? c : "chismes");
    if (a === "me") return ME ? profileView(ME.username) : signIn();
    if (a === "c" && b) return oneView(b);
    if (a === "tag" && b) return tagView(b);
    if (a === "edit") return editView();
    if (a === "new") return composer({});
    if (a === "homies") return homiesView();
    if (a === "alerts") return alertsView();
    if (a === "settings") return settingsView();
    if (a === "signup") return signUp();
    if (a === "forgot") return forgot();
    if (a === "signin") return signIn();
    return feed("sananto");
  }
  $("#plus").addEventListener("click", plusMenu);
  window.addEventListener("hashchange", route);
  (async () => {
    const c = await api("/api/social/config");
    CFG = c.ok ? c : { reactions: { like: "❤️", laugh: "😂", wow: "😮", chile: "🌶️" }, accents: {}, reasons: {}, areas: [], max_photos: 4, max_video_s: 60 };
    await loadMe();
    route();
  })();
  window.__social = { route, composer, api };
})();
