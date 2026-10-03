/* Chisme · The Juan That Got Away: the owner's GOD MODE panel (v49.15.x, for play-testing every stage and hunting bugs).
   Admin only. This file is not in /static: app.py serves it at GET /stats/juan/god.js only to the signed-in /stats owner
   (the HttpOnly session cookie, path=/stats), and juan.js only asks for it when the chisme_admin=1 marker is there and
   it isn't the native app. juan.js holds the switches (all off); this file only adds the controls:
     • ⚡ God button (in the game's control row) → a sheet: Immortal (no damage, never caught), Fly (hold Jump to rise),
       Noclip (through pallets, tires and cars), Speed 1×–3×, and Jump to a level (1–7).
     • a small "⚡ GOD MODE" badge over the road while it's on.
   A run that ever had god mode on (or started from a level jump) never saves a best score and never goes on the Top 10
   (juan.js skips it; the server refuses god: true too). Fiesta colors: purple, pink, turquoise, silver; no yellow. */
(function (root) {
  "use strict";
  const CSS = `
.juan-god-btn{background:#6d28d9!important;border-color:#000!important;color:#fff!important}
.juan-god-btn.on{background:#FF1A7F!important;box-shadow:0 0 0 3px #00C9CD inset}
.juan-god-badge{position:absolute;left:8px;bottom:8px;z-index:3;pointer-events:none;display:none;align-items:center;gap:4px;
  padding:4px 10px;border-radius:999px;background:rgba(76,29,149,.92);color:#fff;border:2px solid #FF1A7F;
  font:900 12px/1.1 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;letter-spacing:.06em;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.juan-god-badge.on{display:inline-flex}
.juan-god-badge small{font-weight:800;letter-spacing:.02em;color:#a5f3f4}
dialog.juan-god{border:0;padding:0;background:transparent;max-width:min(420px,calc(100vw - 20px));width:100%;color:#fff}
dialog.juan-god::backdrop{background:rgba(10,8,24,.62)}
.juan-god-card{background:#16122a;border:3px solid #000;border-radius:18px;padding:16px 16px 14px;box-shadow:0 0 0 2px #6d28d9 inset;
  font:600 15px/1.3 -apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;max-height:calc(100dvh - 24px);overflow:auto}
.juan-god-t{margin:0 0 2px;font-weight:900;font-size:21px}
.juan-god-t small{display:inline-block;margin-left:6px;padding:2px 8px;border-radius:999px;background:#FF1A7F;font-size:11px;letter-spacing:.06em;vertical-align:middle}
.juan-god-sub{margin:0 0 12px;color:#c9d0d8;font-size:13px}
.juan-god-sw{display:flex;align-items:center;gap:12px;min-height:48px;padding:6px 10px;margin:0 0 6px;border-radius:12px;background:#221b3d;cursor:pointer}
.juan-god-sw input{width:24px;height:24px;accent-color:#FF1A7F;flex:none}
.juan-god-sw b{display:block;font-size:16px}
.juan-god-sw small{display:block;color:#c9d0d8;font-size:12px;font-weight:600}
.juan-god-h{margin:12px 0 6px;font-weight:900;font-size:14px;letter-spacing:.04em;color:#a5f3f4;text-transform:uppercase}
.juan-god-seg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.juan-god-seg button,.juan-god-lv button{min-height:44px;border-radius:12px;border:2px solid #000;background:#2c2450;color:#fff;font:800 15px/1.1 inherit;font-family:inherit;cursor:pointer}
.juan-god-seg button[aria-pressed=true]{background:#00C9CD;color:#06121a}
.juan-god-lv{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.juan-god-lv button{display:flex;align-items:center;gap:8px;padding:6px 10px;text-align:left;font-size:14px}
.juan-god-lv button b{flex:none;display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#FF1A7F;color:#fff;font-size:13px}
.juan-god-lv button.cur{background:#4c1d95;box-shadow:0 0 0 2px #00C9CD inset}
.juan-god-note{margin:12px 0 10px;color:#c9d0d8;font-size:12.5px}
.juan-god-done{width:100%;min-height:48px;border-radius:14px;border:3px solid #000;background:#00C9CD;color:#06121a;font:900 17px/1 inherit;font-family:inherit;cursor:pointer}
.juan-god-off{width:100%;min-height:44px;margin-top:8px;border-radius:14px;border:2px solid #FF1A7F;background:transparent;color:#fff;font:800 14px/1 inherit;font-family:inherit;cursor:pointer}
`;
  const esc = (x) => String(x).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const SPEEDS = [1, 1.5, 2, 3];
  function attach(h) {
    if (!document.getElementById("juan-god-css")) { const s = document.createElement("style"); s.id = "juan-god-css"; s.textContent = CSS; document.head.appendChild(s); }
    const ctr = h.el.querySelector(".juan-controls");
    const btn = document.createElement("button"); btn.type = "button"; btn.className = "lot-btn juan-god-btn"; btn.id = "juan-god";
    btn.setAttribute("aria-haspopup", "dialog"); btn.innerHTML = '<span aria-hidden="true">⚡</span><span class="juan-lbl"> God</span>';
    if (ctr) ctr.appendChild(btn);
    const badge = document.createElement("div"); badge.className = "juan-god-badge"; badge.setAttribute("aria-hidden", "true"); h.wrap.appendChild(badge);
    const live = document.createElement("p"); live.className = "sr-only"; live.setAttribute("aria-live", "polite"); h.wrap.appendChild(live);
    let dlg = null;
    function paint() {
      const g = h.get(), extra = [g.fly && "FLY", g.noclip && "NOCLIP", g.speed > 1 && g.speed + "×"].filter(Boolean).join(" · ");
      btn.classList.toggle("on", g.on); btn.setAttribute("aria-pressed", String(g.on)); btn.setAttribute("aria-label", g.on ? "God mode is on (admin): open the panel" : "God mode (admin): open the panel");
      badge.classList.toggle("on", g.on); badge.innerHTML = "⚡ GOD MODE" + (extra ? ` <small>${esc(extra)}</small>` : "");
    }
    function open() {
      if (dlg) dlg.remove();
      const was = h.get().mode === "run"; h.pause();
      const g = h.get(), d = document.createElement("dialog"); d.className = "juan-god"; d.setAttribute("aria-labelledby", "juan-god-t");
      const sw = (k, name, sub) => `<label class="juan-god-sw"><input type="checkbox" data-k="${k}"${g[k] ? " checked" : ""}><span><b>${name}</b><small>${sub}</small></span></label>`;
      d.innerHTML = `<form method="dialog" class="juan-god-card">
        <p class="juan-god-t" id="juan-god-t">⚡ God mode <small>ADMIN</small></p>
        <p class="juan-god-sub">For play-testing the stages and hunting bugs. Only you see this.</p>
        ${sw("on", "Immortal", "No damage, never caught, never worn out")}
        ${sw("fly", "Fly", "Hold Jump to rise, let go to drift down")}
        ${sw("noclip", "Noclip", "Run straight through pallets, tires and cars")}
        <p class="juan-god-h">Speed</p>
        <div class="juan-god-seg" role="group" aria-label="Speed">${SPEEDS.map((v) => `<button type="button" data-speed="${v}" aria-pressed="${g.speed === v}">${v}×</button>`).join("")}</div>
        <p class="juan-god-h">Jump to a level</p>
        <div class="juan-god-lv">${h.levels.map((n, i) => `<button type="button" data-lv="${i + 1}"${g.level === i + 1 ? ' class="cur" aria-current="true"' : ""}><b>${i + 1}</b><span>${esc(n)}</span></button>`).join("")}</div>
        <p class="juan-god-note">🔒 A run with god mode on, or one started from here, never saves a best score and never goes on the Top 10. To play for real: turn it off, then Start over.</p>
        <button type="submit" class="juan-god-done">Done</button>
        ${g.on ? '<button type="button" class="juan-god-off">Turn god mode off</button>' : ""}
      </form>`;
      document.body.appendChild(d); dlg = d;
      const close = (go) => { if (d.open) d.close(); d.remove(); if (dlg === d) dlg = null; paint(); if (go) go(); else if (was) h.resume();
        const jb = h.el.querySelector("#juan-jump"); (jb || btn).focus({ preventScroll: true, focusVisible: false }); };   // the Jump button: Space jumps (on ⚡ it would reopen this)
      const say = (t) => { live.textContent = t; };
      d.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
      d.querySelector("form").addEventListener("submit", (e) => { e.preventDefault(); close(); });
      d.addEventListener("change", (e) => {
        const k = e.target.dataset && e.target.dataset.k; if (!k) return;
        const o = { [k]: e.target.checked }; if (k !== "on" && e.target.checked) o.on = true;   // fly / noclip need god mode on
        h.set(o); const now = h.get();
        d.querySelectorAll("input[data-k]").forEach((i) => { i.checked = !!now[i.dataset.k]; });
        d.querySelectorAll("[data-speed]").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.speed) === now.speed)));
        paint(); say(now.on ? "God mode on" : "God mode off");
      });
      d.addEventListener("click", (e) => {
        const sp = e.target.closest("[data-speed]"), lv = e.target.closest("[data-lv]"), off = e.target.closest(".juan-god-off");
        if (sp) { const v = Number(sp.dataset.speed); h.set({ speed: v, on: v > 1 ? true : h.get().on }); const now = h.get();
          d.querySelectorAll("[data-speed]").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.speed) === now.speed)));
          d.querySelectorAll("input[data-k]").forEach((i) => { i.checked = !!now[i.dataset.k]; }); paint(); }
        else if (lv) close(() => h.level(Number(lv.dataset.lv)));
        else if (off) { h.set({ on: false }); say("God mode off"); close(); }
      });
      d.showModal(); const first = d.querySelector("input[data-k=on]"); if (first) first.focus({ preventScroll: true });
    }
    btn.addEventListener("click", open);
    paint();
    return { open, paint, destroy() { btn.remove(); badge.remove(); live.remove(); if (dlg) dlg.remove(); } };
  }
  root.ChismeJuanGod = { attach };
})(window);
