"""v49.14: Chisme as a desktop website, kept out of app.py so merges stay easy (app.py only calls website.install(app)).

* SEO + sharing for "/" (title, description, canonical, Open Graph, Twitter card) and the store-ready pages /about and
  /support; robots.txt and sitemap.xml. Every absolute URL comes from PUBLIC_BASE_URL (default: the request's origin),
  so moving to https://chisme.co is one env change.
* The desktop layer: "/" gets static/desktop.css (only applied at >= 1024 px) and static/desktop.js; phones keep the app
  exactly as it is. desktop.js builds the top nav, the homepage hero (QR code from /qr.svg), the story grid, the sidebar
  widgets, the sponsor card (GET /api/sponsors, from data/sponsors.json) and the desktop footer.
* /privacy and /terms get the site footer (and, with ?embed=1 inside the in-app reader, no page chrome).
* Domain move prep, OFF by default: DOMAIN_REDIRECT=1 sends browser page loads on the old host (chisme.onrender.com) to
  PUBLIC_BASE_URL with a 301 (never the service worker, manifest, API, static files, /stats or the installed app's
  start URL); MOVED_BANNER=1 tells installed users on the old origin to re-add Chisme from the new one.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

import qrsvg

BASE = Path(__file__).parent
CT = ZoneInfo("America/Chicago")
CONTACT_EMAIL = "bexartalkradio@gmail.com"     # the contact the repo already uses (legal/*.md, Settings, the footer)
BMC_URL = "https://buymeacoffee.com/Chismoso"
GOAL_TITLE, GOAL_AMOUNT = "Help get Chisme on the App Store", 99   # Apple's developer fee, one year
OLD_HOSTS_DEFAULT = "chisme.onrender.com"
DESKTOP_MIN = 1024   # px; the same number is in desktop.css's <link media> and desktop.js

TITLE = "Chisme · San Antonio news, food & games for los metiches"
DESC = ("Chisme, the community for los metiches: San Antonio news, sports, events, weather, food and games in one "
        "free app. Made for the waiting room.")
OG_IMAGE = "/static/site/og-image.png"
OG_ALT = "Chisme, the community for los metiches: San Antonio news, food and games"

_HOST_RX = re.compile(r"^[A-Za-z0-9.-]{1,253}(:\d{1,5})?$")
_BASE_RX = re.compile(r"^https?://[A-Za-z0-9.-]{1,253}(:\d{1,5})?$")


# ---------------------------------------------------------------- the public origin
def _flag(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def configured_base() -> str | None:
    """PUBLIC_BASE_URL as an origin ("https://chisme.co"), or None when unset/invalid."""
    v = (os.environ.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    return v if _BASE_RX.match(v) else None


def request_origin(request: Request) -> str:
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower() or request.url.scheme
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    if not _HOST_RX.match(host):
        host = request.url.netloc if _HOST_RX.match(request.url.netloc or "") else "localhost"
    return f"{proto if proto in ('http', 'https') else 'http'}://{host}"


def public_base(request: Request) -> str:
    return configured_base() or request_origin(request)


def _host_of(origin: str) -> str:
    return (urllib.parse.urlsplit(origin).hostname or "").lower()


# ---------------------------------------------------------------- the Día de Muertos label (same dates as index.html)
_SEASON = (datetime(2026, 10, 3, 5, tzinfo=timezone.utc), datetime(2026, 11, 4, 6, tzinfo=timezone.utc))


def season_on() -> bool:
    o = (os.environ.get("THEME_OVERRIDE") or "auto").strip().lower()
    if o in ("off", "muertos"):
        return o == "muertos"
    return _SEASON[0] <= datetime.now(timezone.utc) < _SEASON[1]


def dieta_label() -> str:
    return "Ofrendas" if season_on() else "¿Y la dieta?"


# ---------------------------------------------------------------- domain move
REDIRECT_PAGES = ("/", "/about", "/support", "/privacy", "/terms")   # only real pages ever move


def redirect_target(request: Request) -> str | None:
    """Where a request on the old host should go (301), or None. Off unless DOMAIN_REDIRECT=1 and PUBLIC_BASE_URL is set."""
    base = configured_base()
    if not (_flag("DOMAIN_REDIRECT") and base) or request.method not in ("GET", "HEAD"):
        return None
    host = (request.headers.get("host") or "").split(":")[0].strip().lower()
    old = {h.strip().lower() for h in (os.environ.get("REDIRECT_FROM_HOSTS") or OLD_HOSTS_DEFAULT).split(",") if h.strip()}
    if not host or host == _host_of(base) or host not in old:
        return None
    path = request.url.path
    if path not in REDIRECT_PAGES:   # /sw.js, /manifest.webmanifest, /api/*, /static/*, /stats*, /healthz … keep working
        return None
    if request.query_params.get("source") == "pwa":   # the installed app's start URL: it keeps working (+ the moved banner)
        return None
    mode = (request.headers.get("sec-fetch-mode") or "").lower()
    if mode and mode != "navigate":   # fetch()es, e.g. the old service worker precaching "/" for its update
        return None
    if not mode and "text/html" not in (request.headers.get("accept") or ""):
        return None
    q = request.url.query
    return base + path + ("?" + q if q else "")


# ---------------------------------------------------------------- sponsors (data/sponsors.json or SPONSORS_FILE)
_sp_cache: dict = {"path": None, "mtime": None, "data": []}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


def _clean_text(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _clean_url(v) -> str | None:
    u = str(v or "").strip()
    if not u:
        return None
    p = urllib.parse.urlsplit(u)
    return u if p.scheme == "https" and p.netloc and len(u) <= 600 else None


def _clean_img(v) -> str | None:
    u = str(v or "").strip()
    if re.match(r"^/static/[A-Za-z0-9_./-]+\.(png|jpe?g|webp|svg)$", u) and ".." not in u:
        return u
    return _clean_url(u)


def _day(v) -> date | None:
    try:
        return date.fromisoformat(str(v)) if v else None
    except ValueError:
        return None


def _weight(v) -> int:
    try:
        return max(1, min(10, int(v or 1)))
    except (TypeError, ValueError):
        return 1


def sponsors_file() -> Path:
    p = os.environ.get("SPONSORS_FILE")
    return Path(p) if p else BASE / "data" / "sponsors.json"


def load_sponsors() -> list[dict]:
    """The valid sponsor entries (bad ones are skipped, never shown). Re-read whenever the file changes."""
    p = sponsors_file()
    try:
        mt = p.stat().st_mtime
    except OSError:
        return []
    if _sp_cache["path"] == str(p) and _sp_cache["mtime"] == mt:
        return _sp_cache["data"]
    out: list[dict] = []
    try:
        raw = json.loads(p.read_text())
        for s in (raw.get("sponsors") if isinstance(raw, dict) else raw) or []:
            if not isinstance(s, dict):
                continue
            sid, name, url = str(s.get("id") or "").strip().lower(), _clean_text(s.get("name"), 60), _clean_url(s.get("url"))
            if not (_SLUG.match(sid) and name and url):
                continue
            out.append({"id": sid, "name": name, "url": url, "tagline": _clean_text(s.get("tagline"), 140),
                        "area": _clean_text(s.get("area"), 40), "cta": _clean_text(s.get("cta"), 28) or "Visit " + name[:20],
                        "image": _clean_img(s.get("image")), "alt": _clean_text(s.get("alt"), 120),
                        "adult": s.get("adult") is True, "active": s.get("active") is not False,
                        "start": _day(s.get("start")), "end": _day(s.get("end")),
                        "weight": _weight(s.get("weight"))})
    except (OSError, ValueError, TypeError):
        out = []
    _sp_cache.update(path=str(p), mtime=mt, data=out)
    return out


def live_sponsors(adult: bool, today: date | None = None) -> tuple[list[dict], int]:
    """Active sponsors running today (Chicago date). Beer / ice-house (adult) ones only with the 21+ setting on."""
    today = today or datetime.now(CT).date()
    run = [s for s in load_sponsors() if s["active"] and (not s["start"] or s["start"] <= today) and (not s["end"] or today <= s["end"])]
    shown = [s for s in run if adult or not s["adult"]]
    pub = [{k: v for k, v in s.items() if k not in ("active", "start", "end")} for s in shown]
    return pub, len(run) - len(shown)


# ---------------------------------------------------------------- HTML helpers
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def head_tags(base: str, path: str, title: str, desc: str, og_type: str = "website") -> str:
    url = base + path
    img = base + OG_IMAGE
    return "\n".join([
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{esc(url)}">',
        '<meta property="og:site_name" content="Chisme">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{esc(url)}">',
        f'<meta property="og:image" content="{esc(img)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{esc(OG_ALT)}">',
        '<meta property="og:locale" content="en_US">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{esc(img)}">',
        f'<meta name="twitter:image:alt" content="{esc(OG_ALT)}">',
    ])


def app_build() -> str:
    m = re.search(r'VERSION\s*=\s*"chisme-v(\d+(?:\.\d+)?)"', (BASE / "static" / "sw.js").read_text())
    return m.group(1) if m else "0"


def site_footer() -> str:
    """The footer on every desktop page (desktop.js builds the same links inside the app)."""
    return f"""<footer class="site-foot" id="site-foot">
  <div class="sf-in">
    <div class="sf-brand"><img src="/static/icons/icon-192.png" alt="" width="44" height="44" loading="lazy">
      <div><p class="sf-name">Chisme</p><p class="sf-tag">Chisme, the community for los metiches. Made in San Antonio, Texas.</p></div></div>
    <nav class="sf-links" aria-label="Chisme pages">
      <a href="/">Home</a><a href="/about">About</a><a href="/support">Support &amp; contact</a><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a>
    </nav>
    <p class="sf-tip"><a class="sf-bmc" href="{BMC_URL}" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">☕</span> {esc(GOAL_TITLE)}, ${GOAL_AMOUNT}</a></p>
    <p class="sf-fine">© {datetime.now(CT).year} Chisme · Stories belong to their publishers; Chisme links to them and credits them.</p>
  </div>
</footer>"""


def site_nav(active: str = "") -> str:
    tabs = [("/#chisme", "📰", "Chisme"), ("/#weather", "🌤️", "Weather"), ("/#dieta", "🌮", dieta_label()), ("/#juegos", "🎲", "Juegos")]
    links = "".join(f'<a href="{h}"><span aria-hidden="true">{e}</span> {esc(t)}</a>' for h, e, t in tabs)
    return f"""<header class="site-nav">
  <div class="sn-in">
    <a class="sn-logo" href="/" aria-label="Chisme home"><img src="/static/icons/icon-192.png" alt="" width="40" height="40"><span>Chisme</span></a>
    <nav class="sn-tabs" aria-label="Sections">{links}</nav>
    <a class="sn-get" href="/#get-app">📲 Get the app</a>
  </div>
</header>"""


_HREF = re.compile(r'<a\b([^>]*?)\bhref="([^"]*)"([^>]*)>', re.I)
_EMBED_PAGES = ("/about", "/support", "/privacy", "/terms")


def embedify(html: str) -> str:
    """Inside the reader panel (a sandboxed iframe that can't navigate the app), keep Chisme's own pages
    chrome-less (?embed=1) and send everything else (other sites, mail, the app itself) to a new tab."""
    def fix(m: "re.Match") -> str:
        pre, href, post = m.group(1), m.group(2), m.group(3)
        attrs = pre + post
        path, _, frag = href.partition("#")
        if path in _EMBED_PAGES:
            return f'<a{pre}href="{path}?embed=1{"#" + frag if frag else ""}"{post}>'
        if href.startswith("#") or "target=" in attrs:
            return m.group(0)
        return f'<a{pre}href="{href}"{post} target="_blank" rel="noopener noreferrer">'
    return _HREF.sub(fix, html)


def page_shell(request: Request, path: str, title: str, desc: str, body: str, embed: bool) -> HTMLResponse:
    base, b = public_base(request), app_build()
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{head_tags(base, path, title, desc)}
<meta name="theme-color" content="#00C9CD">
<link rel="icon" href="/static/icons/favicon.ico" sizes="any">
<link rel="icon" href="/static/icons/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png" sizes="180x180">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/static/site.css?v={b}">
</head>
<body class="site{' embed' if embed else ''}">
{'' if embed else '<a class="skip" href="#main">Skip to the content</a>'}
{'' if embed else site_nav()}
<main id="main" class="site-main">
{body}
</main>
{'' if embed else site_footer()}
</body>
</html>"""
    if embed:
        page = embedify(page)
    return HTMLResponse(page, headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------- the pages
ABOUT_TITLE = "About Chisme · the community for los metiches"
ABOUT_DESC = "Chisme is a free San Antonio app for local news, sports, events, weather, food videos and games, hosted by Tía Chismosa."
SUPPORT_TITLE = "Support & contact · Chisme"
SUPPORT_DESC = "Get help with Chisme, report a problem, ask about a local sponsor spot or request a takedown. We read every email."


def about_body() -> str:
    d = esc(dieta_label())
    return f"""<article class="prose">
<p class="kicker"><img src="/static/mascot/avatar-128.webp?art=3" alt="Tía Chismosa, Chisme's mascot" width="72" height="72"> <span>¡Hola, metiche!</span></p>
<h1>About Chisme</h1>
<p class="lead">Chisme, the community for los metiches. It's San Antonio's local news, sports, events, weather, food and games in one free app.</p>
<p>Stuck in the waiting room at your doctor's appointment? That's what Chisme is for. Open it, catch up on what's happening around town, watch a local food review, play a quick game, and you're chismeando before they call your name.</p>
<h2>What's inside</h2>
<ul class="feat">
<li><b>📰 Chisme</b>: local news, sports and events mixed into one feed, closest to you first. Stories open inside Chisme, credited to the outlet that reported them.</li>
<li><b>🌤️ Weather</b>: National Weather Service forecasts and alerts, plus live rain radar.</li>
<li><b>🌮 ¿Y la dieta?</b>{" (Ofrendas during Día de Muertos)" if d == "Ofrendas" else ""}: San Antonio's food creators taste-test so you don't have to guess. Save the spots worth the drive.</li>
<li><b>🎲 Juegos</b>: Chismería, our take on Lotería, and The Juan That Got Away. They work offline.</li>
<li><b>☕ Tía Chismosa</b>: the app's mascot. Ask her what's going on and she answers from what's in Chisme, with the source.</li>
</ul>
<h2>How Chisme works</h2>
<p>No account and no sign-up. Your settings, saved spots and scores stay on your phone. Chisme only uses your approximate location to find your weather and nearby stories. The details are in the <a href="/privacy">Privacy Policy</a>.</p>
<p>Chisme is free. It's paid for by tips and by a few local businesses that sponsor a spot. Every sponsored spot is clearly marked <b>Sponsored</b>. Want yours there? <a href="/support#advertise">Ask about a local sponsor spot</a>.</p>
<h2>Get it on your phone</h2>
<p>Chisme is a web app. Open it in your phone's browser and add it to your Home Screen: on iPhone, open it in Safari, tap Share, then <b>Add to Home Screen</b>. On Android, open it in Chrome, tap the ⋮ menu, then <b>Add to Home screen</b> or <b>Install app</b>. Coming soon to the App Store and Google Play.</p>
<aside class="goal-box" aria-labelledby="goal-t">
<p class="goal-t" id="goal-t">{esc(GOAL_TITLE)}, ${GOAL_AMOUNT}</p>
<p>Putting Chisme in the App Store costs ${GOAL_AMOUNT} a year. A coffee helps get it there.</p>
<p><a class="btn bmc" href="{BMC_URL}" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">☕</span> Buy Chisme a coffee</a></p>
<p class="fine">Tips go to the Chisme creator; not a charity, not tax-deductible, unlocks nothing.</p>
</aside>
<p>Questions? <a href="/support">Get in touch</a>.</p>
</article>"""


def _mailto(subject: str, body: str = "") -> str:
    q = {"subject": subject}
    if body:
        q["body"] = body
    return "mailto:" + CONTACT_EMAIL + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def support_body() -> str:
    topics = [
        ("🐞", "Report a problem", "Something broken, slow or wrong? Tell us what you tapped and what happened.",
         _mailto("Chisme: a problem", "What happened:\n\nWhat I was doing:\n\nPhone / browser:\n")),
        ("📣", "Advertise on Chisme", "A local business? Sponsor a spot that reaches local metiches.",
         _mailto("Chisme: local sponsor spot", "Business name:\nNeighborhood:\nWebsite:\n\nWhat you'd like to promote:\n")),
        ("✂️", "Remove content or report copyright", "Publishers and creators: we'll remove your content promptly.",
         _mailto("Chisme: content removal", "The content (link or screenshot):\n\nWho you are:\n")),
        ("🏆", "Delete a high-score name", "Want a Top 10 name taken down? Tell us the name and the game.",
         _mailto("Chisme: delete a high-score name", "Name on the board:\nGame:\n")),
        ("👋", "Just say hi", "Ideas, compliments, chisme tips: we read every email.", _mailto("Chisme: hello")),
    ]
    cards = "".join(f"""<li id="{'advertise' if t == 'Advertise on Chisme' else ''}" class="topic"><span class="t-emo" aria-hidden="true">{e}</span>
<div><h3>{esc(t)}</h3><p>{esc(s)}</p><a class="btn" href="{esc(m)}">Email us about this</a></div></li>""".replace(' id=""', '') for e, t, s, m in topics)
    return f"""<article class="prose">
<h1>Support &amp; contact</h1>
<p class="lead">Need a hand, metiche? Email <a href="{esc(_mailto('Chisme'))}">{CONTACT_EMAIL}</a>. We read every message.</p>
<ul class="topics">{cards}</ul>
<h2>Quick answers</h2>
<details><summary>How do I put Chisme on my phone?</summary>
<p>On iPhone, open Chisme in Safari, tap Share, then <b>Add to Home Screen</b>. On Android, open it in Chrome, tap the ⋮ menu, then <b>Add to Home screen</b> or <b>Install app</b>. It opens full screen like an app. Coming soon to the App Store and Google Play.</p></details>
<details><summary>Is Chisme free?</summary><p>Yes. No account, no subscription. Tips and a few clearly labeled local sponsors keep it running.</p></details>
<details><summary>Why does Chisme ask for my location?</summary><p>To show your weather, alerts and the stories closest to you. It's rounded to about 1 km and never sold. You can type a city or ZIP code instead. See the <a href="/privacy">Privacy Policy</a>.</p></details>
<details><summary>How do notifications work?</summary><p>Turn them on in Settings (tap Tía). Only the big stuff: breaking local news and weather warnings, two a day at most, and none overnight. On iPhone, add Chisme to your Home Screen first.</p></details>
<details><summary>A story is wrong, or Tía said something wrong.</summary><p>Stories come from local outlets, and Chisme links to the original. If Tía got something wrong about a person or a story, <a href="{esc(_mailto('Chisme: a correction'))}">tell us</a> and we'll fix it.</p></details>
<p class="legal-row">Read the <a href="/privacy">Privacy Policy</a> and the <a href="/terms">Terms of Use</a>.</p>
</article>"""


# ---------------------------------------------------------------- decorating "/" and the legal pages
_DESK_LAUNCH = """(function(){try{if(!matchMedia("(min-width: %dpx)").matches)return;var q=new URLSearchParams(location.search);
if(location.hash.length>1||q.has("tab")||q.has("story")||sessionStorage.getItem("chisme-reload-tab")||localStorage.getItem("chisme-default-tab"))return;
sessionStorage.setItem("chisme-reload-tab","chisme");}catch(e){}})();""" % DESKTOP_MIN


def decorate_index(page: str, request: Request) -> str:
    base, b = public_base(request), app_build()
    nonce = getattr(request.state, "csp_nonce", "") or ""
    page = re.sub(r"<title>.*?</title>", f"<title>{esc(TITLE)}</title>", page, count=1, flags=re.S)
    page = re.sub(r'\s*<meta name="description"[^>]*>', "", page, count=1)
    extra = [head_tags(base, "/", TITLE, DESC)]
    if configured_base():   # app.js shares this link (otherwise it keeps its built-in https://chisme.onrender.com/)
        extra.append(f'<meta name="chisme-share-url" content="{esc(configured_base() + "/")}">')
    extra.append(f'<link rel="stylesheet" href="/static/desktop.css?v={b}" media="(min-width: {DESKTOP_MIN}px)">')
    extra.append(f'<script src="/static/desktop.js?v={b}" defer></script>')
    page = page.replace("</head>", "\n".join(extra) + "\n</head>", 1)
    # desktop: open on the homepage (the Chisme tab) unless a link, ?tab, a reload or Settings → Default tab says otherwise.
    # Runs before index.html's launch script, which reads (and clears) chisme-reload-tab.
    i = page.find("<script")
    if i > 0:
        page = page[:i] + f'<script nonce="{esc(nonce)}">{_DESK_LAUNCH}</script>\n  ' + page[i:]
    return page


def decorate_legal(page: str, request: Request, path: str) -> str:
    base, b = public_base(request), app_build()
    embed = request.query_params.get("embed") == "1"
    title = "Privacy Policy · Chisme" if path == "/privacy" else "Terms of Use · Chisme"
    desc = ("How Chisme handles your information: no accounts, no ads tracking, most data stays on your phone."
            if path == "/privacy" else "The rules for using Chisme, San Antonio's free local news, food and games app.")
    tags = head_tags(base, path, title, desc, "article") if '<meta property="og:title"' not in page else ""
    page = page.replace("</head>", f'{tags}\n<link rel="stylesheet" href="/static/site.css?v={b}">\n</head>', 1)
    page = page.replace("<body>", '<body class="legal' + (' embed' if embed else '') + '">', 1)
    if not embed:
        page = page.replace("</body>", site_footer() + "\n</body>", 1)
    cb = configured_base()
    if cb and cb != "https://chisme.onrender.com":   # the policy names the site's address: follow the move
        page = page.replace('href="https://chisme.onrender.com"', f'href="{esc(cb)}"').replace(">https://chisme.onrender.com<", f">{esc(cb)}<")
    if embed:
        page = embedify(page)
    return page


# ---------------------------------------------------------------- routes
router = APIRouter()


@router.get("/about", include_in_schema=False)
async def about(request: Request):
    return page_shell(request, "/about", ABOUT_TITLE, ABOUT_DESC, about_body(), request.query_params.get("embed") == "1")


@router.get("/support", include_in_schema=False)
async def support(request: Request):
    return page_shell(request, "/support", SUPPORT_TITLE, SUPPORT_DESC, support_body(), request.query_params.get("embed") == "1")


@router.get("/contact", include_in_schema=False)
async def contact():
    return RedirectResponse("/support", status_code=308)


@router.get("/robots.txt", include_in_schema=False)
async def robots(request: Request):
    base = public_base(request)
    txt = f"# Chisme · {base}\nUser-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /stats\n\nSitemap: {base}/sitemap.xml\n"
    return Response(txt, media_type="text/plain; charset=utf-8", headers={"Cache-Control": "public, max-age=3600"})


def _lastmod(*files: Path) -> str:
    ts = [f.stat().st_mtime for f in files if f.exists()]
    return datetime.fromtimestamp(max(ts) if ts else time.time(), CT).date().isoformat()


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request):
    base = public_base(request)
    me = Path(__file__)
    pages = [("/", "hourly", "1.0", _lastmod(BASE / "static" / "index.html", me)),
             ("/about", "monthly", "0.6", _lastmod(me)), ("/support", "monthly", "0.6", _lastmod(me)),
             ("/privacy", "yearly", "0.3", _lastmod(BASE / "static" / "legal" / "privacy.html")),
             ("/terms", "yearly", "0.3", _lastmod(BASE / "static" / "legal" / "terms.html"))]
    rows = "".join(f"  <url><loc>{esc(base + p)}</loc><lastmod>{m}</lastmod><changefreq>{c}</changefreq><priority>{pr}</priority></url>\n"
                   for p, c, pr, m in pages)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


_qr_cache: dict[str, str] = {}


@router.get("/qr.svg", include_in_schema=False)
async def qr(request: Request):
    """The homepage's "open it on your phone" code: always PUBLIC_BASE_URL's homepage (never user input)."""
    url = public_base(request) + "/"
    if url not in _qr_cache:
        if len(_qr_cache) > 20:
            _qr_cache.clear()
        _qr_cache[url] = qrsvg.svg(url, title="QR code: open " + url + " on your phone")
    return Response(_qr_cache[url], media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600", "Vary": "Host"})


@router.get("/api/site")
async def api_site(request: Request):
    base = public_base(request)
    here = request_origin(request)
    moved = _flag("MOVED_BANNER") and configured_base() is not None and _host_of(here) != _host_of(base)
    raised = (os.environ.get("APP_STORE_GOAL_RAISED") or "").strip()
    return JSONResponse({"base": base, "moved": {"on": moved, "to": base + "/", "host": _host_of(base)},
                         "goal": {"title": GOAL_TITLE, "amount": GOAL_AMOUNT, "url": BMC_URL,
                                  "raised": min(GOAL_AMOUNT, int(raised)) if raised.isdigit() else None},
                         "contact": CONTACT_EMAIL, "build": app_build()}, headers={"Cache-Control": "no-store"})


@router.get("/api/sponsors")
async def api_sponsors(adult: int = Query(0, ge=0, le=1)):
    shown, hidden = live_sponsors(bool(adult))
    return JSONResponse({"sponsors": shown, "adult_hidden": hidden}, headers={"Cache-Control": "no-store"})


# ---------------------------------------------------------------- wiring
_DECORATE = ("/", "/privacy", "/terms")


def install(app: FastAPI) -> None:
    """Call right after app = FastAPI(...): adds the routes, and a middleware that sits inside app.py's own
    (so the security headers / CSP nonce / X-Chisme still apply to everything here)."""
    app.include_router(router)

    @app.middleware("http")
    async def website_layer(request: Request, call_next):
        to = redirect_target(request)
        if to:
            return RedirectResponse(to, status_code=301, headers={"Cache-Control": "public, max-age=86400"})
        resp = await call_next(request)
        path = request.url.path
        if (request.method == "GET" and path in _DECORATE and resp.status_code == 200
                and (resp.headers.get("content-type") or "").startswith("text/html")):
            body = b"".join([c async for c in resp.body_iterator]).decode("utf-8")
            body = decorate_index(body, request) if path == "/" else decorate_legal(body, request, path)
            headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-type", "etag", "last-modified")}
            return HTMLResponse(body, status_code=200, headers=headers)
        return resp
