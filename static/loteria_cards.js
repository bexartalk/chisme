/* Chisme · Lotería: the 54 traditional card names and their folk verses (traditional sayings), with ORIGINAL art drawn
   here in SVG for Chisme (Fiesta colors: turquoise, pink, orange, black, silver). The art is not copied or traced from any published deck.
   #26: the traditional deck's "El Negrito" is a racial caricature, so this deck uses "El Chocolate" (a folk rhyme) instead.
   #38 "El Apache" keeps the traditional name and verse, but the art is only the huaraches from the verse, not a person. */
(function (root) {
  "use strict";
  const K = "#111", W = "#fff", T = "#00b8b0", T2 = "#3ee8eb", P = "#ff3d8b", P2 = "#c2185b", O = "#ff8a00", O2 = "#c95f00", S = "#b9c0c7", S2 = "#7c858f";
  const G = "#2f9e57", G2 = "#6cc26a", BR = "#8a5a3b", BR2 = "#5e3a22", TC = "#c8643b", SK = "#c98a5e", SK2 = "#a86b42", R = "#e0243a", NV = "#1d2a4d", CR = "#f2efed";
  const L = `stroke="${K}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"`;   // the outline every drawing uses
  const eyes = (x1, x2, y, r = 1.8) => `<circle cx="${x1}" cy="${y}" r="${r}" fill="${K}"/><circle cx="${x2}" cy="${y}" r="${r}" fill="${K}"/>`;
  const smile = (x, y, w = 5) => `<path d="M${x - w} ${y} Q${x} ${y + w * 0.9} ${x + w} ${y}" fill="none" ${L}/>`;
  const ART = {
    1: `<g ${L}><path d="M32 62C14 54 10 36 16 22c6 14 12 18 18 22" fill="${T}"/><path d="M30 68C12 68 6 52 8 42c8 12 16 14 24 16" fill="${P}"/><path d="M34 76C22 72 18 62 20 54c6 8 10 10 16 12" fill="${T2}"/>
      <path d="M30 78C20 60 24 42 42 42h10c6-10 6-18 12-22 6-4 14 0 14 8 0 8-6 12-8 20 10 10 6 30-12 34z" fill="${O}"/><path d="M42 58c8-6 20-2 20 8-8 4-16 2-20-8z" fill="${O2}"/>
      <path d="M62 20c0-8 6-8 6-2 2-8 8-6 6 2" fill="${P}"/><path d="M78 26l10 4-10 3z" fill="${O2}"/><path d="M76 34c2 6-4 8-4 2" fill="${P}"/>
      <path d="M48 82l-2 10M60 82l2 10M40 92h12M56 92h12" fill="none" stroke="${O2}"/></g><circle cx="71" cy="26" r="2.2" fill="${K}"/>`,
    2: `<g ${L}><path d="M66 70c14 2 20-8 16-16" fill="none"/><path d="M80 50l6 2-4 5z" fill="${P}"/><path d="M34 90l4-30h24l4 30z" fill="${P}"/>
      <circle cx="50" cy="40" r="17" fill="${P}"/><path d="M38 28l-4-14 10 8zM62 28l4-14-10 8z" fill="${K}"/>
      <path d="M22 18v70M16 18l6 8 6-8M22 12v10" fill="none" stroke="${S2}"/></g><circle cx="44" cy="38" r="4" fill="${W}"/><circle cx="56" cy="38" r="4" fill="${W}"/>${eyes(45, 55, 39, 1.8)}
      <path d="M42 47q8 7 16 0" fill="${W}" ${L}/>`,
    3: `<g ${L}><path d="M50 44L26 92h48z" fill="${T}"/><path d="M30 84h40" fill="none" stroke="${P}" stroke-width="4"/><path d="M40 46h20l-4 14H44z" fill="${P}"/>
      <circle cx="50" cy="30" r="12" fill="${SK}"/><path d="M38 28c0-12 24-12 24 0-4-6-20-6-24 0z" fill="${K}"/><circle cx="50" cy="14" r="6" fill="${K}"/>
      <path d="M66 60l14-12 4 10z" fill="${O}"/></g>${eyes(46, 54, 30, 1.5)}${smile(50, 35, 3)}<circle cx="41" cy="44" r="0" />`,
    4: `<g ${L}><path d="M38 20h24v-8H38zM32 20h36v5H32z" fill="${K}"/><circle cx="50" cy="36" r="11" fill="${SK}"/><path d="M36 92l2-36c4-6 20-6 24 0l2 36z" fill="${K}"/>
      <path d="M46 50h8l-4 22z" fill="${W}"/><path d="M44 52l6-3 6 3-6 3z" fill="${P}"/><path d="M72 50v42M72 50c0-6 8-6 8 0" fill="none" stroke="${S2}" stroke-width="3.2"/></g>
      ${eyes(46, 54, 34, 1.5)}<path d="M43 40q7-4 14 0" fill="none" ${L}/>`,
    5: `<g ${L}><path d="M14 50C14 26 86 26 86 50c-6-6-12-6-18 0-6-6-12-6-18 0-6-6-12-6-18 0-6-6-12-6-18 0z" fill="${P}"/>
      <path d="M32 50c0-18 8-24 18-24s18 6 18 24c-6-6-12-6-18 0-6-6-12-6-18 0z" fill="${T}"/><path d="M50 26v56c0 8-12 8-12 0" fill="none"/></g>
      <g fill="${T2}"><path d="M20 66q3 5 0 7-3-2 0-7zM80 62q3 5 0 7-3-2 0-7zM70 80q3 5 0 7-3-2 0-7z"/></g>`,
    6: `<g ${L}><path d="M46 56c-10 10-8 22 4 28 10 4 18 8 22 12-2-6-10-10-14-14 10 0 16-4 18-8-8 2-14 2-18-2 4-6 2-12-2-16z" fill="${T}"/>
      <path d="M36 30c-6 10-8 26-2 36 2-10 4-18 4-26z" fill="${K}"/><circle cx="46" cy="30" r="11" fill="${SK}"/><path d="M34 30c0-14 24-16 24 0-6-8-18-6-24 0z" fill="${K}"/>
      <path d="M38 46c4-4 16-4 18 0v12H38z" fill="${SK}"/><circle cx="42" cy="50" r="4" fill="${P}"/><circle cx="52" cy="50" r="4" fill="${P}"/></g>
      ${eyes(42, 50, 30, 1.4)}${smile(46, 35, 3)}<g fill="none" stroke="${W}" stroke-width="1.6" opacity=".8"><path d="M52 68q4 3 8 0M56 76q4 3 8 0"/></g>`,
    7: `<g ${L} fill="${O}"><path d="M28 94L44 8h8L36 94zM58 94L74 8h8L66 94z"/></g><g stroke="${BR2}" stroke-width="5" stroke-linecap="round"><path d="M36 80h26M39 64h26M42 48h26M45 32h26M48 18h24"/></g>`,
    8: `<g ${L}><path d="M42 8h16v16c0 6 12 10 12 22v42c0 4-4 6-8 6H38c-4 0-8-2-8-6V46c0-12 12-16 12-22z" fill="${T}"/><path d="M42 4h16v8H42z" fill="${BR}"/>
      <path d="M30 54h40v22H30z" fill="${P}"/></g><path d="M36 30c-2 6-2 50 0 56" stroke="${W}" stroke-width="3" fill="none" opacity=".6"/><g fill="${W}"><circle cx="50" cy="65" r="4"/><circle cx="41" cy="65" r="2.2"/><circle cx="59" cy="65" r="2.2"/></g>`,
    9: `<g ${L}><path d="M28 14h44c8 26 8 52 0 78H28c-8-26-8-52 0-78z" fill="${BR}"/><path d="M26 30h48M24 76h52" fill="none" stroke="${S2}" stroke-width="6"/>
      <path d="M40 14c-4 26-4 52 0 78M60 14c4 26 4 52 0 78" fill="none" stroke="${BR2}"/></g><ellipse cx="50" cy="14" rx="22" ry="4" fill="${BR2}" ${L}/>`,
    10: `<g ${L}><path d="M44 94c4-16 4-30 0-46h12c-4 16-4 30 0 46z" fill="${BR}"/><circle cx="50" cy="36" r="26" fill="${G}"/><circle cx="30" cy="48" r="14" fill="${G}"/><circle cx="70" cy="48" r="14" fill="${G}"/></g>
      <g fill="${G2}"><circle cx="42" cy="28" r="7"/><circle cx="62" cy="36" r="6"/><circle cx="30" cy="46" r="5"/></g><g fill="${P}"><circle cx="54" cy="22" r="3"/><circle cx="70" cy="50" r="3"/><circle cx="36" cy="54" r="3"/></g>`,
    11: `<g ${L}><circle cx="38" cy="44" r="26" fill="#b8d88f"/><path d="M40 90c4-18 22-32 44-32 4 0 6 2 6 4-2 18-20 30-44 30-4 0-6-1-6-2z" fill="#9cc36f"/><path d="M46 86c4-14 18-24 36-24" fill="none" stroke="${O}" stroke-width="10"/></g>
      <g fill="none" stroke="#7a9c5a" stroke-width="2"><path d="M18 34q20 10 40 0M16 48q22 10 44 0M24 22q12 6 26 0M22 60q16 6 32 0"/></g><g fill="${CR}" stroke="${K}" stroke-width="1"><ellipse cx="58" cy="74" rx="2.4" ry="1.3"/><ellipse cx="66" cy="70" rx="2.4" ry="1.3"/><ellipse cx="74" cy="67" rx="2.4" ry="1.3"/></g>`,
    12: `<g ${L}><path d="M20 30c0-6 60-6 60 0 0 4-10 6-30 6s-30-2-30-6z" fill="${O}"/><path d="M36 30c0-14 28-14 28 0z" fill="${O}"/><circle cx="50" cy="42" r="10" fill="${SK}"/>
      <path d="M30 92l4-36c8-6 24-6 32 0l4 36z" fill="${T}"/><path d="M32 66h36M31 76h38M30 86h40" fill="none" stroke="${P}" stroke-width="4"/>
      <path d="M68 58l16-18" fill="none" stroke="${S2}" stroke-width="4"/><path d="M84 40l4-6-6 2z" fill="${S}"/></g>${eyes(46, 54, 41, 1.5)}<path d="M44 47h12" ${L}/>`,
    13: `<g ${L}><path d="M18 64c0-30 16-46 34-46s30 16 30 46z" fill="${P}"/><path d="M14 64c6-6 10 6 16 0s10 6 16 0 10 6 16 0 10 6 16 0 6 6 8 0v8H14z" fill="${W}"/>
      <path d="M24 72l-6 20M76 72l6 20" fill="none" stroke="${T}" stroke-width="4"/><circle cx="50" cy="42" r="8" fill="${T}"/></g><g fill="${W}" opacity=".85"><circle cx="34" cy="40" r="3"/><circle cx="66" cy="40" r="3"/><circle cx="50" cy="26" r="3"/></g>`,
    14: `<g ${L}><path d="M30 94l6-50c4-10 24-10 28 0l6 50z" fill="${K}"/><path d="M76 10v86" fill="none" stroke="${BR}" stroke-width="4"/><path d="M76 12c-20-4-34 4-40 16 12-6 26-8 40-6z" fill="${S}"/>
      <circle cx="50" cy="32" r="13" fill="${W}"/></g><g fill="${K}"><circle cx="45" cy="30" r="3.4"/><circle cx="55" cy="30" r="3.4"/><path d="M48 37h4l-2 3z"/></g><path d="M44 42h12M46 40v4M50 40v4M54 40v4" stroke="${K}" stroke-width="1.4"/>`,
    15: `<g ${L}><path d="M50 22c-8 0-10 10-10 18 0 8-12 14-12 30 0 14 10 22 22 22s22-8 22-22c0-16-12-22-12-30 0-8-2-18-10-18z" fill="${G2}"/><path d="M50 22c0-6 2-12 6-14" fill="none" stroke="${BR}"/>
      <path d="M54 16c8-8 18-6 20-2-8 6-14 6-20 2z" fill="${G}"/></g><path d="M38 60c-2 10 2 20 8 24" stroke="${W}" stroke-width="3" fill="none" opacity=".6"/>`,
    16: `<g ${L}><path d="M20 10v86" fill="none" stroke="${S2}" stroke-width="4"/><path d="M22 14h22v44H22z" fill="#1f8a4c"/><path d="M44 14h22v44H44z" fill="${W}"/><path d="M66 14h22v44H66z" fill="${R}"/></g>
      <circle cx="55" cy="36" r="6" fill="${BR}" stroke="${K}" stroke-width="1.5"/><path d="M49 42q6 5 12 0" stroke="${G}" stroke-width="2" fill="none"/><circle cx="20" cy="8" r="3" fill="${S}" ${L}/>`,
    17: `<g ${L}><path d="M58 8h10v34H58z" fill="${BR2}"/><path d="M40 40c-18 0-24 20-18 34 6 16 30 22 44 12 14-10 12-36-4-44-8-4-16-4-22-2z" fill="${O}"/><circle cx="48" cy="62" r="7" fill="${K}"/>
      <path d="M40 80h22" fill="none" stroke="${BR2}" stroke-width="4"/></g><g stroke="${W}" stroke-width="1"><path d="M60 10v70M63 10v70M66 10v70"/></g><g fill="${S}"><circle cx="58" cy="12" r="2"/><circle cx="68" cy="12" r="2"/><circle cx="58" cy="20" r="2"/><circle cx="68" cy="20" r="2"/></g>`,
    18: `<g ${L}><path d="M47 4h6v30h-6z" fill="${BR2}"/><circle cx="50" cy="6" r="4" fill="${BR2}"/><path d="M50 30c-12 0-16 8-12 16-10 4-12 18-6 28 6 10 30 10 36 0 6-10 4-24-6-28 4-8 0-16-12-16z" fill="${TC}"/>
      <path d="M50 88v8" fill="none" stroke="${S2}" stroke-width="3"/><path d="M14 30l66 56" fill="none" stroke="${BR}" stroke-width="3"/></g><path d="M42 54c2 4 2 10-1 14M58 54c-2 4-2 10 1 14" stroke="${K}" stroke-width="2" fill="none"/>
      <g stroke="${CR}" stroke-width=".8"><path d="M48.5 34v48M51.5 34v48"/></g>`,
    19: `<path d="M8 86q10-4 20 0t20 0 20 0 24 0v14H8z" fill="${T}"/><g ${L}><path d="M50 58c-14 0-20-10-14-18 6-6 18-2 22 4 6 10 2 14-8 14z" fill="${W}"/>
      <path d="M52 44c2-12-4-20 0-28 4-6 12-6 14 0" fill="none" stroke="${W}" stroke-width="6"/><path d="M52 44c2-12-4-20 0-28 4-6 12-6 14 0" fill="none"/><path d="M66 16l18 2-18 4z" fill="${O}"/>
      <path d="M46 58l-4 30M54 58l2 30" fill="none" stroke="${O2}"/><path d="M36 42c-8 2-14 8-16 14 8-2 14-4 18-8z" fill="${S}"/></g><circle cx="63" cy="15" r="1.6" fill="${K}"/>`,
    20: `<g ${L}><path d="M10 72c20-4 60-4 84 2" fill="none" stroke="${BR}" stroke-width="4"/><path d="M76 72c4-4 10-4 12 2" fill="${G2}"/><path d="M30 52c0-14 12-22 26-18 10 2 14 12 12 20-2 12-14 18-26 16-8-2-12-8-12-18z" fill="${T}"/>
      <path d="M34 58c6 8 20 10 30 0-6 12-24 12-30 0z" fill="${P}"/><circle cx="62" cy="38" r="8" fill="${T}"/><path d="M70 38l10 2-10 4z" fill="${O}"/><path d="M30 52L12 44l4 12z" fill="${T2}"/>
      <path d="M44 70l-2 6M52 70l0 6" fill="none" stroke="${O2}"/></g><circle cx="64" cy="36" r="1.8" fill="${K}"/><path d="M40 46q8-6 16 2" stroke="${K}" stroke-width="2" fill="none"/>`,
    21: `<g ${L}><path d="M34 94V62c-6-4-12-14-14-22-2-6 6-8 8-2l6 14V20c0-6 8-6 8 0v24-30c0-6 8-6 8 0v30-26c0-6 8-6 8 0v28-20c0-6 8-6 8 0v40c0 14-6 22-14 26v2z" fill="${SK}"/></g>
      <path d="M42 64q8 4 16-2M44 56q6 3 12 0" stroke="${SK2}" stroke-width="2" fill="none"/><path d="M34 90h32" stroke="${T}" stroke-width="6"/>`,
    22: `<g ${L}><path d="M34 8h26v52c0 6 6 10 16 12 8 2 12 8 12 14v6H26c-4 0-6-4-4-8l4-10z" fill="${BR}"/><path d="M26 92h14v-6H24z" fill="${BR2}"/><path d="M32 8h30v8H32z" fill="${BR2}"/></g>
      <g fill="none" stroke="${P}" stroke-width="2.4"><path d="M40 24c4 6 10 6 14 0M40 36c4 6 10 6 14 0M44 48q4 6 8 0"/></g><g fill="${S}" ${L}><circle cx="18" cy="86" r="5"/><path d="M22 86h6" /></g>`,
    23: `<circle cx="50" cy="50" r="42" fill="${NV}"/><g ${L}><path d="M58 14c-20 0-34 16-34 36s14 36 34 36c-14-6-22-20-22-36s8-30 22-36z" fill="${S}"/></g><circle cx="38" cy="44" r="2" fill="${K}"/><path d="M34 56q4 3 8 0" stroke="${K}" stroke-width="2" fill="none"/>
      <g fill="${W}"><path d="M70 30l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/><circle cx="76" cy="58" r="2"/><circle cx="64" cy="72" r="1.6"/><circle cx="72" cy="46" r="1.2"/></g>`,
    24: `<g ${L}><path d="M18 62c20-2 48-2 70 2" fill="none" stroke="${BR}" stroke-width="4"/><path d="M44 62c-14 8-18 22-16 32 8-4 12-14 16-22z" fill="${T}"/><path d="M40 62c-8-10-8-30 4-40 10-8 24-4 26 8 2 10-2 20-8 28-6 6-14 8-22 4z" fill="${G}"/>
      <path d="M46 40c0 10 4 18 12 20-4 2-10 2-14-2z" fill="${P}"/><path d="M66 26c8 0 10 8 6 14-2-4-6-6-10-6z" fill="${S}"/><path d="M52 62l-2 6M58 62l0 6" fill="none" stroke="${O2}"/></g><circle cx="60" cy="26" r="2.2" fill="${K}"/>`,
    25: `<g transform="rotate(-10 50 50)"><g ${L}><path d="M34 92l4-36c6-6 20-6 26 0l4 36z" fill="${T}"/><circle cx="50" cy="40" r="12" fill="${SK}"/><path d="M36 34c2-10 26-12 28 0-8-4-20-4-28 0z" fill="${K}"/>
      <path d="M64 60l12 14" fill="none" stroke="${SK}" stroke-width="5"/><path d="M76 64h8v20h-8z" fill="${G}"/><path d="M78 58h4v6h-4z" fill="${BR}"/></g>
      <circle cx="52" cy="44" r="3.4" fill="${R}"/><path d="M43 38l4 2M53 38l4-2" stroke="${K}" stroke-width="2"/><path d="M45 50q5 3 10 0" stroke="${K}" stroke-width="2" fill="none"/></g>
      <g fill="none" stroke="${T}" stroke-width="2"><circle cx="24" cy="26" r="4"/><circle cx="16" cy="16" r="2.5"/><circle cx="28" cy="12" r="1.8"/></g>`,
    26: `<g ${L}><path d="M26 44h44l-4 44H30z" fill="${TC}"/><path d="M70 52c10 0 12 18 0 20" fill="none" stroke="${TC}" stroke-width="6"/><path d="M70 52c10 0 12 18 0 20" fill="none"/>
      <ellipse cx="48" cy="44" rx="22" ry="5" fill="${BR2}"/><path d="M56 6l-6 36" fill="none" stroke="${BR}" stroke-width="4"/><ellipse cx="52" cy="22" rx="5" ry="7" fill="${BR}"/></g>
      <g fill="none" stroke="${W}" stroke-width="2.2"><path d="M34 64h28M32 74h30"/></g><g fill="${P}"><circle cx="38" cy="58" r="2"/><circle cx="48" cy="58" r="2"/><circle cx="58" cy="58" r="2"/></g>
      <g fill="none" stroke="${S}" stroke-width="2.4"><path d="M34 36q-4-6 0-12M42 36q-4-6 0-12"/></g>`,
    27: `<g ${L}><path d="M50 88C20 66 14 50 14 38c0-14 10-22 20-22 8 0 14 6 16 12 2-6 8-12 16-12 10 0 20 8 20 22 0 12-6 28-36 50z" fill="${P}"/><path d="M8 78L90 18" fill="none" stroke="${BR}" stroke-width="3.5"/>
      <path d="M90 18l-10 2 6 6z" fill="${S}"/><path d="M8 78l4-8 4 4zM14 80l0-8 5 3z" fill="${T}"/></g><path d="M28 32c-4 4-4 10-2 14" stroke="${W}" stroke-width="3.4" fill="none" opacity=".8"/>`,
    28: `<g ${L}><path d="M8 40a42 42 0 0 0 84 0z" fill="${G}"/><path d="M14 40a36 36 0 0 0 72 0z" fill="${W}"/><path d="M18 40a32 32 0 0 0 64 0z" fill="${P}"/></g>
      <g fill="${K}"><ellipse cx="34" cy="50" rx="2" ry="3"/><ellipse cx="50" cy="56" rx="2" ry="3"/><ellipse cx="66" cy="50" rx="2" ry="3"/><ellipse cx="42" cy="62" rx="2" ry="3"/><ellipse cx="58" cy="64" rx="2" ry="3"/><ellipse cx="50" cy="46" rx="2" ry="3"/></g>`,
    29: `<g ${L}><path d="M20 36v38c0 8 60 8 60 0V36z" fill="${P}"/><ellipse cx="50" cy="36" rx="30" ry="9" fill="${CR}"/><path d="M20 72c0 8 60 8 60 0" fill="none" stroke="${T}" stroke-width="5"/>
      <path d="M20 40l12 30 12-30 12 30 12-30 12 30" fill="none" stroke="${W}" stroke-width="2.4"/><path d="M34 26L16 6M66 26L84 6" fill="none" stroke="${BR}" stroke-width="4"/></g><g fill="${W}" ${L}><circle cx="16" cy="6" r="4"/><circle cx="84" cy="6" r="4"/></g>`,
    30: `<g ${L}><path d="M70 30c10 10 10 30-4 42-12 10-32 12-42 4 8-2 16-6 20-12-8 4-16 2-18-4 10 0 20-4 26-12-6 2-10 0-12-4 10-2 20-10 30-14z" fill="${O}"/>
      <path d="M24 76c-6 4-10 10-8 16 6-2 10-6 12-12z" fill="${P}"/><path d="M70 30c6-10 16-14 24-12M68 28c2-10 8-18 18-22" fill="none" stroke="${P2}" stroke-width="2"/></g>
      <g fill="none" stroke="${O2}" stroke-width="2"><path d="M60 38q4 8 0 16M50 50q4 8-2 14M40 58q4 6-2 12"/></g><circle cx="68" cy="36" r="2" fill="${K}"/>`,
    31: `<g ${L}><path d="M14 88L84 18M22 94L90 30M10 76L78 10" fill="none" stroke="${BR}" stroke-width="3.5"/><path d="M84 18l6-10-10 4zM90 30l8-8-10 2zM78 10l4-8-8 4z" fill="${S}"/>
      <path d="M14 88l-8 2 4-10 6 2zM22 94l-10 2 6-8 6 2zM10 76l-8 0 6-8 4 4z" fill="${P}"/><path d="M18 84l-4-10M26 90l-4-10M14 72l-4-8" fill="none" stroke="${T}" stroke-width="3"/></g>`,
    32: `<g ${L}><path d="M18 26c0-6 64-6 64 0 0 4-12 6-32 6s-32-2-32-6z" fill="${K}"/><path d="M36 26c0-14 28-14 28 0z" fill="${K}"/><circle cx="50" cy="40" r="11" fill="${SK}"/>
      <path d="M32 94l4-40c8-6 20-6 28 0l4 40z" fill="${K}"/><path d="M54 48h24l6-6v16l-6-6H54z" fill="${O}"/></g><g fill="${S}"><circle cx="40" cy="66" r="2"/><circle cx="40" cy="76" r="2"/><circle cx="40" cy="86" r="2"/><circle cx="60" cy="66" r="2"/><circle cx="60" cy="76" r="2"/><circle cx="60" cy="86" r="2"/></g>
      ${eyes(46, 54, 38, 1.5)}<path d="M44 44q6-3 12 0" stroke="${K}" stroke-width="2.4" fill="none"/>`,
    33: `<g fill="none" stroke="${S}" stroke-width="1.4"><path d="M50 4v92M4 50h92M16 16l68 68M84 16L16 84"/><circle cx="50" cy="50" r="14"/><circle cx="50" cy="50" r="28"/><circle cx="50" cy="50" r="42"/></g>
      <g ${L} fill="none"><path d="M44 52l-18-10-6 8M44 56l-20 0-4 10M46 60l-14 10 0 10M48 62l-6 16M56 52l18-10 6 8M56 56l20 0 4 10M54 60l14 10 0 10M52 62l6 16"/></g>
      <circle cx="50" cy="56" r="10" fill="${K}"/><circle cx="50" cy="44" r="6" fill="${K}"/><circle cx="47" cy="43" r="1.5" fill="${P}"/><circle cx="53" cy="43" r="1.5" fill="${P}"/>`,
    34: `<g ${L}><path d="M40 6h20v22H40z" fill="${K}"/><path d="M58 6c6-6 10 4 4 8" fill="${P}"/><circle cx="50" cy="36" r="10" fill="${SK}"/><path d="M36 94l2-44c4-4 20-4 24 0l2 44z" fill="${T}"/>
      <path d="M38 54l24 24M62 54L38 78" fill="none" stroke="${W}" stroke-width="3"/><path d="M36 94h12M52 94h12" fill="none" stroke="${K}" stroke-width="5"/><path d="M64 56l14-12 2 8" fill="none" stroke="${SK}" stroke-width="5"/></g>
      ${eyes(46, 54, 35, 1.5)}<path d="M46 41h8" stroke="${K}" stroke-width="2"/><g fill="${O}"><circle cx="50" cy="60" r="2"/><circle cx="50" cy="70" r="2"/></g>`,
    35: `<g ${L}><path d="M50 6l12 28 30 2-24 20 8 30-26-16-26 16 8-30-24-20 30-2z" fill="${O}"/><path d="M50 28l5 12 13 1-10 8 3 13-11-7-11 7 3-13-10-8 13-1z" fill="${W}"/></g>
      <g fill="${T2}"><path d="M84 12l2 4 4 2-4 2-2 4-2-4-4-2 4-2z"/><path d="M14 80l2 4 4 2-4 2-2 4-2-4-4-2 4-2z"/></g>`,
    36: `<g ${L}><path d="M16 40h68c0 26-14 44-34 44S16 66 16 40z" fill="${TC}"/><path d="M8 42c0-6 8-6 8-2M92 42c0-6-8-6-8-2" fill="none" stroke="${TC}" stroke-width="6"/><path d="M8 42c0-6 8-6 8-2M92 42c0-6-8-6-8-2" fill="none"/>
      <ellipse cx="50" cy="40" rx="34" ry="7" fill="${BR2}"/></g><path d="M26 54c2 12 10 20 20 22" stroke="${O}" stroke-width="3.4" fill="none" opacity=".9"/>
      <g fill="none" stroke="${S}" stroke-width="2.6"><path d="M36 30q-6-8 0-16M50 30q-6-8 0-18M64 30q-6-8 0-16"/></g>`,
    37: `<g ${L}><path d="M28 94h44M50 84v10M24 50a26 26 0 0 0 52 0" fill="none" stroke="${S2}" stroke-width="4"/><circle cx="50" cy="48" r="26" fill="${T}"/></g>
      <g fill="${G2}" stroke="${K}" stroke-width="1.6"><path d="M34 32c6-4 14-2 14 4s-8 6-8 12-8 6-10 0 0-12 4-16z"/><path d="M56 42c6 0 12 4 10 12s-10 10-14 4 0-16 4-16z"/><path d="M58 26c4-2 8 0 8 4-4 2-8 0-8-4z"/></g>
      <path d="M26 46h48M30 34q20 6 40 0M30 62q20-6 40 0" stroke="${W}" stroke-width="1" fill="none" opacity=".6"/>`,
    38: `<g ${L}><path d="M30 12c10 0 14 14 14 38s-4 40-14 40-14-16-14-40 4-38 14-38z" fill="${BR}"/><path d="M70 12c10 0 14 14 14 38s-4 40-14 40-14-16-14-40 4-38 14-38z" fill="${BR}"/></g>
      <g fill="none" stroke="${O}" stroke-width="3.4"><path d="M18 30l24 10M18 40l24-10M17 50l26 8M17 58l26-8M58 30l24 10M58 40l24-10M57 50l26 8M57 58l26-8"/></g><g fill="none" stroke="${K}" stroke-width="1.6"><path d="M18 30l24 10M18 40l24-10M58 30l24 10M58 40l24-10"/></g>
      <g fill="${T}" stroke="${K}" stroke-width="1.6"><circle cx="30" cy="22" r="3"/><circle cx="70" cy="22" r="3"/></g>`,
    39: `<g ${L} fill="${G}"><ellipse cx="50" cy="72" rx="16" ry="22"/><ellipse cx="30" cy="42" rx="12" ry="17" transform="rotate(-24 30 42)"/><ellipse cx="68" cy="36" rx="12" ry="17" transform="rotate(20 68 36)"/></g>
      <g fill="${P}" ${L}><ellipse cx="24" cy="22" rx="5" ry="6"/><ellipse cx="62" cy="16" rx="5" ry="6"/><ellipse cx="78" cy="20" rx="5" ry="6"/></g><g fill="${W}"><circle cx="46" cy="64" r="1.4"/><circle cx="56" cy="74" r="1.4"/><circle cx="46" cy="84" r="1.4"/><circle cx="28" cy="40" r="1.4"/><circle cx="34" cy="50" r="1.4"/><circle cx="66" cy="34" r="1.4"/><circle cx="72" cy="44" r="1.4"/></g>`,
    40: `<g ${L}><path d="M58 66c10 4 20 0 24-10 4-10 0-22-10-26-8-4-14 2-12 8" fill="none" stroke="${O2}" stroke-width="7"/><path d="M58 66c10 4 20 0 24-10 4-10 0-22-10-26-8-4-14 2-12 8" fill="none"/>
      <path d="M58 38l-2-8 6 4z" fill="${K}"/><ellipse cx="44" cy="66" rx="16" ry="10" fill="${O2}"/><path d="M34 60l-8-10M30 64l-12-4M30 70l-12 4M34 74l-8 10M50 76l2 12M56 74l8 10" fill="none"/>
      <path d="M30 62c-8-6-14-14-12-22M30 70c-10 0-18 6-20 14" fill="none"/><path d="M14 34c2-6 10-6 10 0l-4 6c-4 0-6-2-6-6z" fill="${O2}"/><path d="M6 82c0-6 8-8 10-2l-2 6c-4 0-8-1-8-4z" fill="${O2}"/></g>
      <circle cx="30" cy="63" r="1.8" fill="${K}"/><circle cx="30" cy="69" r="1.8" fill="${K}"/><path d="M46 57v18M40 58v16" stroke="${K}" stroke-width="1.6"/>`,
    41: `<g ${L}><path d="M50 50v44" fill="none" stroke="${G}" stroke-width="4"/><path d="M50 72c-10-8-20-6-24 0 8 4 16 4 24 0zM50 64c10-8 20-6 24 0-8 4-16 4-24 0z" fill="${G2}"/>
      <circle cx="50" cy="32" r="22" fill="${P}"/><path d="M50 22c8 0 12 6 10 12-2 6-10 8-14 4-4-4 0-10 4-8" fill="none" stroke="${P2}" stroke-width="2.4"/><path d="M32 30c4 10 12 16 24 14M36 18c8-6 22-4 28 6" fill="none" stroke="${P2}" stroke-width="2.4"/></g>
      <path d="M50 84l-4-2M50 80l4-2" stroke="${K}" stroke-width="2"/>`,
    42: `<g ${L}><path d="M50 10c-20 0-32 14-32 32 0 12 6 20 14 24v14h36V66c8-4 14-12 14-24 0-18-12-32-32-32z" fill="${W}"/></g>
      <g fill="${T}" stroke="${K}" stroke-width="2"><circle cx="37" cy="42" r="9"/><circle cx="63" cy="42" r="9"/></g><g fill="${K}"><circle cx="37" cy="42" r="4.4"/><circle cx="63" cy="42" r="4.4"/><path d="M50 52l-4 8h8z"/></g>
      <path d="M36 70h28M42 66v8M50 66v8M58 66v8" stroke="${K}" stroke-width="2"/><g fill="${P}"><circle cx="50" cy="22" r="4"/><circle cx="44" cy="20" r="2.4"/><circle cx="56" cy="20" r="2.4"/><circle cx="50" cy="16" r="2.4"/><circle cx="26" cy="54" r="2.4"/><circle cx="74" cy="54" r="2.4"/></g>
      <g fill="${O}"><circle cx="50" cy="21" r="1.6"/></g>`,
    43: `<g ${L}><path d="M50 10c-14 0-22 12-22 30 0 14-4 24-12 30h68c-8-6-12-16-12-30 0-18-8-30-22-30z" fill="${O}"/><path d="M14 70h72v8H14z" fill="${O2}"/><circle cx="50" cy="84" r="7" fill="${S2}"/>
      <path d="M44 8c-8-6-16 0-12 4M56 8c8-6 16 0 12 4" fill="none" stroke="${P}" stroke-width="3.4"/></g><path d="M38 24c-4 10-4 26-2 36" stroke="${W}" stroke-width="3.4" fill="none" opacity=".7"/>`,
    44: `<g ${L}><path d="M40 12h20l-2 12c16 4 26 18 22 36-4 18-18 30-30 30S24 78 20 60c-4-18 6-32 22-36z" fill="${TC}"/><path d="M60 26c16-8 26 10 10 22" fill="none" stroke="${TC}" stroke-width="6"/><path d="M60 26c16-8 26 10 10 22" fill="none"/></g>
      <g fill="${W}"><circle cx="34" cy="50" r="3"/><circle cx="44" cy="54" r="3"/><circle cx="54" cy="54" r="3"/><circle cx="64" cy="50" r="3"/></g><path d="M26 66q24 10 48 0" stroke="${W}" stroke-width="2.4" fill="none"/><path d="M28 40q22 6 44 0" stroke="${T}" stroke-width="3" fill="none"/>`,
    45: `<g ${L}><path d="M28 50c10-6 34-6 42 0 6 6 4 16-4 18H32c-8-2-10-12-4-18z" fill="${BR}"/><path d="M34 66l-8 26M44 68l-2 24M60 68l6 24M66 64l12 24" fill="none" stroke="${BR}" stroke-width="5"/><path d="M34 66l-8 26M44 68l-2 24M60 68l6 24M66 64l12 24" fill="none"/>
      <path d="M66 50c2-10 6-18 14-20 6 0 8 6 4 10l-8 4c0 4-2 8-8 8z" fill="${BR}"/><path d="M78 30c-2-8-8-12-8-20M78 30c4-8 10-10 10-18M72 18l-6-4M84 20l6-4" fill="none" stroke="${BR2}" stroke-width="3"/>
      <path d="M26 52l-8-4 4 8z" fill="${W}"/></g><circle cx="80" cy="36" r="1.8" fill="${K}"/><g fill="${CR}"><circle cx="40" cy="54" r="2"/><circle cx="50" cy="52" r="2"/><circle cx="58" cy="56" r="2"/></g>`,
    46: `<g ${L}><g fill="${P}"><path d="M50 2l6 16H44zM50 98l6-16H44zM2 50l16 6V44zM98 50l-16 6V44zM16 16l16 6-6 6zM84 84l-16-6 6-6zM84 16l-6 16-6-6zM16 84l6-16 6 6z"/></g><circle cx="50" cy="50" r="28" fill="${O}"/></g>
      ${eyes(41, 59, 45, 2.6)}<path d="M38 56q12 12 24 0" fill="${W}" ${L}/><g fill="${P}" opacity=".7"><circle cx="34" cy="54" r="4"/><circle cx="66" cy="54" r="4"/></g>`,
    47: `<g ${L}><path d="M16 74l-4-46 20 18 18-30 18 30 20-18-4 46z" fill="${O}"/><path d="M16 74h68v12H16z" fill="${S}"/></g><g fill="${T}" stroke="${K}" stroke-width="1.6"><circle cx="30" cy="80" r="3.4"/><circle cx="50" cy="80" r="3.4"/><circle cx="70" cy="80" r="3.4"/></g>
      <g fill="${P}" stroke="${K}" stroke-width="1.6"><circle cx="12" cy="26" r="4"/><circle cx="50" cy="14" r="4"/><circle cx="88" cy="26" r="4"/><circle cx="50" cy="56" r="6"/></g>`,
    48: `<path d="M4 80q12-5 23 0t23 0 23 0 23 0v16H4z" fill="${T}"/><g ${L}><path d="M8 64h84l-10 16H18z" fill="${P}"/><path d="M8 64h84" stroke="${W}"/><path d="M20 64V36h60v28" fill="none" stroke="${BR}" stroke-width="3"/><path d="M16 38c10-14 58-14 68 0z" fill="${T}"/>
      <path d="M72 30l14 56" fill="none" stroke="${BR}" stroke-width="3"/><path d="M82 72l8 16-8-2z" fill="${BR}"/></g><text x="50" y="76" text-anchor="middle" font-size="9" font-weight="900" fill="${W}" font-family="system-ui,sans-serif">LUPITA</text>
      <g fill="${O}"><circle cx="30" cy="34" r="3"/><circle cx="50" cy="30" r="3"/><circle cx="70" cy="34" r="3"/></g>`,
    49: `<g ${L}><path d="M44 80h12v14H44z" fill="${BR}"/><path d="M50 4L22 40h12L16 62h14L10 84h80L70 62h14L66 40h12z" fill="${G}"/></g><g fill="${G2}"><path d="M50 10l-10 14h8zM40 44l-8 12h8zM64 66l8 12h-8z"/></g>
      <g fill="${W}" opacity=".8"><circle cx="30" cy="16" r="1.6"/><circle cx="78" cy="30" r="1.6"/><circle cx="86" cy="54" r="1.6"/></g>`,
    50: `<g ${L}><path d="M18 50c14-22 44-26 62 0-18 26-48 22-62 0z" fill="${T}"/><path d="M80 50l14-14v28z" fill="${P}"/><path d="M40 34c4-8 14-10 20-6-6 2-14 4-20 6zM44 68c4 6 12 8 18 4-6-2-12-2-18-4z" fill="${P}"/></g>
      <circle cx="30" cy="46" r="3" fill="${K}"/><path d="M24 56q4 2 8 0" stroke="${K}" stroke-width="2" fill="none"/><g fill="none" stroke="${T2}" stroke-width="2"><path d="M44 44q4 6 0 12M54 42q4 8 0 16M64 44q4 6 0 12"/></g>
      <g fill="none" stroke="${T}" stroke-width="1.8"><circle cx="12" cy="30" r="3"/><circle cx="8" cy="18" r="2"/></g>`,
    51: `<path d="M4 90q46-10 92 0v8H4z" fill="${CR}"/><g ${L}><path d="M46 92c4-20 6-44 2-62h8c4 18 2 42-2 62z" fill="${BR}"/>
      <path d="M52 30C38 16 20 18 10 30c14-4 26-2 42 0zM52 30c10-16 26-20 38-14-14 2-26 6-38 14zM52 30c-6-14-2-24 6-28 0 10-2 18-6 28zM52 30C40 34 30 44 28 56c10-10 16-16 24-26zM52 30c12 2 22 10 26 22-10-8-16-14-26-22z" fill="${G}"/>
      <circle cx="48" cy="34" r="4" fill="${BR2}"/><circle cx="56" cy="34" r="4" fill="${BR2}"/></g><path d="M50 50v6M50 64v6M49 78v6" stroke="${BR2}" stroke-width="2"/>`,
    52: `<g ${L}><path d="M26 58h48l-6 34H32z" fill="${TC}"/><path d="M22 52h56v8H22z" fill="${TC}"/><path d="M50 52V24M50 40c-8-6-14-4-18 0 6 4 12 4 18 0zM50 34c8-6 14-4 18 0-6 4-12 4-18 0z" fill="${G2}"/>
      <circle cx="50" cy="18" r="8" fill="${P}"/><circle cx="32" cy="30" r="6" fill="${O}"/><circle cx="68" cy="28" r="6" fill="${T}"/><path d="M32 36v16M68 34v18" fill="none" stroke="${G}" stroke-width="2.4"/></g>
      <g fill="${W}"><circle cx="50" cy="18" r="2.4"/><circle cx="32" cy="30" r="1.8"/><circle cx="68" cy="28" r="1.8"/></g><path d="M34 72h32" stroke="${W}" stroke-width="2.4" stroke-dasharray="4 4"/>`,
    53: `<g ${L}><path d="M24 92L28 8c20 0 44 14 52 34-10 4-16 16-18 50z" fill="none" stroke="${O2}" stroke-width="7"/><path d="M24 92L28 8c20 0 44 14 52 34-10 4-16 16-18 50z" fill="none"/><path d="M20 92h46" fill="none" stroke="${BR2}" stroke-width="6"/></g>
      <g stroke="${S}" stroke-width="1.3"><path d="M32 16v76M38 18v74M44 21v71M50 25v67M56 29v63M62 34v58M68 40v50M74 44v4"/></g><g fill="${P}"><circle cx="28" cy="8" r="4"/><circle cx="80" cy="42" r="4"/></g>`,
    54: `<g ${L}><ellipse cx="50" cy="84" rx="40" ry="10" fill="${T}"/><path d="M50 84l14-10" fill="none" stroke="${K}"/><path d="M24 78c-4-20 6-36 26-36s30 16 26 36z" fill="${G2}"/><circle cx="36" cy="40" r="10" fill="${G2}"/><circle cx="64" cy="40" r="10" fill="${G2}"/>
      <path d="M22 80c-8 0-12-6-8-10 4 4 8 4 12 2M78 80c8 0 12-6 8-10-4 4-8 4-12 2" fill="${G2}"/><path d="M34 60q16 12 32 0" fill="${P}"/></g><g fill="${W}"><circle cx="36" cy="40" r="5"/><circle cx="64" cy="40" r="5"/></g>${eyes(37, 63, 41, 2.6)}
      <g fill="${G}"><circle cx="44" cy="70" r="2"/><circle cx="58" cy="72" r="2.4"/></g>`,
  };
  // [number, name, traditional verse]
  const DECK = [
    [1, "El Gallo", "El que le cantó a San Pedro no le volverá a cantar."],
    [2, "El Diablito", "Pórtate bien, cuatito, si no te lleva el coloradito."],
    [3, "La Dama", "Puliendo el paso, por toda la calle real."],
    [4, "El Catrín", "Don Ferruco en la alameda, su bastón quería tirar."],
    [5, "El Paraguas", "Para el sol y para el agua."],
    [6, "La Sirena", "Con los cantos de sirena, no te vayas a marear."],
    [7, "La Escalera", "Súbeme paso a pasito, no quieras pegar brinquitos."],
    [8, "La Botella", "La herramienta del borracho."],
    [9, "El Barril", "Tanto bebió el albañil, que quedó como barril."],
    [10, "El Árbol", "El que a buen árbol se arrima, buena sombra le cobija."],
    [11, "El Melón", "Me lo das o me lo quitas."],
    [12, "El Valiente", "¿Por qué le corres, cobarde, trayendo tan buen puñal?"],
    [13, "El Gorrito", "Ponle su gorrito al nene, no se nos vaya a resfriar."],
    [14, "La Muerte", "La muerte tilica y flaca."],
    [15, "La Pera", "El que espera, desespera."],
    [16, "La Bandera", "Verde, blanco y colorado, la bandera del soldado."],
    [17, "El Bandolón", "Tocando su bandolón, está el mariachi Simón."],
    [18, "El Violoncello", "Creciendo se fue hasta el cielo, y como no fue violín, tuvo que ser violoncello."],
    [19, "La Garza", "Al otro lado del río tengo mi banco de arena, donde se sienta mi chata, pico de garza morena."],
    [20, "El Pájaro", "Tú me traes a puros brincos, como pájaro en la rama."],
    [21, "La Mano", "La mano de un criminal."],
    [22, "La Bota", "Una bota igual que la otra."],
    [23, "La Luna", "El farol de los enamorados."],
    [24, "El Cotorro", "Cotorro, cotorro, saca la pata, y empiézame a platicar."],
    [25, "El Borracho", "¡Qué borracho tan necio, ya no lo puedo aguantar!"],
    [26, "El Chocolate", "Bate, bate, chocolate, con arroz y con tomate."],
    [27, "El Corazón", "No me extrañes, corazón, que regreso en el camión."],
    [28, "La Sandía", "La barriga que Juan tenía, era empacho de sandía."],
    [29, "El Tambor", "No te arrugues, cuero viejo, que te quiero pa' tambor."],
    [30, "El Camarón", "Camarón que se duerme, se lo lleva la corriente."],
    [31, "Las Jaras", "Las jaras del indio Adán, donde pegan, dan."],
    [32, "El Músico", "El músico trompas de hule, ya no me quiere tocar."],
    [33, "La Araña", "Atarántamela a palos, no me la dejes llegar."],
    [34, "El Soldado", "Uno, dos y tres, el soldado p'al cuartel."],
    [35, "La Estrella", "La guía de los marineros."],
    [36, "El Cazo", "El caso que te hago es poco."],
    [37, "El Mundo", "Este mundo es una bola, y nosotros un bolón."],
    [38, "El Apache", "¡Ah, Chihuahua! Cuánto apache con pantalón y huarache."],
    [39, "El Nopal", "Al nopal lo van a ver, nomás cuando tiene tunas."],
    [40, "El Alacrán", "El que con la cola pica, le dan una paliza."],
    [41, "La Rosa", "Rosita, Rosaura, ven que te quiero ahora."],
    [42, "La Calavera", "Al pasar por el panteón, me encontré un calaverón."],
    [43, "La Campana", "Tú con la campana y yo con tu hermana."],
    [44, "El Cantarito", "Tanto va el cántaro al agua, que se quiebra y te moja las enaguas."],
    [45, "El Venado", "Saltando va buscando, pero no ve nada el venado."],
    [46, "El Sol", "La cobija de los pobres."],
    [47, "La Corona", "El sombrero de los reyes."],
    [48, "La Chalupa", "Rema que rema Lupita, sentada en su chalupita."],
    [49, "El Pino", "Fresco y oloroso, en todo tiempo hermoso."],
    [50, "El Pescado", "El que por la boca muere, aunque mudo fuera."],
    [51, "La Palma", "Palmero, sube a la palma y bájame un coco real."],
    [52, "La Maceta", "El que nace pa' maceta, no sale del corredor."],
    [53, "El Arpa", "Arpa vieja de mi suegra, ya no sirves pa' tocar."],
    [54, "La Rana", "Al ver a la verde rana, qué susto le dio a mi hermana."],
  ];
  const TINTS = ["#d6f6f3", "#ffe0ec", "#ffd9c7", "#e6e9ec"];   // light turquoise, pink, peach, silver behind the art
  // v43: each card is also a finished picture in the vintage lithograph style (tools/make_loteria_cards.py renders these
  // drawings with a painted scene, textures, the number and the name banner): static/loteria/cards/01.webp … 54.webp
  const CARDS = DECK.map(([id, name, verse]) => ({ id, name, verse, tint: TINTS[(id - 1) % TINTS.length],
    img: `/static/loteria/cards/${String(id).padStart(2, "0")}.webp`,
    svg: `<svg class="lc-svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">${ART[id]}</svg>` }));
  // v43: "Pick your tabla": a few ready-made tablas (16 cards, row by row) plus a random mix
  const PRESETS = [
    { id: "clasica", name: "La Clásica", cards: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16] },
    { id: "campo", name: "Del Campo", cards: [1, 19, 20, 24, 10, 39, 41, 49, 30, 33, 40, 45, 50, 51, 52, 54] },
    { id: "fiesta", name: "La Fiesta", cards: [17, 18, 29, 32, 53, 43, 8, 9, 25, 26, 28, 11, 15, 44, 36, 16] },
    { id: "cielo", name: "Cielo y Mar", cards: [23, 35, 46, 37, 5, 6, 19, 30, 48, 50, 51, 54, 20, 7, 47, 27] },
    { id: "gente", name: "La Gente", cards: [3, 4, 12, 14, 2, 25, 32, 34, 38, 6, 21, 22, 13, 42, 47, 31] },
  ];
  // what she says out loud for a card (the verse, then the name, like a real cantor) and the other calls
  const callText = (c) => `${c.verse} ¡${c.name}!`;
  const LINES_ES = { intro: "¡Se va y se corre con…!", loteria: "¡Lotería!", over: "¡Se acabaron las cartas!" };
  const api = { CARDS, DECK, PRESETS, callText, LINES_ES, TINTS };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.ChismeLoteriaCards = api;
})(typeof window !== "undefined" ? window : this);
