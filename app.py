"""Chisme — location-aware local news + weather.

Small FastAPI backend that
  * reverse/forward geocodes (OpenStreetMap Nominatim, rate-limited + cached),
  * proxies/caches NWS weather for any US point (/points -> forecast, hourly, obs, alerts),
  * proxies RainViewer radar metadata,
  * builds a local news list: San Antonio publisher RSS + Google News RSS searches for the
    user's neighborhood / city / county, ranked by how close the named places are,
and serves the single-page PWA frontend."""
from __future__ import annotations

import asyncio
import html
import json
import math
import os
import re
import time
import urllib.parse
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------- config
DEFAULT_LAT, DEFAULT_LON = 29.4241, -98.4936  # San Antonio, TX (used until the user picks)
UA = os.environ.get(
    "APP_USER_AGENT", "Chisme/1.0 (personal local news+weather app; contact: set APP_USER_AGENT)"
)
WEATHER_TTL = 5 * 60        # server caches; the browser refreshes weather every 10 min
ALERTS_TTL = 3 * 60
NEWS_TTL = 10 * 60          # per feed URL; the browser refreshes news every 15 min
POINTS_TTL = 24 * 3600      # NWS /points metadata per ~1 km cell
PLACE_TTL = 7 * 86400       # reverse geocode per ~1 km cell
NEARBY_TTL = 30 * 86400     # nearby neighborhood names per ~2 km cell
GEOCODE_TTL = 30 * 86400
RADAR_TTL = 2 * 60
BASE = Path(__file__).parent
NOMINATIM = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")

GN = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="


def gnews(fid: str, name: str, query: str, kind: str = "gnews") -> dict:
    return {"id": fid, "name": name, "kind": kind, "url": GN + urllib.parse.quote(query), "query": query}


# San Antonio publisher feeds (verified 2026-09-29). Always fetched; when the user is not in
# San Antonio they only count for "Near You" if they name the user's places.
SA_FEEDS = [
    {"id": "ksat", "name": "KSAT 12", "kind": "direct",
     "url": "https://www.ksat.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml"},
    {"id": "kens5", "name": "KENS 5", "kind": "direct",
     "url": "https://www.kens5.com/feeds/syndication/rss/news/local"},
    {"id": "sareport", "name": "San Antonio Report", "kind": "direct",
     "url": "https://sanantonioreport.org/feed/"},
    {"id": "tpr", "name": "Texas Public Radio", "kind": "direct",
     "url": "https://www.tpr.org/news.rss"},
    {"id": "news4", "name": "News 4 San Antonio", "kind": "direct",
     "url": "https://news4sanantonio.com/news/local.rss"},
    {"id": "sacurrent", "name": "San Antonio Current", "kind": "direct",
     "url": "https://sacurrent.com/sanantonio/Rss.xml"},
    gnews("expressnews", "Express-News (via Google News)", "site:expressnews.com/news when:3d"),
]
for f in SA_FEEDS:
    f["sa"] = True

# Extra searches used only when the user is on San Antonio's South Side.
_SS_TERMS_A = ('("South Side" OR Harlandale OR "South San" OR "Palm Heights" OR Nogalitos '
               'OR "Port San Antonio" OR Zarzamora OR "Military Drive" OR "Kelly Field")')
_SS_TERMS_B = ('("Quintana Road" OR "Somerset Road" OR Southcross OR "Pleasanton Road" '
               'OR "Palo Alto College" OR "South Park Mall" OR "Southwest Military" OR "Frio City Road")')
SOUTH_SIDE_FEEDS = [
    gnews("southside1", "Google News: South Side", _SS_TERMS_A + ' "San Antonio" when:14d', "gnews_strict"),
    gnews("southside2", "Google News: South Side (more)", _SS_TERMS_B + ' "San Antonio" when:14d', "gnews_strict"),
]
# South Side boost words (only applied when the user is on the South Side). (regex, label)
SOUTH_SIDE_TERMS: list[tuple[str, str]] = [
    (r"\bsouth[\s-]?side\b", "South Side"),
    (r"\bsouth\s+san\b(?!\s+francisco)", "South San"),
    (r"\bharlandale\b", "Harlandale"),
    (r"\bpalm\s+heights\b", "Palm Heights"),
    (r"\bnogalitos\b", "Nogalitos"),
    (r"\bzarzamora\b", "Zarzamora"),
    (r"\b(?:sw|southwest|s\.?w\.?)\s+military\b", "SW Military"),
    (r"\bmilitary\s+(?:drive|dr\.?)\b", "Military Dr"),
    (r"\bkelly\s+(?:field|usa|air\s+force\s+base|afb)\b|\bformer\s+kelly\b", "Kelly"),
    (r"\bport\s+san\s+antonio\b", "Port San Antonio"),
    (r"\bquintana\s+(?:road|rd)\b", "Quintana Rd"),
    (r"\bsomerset\s+(?:road|rd)\b", "Somerset Rd"),
    (r"\bsouthcross\b", "Southcross"),
    (r"\bpleasanton\s+(?:road|rd)\b", "Pleasanton Rd"),
    (r"\bfrio\s+city\s+(?:road|rd)\b", "Frio City Rd"),
    (r"\bstinson\b", "Stinson"),
    (r"\bpalo\s+alto\s+college\b", "Palo Alto College"),
    (r"\bsouth\s+park\s+mall\b", "South Park Mall"),
    (r"\bcommerce\b.{0,20}\bzarzamora\b|\bzarzamora\b.{0,20}\bcommerce\b", "Commerce/Zarzamora"),
    (r"\bcassiano\b", "Cassiano"),
    (r"\bvilla\s+coronado\b", "Villa Coronado"),
    (r"\bsouthwest\s+isd\b", "Southwest ISD"),
]
# San Antonio neighborhood points (OSM has almost no neighbourhood polygons there);
# built by tools/build_sa_gazetteer.py from Nominatim lookups.
try:
    SA_PLACES = json.loads((BASE / "data" / "sa_neighborhoods.json").read_text())["places"]
except Exception:
    SA_PLACES = []

# Neighborhood names so generic they only count if the city is named too.
GENERIC_PLACE = re.compile(
    r"^(downtown|midtown|uptown|central|city cent(er|re)|old town|historic district|north ?side|south ?side|"
    r"east ?side|west ?side|north|south|east|west|northeast|northwest|southeast|southwest|the heights|heights|"
    r"university|airport|industrial|park|village|medical center)$", re.I)

JUNK_SOURCES = re.compile(r"maxpreps|hudl|zillow|realtor|apartments\.com|legacy|obituar|dignity memorial|funeral|"
                          r"tripadvisor|yelp|niche\.com|homes\.com|redfin|trulia|^x\.com$|twitter|facebook|instagram|tiktok|youtube|reddit", re.I)
JUNK_TITLES = re.compile(r"\bobituar(y|ies)\b|funeral information|\bfor sale\b|homes for sale", re.I)

# ---------------------------------------------------------------- infra
app = FastAPI(title="Chisme")
_cache: dict[str, tuple[float, Any]] = {}
_locks: dict[str, asyncio.Lock] = {}
_client: httpx.AsyncClient | None = None
MAX_CACHE = 5000


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(headers={"User-Agent": UA}, timeout=httpx.Timeout(20.0), follow_redirects=True)
    return _client


async def cached(key: str, ttl: int, producer):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
        try:
            value = await producer()
        except Exception:
            if hit:  # serve stale data rather than nothing
                return hit[1]
            raise
        _cache[key] = (time.time(), value)
        if len(_cache) > MAX_CACHE:  # drop the oldest ~10%
            for k, _ in sorted(_cache.items(), key=lambda kv: kv[1][0])[: MAX_CACHE // 10]:
                _cache.pop(k, None)
                _locks.pop(k, None)
        return value


async def get_json(url: str, **params) -> Any:
    r = await client().get(url, params=params or None, headers={"Accept": "application/geo+json"})
    r.raise_for_status()
    return r.json()


def cell(lat: float, lon: float, step: float) -> tuple[float, float]:
    """Snap a coordinate to a grid cell (used for cache keys and upstream requests)."""
    return (round(round(lat / step) * step, 4), round(round(lon / step) * step, 4))


def km_between(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def bad_coords(lat, lon) -> bool:
    return lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180)


# ---------------------------------------------------------------- geocoding (Nominatim)
_nomi_lock = asyncio.Lock()
_nomi_last = 0.0


async def nominatim(path: str, params: dict) -> Any:
    """Nominatim usage policy: identify the app (User-Agent), max 1 request/second, cache results."""
    global _nomi_last
    async with _nomi_lock:
        wait = 1.1 - (time.time() - _nomi_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await client().get(NOMINATIM + path, params={**params, "format": "jsonv2"},
                                   headers={"Accept-Language": "en"})
        finally:
            _nomi_last = time.time()
    r.raise_for_status()
    return r.json()


def _addr_city(a: dict) -> str | None:
    return a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("municipality")


def _state_abbr(a: dict) -> str | None:
    iso = a.get("ISO3166-2-lvl4") or ""
    return iso.split("-", 1)[1] if a.get("country_code") == "us" and "-" in iso else a.get("state")


async def build_place(lat: float, lon: float) -> dict:
    rev = await nominatim("/reverse", {"lat": lat, "lon": lon, "zoom": 16, "addressdetails": 1})
    if not isinstance(rev, dict) or "error" in rev:
        return {"lat": lat, "lon": lon, "label": f"{lat:.3f}, {lon:.3f}", "city": None, "county": None,
                "state": None, "country_code": None, "neighborhood": None, "nearby": [], "south_side": False}
    a = rev.get("address", {})
    city, county, cc = _addr_city(a), a.get("county"), a.get("country_code")
    nearby: list[dict] = []

    def add(name, plat, plon, terms=None, src="osm"):
        if not name or any(n["name"].lower() == name.lower() for n in nearby):
            return
        nearby.append({"name": name, "km": round(km_between(lat, lon, plat, plon), 2), "terms": terms or [name], "src": src})

    for key in ("neighbourhood", "quarter", "suburb", "city_district"):
        if a.get(key) and a.get(key) != city:
            add(a[key], lat, lon)
    if city == "San Antonio" or county == "Bexar County":
        for p in SA_PLACES:
            if km_between(lat, lon, p["lat"], p["lon"]) <= 5:
                add(p["name"], p["lat"], p["lon"], p.get("terms"), "gazetteer")
    nearby.sort(key=lambda n: n["km"])
    hood = nearby[0]["name"] if nearby and nearby[0]["km"] <= 3 else None
    south_side = city == "San Antonio" and lat < 29.405  # south of downtown / the Alamo (~29.42N)
    st = _state_abbr(a)
    label = ", ".join(x for x in [hood, city or county] if x) or rev.get("display_name", "")[:60]
    if cc != "us" and a.get("country"):
        label += f", {a['country']}"
    return {"lat": lat, "lon": lon, "label": label, "neighborhood": hood, "city": city, "county": county,
            "state": a.get("state"), "state_abbr": st, "country_code": cc, "country": a.get("country"),
            "postcode": a.get("postcode"), "nearby": nearby[:12], "south_side": south_side,
            "display_name": rev.get("display_name")}


async def get_place(lat: float, lon: float) -> dict:
    c = cell(lat, lon, 0.01)  # ~1 km
    return await cached(f"place:{c}", PLACE_TTL, lambda: build_place(*c))


async def get_nearby_osm(lat: float, lon: float) -> list[dict]:
    """Neighborhood names ~1.5 km around the point (4 extra reverse lookups, cached for a month)."""
    c = cell(lat, lon, 0.02)

    async def prod():
        out = []
        d = 0.0135  # ~1.5 km
        for dlat, dlon in ((d, 0), (-d, 0), (0, d / math.cos(math.radians(c[0]))), (0, -d / math.cos(math.radians(c[0])))):
            try:
                rev = await nominatim("/reverse", {"lat": c[0] + dlat, "lon": c[1] + dlon, "zoom": 16, "addressdetails": 1})
            except Exception:
                continue
            a = (rev or {}).get("address", {})
            for key in ("neighbourhood", "quarter", "suburb"):
                if a.get(key) and a.get(key) != _addr_city(a):
                    out.append({"name": a[key], "lat": c[0] + dlat, "lon": c[1] + dlon})
        return out

    return await cached(f"nearby:{c}", NEARBY_TTL, prod)


# ---------------------------------------------------------------- news helpers
SOURCE_ALIASES = {
    "kens5.com": "KENS 5", "kens 5": "KENS 5", "ksat": "KSAT 12", "ksat.com": "KSAT 12",
    "woai": "News 4 San Antonio", "kabb": "FOX San Antonio", "tpr": "Texas Public Radio",
    "tpr.org": "Texas Public Radio", "mysa": "MySA", "sacurrent.com": "San Antonio Current",
}
TAG_RX = re.compile(r"<[^>]+>")
IMG_RX = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def clean_text(s: str | None, limit: int = 240) -> str:
    if not s:
        return ""
    t = html.unescape(TAG_RX.sub(" ", s))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > limit:
        t = t[: limit - 1].rsplit(" ", 1)[0] + "…"
    return t


def thumbnail(e: dict) -> str | None:
    for m in e.get("media_thumbnail") or []:
        if m.get("url"):
            return m["url"]
    for m in e.get("media_content") or []:
        if m.get("url") and (m.get("medium") == "image" or "image" in (m.get("type") or "image")):
            return m["url"]
    for enc in e.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return enc["href"]
    for l in e.get("links") or []:
        if l.get("rel") == "enclosure" and (l.get("type") or "").startswith("image"):
            return l.get("href")
    for field in ("summary", "content"):
        v = e.get(field)
        if isinstance(v, list):
            v = " ".join(c.get("value", "") for c in v)
        if v:
            m = IMG_RX.search(v)
            if m:
                return html.unescape(m.group(1))
    return None


def entry_time(e: dict) -> float | None:
    for k in ("published_parsed", "updated_parsed"):
        if e.get(k):
            return float(timegm(e[k]))
    return None


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


async def _fetch_feed(feed: dict) -> list[dict]:
    r = await client().get(feed["url"])
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    is_g = feed["kind"].startswith("gnews")
    items = []
    for e in parsed.entries:
        title = clean_text(e.get("title"), 300)
        link = e.get("link")
        if not title or not link:
            continue
        source = feed["name"]
        if is_g:
            src = (e.get("source") or {}).get("title")
            if src:
                source = SOURCE_ALIASES.get(src.lower(), src)
                title = re.sub(r"\s+-\s+" + re.escape(src) + r"$", "", title)
            else:
                title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title)
            summary = ""  # Google News summaries are just the title + source
        else:
            summary = clean_text(e.get("summary") or e.get("description"), 2000)
            summary = re.sub(r"\s*(The post\s+)?" + re.escape(title) + r"\s+(was first posted|appeared first) on.*$",
                             "", summary, flags=re.I | re.S)
            summary = re.sub(r"\s*The post .{0,300}? appeared first on .*$", "", summary, flags=re.S)
            summary = clean_text(summary)
        items.append({"title": title, "link": link, "source": source, "published": entry_time(e),
                      "summary": summary, "image": None if is_g else thumbnail(e)})
    return items


async def fetch_feed(feed: dict) -> dict:
    t0 = time.time()
    try:
        items = await cached("feed:" + feed["url"], NEWS_TTL, lambda: _fetch_feed(feed))
        items = [dict(i, feed=feed["id"], kind=feed["kind"], sa=bool(feed.get("sa"))) for i in items]
        return {"items": items, "status": {"id": feed["id"], "name": feed["name"], "ok": True, "count": len(items),
                                           "ms": int((time.time() - t0) * 1000), "query": feed.get("query")}}
    except Exception as ex:  # keep going if one feed fails
        return {"items": [], "status": {"id": feed["id"], "name": feed["name"], "ok": False,
                                        "error": f"{type(ex).__name__}: {ex}"[:200], "query": feed.get("query")}}


def _rx(term: str) -> re.Pattern:
    words = [re.escape(w) for w in term.split()]
    return re.compile(r"(?<![\w-])" + r"[\s-]+".join(words) + r"(?![\w-])", re.I)


def build_terms(place: dict) -> list[dict]:
    """Place terms with weights; higher = closer to the user."""
    terms: list[dict] = []
    city = place.get("city")

    def add(label, rx, weight, tier, needs_city=False):
        terms.append({"label": label, "rx": rx, "w": weight, "tier": tier, "needs_city": needs_city})

    for n in place.get("nearby", []):
        w = max(4.0, 10.0 - 1.2 * n["km"])
        for t in n.get("terms") or [n["name"]]:
            generic = bool(GENERIC_PLACE.match(t.strip()))
            # OSM neighborhood names (e.g. "Clarksville") also exist elsewhere, so the story must
            # name the city too. Curated San Antonio names don't need that.
            add(n["name"], _rx(t), w, "near", needs_city=generic or n.get("src") != "gazetteer")
    if place.get("south_side"):
        for p, label in SOUTH_SIDE_TERMS:
            add(label, re.compile(p, re.I), 6.0, "near")
    if place.get("postcode") and place.get("country_code") == "us":
        add(place["postcode"], re.compile(r"\b" + re.escape(place["postcode"]) + r"\b"), 6.0, "near")
    if city:
        # e.g. "Austin College" (Sherman) or "Austin Peay" (Tennessee) are not about Austin
        city_rx = re.compile(_rx(city).pattern + r"(?!\s+(?:College|Peay|Community College|University))", re.I)
        add(city, city_rx, 3.0, "city")
    if place.get("county"):
        co = place["county"]
        add(co, _rx(co), 2.0, "county")
        short = re.sub(r"\s+(County|Parish|Borough)$", "", co)
        if short != co and len(short) > 3 and short != city:
            add(co, _rx(short), 1.5, "county")
    return terms


TIER_RANK = {"near": 0, "city": 1, "county": 2}


def score_item(it: dict, terms: list[dict], city_context: bool = False) -> tuple[float, str | None, list[str], bool]:
    """city_context: the item comes from a publisher feed for the user's own city."""
    title, body = it["title"], it["summary"]
    city_rx = next((t["rx"] for t in terms if t["tier"] == "city"), None)
    has_city = city_context or bool(city_rx and (city_rx.search(title) or city_rx.search(body)))
    score, best, labels, title_hit = 0.0, None, [], False
    for t in terms:
        in_title = bool(t["rx"].search(title))
        in_body = not in_title and bool(body and t["rx"].search(body))
        if not (in_title or in_body):
            continue
        if t["needs_city"] and not has_city:
            continue
        score += t["w"] * (2 if in_title else 1)
        title_hit = title_hit or in_title
        if t["label"] not in labels:
            labels.append(t["label"])
        if best is None or TIER_RANK[t["tier"]] < TIER_RANK[best]:
            best = t["tier"]
    return score, best, labels, title_hit


def feeds_for(place: dict) -> list[dict]:
    city, st, county = place.get("city"), place.get("state_abbr") or place.get("state") or "", place.get("county")
    in_sa = city == "San Antonio" or county == "Bexar County"
    feeds = list(SA_FEEDS)
    if city and not in_sa:
        feeds.append(gnews("city", f"Google News: {city}", f'"{city}" {st} when:3d'.strip()))
    if county:
        feeds.append(gnews("county", f"Google News: {county}", f'"{county}" {st} when:7d'.strip(), "gnews_strict"))
    # neighborhood searches for the 2 closest specific (non-generic) names
    specific = [n for n in place.get("nearby", []) if not GENERIC_PLACE.match(n["name"])][:2]
    generic = [n for n in place.get("nearby", []) if GENERIC_PLACE.match(n["name"])][:1]
    for i, n in enumerate(specific):
        q = f'"{(n.get("terms") or [n["name"]])[0]}" "{city}" when:30d' if city else f'"{n["name"]}" when:30d'
        feeds.append(gnews(f"hood{i + 1}", f"Google News: {n['name']}", q, "gnews_strict"))
    for n in generic:
        if city:
            feeds.append(gnews("hood_g", f"Google News: {n['name']} {city}", f'"{n["name"]} {city}" when:14d', "gnews_strict"))
    if place.get("south_side"):
        feeds += SOUTH_SIDE_FEEDS
    return feeds


async def build_news(lat: float, lon: float) -> dict:
    place = dict(await get_place(lat, lon))
    if place.get("country_code"):
        try:  # add neighborhood names found around the point
            extra = await get_nearby_osm(lat, lon)
            for x in extra:
                if not any(n["name"].lower() == x["name"].lower() for n in place["nearby"]):
                    place["nearby"].append({"name": x["name"], "km": round(km_between(lat, lon, x["lat"], x["lon"]), 2),
                                            "terms": [x["name"]], "src": "osm"})
            place["nearby"].sort(key=lambda n: n["km"])
        except Exception:
            pass
    terms = build_terms(place)
    feeds = feeds_for(place)
    results = await asyncio.gather(*(fetch_feed(f) for f in feeds))
    in_sa = place.get("city") == "San Antonio" or place.get("county") == "Bexar County"
    now = time.time()
    seen: set[str] = set()
    near, more, sa_other = [], [], []
    all_items = [i for r in results for i in r["items"]]
    all_items.sort(key=lambda i: (i["kind"] != "direct", -(i["published"] or 0)))  # keep thumbnail copies
    for it in all_items:
        key = norm_title(it["title"])[:90]
        if not key or key in seen or JUNK_SOURCES.search(it["source"]) or JUNK_TITLES.search(it["title"]):
            continue
        age_days = (now - it["published"]) / 86400 if it["published"] else 0
        score, tier, labels, title_hit = score_item(it, terms, city_context=bool(it.get("sa") and in_sa))
        if it["kind"] == "gnews_strict" and not title_hit:
            continue  # keyword searches: keep only headlines that name the place
        limit_days = 14 if tier == "near" else (30 if it["feed"].startswith("hood") and tier else 7)
        if age_days > limit_days:
            continue
        seen.add(key)
        it.update(local_terms=labels, local_score=round(score, 1), tier=tier)
        if tier:
            near.append(it)
        elif it.get("sa") and not in_sa:
            sa_other.append(it)
        else:
            more.append(it)
    near.sort(key=lambda i: (TIER_RANK[i["tier"]], -(i["published"] or 0)))
    # drop near-duplicate headlines (same story from several outlets), keep the first (newest)
    kept, overflow, sigs = [], [], []
    for it in near:
        sig = {w for w in norm_title(it["title"]).split() if len(w) >= 4}
        if any(sig and len(sig & o) / max(1, min(len(sig), len(o))) >= 0.6 for o in sigs):
            continue
        sigs.append(sig)
        kept.append(it)
    # proximity order, but leave room for city/county stories: at most 18 neighborhood-level items
    hood = [i for i in kept if i["tier"] == "near"]
    rest = [i for i in kept if i["tier"] != "near"]
    near = (hood[:18] + rest)[:30]
    overflow = hood[18:] + rest[max(0, 30 - len(hood[:18])):]
    more = sorted(more + overflow, key=lambda i: -(i["published"] or 0))
    sa_other.sort(key=lambda i: -(i["published"] or 0))
    return {
        "generated": now,
        "place": {k: place.get(k) for k in ("label", "neighborhood", "city", "county", "state", "state_abbr",
                                            "country_code", "south_side", "postcode")}
                 | {"nearby": [{"name": n["name"], "km": n["km"]} for n in place["nearby"][:10]]},
        "in_san_antonio": in_sa,
        "near": near,
        "more": more[:80],
        "san_antonio": sa_other[:40],
        "feeds": [r["status"] for r in results],
    }


# ---------------------------------------------------------------- weather (NWS)
async def get_points(lat: float, lon: float) -> dict:
    c = cell(lat, lon, 0.01)

    async def prod():
        r = await client().get(f"https://api.weather.gov/points/{c[0]},{c[1]}", headers={"Accept": "application/geo+json"})
        if r.status_code == 404:
            return {"unsupported": True, "detail": (r.json() or {}).get("detail")}
        r.raise_for_status()
        return r.json()["properties"]

    return await cached(f"points:{c}", POINTS_TTL, prod)


async def get_observation(stations_url: str) -> dict | None:
    async def stations():
        return await get_json(stations_url, limit=4)

    st_doc = await cached("stations:" + stations_url, POINTS_TTL, stations)
    for st in (st_doc.get("features") or [])[:4]:
        sid = st["properties"]["stationIdentifier"]
        try:
            obs = await cached(f"obs:{sid}", WEATHER_TTL,
                               lambda sid=sid: get_json(f"https://api.weather.gov/stations/{sid}/observations/latest"))
        except Exception:
            continue
        o = obs.get("properties", {})
        if (o.get("temperature") or {}).get("value") is None:
            continue
        v = lambda k: (o.get(k) or {}).get("value")
        return {"station": sid, "station_name": st["properties"].get("name"), "timestamp": o.get("timestamp"),
                "text": o.get("textDescription"), "icon": o.get("icon"), "temp_c": v("temperature"),
                "dewpoint_c": v("dewpoint"), "humidity": v("relativeHumidity"), "wind_kmh": v("windSpeed"),
                "wind_gust_kmh": v("windGust"), "wind_dir": v("windDirection"), "heat_index_c": v("heatIndex"),
                "wind_chill_c": v("windChill"), "pressure_pa": v("barometricPressure"), "visibility_m": v("visibility")}
    return None


async def build_weather(lat: float, lon: float) -> dict:
    p = await get_points(lat, lon)
    c = cell(lat, lon, 0.01)
    if p.get("unsupported"):
        return {"generated": time.time(), "supported": False, "location": {"lat": c[0], "lon": c[1]},
                "message": "Weather, forecasts and alerts come from the U.S. National Weather Service, "
                           "which only covers the United States and its territories.",
                "detail": p.get("detail"), "current": None, "forecast": [], "hourly": [], "alerts": []}

    async def safe(coro):
        try:
            return await coro
        except Exception as ex:
            return {"_error": f"{type(ex).__name__}: {ex}"[:200]}

    grid = f'{p.get("gridId")}/{p.get("gridX")},{p.get("gridY")}'
    forecast, hourly, alerts, current = await asyncio.gather(
        safe(cached(f"fc:{grid}", WEATHER_TTL, lambda: get_json(p["forecast"]))),
        safe(cached(f"hr:{grid}", WEATHER_TTL, lambda: get_json(p["forecastHourly"]))),
        safe(cached(f"alerts:{c}", ALERTS_TTL,
                    lambda: get_json("https://api.weather.gov/alerts/active", point=f"{c[0]},{c[1]}"))),
        safe(get_observation(p["observationStations"])),
    )
    if isinstance(current, dict) and "_error" in current:
        current = None

    def periods(doc):
        return ((doc.get("properties") or {}).get("periods") or []) if isinstance(doc, dict) else []

    alert_list = []
    for f in (alerts.get("features") or []) if isinstance(alerts, dict) else []:
        a = f["properties"]
        alert_list.append({k: a.get(k) for k in (
            "id", "event", "headline", "severity", "urgency", "certainty", "areaDesc",
            "description", "instruction", "effective", "onset", "expires", "ends", "senderName")})
    sev_rank = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}
    alert_list.sort(key=lambda a: sev_rank.get(a.get("severity"), 4))
    rl = (p.get("relativeLocation") or {}).get("properties", {})
    return {
        "generated": time.time(),
        "supported": True,
        "location": {"lat": c[0], "lon": c[1], "tz": p.get("timeZone"), "office": p.get("gridId"),
                     "grid": [p.get("gridX"), p.get("gridY")], "city": rl.get("city"), "state": rl.get("state"),
                     "forecast_zone": (p.get("forecastZone") or "").rsplit("/", 1)[-1],
                     "county": (p.get("county") or "").rsplit("/", 1)[-1]},
        "current": current,
        "forecast": [
            {k: x.get(k) for k in ("name", "startTime", "isDaytime", "temperature", "temperatureUnit",
                                     "windSpeed", "windDirection", "shortForecast", "detailedForecast", "icon")}
            | {"pop": (x.get("probabilityOfPrecipitation") or {}).get("value")}
            for x in periods(forecast)
        ],
        "forecast_updated": (forecast.get("properties") or {}).get("updateTime") if isinstance(forecast, dict) else None,
        "hourly": [
            {"startTime": x.get("startTime"), "temperature": x.get("temperature"),
             "shortForecast": x.get("shortForecast"), "icon": x.get("icon"),
             "pop": (x.get("probabilityOfPrecipitation") or {}).get("value")}
            for x in periods(hourly)[:12]
        ],
        "alerts": alert_list,
        "errors": {k: v["_error"] for k, v in {"forecast": forecast, "hourly": hourly, "alerts": alerts}.items()
                   if isinstance(v, dict) and "_error" in v},
    }


async def build_radar() -> dict:
    r = await client().get("https://api.rainviewer.com/public/weather-maps.json")
    r.raise_for_status()
    return r.json()


async def geocode(q: str) -> list[dict]:
    q = q.strip()
    params: dict = {"addressdetails": 1, "limit": 5}
    if re.fullmatch(r"\d{5}(-\d{4})?", q):  # US ZIP code
        params |= {"postalcode": q[:5], "countrycodes": "us"}
    else:
        params["q"] = q
    res = await nominatim("/search", params)
    out = []
    for x in res or []:
        a = x.get("address", {})
        city = _addr_city(a) or a.get("county")
        parts = [a.get("postcode") if "postalcode" in params else None, city, _state_abbr(a),
                 a.get("country") if a.get("country_code") != "us" else None]
        label = ", ".join(p for p in parts if p) or x.get("display_name", "")[:80]
        out.append({"lat": round(float(x["lat"]), 4), "lon": round(float(x["lon"]), 4), "label": label,
                    "display_name": x.get("display_name"), "country_code": a.get("country_code")})
    return out


# ---------------------------------------------------------------- routes
def _err(ex: Exception, code: int = 502) -> JSONResponse:
    return JSONResponse({"error": f"{type(ex).__name__}: {ex}"[:300]}, status_code=code)


def _coords(lat, lon):
    if lat is None and lon is None:
        return DEFAULT_LAT, DEFAULT_LON
    if bad_coords(lat, lon):
        raise ValueError("lat/lon out of range")
    return lat, lon


@app.get("/api/weather")
async def api_weather(lat: float | None = Query(None), lon: float | None = Query(None)):
    try:
        la, lo = _coords(lat, lon)
    except ValueError as ex:
        return _err(ex, 400)
    try:
        c = cell(la, lo, 0.01)
        return await cached(f"weather:{c}", 60, lambda: build_weather(*c))
    except Exception as ex:
        return _err(ex)


@app.get("/api/news")
async def api_news(lat: float | None = Query(None), lon: float | None = Query(None)):
    try:
        la, lo = _coords(lat, lon)
    except ValueError as ex:
        return _err(ex, 400)
    try:
        c = cell(la, lo, 0.01)
        return await cached(f"news:{c}", 5 * 60, lambda: build_news(*c))
    except Exception as ex:
        return _err(ex)


@app.get("/api/place")
async def api_place(lat: float = Query(...), lon: float = Query(...)):
    if bad_coords(lat, lon):
        return _err(ValueError("lat/lon out of range"), 400)
    try:
        p = await get_place(lat, lon)
        return {k: v for k, v in p.items() if k != "display_name"} | {"nearby": [
            {"name": n["name"], "km": n["km"]} for n in p.get("nearby", [])]}
    except Exception as ex:
        return _err(ex)


@app.get("/api/geocode")
async def api_geocode(q: str = Query(..., min_length=2, max_length=120)):
    try:
        key = "geo:" + re.sub(r"\s+", " ", q.strip().lower())
        return {"results": await cached(key, GEOCODE_TTL, lambda: geocode(q))}
    except Exception as ex:
        return _err(ex)


@app.get("/api/radar")
async def api_radar():
    try:
        return await cached("radar", RADAR_TTL, build_radar)
    except Exception as ex:
        return _err(ex)


@app.get("/healthz")
async def healthz():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(BASE / "static" / "icons" / "favicon.ico", media_type="image/x-icon")


@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest():
    return FileResponse(BASE / "static" / "manifest.webmanifest", media_type="application/manifest+json",
                        headers={"Cache-Control": "no-cache"})


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    return FileResponse(BASE / "static" / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/")
async def index():
    return FileResponse(BASE / "static" / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.on_event("startup")
async def warm():
    async def _w():  # warm caches for the default location
        await asyncio.gather(api_weather(DEFAULT_LAT, DEFAULT_LON), api_radar(), return_exceptions=True)
    asyncio.create_task(_w())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 8211)))
