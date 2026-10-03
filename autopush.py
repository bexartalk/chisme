"""v45: big-news auto alerts and the owner's send box (on /stats). Transport + subscriptions: push.py.

Auto alerts — only truly major local or breaking stories:
  • The app's own San Antonio news feed (the same cached build_news the News tab uses) is checked at most every
    AUTO_PUSH_CHECK_MIN minutes (default 10). Each fresh story (< 3 h old) gets a keyword score (breaking cues, serious
    incidents, emergencies, local places/agencies, several outlets on the same story; soft features, opinion, sports,
    "things to do" lists count against it).
  • With GEMINI_API_KEY, stories scoring ≥ CANDIDATE_MIN go to Gemini, which must agree it's a major breaking local
    story. Fail safe: if Gemini is missing, slow, over quota or answers garbage, only stories scoring ≥ STRICT_MIN go out
    (a higher bar), so an outage never means more pushes.
  • Hard caps (cannot be raised by env): at most 2 auto pushes per day (America/Chicago day), none from 10 PM to 7 AM
    Central, and never the same story twice: the link is claimed in Upstash (SET NX, kept 30 days) and a headline that
    looks like a recent auto push (same key words, any outlet) is skipped too.
  • The owner's on/off switch (chisme:push:auto:on, default OFF) and a log of recent auto pushes are on /stats.
    (v49.5: the page is rendered by admin.py; this module only supplies admin_info / admin_send / check.)
  • Recipients: subscribers with news alerts on whose area is within AUTO_PUSH_RADIUS_KM (default 100) of San Antonio.

When it runs (Render's free plan sleeps after ~15 min without traffic, and nothing runs while it sleeps):
  • kick(): any incoming request starts a check in the background if the last one is older than the interval (never
    awaited, never blocks the request), and once ~20 s after the server wakes up.
  • POST /api/push/tick with the PUSH_TICK_SECRET (an external cron: GitHub Actions, cron-job.org …) wakes the server
    and runs a check. Without one, a quiet night means no check until the next visitor; that's documented in README.

Upstash keys (chisme:push:auto:*): on, day:<YYYY-MM-DD> (counter, 3 days), story:<id> (dedupe, 30 days), log (last 30
auto pushes, JSON), manual (last 30 owner sends), last (the last check's summary)."""
from __future__ import annotations

import asyncio, json, math, os, re, time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

import push

TZ = ZoneInfo("America/Chicago")
K = "chisme:push:auto:"
HARD_DAILY_MAX = 2
QUIET_FROM, QUIET_TO = 22, 7          # Central time, hard
MAX_AGE = 3 * 3600                    # only fresh stories
CANDIDATE_MIN, STRICT_MIN = 8, 11     # score to ask Gemini / score to send without Gemini
DEDUPE_TTL, LOG_KEEP = 30 * 86400, 30
DEFAULT_TITLE, DEFAULT_BODY = "Chisme", "New chisme! 👀"   # v49.12: English (was ¡Órale, new chisme!)
AUTO_TITLE = "Breaking news"


def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(os.environ.get(name, default))))
    except ValueError:
        return default


daily_max = lambda: _int_env("AUTO_PUSH_DAILY_MAX", HARD_DAILY_MAX, 0, HARD_DAILY_MAX)   # can be lowered, never raised
check_every = lambda: _int_env("AUTO_PUSH_CHECK_MIN", 10, 5, 120) * 60
radius_km = lambda: _int_env("AUTO_PUSH_RADIUS_KM", 100, 10, 2000)
day_of = lambda ts: datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d")


def is_quiet(now: float) -> bool:
    h = datetime.fromtimestamp(now, TZ).hour
    return h >= QUIET_FROM or h < QUIET_TO


# ---------------------------------------------------------------- the heuristic
# Urgency and scale matter, not crime words: an arrest, a court date or one fatal crash is news, but not a push.
BREAKING = re.compile(r"\b(breaking|developing|just in|happening now|urgent|live updates?)\b", re.I)
URGENT = re.compile(r"\b(active shooter|mass shooting|manhunt|hostage|shelter[- ]in[- ]place|lockdown|evacuat\w*|amber alert|"
                    r"boil[- ]water|water outage|tornado(es)? (touch(es|ed)? down|damage|hits?|strikes?)|flash flood emergency|"
                    r"high[- ]water rescues?|wildfire|explosion|blast|(bridge|building|roof|parking garage) collapse|derail\w*|"
                    r"plane crash|hazmat|chemical (leak|spill|fire)|gas leak|state of emergency|disaster declaration|"
                    r"emergency declaration|curfew|(closed|shut down) in both directions|all (lanes|directions) (closed|shut|blocked)|"
                    r"widespread (power )?outages?|citywide)\b", re.I)
ROUTINE = re.compile(r"\b(shootings?|shot|gunfire|stabb(ed|ing)|killed|dead|deaths?|fatal(ly)?|homicide|murder(ed)?|crash|"
                     r"fire|power outages?|flooding|standoff|police chase|missing)\b", re.I)
SCALE = re.compile(r"\b((\d{2,}|several|multiple|dozens?|hundreds?|thousands?|\d{1,3},\d{3}) (people|dead|killed|injured|hurt|"
                   r"homes|residents|students|customers|families|without power)|mass casualty)\b", re.I)
AFTERMATH = re.compile(r"\b(arrested|charged|indicted|sentenced|pleads?|plea|trial|court|lawsuit|sues?|suspect identified|"
                       r"identified as|victims? identified|years after|cold case|anniversary|remember(ed|ing)?|vigil|funeral|"
                       r"bond|jury|appeal|investigation continues|update on)\b", re.I)
LOCAL = re.compile(r"\b(san antonio|bexar|sapd|bcso|safd|alamo city|alamo heights|leon valley|converse|universal city|live oak|schertz|"
                   r"cibolo|selma|new braunfels|boerne|helotes|kirby|windcrest|castle hills|balcones heights|china grove|elmendorf|"
                   r"von ormy|somerset|lackland|jbsa|fort sam|randolph afb|saws|cps energy|via metropolitan|northside isd|neisd|saisd|"
                   r"utsa|ih?-35|ih?-10|ih?-37|loop 410|loop 1604|(us|u\.s\.) ?-?281|(highway|hwy) 151|medina river|salado creek|"
                   r"san antonio river|leon creek)\b", re.I)
SOFT = re.compile(r"\b(opinion|editorial|column|commentary|review|recipe|things to do|where to eat|weekend guide|this weekend|horoscope|"
                  r"sponsored|podcast|quiz|giveaway|deals?|coupon|obituary|look back|throwback|photos|gallery|ranking|ranked|"
                  r"top \d+|\d+ (best|things|places)|best \w+ in|how to|explainer|what to know|recap|preview|watch:|video:|data:|data shows|analysis|by the numbers|survey|study)\b", re.I)
SPORTS = re.compile(r"\b(spurs|wembanyama|wemby|missions|rampage|sa fc|nba|nfl|mlb|wnba|playoffs?|preseason|quarterback|touchdown|"
                    r"draft pick|box score|roster|trade|game \d+)\b", re.I)


def score(s: dict, now: float | None = None) -> tuple[int, list[str]]:
    """Keyword + signal score for one story, and the reasons (shown in the /stats log)."""
    now = now or time.time()
    title = s.get("title") or ""
    t = title + " " + (s.get("summary") or "")[:300]
    sc, why = 0, []
    brk = bool(BREAKING.search(title))
    if brk:
        sc += 3; why.append("breaking")
    urg = sorted({m.group(0).lower() for m in URGENT.finditer(t)})
    if urg:
        sc += 5 * min(2, len(urg)); why.append("urgent: " + ", ".join(urg[:3]))
    rout = {m.group(0).lower() for m in ROUTINE.finditer(t)}
    if rout:
        sc += min(2, len(rout))
    if SCALE.search(t):
        sc += 3; why.append("scale")
    loc_t = bool(LOCAL.search(title))
    local = loc_t or bool(LOCAL.search(t)) or bool(s.get("tier"))
    if local:
        sc += 2 if loc_t else 1; why.append("local")
        if urg and loc_t:
            sc += 2
    rel = len(s.get("related") or [])
    if rel:
        sc += 1 if rel == 1 else 2; why.append(f"{rel + 1} outlets")
    pub = s.get("published") or 0
    if pub and now - pub < 3600:
        sc += 1
    if AFTERMATH.search(title):
        sc -= 3; why.append("follow-up")
    if SOFT.search(title):
        sc -= 6; why.append("soft/feature")
    if SPORTS.search(title) and not urg:
        sc -= 4; why.append("sports")
    if not local and not brk:
        sc = min(sc, CANDIDATE_MIN - 1); why.append("not local")
    return sc, why


STOP = set("the a an and or of to in on for at by with from as is are was were be been it its this that after over into new".split())
fingerprint = lambda title: sorted({w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if len(w) >= 4 and w not in STOP})


def same_story(a: list, b: list) -> bool:
    A, B = set(a), set(b)
    return len(A) >= 3 and len(B) >= 3 and len(A & B) / min(len(A), len(B)) >= 0.6


# ---------------------------------------------------------------- Gemini (optional, fail safe)
_verdicts: dict[str, tuple[float, dict]] = {}


async def gemini_verdicts(cands: list[dict], client: httpx.AsyncClient | None = None, timeout: float = 12) -> dict | None:
    """{story_id: {"major": bool, "why": str}} for the candidates, or None when Gemini can't answer (no key, error,
    timeout, quota, unparsable). Verdicts are remembered 6 h so a story is asked about once."""
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key or os.environ.get("AUTO_PUSH_GEMINI") == "0":
        return None
    now = time.time()
    out, ask = {}, []
    for s in cands:
        sid = push.story_id(s.get("link"))
        hit = _verdicts.get(sid)
        if hit and now - hit[0] < 6 * 3600:
            out[sid] = hit[1]
        else:
            ask.append(s)
    if ask:
        lines = "\n".join(f'{i}. "{(s.get("title") or "")[:200]}" ({s.get("source") or "?"}) {(s.get("summary") or "")[:240]}' for i, s in enumerate(ask))
        prompt = ("You decide whether a local news app for San Antonio, Texas should send a phone push notification. "
                  "Answer yes ONLY for truly major, urgent, breaking news that matters to many people in the San Antonio area right now: "
                  "e.g. a mass-casualty event, an active threat or manhunt, a large evacuation or shelter-in-place, a boil-water notice, "
                  "a major freeway closed for hours, a severe storm/flood/fire disaster, a big citywide emergency or decision. "
                  "Answer no for routine crime, single crashes, features, opinion, business, sports results, politics as usual, "
                  "or anything not urgent. At most 2 pushes a day go out, so be strict.\n\nStories:\n" + lines +
                  '\n\nReply with JSON only: [{"i": <number>, "major": true|false, "why": "<max 12 words>"}]')
        model = os.environ.get("AUTO_PUSH_MODEL") or os.environ.get("MASCOT_MODEL") or "gemini-3.5-flash-lite"
        base = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 400, "responseMimeType": "application/json"}}
        try:
            own = client is None
            c = client or httpx.AsyncClient(timeout=timeout)
            try:
                r = await asyncio.wait_for(c.post(f"{base}/v1beta/models/{model}:generateContent", json=body,
                                                  headers={"x-goog-api-key": key}, timeout=timeout), timeout + 1)
            finally:
                if own:
                    await c.aclose()
            if r.status_code != 200:
                return None
            txt = "".join(p.get("text", "") for p in ((r.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
            m = re.search(r"\[.*\]", txt, re.S)
            arr = json.loads(m.group(0) if m else txt)
            if not isinstance(arr, list):
                return None
            for v in arr:
                if not isinstance(v, dict) or not isinstance(v.get("i"), int) or not 0 <= v["i"] < len(ask):
                    continue
                verdict = {"major": v.get("major") is True, "why": str(v.get("why") or "")[:120]}
                sid = push.story_id(ask[v["i"]].get("link"))
                out[sid] = verdict; _verdicts[sid] = (now, verdict)
        except Exception:
            return None
    return out


# ---------------------------------------------------------------- state (Upstash through push.store())
async def auto_on() -> bool:
    try:
        return (await push.store().kv_get(K + "on")) is True
    except Exception:
        return False   # storage down: off (fail safe)


async def set_auto(on: bool) -> bool:
    await push.store().kv_set(K + "on", bool(on))
    return bool(on)


async def today_count(now: float | None = None) -> int:
    return int(await push.store().kv_get(K + "day:" + day_of(now or time.time())) or 0)


async def recent(key: str = "log", n: int = 10) -> list[dict]:
    out = []
    for v in await push.store().list_get(K + key, n):
        try:
            out.append(json.loads(v) if isinstance(v, str) else v)
        except Exception:
            pass
    return out


def km(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def near_sa(r: dict) -> bool:
    if not push.wants_news(r):
        return False
    try:
        return km(float(r["lat"]), float(r["lon"]), push.SA_LAT, push.SA_LON) <= radius_km()
    except Exception:
        return True   # no area stored: it's a San Antonio app


# ---------------------------------------------------------------- the check
_lock = asyncio.Lock()
_last_kick = 0.0


async def check(get_stories, now: float | None = None, reason: str = "request", fake_news: list | None = None) -> dict:
    """One auto-alert decision. Safe to call any time: the switch, quiet hours, the daily cap and dedupe all apply."""
    if _lock.locked():
        return {"ok": True, "result": "skipped: a check is already running"}
    async with _lock:
        now = now or time.time()
        res = {"ts": now, "reason": reason, "result": "", "considered": 0, "top": None}
        try:
            res.update(await _check(get_stories, now, fake_news))
        except Exception as ex:
            res["result"] = f"error: {type(ex).__name__}: {str(ex)[:120]}"
        try:
            await push.store().kv_set(K + "last", res, ex=7 * 86400)
        except Exception:
            pass
        return {"ok": True, **res}


async def _check(get_stories, now: float, fake_news) -> dict:
    if not push.enabled():
        return {"result": "push isn't set up (VAPID keys missing)"}
    if not await auto_on():
        return {"result": "auto-send is off"}
    if is_quiet(now):
        return {"result": "quiet hours (10 PM – 7 AM CT)"}
    st, day, cap = push.store(), day_of(now), daily_max()
    if await today_count(now) >= cap:
        return {"result": f"daily cap reached ({cap})"}
    stories = fake_news if fake_news is not None else await get_stories()
    fresh = [s for s in stories or [] if s.get("link") and s.get("title") and s.get("published")
             and 0 <= now - s["published"] <= MAX_AGE]
    scored = sorted(((score(s, now), s) for s in fresh), key=lambda x: -x[0][0])
    out = {"considered": len(fresh), "top": ({"t": scored[0][1]["title"][:120], "score": scored[0][0][0]} if scored else None)}
    recent_fps = [e.get("fp") or [] for e in await recent("log", LOG_KEEP) if now - (e.get("ts") or 0) < 3 * 86400]
    cands = []
    for (sc, why), s in scored:
        if sc < CANDIDATE_MIN or len(cands) >= 5:
            break
        sid = push.story_id(s["link"])
        if await st.kv_get(K + "story:" + sid) is not None or any(same_story(fingerprint(s["title"]), f) for f in recent_fps):
            continue   # already pushed (this link, or the same story from another outlet)
        cands.append((sc, why, s))
    if not cands:
        return {**out, "result": "nothing major"}
    verdicts = await gemini_verdicts([c[2] for c in cands])
    pick = None
    for sc, why, s in cands:
        v = (verdicts or {}).get(push.story_id(s["link"]))
        if verdicts is not None and v is not None:
            if v["major"]:
                pick = (sc, why + [f"gemini: {v['why'] or 'major'}"], s); break
        elif sc >= STRICT_MIN:   # no Gemini answer for it: only the strongest signals go out
            pick = (sc, why + ["keywords only" if verdicts is None else "gemini skipped it"], s); break
    if not pick:
        return {**out, "result": "candidates, but none major " + ("(below the no-AI bar)" if verdicts is None else "(gemini said no)"),
                "gemini": verdicts is not None}
    sc, why, s = pick
    sid = push.story_id(s["link"])
    if not any(near_sa(r) for r in (await st.all()).values()):
        return {**out, "result": f"would send, but nobody near San Antonio has news alerts on: {s['title'][:80]}"}
    if not await st.kv_setnx(K + "story:" + sid, now, ex=DEDUPE_TTL):
        return {**out, "result": "already sent (claimed elsewhere)"}
    n = await st.kv_incr(K + "day:" + day, 1, ex=3 * 86400)
    if n > cap:
        await st.kv_incr(K + "day:" + day, -1)
        return {**out, "result": f"daily cap reached ({cap})"}
    payload = push.news_payload(s, title=AUTO_TITLE)
    sent = await push.broadcast(payload, want=near_sa, urgent=True, ttl=2 * 3600)
    entry = {"ts": now, "title": s["title"][:200], "source": (s.get("source") or "")[:60], "link": s["link"][:500], "score": sc,
             "why": why[:5], "fp": fingerprint(s["title"]), **{k: sent[k] for k in ("total", "sent", "failed", "removed")}}
    await st.list_push(K + "log", json.dumps(entry, ensure_ascii=False), LOG_KEEP)
    return {**out, "result": f"sent: {s['title'][:90]}", "sent": sent["sent"], "failed": sent["failed"], "removed": sent["removed"]}


def kick(get_stories, now: float | None = None, reason: str = "request") -> bool:
    """Called from every incoming request: start a background check if the last one is older than the interval.
    Never awaits anything (the request isn't slowed down)."""
    global _last_kick
    now = now or time.time()
    if now - _last_kick < check_every() or _lock.locked() or not push.enabled():
        return False
    _last_kick = now
    try:
        asyncio.get_running_loop().create_task(check(get_stories, reason=reason))
    except RuntimeError:
        return False
    return True


# ---------------------------------------------------------------- the owner's send box
LINK_RX = re.compile(r"^https?://[^\s<>\"']{4,1800}$", re.I)
_send_lock = asyncio.Lock()


def clean(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def admin_payload(body: dict) -> tuple[dict | None, str]:
    title = clean(body.get("title"), 80) or DEFAULT_TITLE
    msg = clean(body.get("message") if body.get("message") is not None else DEFAULT_BODY, 240)
    link = clean(body.get("link"), 1800)
    if not msg:
        return None, "the message is empty"
    if link and LINK_RX.match(link):
        url = push.story_url(link, title=title, source="")   # opens in Chisme's in-app reader
    elif link and re.match(r"^/(?!/)[\w\-./?=&%#]*$", link):
        url = link                                           # an app path like /#weather
    elif link:
        return None, "the link must start with https:// (or be an app path like /#weather)"
    else:
        url = "/#news"
    return {"title": title, "body": msg, "url": url, "tag": "chisme-owner-" + str(int(time.time()))}, ""


async def admin_send(body: dict) -> dict:
    payload, err = admin_payload(body)
    if not payload:
        return {"ok": False, "error": err}
    if not push.enabled():
        return {"ok": False, "error": "push isn't set up (VAPID keys missing)"}
    if _send_lock.locked():
        return {"ok": False, "error": "a send is already running"}
    async with _send_lock:
        r = await push.broadcast(payload, urgent=False, ttl=6 * 3600)
        entry = {"ts": time.time(), "title": payload["title"], "body": payload["body"], "url": payload["url"],
                 **{k: r[k] for k in ("total", "sent", "failed", "removed")}}
        try:
            await push.store().list_push(K + "manual", json.dumps(entry, ensure_ascii=False), LOG_KEEP)
        except Exception:
            pass
        return {"ok": True, **{k: r[k] for k in ("total", "sent", "failed", "removed", "errors")}}


async def admin_info(now: float | None = None) -> dict:
    now = now or time.time()
    st = push.store()
    recs = list((await st.all()).values())
    return {"enabled": push.enabled(), "store": st.name, "subs": len(recs), "news": sum(1 for r in recs if push.wants_news(r)),
            "near": sum(1 for r in recs if near_sa(r)), "on": await auto_on(), "today": await today_count(now), "cap": daily_max(),
            "quiet": is_quiet(now), "gemini": bool((os.environ.get("GEMINI_API_KEY") or "").strip()) and os.environ.get("AUTO_PUSH_GEMINI") != "0",
            "every": check_every() // 60, "radius": radius_km(), "last": await st.kv_get(K + "last"),
            "log": await recent("log", 10), "manual": await recent("manual", 5), "secret": bool(push.conf()["secret"])}


# ---------------------------------------------------------------- the /stats page: rendered by admin.py (v49.5)
