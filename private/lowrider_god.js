// v49.27: served only by /stats/lowrider/god.js after the owner session check.
(function (root) {
  "use strict";
  root.ChismeLowriderGod = { attach(h, enabled) {
    const box = document.createElement("div"), badge = document.createElement("button"), panel = document.createElement("div");
    box.className = "lr-god"; box.style.cssText = "position:absolute;left:10px;top:86px;z-index:40;color:#fff;font:700 13px sans-serif";
    badge.type = "button"; badge.className = "lr-god-badge"; badge.style.cssText = "background:#7B2CBF;color:#fff;border:2px solid #FF1A7F;border-radius:8px;padding:5px 10px";
    panel.style.cssText = "display:none;background:#20122e;border:2px solid #FF1A7F;padding:12px;border-radius:10px;max-width:290px";
    panel.innerHTML = '<label><input data-g="on" type="checkbox"> God mode</label><br><label><input data-g="invincible" type="checkbox" checked> Invincible</label><br><label><input data-g="gas" type="checkbox" checked> Infinite gas</label><p>Speed <select data-g="speed"><option>0.5</option><option selected>1</option><option>2</option><option>3</option></select>×</p><p>Skip to: <button data-s="chase">chase</button> <button data-s="party">party ending</button> <button data-s="lap">next lap</button></p>';
    function paint() { const on = h.get().on; badge.textContent = on ? "GOD" : "Owner"; badge.dataset.on = on ? "1" : "0"; panel.querySelector('[data-g="on"]').checked = !!on; }
    h.set({ on: !!enabled, invincible: true, gas: true, speed: 1 }); paint();
    badge.onclick = () => { panel.style.display = panel.style.display === "none" ? "block" : "none"; };
    panel.onchange = (e) => { const k = e.target.dataset.g; if (k) { h.set({ [k]: k === "speed" ? +e.target.value : e.target.checked }); paint(); } };
    panel.onclick = async (e) => { const to = e.target.dataset.s; if (to) { h.set({ on: true }); await h.skip(to); paint(); } };
    box.append(badge, panel); h.el.appendChild(box);
    return { destroy() { box.remove(); } };
  } };
})(window);
