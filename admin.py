"""v49.5: the owner's admin page at /stats, rebuilt for a phone (mostly an iPhone) and a non-technical owner.

Top to bottom: a sticky header (‹ App, ↻, Sign out) → "Send a notification" (subscriber count, quick templates, a
live lock-screen preview, a confirm sheet, a toast with the result) → "Auto-alerts for big news" (one big switch, a
plain-English status line, Run a check now) → "At a glance" cards (today, this week, subscribers, installed) and the
week's top stories → everything else folded into <details> (all the numbers, the chart, tabs/games/cities, the logs,
technical details). Sign-in is a simple form (login_page) that remembers the phone for 30 days (v49.11: a revocable session, Sign out everywhere in Technical details); the old
/stats?key=… link still works. Fiesta palette (turquoise, pink, orange, black, silver), no yellow.
The data comes from stats.py (anonymous counts) and autopush.admin_info (push); this module only renders."""
from __future__ import annotations

import html, json, time
from datetime import datetime
from urllib.parse import urlsplit

import stats

e = html.escape
fmt = lambda n: f"{int(n or 0):,}"
TZ = stats.TZ

# the quick templates (title, message, where tapping it goes); the wording stays plain for news, warm for the rest (v49.12: English)
TEMPLATES = [
    ("news", "👀 New chisme", "Chisme", "New chisme! 👀", "news"),
    ("breaking", "🚨 Breaking news", "Breaking news", "Big news in San Antonio right now. Tap to read the latest.", "link"),
    ("weather", "🌧️ Weather alert", "Weather alert", "Severe weather is heading for San Antonio. Tap for the radar and the latest alerts.", "weather"),
    ("game", "🎮 New game", "🎮 New game in Chisme", "A new game just dropped in Juegos. Come play 👀", "juegos"),
    ("thanks", "💗 Donation thank-you", "💗 Thank you, metiches!", "Thank you for supporting Chisme. Every coffee keeps San Antonio's chisme free for everybody.", "news"),
]
WHERE = [("news", "Chisme · News", "/#news"), ("weather", "Weather (radar + alerts)", "/#weather"), ("juegos", "Juegos (games)", "/#juegos"),
         ("events", "Chisme · Events", "/#events"), ("sports", "Chisme · Sports", "/#sports"), ("link", "A story or web page (paste a link)", "")]


def plural(n: int, one: str, many: str | None = None) -> str:
    n = int(n or 0)
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def clock(ts, now: float | None = None) -> str:
    """'just now', '12 min ago', '2:55 AM', 'Yesterday 4:10 PM', 'Tue Sep 29, 4:10 PM' (Central time)."""
    try:
        ts = float(ts)
    except Exception:
        return "—"
    now = now or time.time()
    d, n = datetime.fromtimestamp(ts, TZ), datetime.fromtimestamp(now, TZ)
    if 0 <= now - ts < 60:
        return "just now"
    if 0 <= now - ts < 3600:
        return f"{int((now - ts) // 60)} min ago"
    t = d.strftime("%-I:%M %p")
    if d.date() == n.date():
        return t
    if (n.date() - d.date()).days == 1:
        return "Yesterday " + t
    return d.strftime("%a %b %-d, ") + t


# ---------------------------------------------------------------- plain English for the push panel
def status_line(i: dict | None) -> str:
    """'On · 1 of 2 sent today · quiet hours 10pm–7am' and friends."""
    if not i:
        return "Unavailable right now (push storage didn't answer)"
    if not i.get("enabled"):
        return "Off · notifications aren't set up on the server yet"
    if not i.get("on"):
        return "Off · nothing is sent automatically"
    today, cap = int(i.get("today") or 0), int(i.get("cap") or 2)
    parts = ["On", f"{today} of {cap} sent today" + (" (today's limit reached)" if today >= cap else "")]
    parts.append("quiet hours now, back at 7am" if i.get("quiet") else "quiet hours 10pm–7am")
    return " · ".join(parts)


def plain_result(res: dict | None) -> str:
    """A check's result (autopush.check / the stored 'last') → one sentence for the owner."""
    if not res:
        return "No check yet."
    r = str(res.get("result") or "")
    n = res.get("considered")
    seen = f"Looked at {plural(n, 'new story', 'new stories')}" if isinstance(n, int) else "Looked at the news"
    if r.startswith("sent"):
        t = r.split(":", 1)[1].strip() if ":" in r else ""
        return f"Sent an alert: “{t}”" + (f" to {plural(res['sent'], 'phone')}." if isinstance(res.get("sent"), int) else ".")
    if r == "nothing major":
        return f"{seen}: nothing big enough to send."
    if r.startswith("candidates"):
        return f"{seen}: a few looked important, but none were big enough to send."
    if r.startswith("would send"):
        return "Found a big story, but nobody near San Antonio has news alerts on yet."
    if r.startswith("auto-send is off"):
        return "Auto-alerts are off, so nothing was checked. Turn them on first."
    if r.startswith("quiet hours"):
        return "Quiet hours (10pm–7am): no alerts until 7am."
    if r.startswith("daily cap"):
        return "Already sent today's limit of alerts. More tomorrow."
    if r.startswith("already sent"):
        return "That story was already sent."
    if r.startswith("push isn't set up"):
        return "Notifications aren't set up on the server yet."
    if r.startswith("skipped"):
        return "A check is already running. Try again in a minute."
    if r.startswith("error"):
        return "The check ran into a problem (see Technical details). It'll try again on the next visit."
    return r[:160] or "Done."


def send_result(j: dict) -> str:
    if not j.get("ok"):
        return "Not sent: " + str(j.get("error") or "something went wrong")
    if not j.get("total"):
        return "Nobody has news alerts on yet, so nothing was sent."
    s = "Sent to " + plural(j.get("sent"), "phone")
    if j.get("failed"):
        s += f" · {fmt(j['failed'])} didn't go through"
    if j.get("removed"):
        s += f" · {plural(j['removed'], 'old subscription')} cleaned up"
    return s


def info_json(i: dict | None, now: float | None = None) -> dict:
    """What the page's script needs after an action (no secrets in here)."""
    i = i or {}
    last = i.get("last") or None
    return {"ok": bool(i), "enabled": bool(i.get("enabled")), "on": bool(i.get("on")), "news": int(i.get("news") or 0),
            "subs": int(i.get("subs") or 0), "today": int(i.get("today") or 0), "cap": int(i.get("cap") or 2), "quiet": bool(i.get("quiet")),
            "status": status_line(i or None), "last": (f"{clock(last.get('ts'), now)} · {plain_result(last)}" if last else "No check yet.")}


# ---------------------------------------------------------------- pieces
def _bars(rows: list[tuple[str, int]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{e(empty)}</p>'
    mx = max(v for _, v in rows) or 1
    return "<ol class='bars'>" + "".join(
        f'<li><span class="bl">{lab}</span><span class="bv">{fmt(v)}</span><span class="bb"><i style="width:{max(2, round(100 * v / mx))}%"></i></span></li>'
        for lab, v in rows) + "</ol>"


def _story_rows(r: dict, c: dict, n: int) -> list[tuple[str, int]]:
    out = []
    for k, v in stats._top(c, "story:", n):
        m = r["stories"].get(k) or {}
        t, src = e(m.get("t") or "(a story)"), e(m.get("s") or "")
        out.append((f'<a href="{e(m.get("u") or "#")}" target="_blank" rel="noopener noreferrer">{t}</a>' + (f' <small>{src}</small>' if src else ""), v))
    return out


def _period_cards(S: dict, n: int) -> str:
    c, u = S[n]["c"], S[n]["u"]
    items = [("Visitors", u["all"], "different phones"), ("Installed app", u["app"], "phones opening from the Home Screen"),
             ("In Safari / browser", u["web"], "phones in the browser"), ("Opens", c.get("open", 0), f"{fmt(c.get('open:app', 0))} app · {fmt(c.get('open:web', 0))} browser"),
             ("ChismeTV views", c.get("food", 0), f"{fmt(c.get('food:yt', 0))} YouTube · {fmt(c.get('food:tt', 0))} TikTok · ♥ {fmt(c.get('reel:like', 0))} likes · {fmt(c.get('reel:share', 0))} shares"),
             ("Game plays", c.get("game", 0), ""), ("Donate taps", c.get("donate", 0), " · ".join(f"{e(k)} {fmt(v)}" for k, v in stats._top(c, "donate:"))),
             ("Tía chats", c.get("tia", 0), "messages (never the text)")]
    return "".join(f'<div class="stat"><div class="n">{fmt(v)}</div><div class="l">{e(l)}</div><div class="s">{s}</div></div>' for l, v, s in items)


def _chart(r: dict, days: list[str]) -> str:
    mx = max([r["per"][d]["u"]["all"] for d in days] + [1])
    W, H, bw = 600, 160, 600 / 30
    rects = []
    for i, d in enumerate(days):
        a, p_ = r["per"][d]["u"]["all"], r["per"][d]["u"]["app"]
        ha, hp = H * a / mx, H * min(p_, a) / mx
        x = i * bw + 2
        lab = datetime.strptime(d, "%Y-%m-%d").strftime("%b %-d")
        rects.append(f'<g><title>{lab}: {a} visitors, {p_} in the app</title><rect x="{x:.1f}" y="{H - ha:.1f}" width="{bw - 4:.1f}" height="{ha:.1f}" rx="3" class="va"/>'
                     f'<rect x="{x:.1f}" y="{H - hp:.1f}" width="{bw - 4:.1f}" height="{hp:.1f}" rx="3" class="vp"/></g>')
    ticks = "".join(f'<text x="{i * bw + bw / 2:.1f}" y="{H + 16}" text-anchor="middle">{datetime.strptime(days[i], "%Y-%m-%d").strftime("%b %-d")}</text>' for i in (0, 7, 14, 21, 29))
    return (f'<svg viewBox="0 -8 {W} {H + 26}" role="img" aria-label="Visitors per day, last 30 days (most on one day: {mx})">'
            f'<line x1="0" y1="{H}" x2="{W}" y2="{H}" class="ax"/>{"".join(rects)}{ticks}</svg>'
            '<p class="key"><i style="background:var(--turq)"></i>All visitors<i style="background:var(--pink)"></i>In the installed app</p>')


def _fold(title: str, body: str, id_: str, count: str = "") -> str:
    return (f'<details class="fold" id="{id_}"><summary><span>{title}</span>{f"<small>{count}</small>" if count else ""}</summary>'
            f'<div class="fold-b">{body}</div></details>')


# ---------------------------------------------------------------- the page
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer">
<meta name="theme-color" content="#0a0a0a"><meta name="color-scheme" content="light">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Chisme Admin"><meta name="apple-mobile-web-app-status-bar-style" content="black">
<link rel="manifest" href="/stats/manifest.webmanifest"><link rel="apple-touch-icon" href="/static/icons/admin-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="/static/icons/admin-192.png">
<title>%%TITLE%%</title>
<style>
:root{--ink:#0a0a0a;--bg:#f4f3ef;--card:#fff;--line:#d6d2ca;--pink:#EF426F;--turq:#00C9CD;--orange:#FF8200;--pinkd:#b8123f;--turqd:#00797c;--silver:#a7a9ac;--silverl:#eceded;--muted:#3b3b3b}
*{box-sizing:border-box}[hidden]{display:none!important}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:500 17px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;overflow-x:hidden}
button,input,select,textarea{font:inherit;color:inherit}a{color:#0a3d8f}
button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:4px solid var(--pink);outline-offset:2px}
.top{position:sticky;top:0;z-index:20;background:var(--ink);color:#fff;padding:calc(env(safe-area-inset-top) + 6px) 10px 0}
.top-r{display:flex;align-items:center;gap:6px;max-width:640px;margin:0 auto;padding-bottom:6px}
.top h1{margin:0;font-size:1.15rem;font-weight:900;line-height:1.1}.top p{margin:0;font-size:.75rem;color:var(--silver)}.ht{flex:1;min-width:0}
.hb{display:inline-flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:0 12px;border-radius:12px;border:2px solid var(--silver);background:transparent;color:#fff;font-weight:800;font-size:.95rem;text-decoration:none;cursor:pointer;white-space:nowrap}
.hb.ic{font-size:1.25rem;padding:0}.top form{margin:0}
.picado{height:8px;margin:0 -10px;background:repeating-linear-gradient(90deg,var(--pink) 0 28px,var(--orange) 28px 56px,var(--turq) 56px 84px)}
main{max-width:640px;margin:0 auto;padding:12px 12px calc(env(safe-area-inset-bottom) + 90px)}
.card{background:var(--card);border:2px solid var(--line);border-radius:18px;padding:14px;margin:0 0 14px;border-top:7px solid var(--pink)}
.card.auto{border-top-color:var(--turq)}.card.glance-top{border-top-color:var(--orange)}
.card h2{margin:0 0 4px;font-size:1.25rem;font-weight:900;line-height:1.2}.sec{font-size:1.1rem;font-weight:900;margin:22px 4px 8px}
.ban{border-radius:14px;padding:10px 12px;margin:0 0 12px;border:3px solid;font-size:.92rem}.ban.warn{border-color:var(--orange);background:#ffece6}
.ban.test{border-color:var(--pink);background:#fde7ed}.ban.tip{border-color:var(--turqd);background:#e5fbfb;display:flex;gap:10px;align-items:flex-start}
.ban.tip p{margin:0;flex:1}.ban.tip button{flex:0 0 auto}code{font-size:.82em;background:#0000000d;padding:0 .25em;border-radius:4px;overflow-wrap:anywhere}
.count{margin:0 0 10px;font-size:1rem}.count b{font-size:1.5rem;font-weight:900}
.tpl{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 6px}
.chip{min-height:44px;padding:0 14px;border-radius:999px;border:2px solid var(--ink);background:#fff;font-weight:800;font-size:.95rem;cursor:pointer}
.chip[aria-pressed=true]{background:var(--ink);color:#fff}
.f{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-weight:800;font-size:.95rem;margin:12px 0 4px}.f small{font-weight:600;color:var(--muted)}
.inp{display:block;width:100%;min-height:50px;padding:11px 12px;border:2px solid var(--ink);border-radius:12px;background:#fff;font-size:17px}
textarea.inp{min-height:92px;resize:vertical}select.inp{appearance:none;-webkit-appearance:none;background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='9'%3E%3Cpath d='M1 1l6 6 6-6' stroke='%230a0a0a' stroke-width='2.5' fill='none'/%3E%3C/svg%3E") no-repeat right 14px center;padding-right:40px}
.help{margin:4px 2px 0;font-size:.82rem;color:var(--muted)}.err{margin:8px 2px 0;color:var(--pinkd);font-weight:800;font-size:.92rem}
.pvh{margin:16px 0 6px;font-size:.95rem;font-weight:900}
.phone{border-radius:22px;padding:14px 12px 16px;background:linear-gradient(160deg,#00797c 0%,#0a0a0a 70%);color:#fff}
.phone .clk{text-align:center;font-size:2.4rem;font-weight:300;line-height:1;margin:2px 0 2px;letter-spacing:-.02em}.phone .dt{text-align:center;font-size:.8rem;color:#e6e6e6;margin:0 0 12px}
.ntf{display:flex;gap:10px;background:rgba(245,245,245,.94);color:#0a0a0a;border-radius:16px;padding:10px 12px;box-shadow:0 2px 10px rgba(0,0,0,.25)}
.ntf img{width:38px;height:38px;border-radius:9px;flex:0 0 auto}.ntf .nb{flex:1;min-width:0}.ntf .nh{display:flex;justify-content:space-between;font-size:.72rem;color:#555;text-transform:uppercase;letter-spacing:.03em}
.ntf .nt{font-weight:800;font-size:.95rem;overflow-wrap:anywhere}.ntf .nm{font-size:.92rem;overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.phone .nl{margin:10px 2px 0;font-size:.8rem;color:#e6e6e6;text-align:center}
.big{display:flex;width:100%;align-items:center;justify-content:center;gap:8px;min-height:56px;margin-top:14px;border-radius:14px;border:2px solid var(--ink);background:#fff;font-weight:900;font-size:1.08rem;cursor:pointer}
.big.go{background:var(--pink);border-color:var(--pinkd);color:#fff}.big:disabled{opacity:.5;cursor:default}
.res{margin:10px 2px 0;font-weight:800;min-height:1em}.res.ok{color:var(--turqd)}.res.bad{color:var(--pinkd)}
.sw{display:flex;align-items:center;justify-content:space-between;gap:14px;min-height:60px;margin:6px 0 2px;padding:8px 12px;border:2px solid var(--line);border-radius:14px;font-weight:900;font-size:1.08rem;cursor:pointer}
.sw input{appearance:none;-webkit-appearance:none;width:64px;height:38px;border-radius:999px;background:var(--silver);position:relative;margin:0;cursor:pointer;border:2px solid var(--ink);flex:0 0 auto}
.sw input::after{content:"";position:absolute;top:3px;left:3px;width:28px;height:28px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.4);transition:transform .2s}
.sw input:checked{background:var(--turqd)}.sw input:checked::after{transform:translateX(26px)}
.status{margin:8px 2px 0;font-weight:800;font-size:1rem}.status .dot{display:inline-block;width:12px;height:12px;border-radius:50%;background:var(--silver);margin-right:6px;vertical-align:0}
.status.on .dot{background:var(--turqd)}.status.hot .dot{background:var(--orange)}
.sub{margin:6px 2px 0;font-size:.88rem;color:var(--muted)}
.glance{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.gl{background:var(--card);border:2px solid var(--line);border-radius:16px;padding:12px;border-left:7px solid var(--turq)}
.gl:nth-child(2){border-left-color:var(--pink)}.gl:nth-child(3){border-left-color:var(--orange)}.gl:nth-child(4){border-left-color:var(--ink)}
.gl .n{font-size:1.9rem;font-weight:900;line-height:1.05}.gl .l{font-weight:900;font-size:.95rem}.gl .s{font-size:.78rem;color:var(--muted)}
.topl{list-style:none;margin:6px 0 0;padding:0;counter-reset:t}.topl li{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid var(--silverl)}
.topl li::before{counter-increment:t;content:counter(t);flex:0 0 28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;font-weight:900;font-size:.85rem;display:flex;align-items:center;justify-content:center}
.topl .tt{flex:1;min-width:0;font-weight:700;font-size:.95rem;overflow-wrap:anywhere}.topl .tt small{display:block;color:var(--muted);font-weight:600}.topl .tv{font-weight:900;white-space:nowrap}
.empty{margin:6px 2px;color:var(--muted);font-size:.95rem}
.fold{background:var(--card);border:2px solid var(--line);border-radius:16px;margin:0 0 10px;overflow:hidden}
.fold summary{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:56px;padding:8px 14px;font-weight:900;cursor:pointer;list-style:none}
.fold summary::-webkit-details-marker{display:none}.fold summary::after{content:"";width:10px;height:10px;border-right:3px solid var(--ink);border-bottom:3px solid var(--ink);transform:rotate(45deg);margin:-4px 4px 0 0;flex:0 0 auto;transition:transform .2s}
.fold[open] summary::after{transform:rotate(-135deg);margin-top:4px}.fold summary small{margin-left:auto;font-weight:700;color:var(--muted);font-size:.85rem;white-space:nowrap}
.fold-b{padding:0 14px 14px}
.seg{display:flex;gap:6px;margin:4px 0 10px}.seg button{flex:1;font-weight:800;min-height:44px;border:2px solid var(--ink);border-radius:10px;background:#fff}
.seg button[aria-selected=true]{background:var(--ink);color:#fff}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.stat{background:var(--card);border:2px solid var(--line);border-radius:14px;padding:10px 12px;border-top:6px solid var(--turq)}
.stat:nth-child(2){border-top-color:var(--pink)}.stat:nth-child(3){border-top-color:var(--orange)}.stat:nth-child(4){border-top-color:#000}
.stat .n{font-size:1.5rem;font-weight:900;line-height:1.1}.stat .l{font-weight:800;font-size:.9rem}.stat .s{font-size:.75rem;color:var(--muted)}
svg{width:100%;height:auto;display:block}svg text{font-size:11px;fill:#333}.va{fill:var(--turq)}.vp{fill:var(--pink)}.ax{stroke:#999}
.key{font-size:.8rem;margin:6px 0 0}.key i{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 8px;vertical-align:-1px}
.bars{list-style:none;margin:0;padding:0}.bars li{display:grid;grid-template-columns:1fr auto;gap:2px 8px;padding:7px 0;border-bottom:1px solid var(--silverl)}
.bl{font-weight:700;font-size:.92rem;overflow-wrap:anywhere}.bl small{color:var(--muted);font-weight:500}.bv{font-weight:900}
.bb{grid-column:1/-1;height:6px;background:var(--silverl);border-radius:3px;overflow:hidden}.bb i{display:block;height:100%;background:var(--orange)}
.plog{list-style:none;margin:0;padding:0}.plog li{display:grid;gap:2px;padding:9px 0;border-bottom:1px solid var(--silverl)}
.pl-t{font-weight:800;font-size:.92rem;overflow-wrap:anywhere}.pl-t small{color:var(--muted);font-weight:600}.pl-m,.pl-n{font-size:.8rem;color:var(--muted)}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px}.pill{border:2px solid var(--silver);background:var(--silverl);border-radius:999px;padding:3px 10px;font-size:.8rem;font-weight:800}
.pill.on{border-color:var(--turqd);background:#e5fbfb}.pill.hot{border-color:var(--orange);background:#ffece6}
.hs-list{list-style:none;margin:8px 0 0;padding:0}.hs-row{display:grid;grid-template-columns:32px 1fr;gap:6px 10px;padding:10px 0;border-bottom:1px solid var(--silverl);align-items:start}
.hs-rk{width:32px;height:32px;border-radius:50%;background:var(--ink);color:#fff;font-weight:900;font-size:.9rem;display:flex;align-items:center;justify-content:center;margin-top:8px}
.hs-row:nth-child(1) .hs-rk{background:var(--pink)}.hs-row:nth-child(2) .hs-rk{background:var(--turqd)}.hs-row:nth-child(3) .hs-rk{background:var(--orange);color:#000}
.hs-main{min-width:0}.hs-name{min-height:46px;padding:8px 10px;font-weight:800}.hs-meta{font-size:.85rem;color:var(--muted);margin:4px 2px 0}.hs-meta b{color:var(--ink);font-size:1.05rem}
.hs-btns{grid-column:2;display:flex;gap:8px}.hs-btns button{flex:1;min-height:44px;border-radius:12px;border:2px solid var(--ink);background:#fff;font-weight:900;font-size:.95rem;cursor:pointer}
.hs-btns .hs-save{background:var(--turq);border-color:var(--turqd);color:#000}.hs-btns .hs-del{color:var(--pinkd);border-color:var(--pinkd)}.hs-btns .hs-del.arm{background:var(--pinkd);color:#fff}
.hs-clear{border-color:var(--pinkd);color:var(--pinkd)}
.kv{margin:0;display:grid;grid-template-columns:auto 1fr;gap:6px 12px;font-size:.88rem}.kv dt{font-weight:800}.kv dd{margin:0;overflow-wrap:anywhere}
dialog.sheet{border:0;padding:0;margin:auto auto 0;width:100%;max-width:520px;border-radius:22px 22px 0 0;background:var(--card);color:var(--ink)}
@media(min-width:560px){dialog.sheet{margin:auto;border-radius:22px}}
dialog.sheet::backdrop{background:rgba(0,0,0,.55)}.sheet-b{padding:18px 16px calc(env(safe-area-inset-bottom) + 16px)}
.sheet h3{margin:0 0 4px;font-size:1.3rem;font-weight:900}.sheet .two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.sheet .two .big{margin-top:14px}
.toast{position:fixed;left:50%;bottom:calc(env(safe-area-inset-bottom) + 16px);transform:translate(-50%,140%);width:min(92vw,520px);padding:14px 16px;border-radius:16px;
 background:var(--turqd);color:#fff;font-weight:800;box-shadow:0 6px 24px rgba(0,0,0,.3);transition:transform .25s,visibility .25s;z-index:50;visibility:hidden}
.toast.show{transform:translate(-50%,0);visibility:visible}.toast.bad{background:var(--pinkd)}
footer{font-size:.78rem;color:var(--muted);padding:14px 4px}
.login{max-width:440px;margin:0 auto;padding:18px 14px calc(env(safe-area-inset-bottom) + 40px)}
.login .card{border-top-color:var(--turq)}.login h2{font-size:1.35rem}.row{display:flex;gap:8px;align-items:stretch}.row .inp{flex:1}
.chk{display:flex;align-items:center;gap:12px;min-height:48px;margin-top:10px;font-weight:700}.chk input{width:26px;height:26px;accent-color:var(--turqd);margin:0}
</style></head><body>"""


def header(sub: str, signed_in: bool = True) -> str:
    right = ('<button type="button" class="hb ic" id="refresh" aria-label="Refresh">↻</button>'
             '<form method="post" action="/stats/logout"><button type="submit" class="hb" id="logout">Sign out</button></form>') if signed_in else ""
    return (f'<header class="top"><div class="top-r"><a class="hb" href="/" aria-label="Back to the Chisme app">‹ App</a>'
            f'<div class="ht"><h1>Chisme Admin</h1><p id="updated">{e(sub)}</p></div>{right}</div><div class="picado" aria-hidden="true"></div></header>')


def _scores(scores: list | None, now: float) -> str:
    """v49.5: 🏆 Juan High Scores: every saved score, best first; rename (12 characters), delete (tap twice), clear the board (confirm sheet)."""
    if scores is None:
        return '<p class="empty">Couldn\'t load the scores right now (storage). Try again in a minute.</p>'
    rows = []
    for i, r in enumerate(scores):
        sid = html.escape(str(r.get("id") or ""), quote=True); nm = html.escape(str(r.get("name") or ""), quote=True)
        when = datetime.fromtimestamp(int(r.get("t") or now), TZ).strftime("%b %-d, %-I:%M %p")
        rows.append(f'<li class="hs-row" data-id="{sid}"><span class="hs-rk">{i + 1}</span>'
                    f'<div class="hs-main"><input class="inp hs-name" maxlength="12" value="{nm}" aria-label="Name for the {int(r.get("score") or 0):,} score" autocomplete="off" enterkeyhint="done">'
                    f'<div class="hs-meta"><b>{int(r.get("score") or 0):,}</b> · level {int(r.get("level") or 1)} · {when}</div></div>'
                    f'<div class="hs-btns"><button type="button" class="hs-save">Save</button><button type="button" class="hs-del" aria-label="Delete the {int(r.get("score") or 0):,} score">🗑️ Delete</button></div></li>')
    lst = f'<ol class="hs-list" id="hs-list">{"".join(rows)}</ol>' if rows else ""
    return (f'<p class="sub">Every saved score, best first. Fix a name (12 characters max) and tap Save, or delete one (tap Delete twice).</p>'
            f'<p class="empty" id="hs-empty"{" hidden" if rows else ""}>No scores on the board yet.</p>{lst}'
            f'<button type="button" class="big hs-clear" id="hs-clear"{" hidden" if not rows else ""}>🧹 Clear the board</button>'
            '<dialog class="sheet" id="hs-confirm" aria-labelledby="hs-confirm-h"><div class="sheet-b"><h3 id="hs-confirm-h">Clear the whole board?</h3>'
            f'<p class="sub" id="hs-confirm-n">All {plural(len(scores), "score")} will be deleted for good. This can\'t be undone.</p>'
            '<div class="two"><button type="button" class="big" id="hs-no">Cancel</button><button type="button" class="big go" id="hs-yes">Yes, clear it</button></div></div></dialog>')


def tia_card(t: dict | None) -> str:
    """v49.12: Tía's AI messages today (Chicago day) against the daily caps."""
    if not t or t.get("error"):
        return ('<section class="card glance-top" id="tia-today" style="margin-top:12px"><h2>💬 Tía today</h2>'
                '<p class="empty">Tía\'s usage isn\'t available right now (the storage didn\'t answer). Try ↻ in a minute.</p></section>')
    ai, cap, dcap = int(t.get("ai") or 0), int(t.get("global_cap") or 0), int(t.get("device_cap") or 0)
    pct = min(100, round(100 * ai / cap)) if cap else 0
    hit = ai >= cap > 0
    return (f'<section class="card glance-top" id="tia-today" style="margin-top:12px"><h2>💬 Tía today</h2>'
            f'<p class="sub" style="margin:0">AI (Gemini) answers since midnight Central · resets at midnight</p><div class="glance">'
            f'<div class="gl"><div class="n" id="tia-ai">{fmt(ai)}</div><div class="l">of {fmt(cap)}</div><div class="s">AI answers today ({pct}% of the daily cap){" · cap reached: Tía is answering from the feeds" if hit else ""}</div></div>'
            f'<div class="gl"><div class="n" id="tia-devs">{fmt(t.get("devices"))}</div><div class="l">Phones</div><div class="s">chatted with the AI today</div></div>'
            f'<div class="gl"><div class="n" id="tia-capped">{fmt(t.get("capped-devices"))}</div><div class="l">At their limit</div><div class="s">phones that used all {dcap} AI answers today</div></div></div>'
            f'<p class="sub" style="margin:8px 0 0">Turned away today: {plural(t.get("blocked-device"), "message")} over a phone\'s limit, '
            f'{plural(t.get("blocked-global"), "message")} over the daily cap (they still got an answer from the feeds; the 988 crisis reply is never limited). '
            f'Change the caps on Render: <code>TIA_DEVICE_DAILY_CAP</code> (now {dcap}), <code>TIA_DAILY_GLOBAL_CAP</code> (now {fmt(cap)}).</p></section>')


def page(r: dict, store_name: str, info: dict | None = None, now: float | None = None, info_error: str = "", extra: str = "", scores: list | None = None, refresh: dict | None = None, nonce: str = "", tia: dict | None = None) -> str:
    now = now or time.time()
    days = stats.last_days(30, stats.day_of(now))
    S = stats.summarize(r, days)
    i = info or {}
    has_push = info is not None
    n_news = int(i.get("news") or 0)
    enabled = bool(i.get("enabled"))

    banners, sbanners = [], []   # sbanners: about the numbers, shown under "At a glance"
    if r.get("sample"):
        sbanners.append('<div class="ban test" role="note"><b>🧪 TEST DATA</b> — made-up sample numbers for a screenshot, not real visitors.</div>')
    if store_name != "upstash":
        sbanners.append('<div class="ban warn" role="note"><b>Heads up, temporary storage:</b> these numbers reset on every redeploy (and when the free server sleeps) until Upstash is set up. See Technical details.</div>')
    if has_push and not enabled:
        banners.append('<div class="ban warn" role="note"><b>Notifications aren\'t set up yet.</b> Add <code>VAPID_PUBLIC_KEY</code>, <code>VAPID_PRIVATE_KEY</code> and <code>VAPID_SUBJECT</code> on Render (Environment); until then nothing can be sent.</div>')
    if info_error:
        banners.append(f'<div class="ban warn" role="note"><b>The notification tools are unavailable right now</b> ({e(info_error)}). Try ↻ in a minute; details are under Technical details.</div>')
    banners.append(extra)
    tip = ('<div class="ban tip" id="a2hs-tip" hidden><p><b>Tip:</b> for a one-tap Admin button, <span id="a2hs-how">tap Share <span aria-hidden="true">⬆️</span> → '
           '<b>Add to Home Screen</b></span>. Sign in once there.</p><button type="button" class="hb" id="a2hs-x" '
           'style="color:var(--ink);border-color:var(--ink)" aria-label="Hide this tip">✕</button></div>')

    # ---- send card
    chips = "".join(f'<button type="button" class="chip" data-tpl="{k}" aria-pressed="false">{e(lab)}</button>' for k, lab, *_ in TEMPLATES)
    opts = "".join(f'<option value="{k}"{" selected" if k == "news" else ""}>{e(lab)}</option>' for k, lab, _ in WHERE)
    t0 = TEMPLATES[0]
    dis = "" if (enabled and has_push) else " disabled"
    send_lbl = f"Send to {plural(n_news, 'phone')}…" if n_news else "Send…"
    send = f"""<section class="card send" id="send" aria-labelledby="push-h"><h2 id="push-h">📣 Send a notification</h2>
<p class="count" id="push-count" aria-live="polite"><b>{fmt(n_news)}</b> {"phone will get it" if n_news == 1 else "phones will get it"}<span class="sub" style="display:block;margin:0">{"Everyone who turned on news alerts in Chisme." if n_news else "Nobody has turned on news alerts yet. When people do, they'll show up here."}</span></p>
<p class="f" style="margin-top:4px">Quick templates <small>tap one, then edit</small></p><div class="tpl" role="group" aria-label="Quick templates">{chips}</div>
<form id="pf-form" novalidate>
<label class="f" for="pf-title">Title <small id="pf-tc">0 / 80</small></label><input class="inp" type="text" id="pf-title" maxlength="80" value="{e(t0[2])}" autocomplete="off" enterkeyhint="next">
<label class="f" for="pf-msg">Message <small id="pf-mc">0 / 240</small></label><textarea class="inp" id="pf-msg" maxlength="240" required>{e(t0[3])}</textarea>
<label class="f" for="pf-where">Tapping it opens</label><select class="inp" id="pf-where">{opts}</select>
<div id="pf-link-wrap" hidden><label class="f" for="pf-link">Link to the story</label>
<input class="inp" type="url" id="pf-link" maxlength="1800" placeholder="https://www.ksat.com/news/…" inputmode="url" autocomplete="off" autocapitalize="off" spellcheck="false">
<p class="help">Paste the story's address (it starts with https://). It opens inside Chisme's reader, not another app.</p></div>
<p class="err" id="pf-err" role="alert" hidden></p>
<p class="pvh">Preview <small style="font-weight:600;color:var(--muted)">roughly how it looks on a phone</small></p>
<div class="phone" id="pv" aria-label="Notification preview"><div class="clk" id="pv-clk">9:41</div><div class="dt" id="pv-dt">Today</div>
<div class="ntf"><img src="/static/icons/apple-touch-icon.png" alt="" width="38" height="38"><div class="nb"><div class="nh"><span>Chisme</span><span>now</span></div>
<div class="nt" id="pv-t"></div><div class="nm" id="pv-m"></div></div></div><p class="nl" id="pv-l"></p></div>
<button type="submit" class="big go" id="pf-send"{dis}>{e(send_lbl)}</button>
<p class="res" id="pf-res" role="status" aria-live="polite"></p></form>
<dialog class="sheet" id="pf-confirm" aria-labelledby="pf-confirm-h"><div class="sheet-b"><h3 id="pf-confirm-h">Send this to {plural(n_news, 'phone')}?</h3>
<p class="sub" style="margin:0 0 10px">Everyone with news alerts on gets it right away. It can't be taken back.</p>
<div class="ntf"><img src="/static/icons/apple-touch-icon.png" alt="" width="38" height="38"><div class="nb"><div class="nh"><span>Chisme</span><span>now</span></div>
<div class="nt" id="pf-pt"></div><div class="nm" id="pf-pm"></div></div></div><p class="sub" id="pf-pl"></p>
<div class="two"><button type="button" class="big" id="pf-no">Cancel</button><button type="button" class="big go" id="pf-yes">Yes, send it</button></div></div></dialog>
</section>"""

    # ---- auto-alerts card
    on = bool(i.get("on"))
    st_cls = "status" + (" on" if on and enabled else "") + (" hot" if on and (i.get("quiet") or int(i.get("today") or 0) >= int(i.get("cap") or 2)) else "")
    last = i.get("last") or None
    last_txt = f"{clock(last.get('ts'), now)} · {plain_result(last)}" if last else "No check yet."
    auto = f"""<section class="card auto" id="auto" aria-labelledby="auto-h"><h2 id="auto-h">📡 Auto-alerts for big news</h2>
<label class="sw" for="auto-on"><span id="auto-on-l">Auto-alerts are {"on" if on else "off"}</span><input type="checkbox" role="switch" id="auto-on"{" checked" if on else ""}{dis}></label>
<p class="{st_cls}" id="auto-status"><span class="dot" aria-hidden="true"></span><span id="auto-status-t">{e(status_line(info))}</span></p>
<p class="sub">Only truly major San Antonio or breaking stories: never more than {int(i.get("cap") or 2)} a day, never 10pm–7am, never the same story twice.</p>
<p class="sub"><b>Last check:</b> <span id="auto-last">{e(last_txt)}</span></p>
<button type="button" class="big" id="auto-check"{dis}><span aria-hidden="true">🔎</span> Run a check now</button>
<p class="res" id="auto-res" role="status" aria-live="polite"></p></section>"""

    # ---- v49.10: 🔄 Refresh everyone now (bumps the token every open Chisme checks about once a minute)
    rts = (refresh or {}).get("ts")
    rcard = f"""<section class="card rf" id="rf" aria-labelledby="rf-h"><h2 id="rf-h">🔄 Refresh everyone</h2>
<p class="sub">Every open Chisme reloads to the newest version within about a minute. Anyone in the middle of a game gets a "Refresh" button instead and reloads once they leave the game.</p>
<p class="sub"><b>Last pushed:</b> <span id="rf-last">{e(clock(rts, now)) if rts else "never"}</span></p>
<button type="button" class="big go" id="rf-go"><span aria-hidden="true">🔄</span> Refresh everyone now</button>
<p class="res" id="rf-res" role="status" aria-live="polite"></p>
<dialog class="sheet" id="rf-confirm" aria-labelledby="rf-confirm-h"><div class="sheet-b"><h3 id="rf-confirm-h">Refresh everyone's Chisme?</h3>
<p class="sub">Every open copy of Chisme (phones and computers) reloads to the newest version within about a minute.</p>
<div class="two"><button type="button" class="big" id="rf-no">Cancel</button><button type="button" class="big go" id="rf-yes">Yes, refresh everyone</button></div></div></dialog></section>"""

    # ---- at a glance
    s1, s7 = S[1], S[7]
    glance = f"""<h2 class="sec">📊 At a glance</h2>{"".join(sbanners)}<div class="glance">
<div class="gl"><div class="n">{fmt(s1["u"]["all"])}</div><div class="l">Today</div><div class="s">{plural(s1["u"]["all"], "visitor")} · {plural(s1["c"].get("open", 0), "open")}</div></div>
<div class="gl"><div class="n">{fmt(s7["u"]["all"])}</div><div class="l">This week</div><div class="s">{plural(s7["u"]["all"], "visitor")} in 7 days</div></div>
<div class="gl"><div class="n" id="gl-subs">{fmt(n_news) if has_push else "—"}</div><div class="l">Subscribers</div><div class="s">phones with news alerts on</div></div>
<div class="gl"><div class="n">{fmt(s7["u"]["app"])}</div><div class="l">Installed app</div><div class="s">phones using the Home Screen app this week</div></div></div>"""
    top7 = _story_rows(r, s7["c"], 5)
    top_html = ("<ol class='topl'>" + "".join(f'<li><span class="tt">{lab}</span><span class="tv">{fmt(v)}</span></li>' for lab, v in top7) + "</ol>") if top7 else \
        '<p class="empty">No stories opened yet this week. Once people start reading, the most-read ones show up here.</p>'
    tops = f'<section class="card glance-top" id="top-week" style="margin-top:12px"><h2>📰 Most-read stories this week</h2><p class="sub" style="margin:0">times opened in Chisme</p>{top_html}</section>'

    # ---- folded sections
    c30 = S[30]["c"]
    tabs = [(e(stats.TAB_NAMES.get(k, k)), v) for k, v in stats._top(c30, "tab:", 10)]
    games = [(e({"loteria": "Chismería", "juan": "The Juan That Got Away", "icebebe": "The Juan That Got Away (old runner)"}.get(k, k)), v) for k, v in stats._top(c30, "game:")]
    cities = [(e(k), v) for k, v in stats._top(c30, "city:", 10)]
    a2 = [(e(stats.A2HS_NAMES.get(k, k)), v) for k, v in stats._top(c30, "a2hs:")]
    tab_btns = "".join(f'<button type="button" role="tab" id="t{n}" aria-controls="p{n}" aria-selected="{"true" if n == 1 else "false"}">{lab}</button>'
                       for n, lab in ((1, "Today"), (7, "7 days"), (30, "30 days")))
    panels = "".join(f'<div class="grid" role="tabpanel" id="p{n}" aria-labelledby="t{n}"{"" if n == 1 else " hidden"}>{_period_cards(S, n)}</div>' for n in (1, 7, 30))

    def logrow_auto(x):
        return (f'<li><span class="pl-t"><a href="{e(x.get("link") or "#")}" target="_blank" rel="noopener noreferrer">{e(x.get("title") or "")}</a>'
                f'{" <small>" + e(x.get("source")) + "</small>" if x.get("source") else ""}</span>'
                f'<span class="pl-m">{e(clock(x.get("ts"), now))} · score {int(x.get("score") or 0)} · {e(", ".join(x.get("why") or []))}</span>'
                f'<span class="pl-n">{e(send_result({"ok": True, **x}))}</span></li>')

    def logrow_manual(x):
        return (f'<li><span class="pl-t">{e(x.get("title") or "")}: {e(x.get("body") or "")}</span><span class="pl-m">{e(clock(x.get("ts"), now))}</span>'
                f'<span class="pl-n">{e(send_result({"ok": True, **x}))}</span></li>')
    alog, mlog = i.get("log") or [], i.get("manual") or []
    auto_hist = (('<ol class="plog">' + "".join(logrow_auto(x) for x in alog) + '</ol>') if alog else
                 '<p class="empty">No automatic alerts yet. When a major San Antonio story breaks (and auto-alerts are on), it shows up here.</p>')
    auto_hist += (f'<div class="pills" style="margin-top:10px"><span class="pill{" on" if i.get("gemini") else ""}">AI double-check: {"on (Gemini)" if i.get("gemini") else "off · keywords only (stricter)"}</span>'
                  f'<span class="pill">{plural(i.get("near"), "subscriber")} within {int(i.get("radius") or 100)} km of San Antonio</span>'
                  f'<span class="pill">checks at most every {int(i.get("every") or 10)} min</span></div>') if has_push else ""
    man_hist = (('<ol class="plog">' + "".join(logrow_manual(x) for x in mlog) + '</ol>') if mlog else
                '<p class="empty">You haven\'t sent any yet. Your sends from the box above show up here.</p>')
    tech = (f'<dl class="kv"><dt>Stats storage</dt><dd>{e("Upstash Redis" if store_name == "upstash" else "temporary file (resets)")}</dd>'
            f'<dt>Upstash</dt><dd>{e(stats.upstash_diag() or "not set")}{"" if store_name == "upstash" else " · set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN on Render to keep the numbers"}</dd>'
            f'<dt>Notifications</dt><dd>{"ready (VAPID keys set)" if enabled else "not set up (VAPID keys missing)"}</dd>'
            f'<dt>Subscriptions</dt><dd>{plural(i.get("subs"), "phone")} in total · {plural(n_news, "phone")} with news alerts</dd>'
            f'<dt>Push storage</dt><dd>{e("Upstash" if i.get("store") == "upstash" else ("temporary file" if has_push else "unavailable"))}</dd>'
            f'<dt>Outside timer</dt><dd>{"PUSH_TICK_SECRET set: a cron can call /api/push/tick" if i.get("secret") else "not set: checks only run when someone opens the app"}</dd>'
            f'<dt>Last check (raw)</dt><dd><code>{e(str((last or {}).get("result") or "—"))}</code></dd></dl>'
            '<p class="sub">The free server sleeps when nobody visits, so automatic checks can be late until the next visit (or the outside timer). '
            'Signing out only signs out this phone. A sign-in lasts 30 days (12 hours without "Keep me signed in").</p>'
            '<button type="button" class="big" id="out-all"><span aria-hidden="true">🚪</span> Sign out everywhere</button>'
            '<p class="sub">Ends every admin sign-in on every phone and computer, this one too (use it if a phone was lost or shared). '
            'Then sign in again with the key.</p>')
    folds = "".join([
        _fold("📈 All the numbers", f'<div class="seg" role="tablist" aria-label="Period">{tab_btns}</div>{panels}', "f-all", "today · 7 · 30 days"),
        _fold("📅 Visitors per day", _chart(r, days), "f-chart", "30 days"),
        _fold("🗞️ Top stories", _bars(_story_rows(r, c30, 10), "No stories opened yet."), "f-stories", "30 days"),
        _fold("📱 Top tabs", _bars(tabs, "Nothing yet."), "f-tabs", "30 days"),
        _fold("🎮 Games", _bars(games, "No games played yet."), "f-games", "30 days"),
        _fold("📍 Cities", _bars(cities, "No cities yet."), "f-cities", "30 days"),
        _fold("📲 Add to Home Screen tutorial", _bars(a2, "Nobody has seen it yet."), "f-a2hs", "30 days"),
        _fold("📣 Notifications you sent", man_hist, "f-sent", plural(len(mlog), "recent") if mlog else ""),
        _fold("📡 Auto-alert history", auto_hist, "f-autolog", plural(len(alog), "recent") if alog else ""),
        _fold("🏆 Juan High Scores", _scores(scores, now), "f-scores", plural(len(scores), "score") if scores else ("none yet" if scores is not None else "")),
        _fold("🔧 Technical details", tech, "f-tech"),
    ])

    tpl_js = json.dumps({k: {"t": t, "m": m, "w": w} for k, _, t, m, w in TEMPLATES}, ensure_ascii=False)
    where_js = json.dumps({k: p for k, _, p in WHERE})
    updated = "Updated " + datetime.fromtimestamp(now, TZ).strftime("%-I:%M %p CT")
    body = (header(updated) + f'<main>{"".join(banners)}{tip}{send if has_push else ""}{auto if has_push else ""}{rcard}{glance}{tops}{tia_card(tia) if tia is not None else ""}'
            f'<h2 class="sec">More</h2>{folds}'
            '<footer>Chisme counts anonymous visits: no names, no IPs, no ads, no third parties. Visitors are counted from a random ID on each phone, hashed on the server and never stored as-is.</footer>'
            '</main><div class="toast" id="toast" role="status" aria-live="polite"></div>')
    sc = f'<script nonce="{e(nonce)}">' if nonce else "<script>"
    return (HEAD.replace("%%TITLE%%", "Chisme Admin") + body + sc + SCRIPT.replace("%%TPL%%", tpl_js).replace("%%WHERE%%", where_js)
            .replace("%%N%%", str(n_news)) + "</script>" + sc + SCORES_JS + "</script>" + sc + REFRESH_JS + "</script></body></html>")



REFRESH_JS = r"""(function(){
var oa=document.getElementById('out-all');if(oa)oa.onclick=function(){if(!confirm('Sign out everywhere? Every phone and computer signed in to Chisme Admin (this one too) will need the key again.'))return;
  oa.disabled=true;fetch('/stats/logout-all',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'})
  .then(function(r){return r.json().catch(function(){return {ok:false}})}).then(function(j){if(j.ok)location.href='/stats';else{oa.disabled=false;alert('Couldn\'t sign out everywhere: '+(j.error||'try again'))}})
  .catch(function(){oa.disabled=false;alert('No connection. Try again.')})};
})();
(function(){
var $=function(id){return document.getElementById(id)},go=$('rf-go'),dlg=$('rf-confirm'),res=$('rf-res');if(!go)return;
function toast(m,bad){var t=$('toast');t.textContent=m;t.className='toast show'+(bad?' bad':'');setTimeout(function(){t.className='toast'},bad?7000:4500)}
go.onclick=function(){$('toast').className='toast';if(dlg.showModal)dlg.showModal();else if(confirm('Refresh everyone\'s Chisme?'))push()};
$('rf-no').onclick=function(){dlg.close()};dlg.addEventListener('click',function(ev){if(ev.target===dlg)dlg.close()});
$('rf-yes').onclick=function(){dlg.close();push()};
function push(){go.disabled=true;res.className='res';res.textContent='Pushing…';
  fetch('/stats/refresh',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'})
  .then(function(r){if(r.status===401){toast('You were signed out. Reloading…',true);setTimeout(function(){location.reload()},1500)}return r.json().catch(function(){return {ok:false,error:'the server answered '+r.status}})})
  .then(function(j){if(j.ok){$('rf-last').textContent=j.last||'just now';res.className='res ok';res.textContent='✅ Pushed. Open Chismes reload within about a minute.'}
    else{res.className='res bad';res.textContent='Not pushed: '+(j.error||'error')}toast((j.ok?'':'❗ ')+res.textContent,!j.ok)})
  .catch(function(){res.className='res bad';res.textContent='Not pushed: no connection';toast('❗ Not pushed: no connection',true)})
  .then(function(){go.disabled=false})}
})();"""

SCRIPT = r"""(function(){
var $=function(id){return document.getElementById(id)};
var TPL=%%TPL%%, WHERE=%%WHERE%%, N=%%N%%;
var toastT;
function toast(msg,bad){var t=$('toast');t.textContent=msg;t.className='toast show'+(bad?' bad':'');clearTimeout(toastT);toastT=setTimeout(function(){t.className='toast'+(bad?' bad':'')},bad?7000:4500)}
function post(path,body){return fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})})
  .then(function(r){if(r.status===401){toast('You were signed out. Reloading…',true);setTimeout(function(){location.reload()},1500)}
    return r.json().catch(function(){return {ok:false,error:'the server answered '+r.status}}).then(function(j){if(!r.ok&&j.ok!==false)j.ok=false;return j})})}
function plural(n,one,many){return n.toLocaleString()+' '+(n===1?one:(many||one+'s'))}
$('refresh')&&($('refresh').onclick=function(){location.reload()});
// tabs inside "All the numbers"
document.querySelectorAll('[role=tab]').forEach(function(b){b.onclick=function(){document.querySelectorAll('[role=tab]').forEach(function(x){var on=x===b;x.setAttribute('aria-selected',on);$(x.getAttribute('aria-controls')).hidden=!on})}});
// the Home Screen tip (not when already installed, not after ✕)
try{var standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true, ios=/iP(hone|ad|od)/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  if(!standalone&&!localStorage.getItem('chisme-admin-a2hs-x')&&matchMedia('(pointer:coarse)').matches){$('a2hs-tip').hidden=false;
    if(!ios)$('a2hs-how').innerHTML='in Chrome tap <b>⋮</b> → <b>Add to Home screen</b>';}
  $('a2hs-x').onclick=function(){localStorage.setItem('chisme-admin-a2hs-x','1');$('a2hs-tip').hidden=true};}catch(_){}
var form=$('pf-form'); if(!form) return;
var title=$('pf-title'),msg=$('pf-msg'),where=$('pf-where'),link=$('pf-link'),err=$('pf-err'),btn=$('pf-send'),res=$('pf-res'),dlg=$('pf-confirm');
var NAMES={news:'Opens Chisme → News',weather:'Opens Chisme → Weather',juegos:'Opens Chisme → Juegos',events:'Opens Chisme → Events',sports:'Opens Chisme → Sports'};
function host(u){try{return new URL(u).hostname.replace(/^www\./,'')}catch(_){return ''}}
function opens(){var w=where.value;if(w!=='link')return NAMES[w]||'Opens Chisme';var u=link.value.trim();return u?'Opens the story inside Chisme'+(host(u)?' · '+host(u):''):'Paste the story link above'}
function vals(){var w=where.value;return {title:title.value.trim(),message:msg.value.trim(),link:w==='link'?link.value.trim():WHERE[w]}}
function problem(){var v=vals();if(!v.message)return 'Write a message first.';
  if(where.value==='link'){if(!v.link)return 'Paste the story\'s link, or choose a place in the app.';if(!/^https?:\/\/[^\s<>"']{4,}$/i.test(v.link))return 'That link doesn\'t look right. It should start with https://';}
  return ''}
function upd(){var v=vals();$('pv-t').textContent=v.title||'Chisme';$('pv-m').textContent=v.message||'(your message)';$('pv-l').textContent='Tap → '+opens().replace(/^Opens /,'opens ');
  $('pf-tc').textContent=title.value.length+' / 80';$('pf-mc').textContent=msg.value.length+' / 240';$('pf-link-wrap').hidden=where.value!=='link';
  var d=new Date();$('pv-clk').textContent=d.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}).replace(/\s?[AP]M$/i,'');$('pv-dt').textContent=d.toLocaleDateString([], {weekday:'long',month:'long',day:'numeric'});
  if(!err.hidden){var p=problem();err.textContent=p;err.hidden=!p}}
[title,msg,link].forEach(function(x){x.addEventListener('input',function(){document.querySelectorAll('.chip').forEach(function(c){c.setAttribute('aria-pressed','false')});upd()})});
where.addEventListener('change',function(){upd();if(where.value==='link')link.focus()});
document.querySelectorAll('.chip').forEach(function(c){c.onclick=function(){var t=TPL[c.dataset.tpl];title.value=t.t;msg.value=t.m;where.value=t.w;
  document.querySelectorAll('.chip').forEach(function(x){x.setAttribute('aria-pressed',x===c?'true':'false')});err.hidden=true;upd();
  if(t.w==='link'&&!link.value)link.focus();}});
function setCount(n){N=n;var c=$('push-count');c.querySelector('b').textContent=n.toLocaleString();c.childNodes[1].nodeValue=n===1?' phone will get it':' phones will get it';
  btn.textContent=n?'Send to '+plural(n,'phone')+'…':'Send…';$('pf-confirm-h').textContent='Send this to '+plural(n,'phone')+'?';if($('gl-subs'))$('gl-subs').textContent=n.toLocaleString()}
form.addEventListener('submit',function(ev){ev.preventDefault();var p=problem();if(p){err.textContent=p;err.hidden=false;toast(p,true);return}err.hidden=true;
  var v=vals();$('pf-pt').textContent=v.title||'Chisme';$('pf-pm').textContent=v.message;$('pf-pl').textContent='Tap → '+opens().replace(/^Opens /,'opens ');
  $('toast').className='toast';if(dlg.showModal)dlg.showModal();else if(confirm('Send this to '+plural(N,'phone')+'?'))send()});
$('pf-no').onclick=function(){dlg.close()};
dlg.addEventListener('click',function(e){if(e.target===dlg)dlg.close()});
$('pf-yes').onclick=function(){dlg.close();send()};
function send(){btn.disabled=true;var old=btn.textContent;btn.textContent='Sending…';res.className='res';res.textContent='Sending…';
  var v=vals();post('/stats/push/send',v).then(function(j){res.className='res '+(j.ok?'ok':'bad');res.textContent=j.text||(j.ok?'Sent':'Not sent: '+(j.error||'error'));toast((j.ok?'✅ ':'❗ ')+res.textContent,!j.ok);
    if(j.ok&&j.total)logSent(v,res.textContent);refreshInfo()})
  .catch(function(e){res.className='res bad';res.textContent='Not sent: no connection ('+e.message+')';toast('❗ '+res.textContent,true)})
  .then(function(){btn.disabled=false;btn.textContent=old;setCount(N)})}
function logSent(v,txt){var box=document.querySelector('#f-sent .fold-b');if(!box)return;var ol=box.querySelector('ol');if(!ol){box.innerHTML='';ol=document.createElement('ol');ol.className='plog';box.appendChild(ol)}
  var li=document.createElement('li'),a=document.createElement('span'),b=document.createElement('span'),c=document.createElement('span');a.className='pl-t';b.className='pl-m';c.className='pl-n';
  a.textContent=(v.title||'Chisme')+': '+v.message;b.textContent='just now';c.textContent=txt;li.append(a,b,c);ol.insertBefore(li,ol.firstChild)}
function applyInfo(j){if(!j||!j.ok)return;setCount(j.news);var sw=$('auto-on');sw.checked=j.on;$('auto-on-l').textContent='Auto-alerts are '+(j.on?'on':'off');
  $('auto-status-t').textContent=j.status;$('auto-status').className='status'+(j.on&&j.enabled?' on':'')+(j.on&&(j.quiet||j.today>=j.cap)?' hot':'');$('auto-last').textContent=j.last}
function refreshInfo(){return fetch('/stats/push/info',{credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).then(applyInfo).catch(function(){})}
var sw=$('auto-on');sw.addEventListener('change',function(){var want=sw.checked;sw.disabled=true;
  post('/stats/push/auto',{on:want}).then(function(j){if(j.ok){toast(j.on?'✅ Auto-alerts are on':'Auto-alerts are off',false);refreshInfo()}else{sw.checked=!want;toast('❗ Couldn\'t save: '+(j.error||'error'),true)}
    $('auto-on-l').textContent='Auto-alerts are '+(sw.checked?'on':'off')})
  .catch(function(){sw.checked=!want;toast('❗ Couldn\'t save: no connection',true)}).then(function(){sw.disabled=false})});
$('auto-check').onclick=function(){var b=this;b.disabled=true;var ar=$('auto-res');ar.className='res';ar.textContent='Checking the news… (this can take a few seconds)';
  post('/stats/push/check',{}).then(function(j){var t=j.plain||j.result||j.error||'Done.';ar.className='res'+(j.ok?' ok':' bad');ar.textContent=t;toast((j.ok?'🔎 ':'❗ ')+t,!j.ok);refreshInfo()})
  .catch(function(e){ar.className='res bad';ar.textContent='Couldn\'t check: no connection';toast('❗ Couldn\'t check: no connection',true)}).then(function(){b.disabled=false})};
upd();
})();"""


def login_page(error: str = "", status: int = 401, nonce: str = "") -> str:
    err = f'<p class="err" role="alert">{e(error)}</p>' if error else ""
    return (HEAD.replace("%%TITLE%%", "Chisme Admin · Sign in") + header("Private page", signed_in=False) +
            f"""<main class="login"><section class="card"><h2>Sign in</h2>
<p class="sub" style="margin:0 0 6px">Private page: only for the owner of Chisme.</p>
<form method="post" action="/stats/login" id="login-form">
<input type="text" name="username" value="admin" autocomplete="username" hidden aria-hidden="true" tabindex="-1">
<label class="f" for="key">Admin key</label>
<div class="row"><input class="inp" type="password" id="key" name="key" autocomplete="current-password" autocapitalize="off" autocorrect="off" spellcheck="false" required enterkeyhint="go">
<button type="button" class="chip" id="show" aria-pressed="false" aria-controls="key">Show</button></div>
<label class="chk"><input type="checkbox" name="remember" value="1" checked> Keep me signed in on this phone (30 days)</label>
{err}<button type="submit" class="big go" id="login-go">Sign in</button></form>
<p class="sub" style="margin-top:14px">Your admin key is the <code>ADMIN_TOKEN</code> value in Render → chisme → Environment. Your phone can save it as a password.</p></section></main>
<script{f' nonce="{e(nonce)}"' if nonce else ''}>(function(){{var k=document.getElementById('key'),s=document.getElementById('show');s.onclick=function(){{var v=k.type==='password';k.type=v?'text':'password';s.textContent=v?'Hide':'Show';s.setAttribute('aria-pressed',v)}};k.focus()}})();</script></body></html>""")


def manifest() -> dict:
    return {"id": "/stats", "name": "Chisme Admin", "short_name": "Chisme Admin", "start_url": "/stats", "scope": "/stats",
            "display": "standalone", "background_color": "#f4f3ef", "theme_color": "#0a0a0a",
            "description": "Send notifications and see how Chisme is doing (owner only).",
            "icons": [{"src": "/static/icons/admin-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "/static/icons/admin-512.png", "sizes": "512x512", "type": "image/png"}]}


# v49.5: the 🏆 Juan High Scores manager (self-contained; talks to /stats/juan/scores/..., which gets the /stats cookie)
SCORES_JS = r"""(function(){
var list=document.getElementById('hs-list'),clr=document.getElementById('hs-clear'),dlg=document.getElementById('hs-confirm');if(!clr)return;
var sayT;function say(m,bad){var t=document.getElementById('toast');if(!t)return;t.textContent=m;t.className='toast show'+(bad?' bad':'');clearTimeout(sayT);sayT=setTimeout(function(){t.className='toast'+(bad?' bad':'')},bad?7000:4500)}
function call(method,path,body){return fetch(path,{method:method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):(method==='GET'?undefined:'{}')})
  .then(function(r){if(r.status===401){say('You were signed out. Reloading…',true);setTimeout(function(){location.reload()},1500)}return r.json().catch(function(){return {ok:false,error:'HTTP '+r.status}})})}
function count(){var n=list?list.children.length:0;var s=document.querySelector('#f-scores summary small');if(s)s.textContent=n?(n+(n===1?' score':' scores')):'none yet';
  [].forEach.call(list?list.children:[],function(li,i){li.querySelector('.hs-rk').textContent=i+1});
  document.getElementById('hs-empty').hidden=!!n;clr.hidden=!n;var c=document.getElementById('hs-confirm-n');if(c)c.textContent='All '+n+(n===1?' score':' scores')+' will be deleted for good. This can\'t be undone.'}
if(list)list.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b)return;var li=b.closest('.hs-row'),id=li.dataset.id,path='/stats/juan/scores/'+encodeURIComponent(id);
  if(b.classList.contains('hs-save')){var inp=li.querySelector('.hs-name'),v=inp.value.replace(/\s+/g,' ').trim().slice(0,12);b.disabled=true;
    call('PATCH',path,{name:v}).then(function(j){if(j.ok){inp.value=j.score.name;say('✅ Saved: '+j.score.name)}else say('❗ Couldn\'t save: '+(j.error||'error'),true)}).catch(function(){say('❗ Couldn\'t save: no connection',true)}).then(function(){b.disabled=false})}
  else if(b.classList.contains('hs-del')){if(!b.classList.contains('arm')){b.classList.add('arm');b.dataset.t=b.textContent;b.textContent='Tap again';setTimeout(function(){if(b.isConnected&&b.classList.contains('arm')){b.classList.remove('arm');b.textContent=b.dataset.t}},4000);return}
    b.disabled=true;call('DELETE',path).then(function(j){if(j.ok){li.remove();count();say('🗑️ Deleted')}else{b.disabled=false;say('❗ Couldn\'t delete: '+(j.error||'error'),true)}}).catch(function(){b.disabled=false;say('❗ Couldn\'t delete: no connection',true)})}});
if(list)list.addEventListener('keydown',function(ev){if(ev.key==='Enter'&&ev.target.classList.contains('hs-name')){ev.preventDefault();ev.target.closest('.hs-row').querySelector('.hs-save').click()}});
clr.onclick=function(){if(dlg&&dlg.showModal)dlg.showModal();else if(confirm('Clear the whole board?'))go()};
document.getElementById('hs-no').onclick=function(){dlg.close()};
function go(){var y=document.getElementById('hs-yes');y.disabled=true;call('POST','/stats/juan/scores/clear',{confirm:'CLEAR'}).then(function(j){if(j.ok){if(list)list.innerHTML='';count();say('🧹 Board cleared ('+j.cleared+')')}else say('❗ Couldn\'t clear: '+(j.error||'error'),true)})
  .catch(function(){say('❗ Couldn\'t clear: no connection',true)}).then(function(){y.disabled=false;if(dlg.open)dlg.close()})}
document.getElementById('hs-yes').onclick=go;
})();"""
