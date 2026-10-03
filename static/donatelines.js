/* Chisme: the mid-list donate card's lines (v33). It shows on every 5th app open (5, 10, 15 …; localStorage
   "chisme-opens"), each time with a different line, never one of the last 5 shown ("chisme-donate-recent").
   Pure helpers, used by app.js as window.ChismeDonate and loaded in Node by donate_every_tab_test.py. */
(function (root) {
  const OPENS = "chisme-opens", RECENT = "chisme-donate-recent", EVERY = 5, NO_REPEAT = 5;
  const LINES = [   // v49.12: English, with only names in Spanish (Chisme, Tía, metiches)
    "Tía's coffee budget is running low ☕, help a metiche out!",
    "This chisme ain't gonna spill itself. Tip the tea! 🫖",
    "Even the nosy neighbor pays for her soap operas. Donate?",
    "Your donation keeps the rollers rolling 💇‍♀️",
    "Enjoying the chisme? ☕ Donate for more (and better) chisme!",
    "Go on, a few bucks keeps the chisme coming 💅",
    "The metiches have spoken: tip your Tía! 🗣️",
    "Don't act innocent… we saw you reading all that chisme 👀",
    "Pastries ain't free, and neither is good chisme 🥐",
    "Help keep the lights on at chisme HQ (Tía's kitchen table) 💡",
    "Tía wants to know… where's the tip? 🤨",
    "Every donation = one more coffee for the chisme crew ☕",
    "Chisme this good deserves a tip, right? 💸",
    "Donate and Tía will tell everybody you're her favorite 😉",
    "Your tip keeps the phone ringing with fresh chisme ☎️",
    "Tamales for the whole family don't pay for themselves 🫔",
    "Help us upgrade from the flip phone, please 📱",
    "The tea is hot but the wallet is cold 🥶 Help a metiche out!",
    "Tip the chisme like you'd tip the mariachi 🎺",
    "Tía's soap opera subscription won't pay for itself 📺",
    "A couple dollars keeps the chisme free for the whole neighborhood 🌮",
    "Support local chisme, straight from the 210 🤠",
    "Even chisme needs gas money for the truck 🛻",
    "Keep the chisme flowing like the River Walk 🌊",
  ];
  const shouldShow = (opens) => opens > 0 && opens % EVERY === 0;
  // v34: the card is jokey, so it never sits next to a serious story. serious(text, source) → true for crime, death,
  // crashes, fires, missing people … (English + a little Spanish), urgent/breaking titles and NWS warnings.
  const SERIOUS = /\b(di(e|es|ed)|dead(ly)?|deaths?|kill(s|ed|er|ers|ing)?|crash(es|ed)?|shoot(s|er|ers|ing|ings)?|shot|gunfire|stab(s|bed|bing|bings)?|murder(s|ed|er)?|homicides?|manslaughter|missing|abuse[ds]?|fires?|blaze|burned|firefighters?|victims?|fatal(ly|ity|ities)?|arrest(s|ed)?|charged|suspects?|person of interest|assault(s|ed)?|injur(y|ies|ed)|wreck(s|ed)?|overdoses?|drown(s|ed|ing)?|kidnap(ped|ping)?|rape|sexual|sentenced|convicted|trial|amber alert|lockdown|evacuat\w*|muer(e|en|to|ta|tos|te)|asesinad[oa]s?|balacera|desaparecid[oa]s?|accidente fatal)\b/i;
  const NWS = /national weather service|\bnws\b|weather\.gov|weather (impact )?alert|\b(tornado|flood|flash flood|severe thunderstorm|winter storm|ice storm|heat|excessive heat|freeze|hard freeze|hurricane|tropical storm|red flag|high wind|wind|fire weather|dense fog)\s+(warning|watch|advisory|emergency)\b/i;
  function serious(text, source) {
    text = String(text || ""); const nw = root.ChismeNewsOrder;
    return SERIOUS.test(text) || NWS.test(text + " " + (source || "")) || !!(nw && nw.urgent({ title: text }));
  }
  // slot(flags): flags[i] = item i is serious. The card goes after item k (1-based), between item k and item k+1 —
  // about the 5th (the middle of a short list), or else the nearest slot where both neighbors are light (a later slot
  // wins a tie). → k, or 0 when there's no such slot (then it goes at the end, just above the bottom donate card).
  function slot(flags) {
    const n = flags.length; if (n < 2) return 0;
    const k0 = Math.min(5, Math.ceil(n / 2)), ok = (k) => k >= 1 && k < n && !flags[k - 1] && !flags[k];
    for (let d = 0; d < n; d++) for (const k of d ? [k0 + d, k0 - d] : [k0]) if (ok(k)) return k;
    return 0;
  }
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
  const api = { OPENS, RECENT, EVERY, NO_REPEAT, LINES, shouldShow, pick, launch, serious, slot };
  root.ChismeDonate = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
