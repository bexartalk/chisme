/* Chisme: the mid-list donate card's lines (v33). It shows on every 5th app open (5, 10, 15 …; localStorage
   "chisme-opens"), each time with a different line, never one of the last 5 shown ("chisme-donate-recent").
   Pure helpers, used by app.js as window.ChismeDonate and loaded in Node by donate_every_tab_test.py. */
(function (root) {
  const OPENS = "chisme-opens", RECENT = "chisme-donate-recent", EVERY = 5, NO_REPEAT = 5;
  const LINES = [
    "Tía's cafecito budget is running low ☕, help a chismosa out!",
    "This chisme ain't gonna spill itself. Tip the tea! 🫖",
    "Even the vecina pays for her novelas. Donate?",
    "Your donation keeps the rollers rolling 💇‍♀️",
    "Enjoying the chisme? ☕ Donate for more (and better) chisme!",
    "Ándale, a few bucks keeps the chisme coming 💅",
    "The comadres have spoken: tip your chismosa! 🗣️",
    "No te hagas… we saw you reading all that chisme 👀",
    "Pan dulce ain't free, and neither is good chisme 🥐",
    "Help keep the lights on at chisme HQ (Tía's kitchen table) 💡",
    "Tía wants to know… ¿y la propina? 🤨",
    "Every donation = one more cafecito for the chisme crew ☕",
    "Chisme this good deserves a tip, ¿qué no? 💸",
    "Donate and Tía will tell everybody you're her favorite 😉",
    "Your tip keeps the teléfono ringing with fresh chisme ☎️",
    "Tamales for the whole familia don't pay for themselves 🫔",
    "Help us upgrade from the flip phone, porfa 📱",
    "Ay, the tea is hot but the wallet is cold 🥶 Help a chismoso out!",
    "Tip the chisme like you'd tip the mariachi 🎺",
    "Tía's novela subscription won't pay for itself 📺",
    "¡Órale! A couple dollars keeps the chisme free for the whole barrio 🌮",
    "Support local chisme, straight from the 210 🤠",
    "Even chisme needs gas money for the troca 🛻",
    "Keep the chisme flowing like the River Walk 🌊",
  ];
  const shouldShow = (opens) => opens > 0 && opens % EVERY === 0;
  // a random line that isn't one of the last NO_REPEAT shown; returns [index, newRecent]
  function pick(recent, rand) {
    recent = (recent || []).filter((i) => Number.isInteger(i) && i >= 0 && i < LINES.length).slice(-NO_REPEAT);
    const ok = LINES.map((_, i) => i).filter((i) => !recent.includes(i));
    const i = ok[Math.floor((rand || Math.random)() * ok.length)];
    return [i, recent.concat(i).slice(-NO_REPEAT)];
  }
  const get = (s, k, d) => { try { const v = JSON.parse(s.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
  // Count this open; if it's a 5th one, choose (and remember) its line. → { opens, line | null }
  function launch(store) {
    store = store || root.localStorage;
    const opens = (+get(store, OPENS, 0) || 0) + 1;
    try { store.setItem(OPENS, String(opens)); } catch (e) {}
    if (!shouldShow(opens)) return { opens, line: null };
    const [i, recent] = pick(get(store, RECENT, []));
    try { store.setItem(RECENT, JSON.stringify(recent)); } catch (e) {}
    return { opens, line: LINES[i], index: i };
  }
  const api = { OPENS, RECENT, EVERY, NO_REPEAT, LINES, shouldShow, pick, launch };
  root.ChismeDonate = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
