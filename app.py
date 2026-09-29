"""Chisme — location-aware local news + weather.

Small FastAPI backend that
  * reverse/forward geocodes (OpenStreetMap Nominatim, rate-limited + cached),
  * proxies/caches NWS weather for any US point (/points -> forecast, hourly, obs, alerts),
  * proxies RainViewer radar metadata,
  * builds a local news list: San Antonio publisher RSS + Google News RSS searches for the
    user's neighborhood / city / county, ranked by how close the named places are, with
    "related coverage" links (the same story from other fetched outlets),
  * builds an upcoming local events list (Visit San Antonio RSS, Eventbrite and AllEvents public
    pages) with photos, venue, price (only when the source states it), keyword categories and the NWS outlook,
  * collects San Antonio food reviews from local creators' YouTube feeds and local food-desk feeds,
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
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------- config
DEFAULT_LAT, DEFAULT_LON = 29.4241, -98.4936  # San Antonio, TX (used until the user picks)
UA = os.environ.get(
    "APP_USER_AGENT", "Chisme/1.0 (local news+weather PWA; +https://github.com/bexartalk/chisme)"
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


_bg: dict[str, asyncio.Task] = {}


async def cached(key: str, ttl: int, producer, stale: int = 0):
    """Memory cache. With stale>0, an expired value younger than ttl+stale is returned right away and
    refreshed in the background, so a slow upstream never makes the user wait twice."""
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    if hit and stale and time.time() - hit[0] < ttl + stale:
        if key not in _bg or _bg[key].done():
            async def _refresh():
                try:
                    await cached(key, 0, producer)
                except Exception:
                    pass
            _bg[key] = asyncio.create_task(_refresh())
        return hit[1]
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < max(ttl, 1):
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


_nomi_blocked_until = 0.0
NOMI_BLOCK_S = 15 * 60


class GeocoderUnavailable(Exception):
    pass


async def nominatim(path: str, params: dict) -> Any:
    """Nominatim usage policy: identify the app (User-Agent), max 1 request/second, cache results.
    On shared hosting (e.g. Render's free tier) Nominatim often answers 429/403 for the shared IP;
    then we stop asking for 15 minutes and use the fallbacks below instead."""
    global _nomi_last, _nomi_blocked_until
    if time.time() < _nomi_blocked_until:
        raise GeocoderUnavailable("nominatim rate-limited; using fallback")
    async with _nomi_lock:
        wait = 1.1 - (time.time() - _nomi_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await client().get(NOMINATIM + path, params={**params, "format": "jsonv2"},
                                   headers={"Accept-Language": "en"})
        finally:
            _nomi_last = time.time()
    if r.status_code in (403, 429, 503):
        _nomi_blocked_until = time.time() + NOMI_BLOCK_S
        raise GeocoderUnavailable(f"nominatim HTTP {r.status_code}")
    r.raise_for_status()
    return r.json()


PHOTON = os.environ.get("PHOTON_URL", "https://photon.komoot.io")
US_STATES = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
             "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
             "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
             "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
             "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
             "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
             "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
             "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
             "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "Puerto Rico": "PR"}


def _photon_addr(pr: dict) -> dict:
    """Photon (komoot, OSM-based, keyless) feature properties -> a Nominatim-style address dict."""
    cc = (pr.get("countrycode") or "").lower()
    county = pr.get("county")
    if county and cc == "us" and not re.search(r"(County|Parish|Borough)$", county):
        county += " County"
    a = {"city": pr.get("city") or (pr.get("name") if pr.get("osm_value") in ("city", "town", "village") else None),
         "county": county, "state": pr.get("state"), "country_code": cc or None, "country": pr.get("country"),
         "postcode": pr.get("postcode")}
    hood = pr.get("locality") or pr.get("district")
    if hood and hood != a["city"]:
        a["neighbourhood"] = hood
    if cc == "us" and pr.get("state") in US_STATES:
        a["ISO3166-2-lvl4"] = "US-" + US_STATES[pr["state"]]
    return a


async def photon_reverse(lat: float, lon: float) -> dict:
    r = await client().get(PHOTON + "/reverse", params={"lat": lat, "lon": lon, "lang": "en", "limit": 1})
    r.raise_for_status()
    feats = r.json().get("features") or []
    if not feats:
        raise GeocoderUnavailable("photon: no result")
    pr = feats[0]["properties"]
    return {"address": _photon_addr(pr), "display_name": ", ".join(x for x in [pr.get("name"), pr.get("city"), pr.get("state")] if x)}


async def reverse_any(lat: float, lon: float) -> tuple[dict | None, str]:
    """Reverse geocode with fallbacks: Nominatim -> Photon -> NWS points (U.S. city/state)."""
    try:
        rev = await nominatim("/reverse", {"lat": lat, "lon": lon, "zoom": 16, "addressdetails": 1})
        if isinstance(rev, dict) and "error" not in rev:
            return rev, "nominatim"
    except Exception:
        pass
    try:
        return await photon_reverse(lat, lon), "photon"
    except Exception:
        pass
    try:
        r = await client().get(f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}", headers={"Accept": "application/geo+json"})
        r.raise_for_status()
        rl = ((r.json().get("properties") or {}).get("relativeLocation") or {}).get("properties") or {}
        if rl.get("city"):
            st = rl.get("state")
            return {"address": {"city": rl["city"], "state": st, "country_code": "us", "ISO3166-2-lvl4": f"US-{st}"},
                    "display_name": f"{rl['city']}, {st}"}, "nws"
    except Exception:
        pass
    return None, "none"


def _addr_city(a: dict) -> str | None:
    return a.get("city") or a.get("town") or a.get("village") or a.get("hamlet") or a.get("municipality")


def _state_abbr(a: dict) -> str | None:
    iso = a.get("ISO3166-2-lvl4") or ""
    return iso.split("-", 1)[1] if a.get("country_code") == "us" and "-" in iso else a.get("state")


async def build_place(lat: float, lon: float) -> dict:
    rev, via = await reverse_any(lat, lon)
    if not isinstance(rev, dict):
        return {"lat": lat, "lon": lon, "label": f"{lat:.3f}, {lon:.3f}", "city": None, "county": None,
                "state": None, "country_code": None, "neighborhood": None, "nearby": [], "south_side": False,
                "geocoder": via, "degraded": True}
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
            "display_name": rev.get("display_name"), "geocoder": via, "degraded": via != "nominatim"}


async def get_place(lat: float, lon: float) -> dict:
    c = cell(lat, lon, 0.01)  # ~1 km
    key = f"place:{c}"
    p = await cached(key, PLACE_TTL, lambda: build_place(*c))
    if p.get("degraded") and key in _cache and _cache[key][0] > time.time() - 60:
        _cache[key] = (time.time() - PLACE_TTL + 15 * 60, p)  # fallback answer: try Nominatim again in 15 min
    return p


async def get_nearby_osm(lat: float, lon: float) -> list[dict]:
    """Neighborhood names ~1.5 km around the point (4 extra reverse lookups, cached for a month)."""
    c = cell(lat, lon, 0.02)

    async def prod():
        out = []
        d = 0.0135  # ~1.5 km
        for dlat, dlon in ((d, 0), (-d, 0), (0, d / math.cos(math.radians(c[0]))), (0, -d / math.cos(math.radians(c[0])))):
            if time.time() < _nomi_blocked_until:
                raise GeocoderUnavailable("nominatim rate-limited")  # don't cache an empty list for a month
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



# ---------------------------------------------------------------- "dig deeper" links
# Words too common to tell two stories apart.
STOPWORDS = set("""
about after again against also among amid ahead around because been before being below between both but
could does doing down during each from further have having here into itself just more most much must near
never once only other over same says said should since some such than that their them then there these they
this those through under until very want were what when where which while will with within without would
year years your texas antonio news local week today first last make makes made take takes gets live update
updates video photos watch here's what's report reports amid""".split())


def sig_words(title: str) -> set[str]:
    return {w for w in norm_title(title).split() if len(w) >= 4 and w not in STOPWORDS}


def gnews_search_url(title: str, city: str | None) -> str:
    """A Google News search for the story's key words (a real search URL, not a guessed article)."""
    words = [w for w in re.findall(r"[\w'’-]+", title) if len(w) >= 3 and w.lower() not in STOPWORDS]
    q = " ".join(words[:8]) or title
    if city and city.lower() not in title.lower():
        q += f" {city}"
    return "https://news.google.com/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})


def add_related(items: list[dict], pool: list[dict], city: str | None, limit: int = 3) -> None:
    """Attach up to `limit` stories on the same topic from *other* outlets, found among the
    feeds we already fetched (headline word overlap, published within 5 days of each other)."""
    pool_sigs = [(o, sig_words(o["title"])) for o in pool]
    for it in items:
        s = sig_words(it["title"])
        rel, srcs, links = [], {it["source"]}, {it["link"]}
        if len(s) >= 3:
            for o, os_ in pool_sigs:
                if o["link"] in links or o["source"] in srcs or len(os_) < 3:
                    continue
                if it["published"] and o["published"] and abs(it["published"] - o["published"]) > 5 * 86400:
                    continue
                inter = len(s & os_)
                if inter >= 3 and inter / min(len(s), len(os_)) >= 0.5:
                    rel.append({"title": o["title"], "link": o["link"], "source": o["source"], "published": o["published"]})
                    srcs.add(o["source"])
                    links.add(o["link"])
                    if len(rel) >= limit:
                        break
        it["related"] = rel
        it["search_url"] = gnews_search_url(it["title"], city)


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
    more, sa_other = more[:80], sa_other[:40]
    pool = [i for i in all_items if not (JUNK_SOURCES.search(i["source"]) or JUNK_TITLES.search(i["title"]))]
    add_related(near + more + sa_other, pool, place.get("city"))
    return {
        "generated": now,
        "place": {k: place.get(k) for k in ("label", "neighborhood", "city", "county", "state", "state_abbr",
                                            "country_code", "south_side", "postcode")}
                 | {"nearby": [{"name": n["name"], "km": n["km"]} for n in place["nearby"][:10]]},
        "in_san_antonio": in_sa,
        "near": near,
        "more": more,
        "san_antonio": sa_other,
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
    try:
        res = await nominatim("/search", params)
    except Exception:
        return await geocode_fallback(q)
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



async def geocode_fallback(q: str) -> list[dict]:
    """When Nominatim is unavailable: U.S. ZIPs via Zippopotam.us, everything else via Photon."""
    if re.fullmatch(r"\d{5}(-\d{4})?", q):
        r = await client().get(f"https://api.zippopotam.us/us/{q[:5]}")
        if r.status_code == 404:
            return []
        r.raise_for_status()
        pl = (r.json().get("places") or [])
        return [{"lat": round(float(x["latitude"]), 4), "lon": round(float(x["longitude"]), 4),
                 "label": f"{q[:5]}, {x['place name']}, {x['state abbreviation']}",
                 "display_name": f"{x['place name']}, {x['state']} {q[:5]}", "country_code": "us"} for x in pl[:1]]
    r = await client().get(PHOTON + "/api", params={"q": q, "limit": 8, "lang": "en"})
    r.raise_for_status()
    out = []
    for f in r.json().get("features") or []:
        pr = f["properties"]
        if pr.get("osm_key") not in ("place", "boundary") and pr.get("type") not in ("city", "district", "locality", "county"):
            continue
        a = _photon_addr(pr)
        city = pr.get("name") or a.get("city")
        label = ", ".join(x for x in [city, _state_abbr(a), pr.get("country") if a.get("country_code") != "us" else None] if x)
        lon_, lat_ = f["geometry"]["coordinates"]
        out.append({"lat": round(lat_, 4), "lon": round(lon_, 4), "label": label,
                    "display_name": ", ".join(x for x in [pr.get("name"), pr.get("county"), pr.get("state"), pr.get("country")] if x),
                    "country_code": a.get("country_code")})
        if len(out) >= 5:
            break
    return out


# ---------------------------------------------------------------- events
# Public, keyless sources (checked 2026-09-29 from the build box):
#   * Visit San Antonio's events RSS (Simpleview): ~30 current/featured SA events with photos.
#     Each event page carries schema.org JSON-LD (venue, coordinates, dates, big photo) and an
#     "admission" note. robots.txt asks for a 2 s crawl delay, so detail pages are fetched one at
#     a time in the background and cached for a day.
#   * Eventbrite city pages (/d/{state}--{city}/events/): the public listing embeds the events as
#     JSON (name, local start time + time zone, venue + coordinates, photo). Ticket prices come
#     from each event page's JSON-LD "offers" (fetched in the background, cached for a day).
#     Eventbrite's /api/v3/destination/events/ is disallowed in robots.txt, so it isn't used.
#   * AllEvents city pages (allevents.in/{city}/all): schema.org JSON-LD Event list.
# Prices are only shown when the source states them; otherwise the UI says "Check price".
EVENTS_LIST_TTL = 30 * 60
EVENT_DETAIL_TTL = 24 * 3600
EVENT_FC_TTL = 30 * 60
EVENT_RADIUS_KM = 45
EVENT_DAYS = 45
SA_CENTER = (29.4241, -98.4936)
VSA_RSS = "https://www.visitsanantonio.com/event/rss/"
LD_RX = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
MDY_RX = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
HOST_DELAY = {"www.visitsanantonio.com": 2.1, "www.eventbrite.com": 1.0}
_detail_queues: dict[str, list[str]] = {}
_detail_workers: dict[str, asyncio.Task] = {}
_detail_queued: set[str] = set()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def ld_objects(page: str) -> list[dict]:
    """All schema.org objects in a page's JSON-LD blocks (flattening @graph and ItemList)."""
    out: list[dict] = []

    def add(o):
        if isinstance(o, list):
            for x in o:
                add(x)
        elif isinstance(o, dict):
            if "@graph" in o:
                add(o["@graph"])
            if o.get("itemListElement"):
                add([x.get("item", x) if isinstance(x, dict) else x for x in o["itemListElement"]])
            out.append(o)

    for block in LD_RX.findall(page):
        try:
            add(json.loads(block.strip()))
        except Exception:
            continue
    return out


def is_event_obj(o: dict) -> bool:
    t = o.get("@type")
    t = " ".join(t) if isinstance(t, list) else str(t or "")
    return t.endswith("Event") and bool(o.get("name"))


def _tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "America/Chicago")
    except Exception:
        return ZoneInfo("America/Chicago")


def parse_when(v: str | None, tz: ZoneInfo) -> tuple[datetime | None, bool]:
    """ISO date or datetime -> (aware datetime, has_time)."""
    if not v or not isinstance(v, str):
        return None, False
    v = v.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            return datetime.combine(date.fromisoformat(v), dtime(0, 0), tz), False
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=tz)
        return d, True
    except Exception:
        return None, False


def offers_price(offers) -> dict | None:
    """schema.org offers -> {"free", "text"}; None when the source gives no price."""
    if not offers:
        return None
    offers = offers if isinstance(offers, list) else [offers]
    lows, highs, cur = [], [], "USD"
    for o in offers:
        if not isinstance(o, dict):
            continue
        cur = o.get("priceCurrency") or cur
        for k, dest in (("lowPrice", lows), ("price", lows), ("highPrice", highs), ("price", highs)):
            try:
                if o.get(k) not in (None, ""):
                    dest.append(float(o[k]))
            except (TypeError, ValueError):
                pass
    if not lows and not highs:
        return None
    lo, hi = min(lows or highs), max(highs or lows)
    sym = "$" if cur == "USD" else cur + " "
    money = lambda x: f"{sym}{x:,.0f}" if x == int(x) else f"{sym}{x:,.2f}"
    if hi == 0:
        return {"free": True, "text": "Free"}
    if lo == 0:
        return {"free": False, "text": f"Free – {money(hi)}"}
    return {"free": False, "text": money(lo) if lo == hi else f"{money(lo)} – {money(hi)}"}


FREE_RX = re.compile(r"^\s*(free(\s+(admission|entry|event|to attend|and open to the public))?|\$0(\.00)?(\s*[-–(]?\s*free\)?)?)\s*[.!]?\s*$", re.I)


def admission_price(text: str | None) -> dict | None:
    """Visit San Antonio's free-text "admission" note, shown as written. Only plain "Free"/"$0"
    notes get the FREE badge (e.g. "Free with museum admission" is shown as text)."""
    t = clean_text(text, 140)
    if not t:
        return None
    return {"free": bool(FREE_RX.match(t)), "text": t}


def ld_place(loc) -> dict:
    if isinstance(loc, list):
        loc = next((x for x in loc if isinstance(x, dict)), {})
    if not isinstance(loc, dict) or loc.get("@type") == "VirtualLocation":
        return {}
    a = loc.get("address") or {}
    if isinstance(a, str):
        a = {"streetAddress": a}
    g = loc.get("geo") or {}
    try:
        lat, lon = float(g.get("latitude")), float(g.get("longitude"))
    except (TypeError, ValueError):
        lat = lon = None
    street = a.get("streetAddress") or ""
    parts = [street] + [x for x in (a.get("addressLocality"), a.get("addressRegion")) if x and x not in street]
    addr = ", ".join(p for p in parts if p)
    if a.get("postalCode") and a["postalCode"] not in addr:
        addr += " " + a["postalCode"]
    name = loc.get("name") or ""
    # no street address -> the coordinates are just the city's center; don't pin them on a map
    return {"venue": clean_text(name, 120) or None, "address": clean_text(addr, 160) or None,
            "lat": lat, "lon": lon, "city": a.get("addressLocality"), "approx": not street}


def ld_image(img) -> str | None:
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, dict):
        img = img.get("url")
    return img if isinstance(img, str) and img.startswith("http") else None


def base_event(**kw) -> dict:
    e = {"id": None, "title": None, "url": None, "source": None, "source_id": None, "image": None,
         "start": None, "end": None, "has_time": False, "venue": None, "address": None, "lat": None,
         "lon": None, "price": None, "summary": "", "categories": [], "also": [], "online": False, "approx": False}
    e.update(kw)
    return e


# --- Visit San Antonio
async def fetch_vsa() -> list[dict]:
    r = await client().get(VSA_RSS)
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    tz = _tz("America/Chicago")
    out = []
    for x in parsed.entries:
        link, title = x.get("link"), clean_text(x.get("title"), 200)
        if not link or not title:
            continue
        desc = x.get("summary") or x.get("description") or ""
        img = IMG_RX.search(desc)
        dates = [date(int(y), int(m), int(d)) for m, d, y in MDY_RX.findall(desc)]
        text = clean_text(MDY_RX.sub(" ", desc), 600)
        text = re.sub(r"^[\s\-–to]*(?:to\s+)?-?\s*", "", text).strip()
        start = datetime.combine(dates[0], dtime(0, 0), tz) if dates else None
        end = datetime.combine(dates[-1], dtime(0, 0), tz) if dates else None
        out.append(base_event(
            id="vsa:" + link, title=title, url=link, source="Visit San Antonio", source_id="vsa",
            image=html.unescape(img.group(1)) if img else None, start=start, end=end,
            summary=clean_text(text, 260), categories=[t.get("term", "").strip() for t in x.get("tags") or []][:4],
            city="San Antonio"))
    return out


def parse_vsa_detail(page: str) -> dict:
    d: dict = {}
    for o in ld_objects(page):
        if is_event_obj(o):
            d.update(ld_place(o.get("location")))
            tz = _tz("America/Chicago")
            s, st = parse_when(o.get("startDate"), tz)
            e, et = parse_when(o.get("endDate"), tz)
            if s:
                d["start"], d["has_time"] = s, st
            if e:
                d["end"] = e
            if ld_image(o.get("image")):
                d["image"] = ld_image(o.get("image"))
            if o.get("description"):
                d["summary"] = clean_text(o["description"], 260)
            p = offers_price(o.get("offers"))
            if p:
                d["price"] = p
            break
    i = page.find("var data = {")
    if i >= 0:
        try:
            data, _ = json.JSONDecoder().raw_decode(page, i + len("var data = "))
            if not d.get("price") and data.get("admission"):
                d["price"] = admission_price(data["admission"])
            if data.get("recurrence"):
                d["recurrence"] = clean_text(data["recurrence"], 80)
            if data.get("linkUrl", "").startswith("http"):
                d["website"] = data["linkUrl"]
        except Exception:
            pass
    return d


# --- Eventbrite
def eventbrite_url(place: dict, page: int = 1) -> str | None:
    if place.get("country_code") != "us" or not place.get("state_abbr"):
        return None
    city = place.get("city")
    if place.get("county") == "Bexar County" and city != "San Antonio":
        city = "San Antonio"  # suburbs inside the county share SA's listings
    if not city:
        return None
    u = f"https://www.eventbrite.com/d/{place['state_abbr'].lower()}--{_slug(city)}/events/"
    return u + (f"?page={page}" if page > 1 else "")


def parse_eventbrite_list(page: str) -> list[dict]:
    i = page.find("window.__SERVER_DATA__")
    if i < 0:
        return []
    j = page.find("=", i) + 1
    while page[j] in " \n\t":
        j += 1
    data, _ = json.JSONDecoder().raw_decode(page, j)
    found: list[dict] = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("_type") == "destination_event":
                found.append(o)
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    out = []
    for e in found:
        if e.get("is_online_event") or not e.get("url") or not e.get("name"):
            continue
        tz = _tz(e.get("timezone"))
        s = e.get("start_date")
        start = parse_when(f"{s}T{e['start_time']}" if s and e.get("start_time") else s, tz)
        end = parse_when(f"{e.get('end_date')}T{e['end_time']}" if e.get("end_date") and e.get("end_time") else e.get("end_date"), tz)
        v = e.get("primary_venue") or {}
        a = v.get("address") or {}
        try:
            lat, lon = float(a.get("latitude")), float(a.get("longitude"))
        except (TypeError, ValueError):
            lat = lon = None
        ta = e.get("ticket_availability") or {}
        price = None
        if ta.get("is_free") is True:
            price = {"free": True, "text": "Free"}
        elif ta.get("minimum_ticket_price"):
            lo = (ta.get("minimum_ticket_price") or {}).get("value")
            hi = (ta.get("maximum_ticket_price") or {}).get("value")
            if lo is not None:
                price = offers_price([{"lowPrice": lo / 100, "highPrice": (hi or lo) / 100,
                                       "priceCurrency": ta["minimum_ticket_price"].get("currency", "USD")}])
        out.append(base_event(
            id="eb:" + str(e.get("id")), title=clean_text(e["name"], 200), url=e["url"].split("?")[0],
            source="Eventbrite", source_id="eventbrite", image=ld_image(e.get("image")),
            start=start[0], has_time=start[1], end=end[0], venue=clean_text(v.get("name"), 120) or None,
            address=a.get("localized_address_display"), lat=lat, lon=lon, price=price,
            summary=clean_text(e.get("summary"), 260), city=a.get("city"),
            categories=[t.get("display_name") for t in (e.get("tags") or []) if isinstance(t, dict) and t.get("display_name")][:3]))
    return out


def parse_eventbrite_detail(page: str) -> dict:
    for o in ld_objects(page):
        if is_event_obj(o):
            d: dict = {}
            p = offers_price(o.get("offers"))
            if p:
                d["price"] = p
            if ld_image(o.get("image")):
                d["image"] = ld_image(o.get("image"))
            return d
    return {}


# --- AllEvents
def allevents_url(place: dict) -> str | None:
    city = place.get("city")
    if place.get("county") == "Bexar County":
        city = "San Antonio"
    return f"https://allevents.in/{_slug(city)}/all" if city and place.get("country_code") == "us" else None


AE_ID_RX = re.compile(r'\{"event_id":"(\d+)"')
AE_CAT_RX = re.compile(r'"gemma_categories":\[([^\]]*)\]')


def allevents_categories(page: str) -> dict[str, list[str]]:
    """AllEvents embeds its own per-event categories (e.g. "concerts", "comedy") in the list JSON."""
    cats: dict[str, list[str]] = {}
    marks = list(AE_ID_RX.finditer(page))
    for i, m in enumerate(marks):
        chunk = page[m.end(): marks[i + 1].start() if i + 1 < len(marks) else m.end() + 6000]
        c = AE_CAT_RX.search(chunk)
        if c and m.group(1) not in cats:
            vals = re.findall(r'"([^"]+)"', c.group(1))
            cats[m.group(1)] = [v.replace("-", " ").title() for v in vals][:4]
    return cats


def parse_allevents(page: str) -> list[dict]:
    out = []
    ae_cats = allevents_categories(page)
    for o in ld_objects(page):
        if not is_event_obj(o) or not o.get("url"):
            continue
        if "Online" in str(o.get("eventAttendanceMode") or ""):
            continue
        if re.search(r"\btickets?\s*$", o["name"], re.I):  # ticket-resale pages, not event listings
            continue
        tz = _tz("America/Chicago")
        s, st = parse_when(o.get("startDate"), tz)
        e, _ = parse_when(o.get("endDate"), tz)
        pl = ld_place(o.get("location"))
        out.append(base_event(
            id="ae:" + o["url"], title=clean_text(o["name"], 200), url=o["url"], source="AllEvents",
            source_id="allevents", image=ld_image(o.get("image")), start=s, has_time=st, end=e,
            price=offers_price(o.get("offers")), summary=clean_text(o.get("description"), 260),
            categories=ae_cats.get(o["url"].rstrip("/").rsplit("/", 1)[-1], []), **pl))
    return out


async def fetch_page(url: str) -> str:
    r = await client().get(url, headers={"Accept": "text/html,application/xhtml+xml"})
    r.raise_for_status()
    return r.text


async def event_source(sid: str, name: str, url: str, producer) -> dict:
    t0 = time.time()
    try:
        items = await cached(f"evlist:{url}", EVENTS_LIST_TTL, producer)
        return {"items": items, "status": {"id": sid, "name": name, "ok": True, "count": len(items), "url": url,
                                           "ms": int((time.time() - t0) * 1000)}}
    except Exception as ex:
        return {"items": [], "status": {"id": sid, "name": name, "ok": False, "url": url,
                                        "error": f"{type(ex).__name__}: {ex}"[:200]}}


# --- background detail enrichment (one worker per host, polite delay between requests)
def detail_cached(url: str) -> dict | None:
    hit = _cache.get("evdetail:" + url)
    if hit and time.time() - hit[0] < (EVENT_DETAIL_TTL if not hit[1].get("_failed") else 3600):
        return hit[1]
    return None


def queue_detail(url: str) -> None:
    if url in _detail_queued or detail_cached(url) is not None:
        return
    host = urllib.parse.urlsplit(url).netloc
    _detail_queued.add(url)
    _detail_queues.setdefault(host, []).append(url)
    w = _detail_workers.get(host)
    if w is None or w.done():
        _detail_workers[host] = asyncio.create_task(_detail_worker(host))


async def _detail_worker(host: str) -> None:
    q = _detail_queues[host]
    parser = parse_vsa_detail if "visitsanantonio" in host else parse_eventbrite_detail
    while q:
        url = q.pop(0)
        try:
            d = parser(await fetch_page(url))
        except Exception as ex:
            d = {"_failed": True, "error": f"{type(ex).__name__}"}
        _cache["evdetail:" + url] = (time.time(), d)
        _detail_queued.discard(url)
        await asyncio.sleep(HOST_DELAY.get(host, 1.0))


# --- NWS outlook per event day
async def event_forecast(lat: float, lon: float) -> dict | None:
    c = cell(lat, lon, 0.1)  # ~11 km: events around town share a handful of forecasts
    p = await get_points(*c)
    if p.get("unsupported"):
        return None
    grid = f'{p.get("gridId")}/{p.get("gridX")},{p.get("gridY")}'
    fc = await cached(f"evfc:{grid}", EVENT_FC_TTL, lambda: get_json(p["forecast"]))
    periods = []
    for x in (fc.get("properties") or {}).get("periods") or []:
        s, _ = parse_when(x.get("startTime"), timezone.utc)
        e, _ = parse_when(x.get("endTime"), timezone.utc)
        if s and e:
            periods.append((s, e, x))
    return {"periods": periods, "tz": p.get("timeZone"), "city": ((p.get("relativeLocation") or {}).get("properties") or {}).get("city")}


def outlook_for(ev: dict, fc: dict | None, now: datetime) -> dict:
    if not fc or not fc["periods"]:
        return {"available": False, "reason": "unavailable"}
    tz = _tz(fc.get("tz"))
    if ev["has_time"] and ev["start"] > now:
        t = ev["start"]
    else:
        day = max(ev["start"].astimezone(tz).date(), now.astimezone(tz).date())
        t = max(datetime.combine(day, dtime(12, 0), tz), now)
    first, last = fc["periods"][0], fc["periods"][-1]
    if t >= last[1]:
        return {"available": False, "reason": "beyond", "until": last[1].isoformat()}
    s, e, x = next((p for p in fc["periods"] if p[0] <= t < p[1]), first)
    return {"available": True, "name": x.get("name"), "temp": x.get("temperature"), "unit": x.get("temperatureUnit"),
            "short": x.get("shortForecast"), "pop": (x.get("probabilityOfPrecipitation") or {}).get("value"),
            "icon": x.get("icon"), "day": x.get("isDaytime"), "near": fc.get("city")}


def _merge_detail(ev: dict) -> dict:
    d = detail_cached(ev["url"]) or {}
    for k, v in d.items():
        if k.startswith("_") or v in (None, "", []):
            continue
        if k == "image" and ev.get("image") and "visitsanantonio" not in ev["url"]:
            continue
        ev[k] = v
    return ev


def _dedupe_events(events: list[dict]) -> list[dict]:
    rank = {"vsa": 0, "eventbrite": 1, "allevents": 2}
    events.sort(key=lambda e: (rank.get(e["source_id"], 9), -(bool(e.get("price")) + bool(e.get("image")) + bool(e.get("lat")))))
    kept: list[dict] = []
    for e in events:
        sig = sig_words(e["title"])
        dup = None
        for k in kept:
            same_day = k["start"].date() == e["start"].date() or (k["end"] and k["start"] <= e["start"] <= k["end"])
            ks = sig_words(k["title"])
            if same_day and (norm_title(k["title"]) == norm_title(e["title"]) or
                             (sig and ks and len(sig & ks) / min(len(sig), len(ks)) >= 0.7)):
                dup = k
                break
        if dup:
            if e["url"] not in (dup["url"], *[a["url"] for a in dup["also"]]):
                dup["also"].append({"source": e["source"], "url": e["url"]})
            if dup.get("lat") is None and e.get("lat") is not None:
                dup["lat"], dup["lon"], dup["approx"] = e["lat"], e["lon"], e.get("approx", False)
            for f in ("image", "price", "venue", "address"):
                if not dup.get(f) and e.get(f):
                    dup[f] = e[f]
            if e["has_time"] and not dup["has_time"] and e["start"].date() == dup["start"].date():
                dup["start"], dup["has_time"] = e["start"], True
        else:
            kept.append(e)
    return kept


# --- categories (keyword tagging; source categories count too)
CONCERT_CATS = {"music", "concerts", "concert", "live music", "rock music", "jazz", "classical", "country music",
                "hip hop", "latin music", "pop music"}
CONCERT_RX = re.compile(r"\b(concerts?|live music|symphony|orchestra|philharmonic|jazz|blues|mariachi|conjunto|tejano|"
                        r"tribute|recital|opera|choir|chorale|band|dj|hip[- ]hop|r&b|m[uú]sica|en concierto|unplugged|"
                        r"live (in|at)|y la familia|flamenco|singalong|sing-along|open mic)\b", re.I)
COMEDY_RX = re.compile(r"\b(comedy|comedian|stand[- ]up|improv|sketch)\b", re.I)
FEST_RX = re.compile(r"\b(festivals?|fest|fiestas?|parade|carnival|block party|night market|market days?|oktoberfest|"
                     r"muertos|jubilee|jamboree|rodeo|fair)\b", re.I)
NOT_FEST_RX = re.compile(r"\b(career|job|jobs|resource|hiring|college|university|benefits?|health|wellness|vendor)\s+fair\b", re.I)
CLASS_RX = re.compile(r"\b(class(es)?|workshops?|lectures?|talks?|seminars?|courses?|lessons?|training|boot ?camp|"
                      r"clinic|story ?time|tutorial|certification|book club|library|learn(ing)?|panel discussion|"
                      r"demonstration|paint (&|and) sip|speaks?|speakers?|to speak)\b", re.I)
CLASS_CATS = {"class, training, or workshop", "classes", "workshops", "lectures", "workshop"}
FOOD_CATS = {"food", "food & drink", "culinary", "beer", "spirits", "wine", "food drink", "food and drink"}
FOOD_RX = re.compile(r"\b(food|foodie|tacos?|taquer[ií]a|bbq|barbecue|brisket|brunch|breakfast|dinner|lunch|tasting|"
                     r"cook(ing)?|culinary|chef|beer|wine|tequila|mezcal|margaritas?|chili|pozole|tamales?|coffee|brew(ery|ing)?|"
                     r"bak(ery|ed)|pastr(y|ies)|croissants?|pizza|burgers?|dining|feast|eats?|restaurant|menu|dessert|"
                     r"cookies?|seafood|steak(house)?|smokehouse|cantina|caf[eé]|kitchen|torta|birria|barbacoa|"
                     r"panader[ií]a|donuts?|ice cream|paleta|aguas? frescas|cocktails?|sushi|ramen|pho|buffet)\b", re.I)
FREE_TITLE_RX = re.compile(r"\bfree\b(?!\s*(with|w/|for members|parking|refills?|-\s*\$))", re.I)


def event_tags(e: dict) -> tuple[list[str], bool]:
    """Returns (tags, free) where tags ⊆ concerts/festivals/classes/food and free = the source says it's free."""
    cats = {html.unescape(c).strip().lower() for c in e.get("categories") or []}
    title = html.unescape(e.get("title") or "")
    text = title + " " + " ".join(cats)
    tags = []
    comedy = bool(COMEDY_RX.search(text))
    if not comedy and (cats & CONCERT_CATS or CONCERT_RX.search(title)):
        tags.append("concerts")
    if (FEST_RX.search(title) or any("festival" in c for c in cats)) and not NOT_FEST_RX.search(title):
        tags.append("festivals")
    if cats & CLASS_CATS or CLASS_RX.search(title):
        tags.append("classes")
    if cats & FOOD_CATS or FOOD_RX.search(title):
        tags.append("food")
    price = e.get("price")
    free = bool(price and price.get("free")) or (not price and ("free" in cats or bool(FREE_TITLE_RX.search(title))))
    return tags, free


async def build_events(lat: float, lon: float) -> dict:
    place = dict(await get_place(lat, lon))
    now = datetime.now(timezone.utc)
    near_sa = km_between(lat, lon, *SA_CENTER) <= 60
    jobs = []
    if near_sa:
        jobs.append(event_source("vsa", "Visit San Antonio", VSA_RSS, fetch_vsa))
    for pg in (1, 2):
        u = eventbrite_url(place, pg)
        if u:
            jobs.append(event_source("eventbrite" if pg == 1 else "eventbrite2", f"Eventbrite{'' if pg == 1 else f' (page {pg})'}", u,
                                     lambda u=u: _eb(u)))
    u = allevents_url(place)
    if u:
        jobs.append(event_source("allevents", "AllEvents", u, lambda u=u: _ae(u)))
    results = await asyncio.gather(*jobs)
    raw = [dict(e, also=[]) for r in results for e in r["items"]]
    horizon = now + timedelta(days=EVENT_DAYS)
    events = []
    for e in raw:
        _merge_detail(e)
        if not e["start"] or e.get("online"):
            continue
        if e["end"] and e["end"] >= e["start"]:
            end = e["end"]
            if (end.hour, end.minute) == (0, 0):  # date-only end: lasts through that day
                end = datetime.combine(end.date(), dtime(23, 59), end.tzinfo)
        elif e["has_time"]:
            end = e["start"] + timedelta(hours=3)
        else:
            end = datetime.combine(e["start"].date(), dtime(23, 59), e["start"].tzinfo)
        if end < now or e["start"] > horizon:
            continue
        if e["lat"] is not None and km_between(lat, lon, e["lat"], e["lon"]) > EVENT_RADIUS_KM:
            continue
        e["end_eff"] = end
        events.append(e)
    events = _dedupe_events(events)
    # enrich the ones people will see first (photos/venue for Visit SA, prices for Eventbrite)
    events.sort(key=lambda e: e["start"])
    shown = [e for e in events if e["start"] >= now - timedelta(hours=12)][:40] + \
            [e for e in events if e["start"] < now - timedelta(hours=12)]
    pending = 0
    for e in shown:
        if e["source_id"] == "vsa" or (e["source_id"] == "eventbrite" and not e.get("price")):
            if detail_cached(e["url"]) is None:
                queue_detail(e["url"])
                pending += 1
    # NWS outlook: one forecast per ~11 km cell (max 8 cells, else the user's own)
    fcs: dict[tuple, dict | None] = {}
    user_cell = cell(lat, lon, 0.1)

    async def fc_for(c):
        if c not in fcs:
            try:
                fcs[c] = await event_forecast(*c)
            except Exception:
                fcs[c] = None
        return fcs[c]

    await fc_for(user_cell)
    out_up, out_on = [], []
    for e in events:
        c = cell(e["lat"], e["lon"], 0.1) if e["lat"] is not None else user_cell
        if c not in fcs and len(fcs) >= 8:
            c = user_cell
        fc = await fc_for(c)
        ongoing = e["start"] < now - timedelta(hours=12) and (e["end_eff"] - e["start"]) > timedelta(days=1)
        item = {k: e.get(k) for k in ("id", "title", "url", "source", "source_id", "image", "has_time", "venue", "address",
                                      "lat", "lon", "approx", "price", "summary", "categories", "also", "recurrence", "website")}
        tags, free = event_tags(item)
        if not item["price"] and "Free" in (item["categories"] or []):  # Visit San Antonio files it under "Free"
            item["price"] = {"free": True, "text": "Free (per listing)"}
        item.update(tags=tags, free=free)
        item.update(start=e["start"].isoformat(), end=e["end"].isoformat() if e["end"] else None,
                    km=round(km_between(lat, lon, e["lat"], e["lon"]), 1) if e["lat"] is not None and not e.get("approx") else None,
                    weather=outlook_for(e, fc, now), ongoing=ongoing)
        (out_on if ongoing else out_up).append(item)
    out_on.sort(key=lambda i: i["end"] or i["start"])
    return {
        "generated": time.time(),
        "place": {"label": place.get("label"), "city": place.get("city"), "neighborhood": place.get("neighborhood")},
        "events": out_up[:60], "ongoing": out_on[:20], "pending": pending,
        "radius_km": EVENT_RADIUS_KM, "days": EVENT_DAYS,
        "message": None if jobs else "Event listings are only available for U.S. cities for now.",
        "sources": [r["status"] for r in results],
    }


async def _eb(u: str) -> list[dict]:
    return parse_eventbrite_list(await fetch_page(u))


async def _ae(u: str) -> list[dict]:
    return parse_allevents(await fetch_page(u))


# ---------------------------------------------------------------- food reviews (San Antonio)
# Only real, public feeds. Local creators = YouTube channel RSS (public, no key); outlets = RSS or a
# Google News site: search. A feed that fails is simply left out (and reported in "sources").
FOOD_TTL = 30 * 60
FOOD_DAYS = 60
YT_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id="
SA_RX = re.compile(r"\b(san antonio|satx|sanantonio|alamo city|sa\b)", re.I)
ELSEWHERE_RX = re.compile(r"\b(austin|houston|dallas|fort worth|el paso|mckinney|plano|frisco|waco|lubbock|corpus christi|"
                          r"laredo|mcallen|galveston|denton|arlington|killeen|midland|odessa|amarillo)\b", re.I)
FOOD_SOURCES = [
    # local creators (YouTube; checked by hand: San Antonio-based, posting SA food content)
    {"id": "yt-cherise", "kind": "creator", "name": "Cherise SA Texas Food Guide",
     "url": YT_FEED + "UCr5gIcFnRxKTaDNrcfA8ZaA", "home": "https://www.youtube.com/channel/UCr5gIcFnRxKTaDNrcfA8ZaA"},
    {"id": "yt-hannah", "kind": "creator", "name": "Hannah | SATX Creator", "food_only": True,
     "url": YT_FEED + "UCuluE-lMh--_7hyziZAvDvQ", "home": "https://www.youtube.com/channel/UCuluE-lMh--_7hyziZAvDvQ"},
    {"id": "yt-texaseats", "kind": "creator", "name": "Texas Eats", "sa_only": True,
     "url": YT_FEED + "UCsC3RShvhYxR9bTUfogm6pg", "home": "https://www.youtube.com/channel/UCsC3RShvhYxR9bTUfogm6pg"},
    # local food desks
    {"id": "sacurrent-food", "kind": "outlet", "name": "San Antonio Current · Food & Drink",
     "url": "https://www.sacurrent.com/category/food-drink/feed/", "home": "https://www.sacurrent.com/food-drink/"},
    {"id": "en-food", "kind": "outlet", "name": "Express-News · Food", "gnews": True,
     "url": GN + urllib.parse.quote("site:expressnews.com/food when:30d"), "home": "https://www.expressnews.com/food/"},
    {"id": "mysa-food", "kind": "outlet", "name": "MySA · Food", "gnews": True,
     "url": GN + urllib.parse.quote("site:mysanantonio.com/food when:30d"), "home": "https://www.mysanantonio.com/food/"},
]


# --- restaurant guess for food videos (creators put the spot, often with its address, in the title)
_ST = (r"(?:Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd|Parkway|Pkwy|Drive|Dr|Highway|Hwy|Lane|Ln|Way|Trail|Trl|"
       r"Expressway|Expy|Freeway|Fwy|Plaza|Court|Ct|Circle|Cir|Loop\s*\d{3,4})")
ADDR_RX = re.compile(r"\b(\d{2,6}\s+(?:(?:N|S|E|W|NW|NE|SW|SE|North|South|East|West|Northwest|Northeast|Southwest|Southeast)\.?\s+)?"
                     r"(?:[A-Z0-9][\w'’.]*\s+){0,4}?" + _ST + r"\.?)(?![\w])"
                     r"(?:,?\s*(?:Suite|Ste\.?|#)\s*[\w-]+)?"
                     r"(?:,?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),?\s*(?:TX|Texas))?(?:\s*(\d{5}))?")
_MINOR = {"and", "de", "del", "la", "el", "los", "las", "of", "the", "y", "e", "on", "&"}
_NOT_A_SPOT = re.compile(r"^(san antonio|texas|tx|satx|the best|best|this|that|home|here|there|pearl|downtown|the pearl|"
                         r"the airport|san antonio international airport|youtube|tiktok|shorts)$", re.I)


def _spotlike(s: str, max_words: int = 6) -> str | None:
    s = re.sub(r"[\s!?.,:;|–—-]+$", "", re.sub(r"^[\s!?.,:;|–—-]+", "", s or "")).strip()
    words = s.split()
    if not (1 <= len(words) <= max_words) or len(s) > 48 or _NOT_A_SPOT.match(s):
        return None
    if re.match(r"(?:the\s+)?\w+est\b", s, re.I) and not re.match(r"(?:the\s+)?(?:forest|west|crest|nest)\b", s, re.I):
        return None  # "The Wildest Burger", "Best ..." is a claim, not a place
    if len(words) > 1 and s.isupper():
        return None  # "THIS PLACE IS A HOME RUN"
    if not all(w[:1].isupper() or w[:1].isdigit() or w.lower() in _MINOR for w in words):
        return None
    return s


def guess_place(title: str) -> dict | None:
    """Best-effort {name, address} for a food video, from its title. None when we can't tell."""
    t = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", " ", title or "")
    t = re.sub(r"\s+", " ", t).strip()
    m = ADDR_RX.search(t)
    if m:
        city = m.group(2) or "San Antonio"
        addr = f"{m.group(1)}, {city}, TX" + (f" {m.group(3)}" if m.group(3) else "")
        before = re.sub(r"\b\d+\s+Locations?!?", " ", t[:m.start()], flags=re.I)
        words = before.split()
        while len(words) > 1 and words[0].isupper() and len(words[0]) > 1:
            words.pop(0)  # leading ALL-CAPS dish hype: "GIANT PUMPKIN TORTA Panfila Cantina"
        name = _spotlike(" ".join(words), 7)
        return {"name": name, "address": addr}
    for rx in (r"\bat\s+(.+?)[\s!?.]*$",                    # "... in San Antonio at Alzer’s Roastery"
               r"\s[-–—|]\s+([^-–—|]+?)[\s!?.]*$",           # "Best Soup in San Antonio? - Picnikins"
               r"^(.+?)\s+(?:in\s+)?San Antonio\b(?!\s*\?)"):  # "2M Smokehouse in San Antonio is ..."
        m = re.search(rx, t)
        if m and (name := _spotlike(m.group(1), 5 if rx.startswith("^") else 6)):
            return {"name": name, "address": None}
    return None


async def _fetch_food(src: dict) -> list[dict]:
    r = await client().get(src["url"])
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    out = []
    for e in parsed.entries:
        title, link = clean_text(e.get("title"), 200), e.get("link")
        if not title or not link:
            continue
        outlet = src["name"]
        if src.get("gnews"):
            pub = (e.get("source") or {}).get("title")
            title = re.sub(r"\s+-\s+" + re.escape(pub) + r"$", "", title) if pub else re.sub(r"\s+-\s+[^-]{2,60}$", "", title)
        if src.get("food_only") and not FOOD_RX.search(title):
            continue
        if src.get("sa_only") and not SA_RX.search(title):
            continue
        if src["kind"] == "outlet" and ELSEWHERE_RX.search(title) and not SA_RX.search(title):
            continue  # statewide food desks: keep it local
        if src["kind"] == "creator":
            title = re.sub(r"(\s*#[\w]+)+\s*$", "", title).strip() or title  # trailing hashtag soup
        summary = "" if src.get("gnews") or src["kind"] == "creator" else clean_text(
            re.sub(r"The post .{0,300}? appeared first on .*$", "", e.get("summary") or "", flags=re.S), 180)
        out.append({"title": title, "url": link, "creator": outlet if src["kind"] == "creator" else None,
                    "outlet": outlet, "author": None if src["kind"] == "creator" or src.get("gnews") else e.get("author"),
                    "kind": src["kind"], "video": "youtube.com" in link, "published": entry_time(e),
                    "image": None if src.get("gnews") else thumbnail(e), "summary": summary, "source_id": src["id"],
                    "place": guess_place(title) if src["kind"] == "creator" else None})
    return out


async def build_food(lat: float, lon: float) -> dict:
    if km_between(lat, lon, *SA_CENTER) > 80:
        return {"generated": time.time(), "items": [], "sources": [],
                "message": "Food reviews are San Antonio-only for now."}

    async def one(src):
        t0 = time.time()
        try:
            items = await cached("food:" + src["url"], FOOD_TTL, lambda: _fetch_food(src))
            return items, {"id": src["id"], "name": src["name"], "kind": src["kind"], "home": src["home"], "ok": True,
                           "count": len(items), "ms": int((time.time() - t0) * 1000)}
        except Exception as ex:
            return [], {"id": src["id"], "name": src["name"], "kind": src["kind"], "home": src["home"], "ok": False,
                        "error": f"{type(ex).__name__}: {ex}"[:200]}

    res = await asyncio.gather(*(one(s) for s in FOOD_SOURCES))
    cutoff = time.time() - FOOD_DAYS * 86400
    items, seen = [], set()
    for its, _ in res:
        for it in sorted((i for i in its if (i["published"] or 0) >= cutoff), key=lambda i: -(i["published"] or 0))[:8]:
            k = norm_title(it["title"])
            if k not in seen:
                seen.add(k)
                items.append(it)
    items.sort(key=lambda i: -(i["published"] or 0))
    return {"generated": time.time(), "items": items, "days": FOOD_DAYS, "message": None,
            "sources": [st for _, st in res]}



# ---------------------------------------------------------------- sports
# All keyless public sources (verified 2026-09-29): ESPN's public site API (scores, schedules,
# standings, news + the thumbnails that come with each story), the MLB Stats API (MLB scores and
# the Double-A San Antonio Missions), team/fan RSS and YouTube feeds, and Google News.
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports"
MLBAPI = "https://statsapi.mlb.com/api/v1"
SPURS_ID = "24"
MISSIONS_ID = 510
TEXAS_LEAGUE_ID = 109
TX_TEAMS = {"nfl": {"DAL", "HOU"}, "nba": {"SA", "DAL", "HOU"}, "mlb": {"TEX", "HOU"}}
MLB_TX_IDS = {140, 117}   # Rangers, Astros (MLB Stats API ids)
SPORTS_TTL = 5 * 60
SPURS_FEEDS = [
    {"id": "reddit", "name": "r/NBASpurs (Reddit, top this week)", "kind": "reddit", "home": "https://www.reddit.com/r/NBASpurs/",
     "url": "https://www.reddit.com/r/NBASpurs/top/.rss?t=week"},
    {"id": "yt-spurs", "name": "San Antonio Spurs on YouTube", "kind": "video", "home": "https://www.youtube.com/@Spurs",
     "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCEZHE-0CoHqeL1LGFa2EmQw"},
    {"id": "ptr", "name": "Pounding The Rock (SB Nation)", "kind": "blog", "home": "https://www.poundingtherock.com/",
     "url": "https://www.poundingtherock.com/rss/index.xml"},
    dict(gnews("gn-spurs", "Google News: Spurs", "\"San Antonio Spurs\" OR Wembanyama when:3d"), home="https://news.google.com/"),
]
MISSIONS_GN = gnews("gn-missions", "Google News: San Antonio Missions",
                    "\"San Antonio Missions\" (baseball OR \"Wolff Stadium\" OR \"Texas League\" OR Padres OR Double-A) when:60d")
MISSIONS_NOT = re.compile(r"national historical park|unesco|world heritage|mission (church|reach|trail|san jos|concepci|espada)|"
                          r"\bmissions? (park|trail)\b|heritage festival|archdiocese|historic mission", re.I)


def _espn_score(x):
    v = x.get("score")
    if isinstance(v, dict):
        v = v.get("displayValue")
    return v if v not in (None, "") else None


def espn_game(e: dict, league: str) -> dict:
    cc = (e.get("competitions") or [{}])[0]
    st = (cc.get("status") or e.get("status") or {}).get("type") or {}
    side = {}
    for x in cc.get("competitors") or []:
        t = x.get("team") or {}
        rec = x.get("records") or x.get("record") or []
        side[x.get("homeAway", "home")] = {
            "name": t.get("displayName") or t.get("name"), "short": t.get("shortDisplayName") or t.get("name"),
            "abbr": t.get("abbreviation"), "id": str(t.get("id") or ""), "score": _espn_score(x), "winner": x.get("winner"),
            "record": (rec[0].get("summary") or rec[0].get("displayValue")) if rec else None}
    link = next((l.get("href") for l in e.get("links") or [] if (l.get("href") or "").startswith("https://www.espn.com")), None)
    notes = [n.get("headline") for n in cc.get("notes") or [] if n.get("headline")]
    tv = [n for b in cc.get("broadcasts") or [] for n in (b.get("names") or [])]
    abbrs = {side.get("home", {}).get("abbr"), side.get("away", {}).get("abbr")}
    return {"id": str(e.get("id")), "league": league, "date": e.get("date"), "state": st.get("state") or "pre",
            "detail": st.get("shortDetail") or st.get("detail") or st.get("description"), "home": side.get("home"), "away": side.get("away"),
            "note": notes[0] if notes else ((e.get("seasonType") or {}).get("name") if (e.get("seasonType") or {}).get("type") in (1, 3) else None),
            "tv": ", ".join(tv[:2]) or None, "link": link, "texas": bool(abbrs & TX_TEAMS.get(league, set()))}


def espn_articles(d: dict, limit: int = 12) -> list[dict]:
    out = []
    for a in d.get("articles") or []:
        link = ((a.get("links") or {}).get("web") or {}).get("href")
        if not link or not a.get("headline"):
            continue
        img = next((i.get("url") for i in a.get("images") or [] if i.get("url")), None)
        pub = a.get("published") or a.get("lastModified")
        try:
            ts = datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp() if pub else None
        except ValueError:
            ts = None
        out.append({"id": str(a.get("id") or link), "title": clean_text(a["headline"], 200), "summary": clean_text(a.get("description"), 260),
                    "link": link, "image": img, "source": "ESPN", "published": ts, "video": a.get("type") == "Media"})
        if len(out) >= limit:
            break
    return out


def _merge_news(*lists, limit=14):
    seen, out = set(), []
    for it in sorted((i for l in lists for i in l), key=lambda i: -(i.get("published") or 0)):
        k = norm_title(it["title"])[:60]
        if k in seen or it["id"] in seen:
            continue
        seen.update({k, it["id"]})
        out.append(it)
    return out[:limit]


async def sjson(url: str, ttl: int = SPORTS_TTL) -> Any:
    async def go():
        r = await client().get(url, headers={"Accept": "application/json"})
        r.raise_for_status()
        return r.json()
    return await cached("sport:" + url, ttl, go, stale=6 * 3600)


class SportsLog:
    def __init__(self):
        self.sources: list[dict] = []

    async def run(self, name: str, home: str, coro, default=None):
        t0 = time.time()
        try:
            v = await coro
            n = len(v) if isinstance(v, list) else None
            self.sources.append({"name": name, "home": home, "ok": True, "count": n, "ms": int((time.time() - t0) * 1000)})
            return v
        except Exception as ex:
            self.sources.append({"name": name, "home": home, "ok": False, "error": f"{type(ex).__name__}: {ex}"[:160]})
            return default


def _texas_first(games: list[dict]) -> list[dict]:
    order = {"in": 0, "pre": 1, "post": 2}
    return sorted(games, key=lambda g: (not g["texas"], order.get(g["state"], 3), g["date"] or ""))


async def espn_scoreboard(league: str, path: str) -> list[dict]:
    d = await sjson(f"{ESPN}/{path}/scoreboard", 120)
    return _texas_first([espn_game(e, league) for e in d.get("events") or []])


async def espn_news(path: str, team: str | None = None, limit: int = 12) -> list[dict]:
    q = f"?limit={limit}" + (f"&team={team}" if team else "")
    return espn_articles(await sjson(f"{ESPN}/{path}/news{q}", 15 * 60), limit)


async def feed_items(feed: dict) -> list[dict]:
    items = await cached("feed:" + feed["url"], 20 * 60, lambda: _fetch_feed(feed), stale=6 * 3600)
    out = []
    for i in items:
        it = dict(i, id=i["link"], kind=feed["kind"], video="youtube.com" in (i["link"] or ""))
        if feed["kind"] == "reddit":
            it["summary"] = ""
            it["source"] = "r/NBASpurs"
        out.append(it)
    return out


async def spurs_block(log: SportsLog) -> dict:
    team = await log.run("ESPN: Spurs team page", "https://www.espn.com/nba/team/_/name/sa/san-antonio-spurs",
                         sjson(f"{ESPN}/basketball/nba/teams/{SPURS_ID}", 15 * 60), {})
    t = (team or {}).get("team") or {}
    rec = ((t.get("record") or {}).get("items") or [{}])[0].get("summary")
    # schedule: this season (preseason + regular season + playoffs)
    async def sched(qs):
        try:
            d = await sjson(f"{ESPN}/basketball/nba/teams/{SPURS_ID}/schedule{qs}", 10 * 60)
            return d, [espn_game(e, "nba") for e in d.get("events") or []]
        except Exception:
            return {}, []
    (d1, pre), (_, reg), (_, post) = await asyncio.gather(sched("?seasontype=1"), sched("?seasontype=2"), sched("?seasontype=3"))
    season = (d1.get("season") or {}).get("year")
    games = sorted({g["id"]: g for g in pre + reg + post}.values(), key=lambda g: g["date"] or "")
    done = [g for g in games if g["state"] == "post"]
    last_season = None
    if not done and season:  # offseason / preseason: last season's final game (e.g. the Finals)
        (_, lpost), (_, lreg) = await asyncio.gather(sched(f"?season={season - 1}&seasontype=3"), sched(f"?season={season - 1}&seasontype=2"))
        prev = sorted([g for g in lreg + lpost if g["state"] == "post"], key=lambda g: g["date"] or "")
        done = prev[-5:]
        last_season = f"{season - 2}-{str(season - 1)[2:]}"
    live = [g for g in games if g["state"] == "in"]
    upcoming = [g for g in games if g["state"] == "pre"][:6]
    log.sources.append({"name": "ESPN: Spurs schedule", "home": "https://www.espn.com/nba/team/schedule/_/name/sa", "ok": bool(games or done), "count": len(games)})
    # standings: this season, or last season's final table before any games are played
    standings = None
    try:
        async def table(qs=""):
            d = await sjson(f"{ESPN_STANDINGS}/basketball/nba/standings{qs}", 30 * 60)
            west = next(ch for ch in d["children"] if "West" in ch["name"])
            rows = []
            for e in west["standings"]["entries"]:
                st = {x["name"]: x for x in e["stats"]}
                val = lambda k: (st.get(k) or {}).get("value")
                disp = lambda k: (st.get(k) or {}).get("displayValue")
                rows.append({"team": e["team"].get("displayName"), "abbr": e["team"].get("abbreviation"), "seed": val("playoffSeed"),
                             "w": int(val("wins") or 0), "l": int(val("losses") or 0), "gb": disp("gamesBehind"), "streak": disp("streak"),
                             "spurs": str(e["team"].get("id")) == SPURS_ID})
            rows.sort(key=lambda r: (r["seed"] or 99, -r["w"]))
            return {"season": west["standings"].get("seasonDisplayName"), "conference": west["name"], "rows": rows}
        standings = await table()
        if not any(r["w"] + r["l"] for r in standings["rows"]) and season:
            standings = await table(f"?season={season - 1}")
            standings["final"] = True
        log.sources.append({"name": "ESPN: NBA standings", "home": "https://www.espn.com/nba/standings", "ok": True, "count": len(standings["rows"])})
    except Exception as ex:
        log.sources.append({"name": "ESPN: NBA standings", "home": "https://www.espn.com/nba/standings", "ok": False, "error": f"{type(ex).__name__}: {ex}"[:160]})
    news = await log.run("ESPN: Spurs news", "https://www.espn.com/nba/team/_/name/sa/san-antonio-spurs",
                         espn_news("basketball/nba", SPURS_ID, 16), [])
    feeds = await asyncio.gather(*(log.run(f["name"], f["home"], feed_items(f), []) for f in SPURS_FEEDS))
    by = {f["id"]: items for f, items in zip(SPURS_FEEDS, feeds)}
    now = time.time()
    fresh = lambda items, days: [i for i in items if not i.get("published") or now - i["published"] < days * 86400]
    return {"record": rec, "standing": t.get("standingSummary"), "season": (d1.get("season") or {}).get("displayName"),
            "live": live, "last": done[-3:][::-1], "last_season": last_season, "upcoming": upcoming, "standings": standings,
            "news": _merge_news(news, fresh(by["gn-spurs"], 3), limit=14),
            "reddit": by["reddit"][:8], "videos": fresh(by["yt-spurs"], 21)[:8], "blog": fresh(by["ptr"], 14)[:6]}


def mlb_game(g: dict, league: str = "mlb") -> dict:
    st = g.get("status") or {}
    code = st.get("abstractGameCode")
    state = {"F": "post", "L": "in"}.get(code, "pre")
    if st.get("detailedState") in ("Postponed", "Cancelled", "Suspended"):
        state = "post"
    side = {}
    for k in ("home", "away"):
        t = g["teams"][k]
        tm = t.get("team") or {}
        lr = t.get("leagueRecord") or {}
        side[k] = {"name": tm.get("name"), "short": tm.get("teamName") or tm.get("clubName") or tm.get("name"), "abbr": tm.get("abbreviation"),
                   "id": str(tm.get("id")), "score": None if t.get("score") is None else str(t["score"]), "winner": t.get("isWinner"),
                   "record": f"{lr['wins']}-{lr['losses']}" if "wins" in lr else None}
    ls = g.get("linescore") or {}
    if state == "in":
        detail = f"{ls.get('inningState', '')} {ls.get('currentInningOrdinal', '')}".strip() or st.get("detailedState")
    elif state == "post":
        detail = st.get("detailedState") if st.get("detailedState") != "Final" else ("Final" + (f"/{ls['currentInning']}" if (ls.get("currentInning") or 9) != 9 else ""))
    else:
        detail = None   # the page formats the start time in the user's zone
    ids = {g["teams"]["home"]["team"].get("id"), g["teams"]["away"]["team"].get("id")}
    link = f"https://www.mlb.com/gameday/{g['gamePk']}" if league == "mlb" else f"https://www.milb.com/gameday/{g['gamePk']}"
    return {"id": str(g["gamePk"]), "league": league, "date": g.get("gameDate"), "state": state, "detail": detail,
            "home": side["home"], "away": side["away"], "note": g.get("seriesDescription") if g.get("gameType") not in ("R", None) else None,
            "tv": None, "link": link, "texas": bool(ids & MLB_TX_IDS) or league == "milb",
            "venue": (g.get("venue") or {}).get("name")}


async def mlb_scores() -> dict:
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    d = await sjson(f"{MLBAPI}/schedule?sportId=1&startDate={today - timedelta(days=3)}&endDate={today + timedelta(days=3)}&hydrate=linescore,team", 90)
    dates = {x["date"]: [mlb_game(g) for g in x["games"]] for x in d.get("dates") or []}
    t = str(today)
    show = t if t in dates else max([k for k in dates if k < t], default=None) or min(dates, default=None)
    nxt = min([k for k in dates if k > (show or t)], default=None)
    return {"date": show, "games": _texas_first(dates.get(show, [])), "next_date": nxt,
            "next": _texas_first(dates.get(nxt, []))[:6] if nxt and show != t else []}


async def missions_block(log: SportsLog) -> dict:
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    year = today.year
    async def season_games(y):
        d = await sjson(f"{MLBAPI}/schedule?sportId=12&teamId={MISSIONS_ID}&startDate={y}-01-01&endDate={y}-12-31&hydrate=linescore,team", 10 * 60)
        return [mlb_game(g, "milb") for x in d.get("dates") or [] for g in x["games"]]
    games = await log.run("MLB Stats API: Missions schedule", "https://www.milb.com/san-antonio/schedule", season_games(year), []) or []
    done = [g for g in games if g["state"] == "post" and g["home"]["score"] is not None]
    if not done:
        done = [g for g in (await season_games(year - 1) if True else []) if g["state"] == "post"]
    standings = None
    try:
        d = await sjson(f"{MLBAPI}/standings?leagueId={TEXAS_LEAGUE_ID}&season={year}&standingsTypes=regularSeason&hydrate=team,division", 30 * 60)
        for rec in d.get("records") or []:
            rows = [{"team": tr["team"].get("name"), "short": tr["team"].get("teamName") or tr["team"].get("name"), "w": tr["wins"], "l": tr["losses"],
                     "gb": tr.get("gamesBack"), "pct": tr.get("winningPercentage"), "spurs": tr["team"]["id"] == MISSIONS_ID} for tr in rec["teamRecords"]]
            if any(r["spurs"] for r in rows):
                standings = {"division": (rec.get("division") or {}).get("name") or "Texas League South", "season": str(year), "rows": rows}
        log.sources.append({"name": "MLB Stats API: Texas League standings", "home": "https://www.milb.com/texas/standings", "ok": bool(standings), "count": 5})
    except Exception as ex:
        log.sources.append({"name": "MLB Stats API: Texas League standings", "home": "https://www.milb.com/texas/standings", "ok": False, "error": f"{type(ex).__name__}: {ex}"[:160]})
    news = await log.run(MISSIONS_GN["name"], "https://news.google.com/", feed_items(MISSIONS_GN), []) or []
    news = [n for n in news if not MISSIONS_NOT.search(n["title"])][:10]
    upcoming = [g for g in games if g["state"] == "pre"][:5]
    return {"last": done[-4:][::-1], "upcoming": upcoming, "standings": standings, "news": news,
            "season_over": not upcoming and bool(done), "record": standings and next((f"{r['w']}-{r['l']}" for r in standings["rows"] if r["spurs"]), None)}


async def build_sports() -> dict:
    log = SportsLog()
    nfl_g, nfl_n, cowboys, texans, nba_g, nba_n, mlb_s, mlb_n, rangers, astros, spurs, missions = await asyncio.gather(
        log.run("ESPN: NFL scoreboard", "https://www.espn.com/nfl/scoreboard", espn_scoreboard("nfl", "football/nfl"), []),
        log.run("ESPN: NFL news", "https://www.espn.com/nfl/", espn_news("football/nfl", None, 12), []),
        log.run("ESPN: Cowboys news", "https://www.espn.com/nfl/team/_/name/dal/dallas-cowboys", espn_news("football/nfl", "6", 5), []),
        log.run("ESPN: Texans news", "https://www.espn.com/nfl/team/_/name/hou/houston-texans", espn_news("football/nfl", "34", 5), []),
        log.run("ESPN: NBA scoreboard", "https://www.espn.com/nba/scoreboard", espn_scoreboard("nba", "basketball/nba"), []),
        log.run("ESPN: NBA news", "https://www.espn.com/nba/", espn_news("basketball/nba", None, 10), []),
        log.run("MLB Stats API: MLB scores", "https://www.mlb.com/scores", mlb_scores(), {"games": []}),
        log.run("ESPN: MLB news", "https://www.espn.com/mlb/", espn_news("baseball/mlb", None, 12), []),
        log.run("ESPN: Rangers news", "https://www.espn.com/mlb/team/_/name/tex/texas-rangers", espn_news("baseball/mlb", "13", 5), []),
        log.run("ESPN: Astros news", "https://www.espn.com/mlb/team/_/name/hou/houston-astros", espn_news("baseball/mlb", "18", 5), []),
        spurs_block(log), missions_block(log))
    return {"generated": time.time(),
            "nfl": {"games": nfl_g, "news": _merge_news(cowboys, texans, nfl_n, limit=14)},
            "nba": {"games": nba_g, "news": nba_n, "spurs": spurs},
            "mlb": {**mlb_s, "news": _merge_news(rangers, astros, mlb_n, limit=14)},
            "missions": missions,
            "sources": log.sources}


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
        return await cached(f"news:{c}", 5 * 60, lambda: build_news(*c), stale=6 * 3600)
    except Exception as ex:
        return _err(ex)


@app.get("/api/events")
async def api_events(lat: float | None = Query(None), lon: float | None = Query(None)):
    try:
        la, lo = _coords(lat, lon)
    except ValueError as ex:
        return _err(ex, 400)
    try:
        c = cell(la, lo, 0.02)  # ~2 km: events are city-wide anyway
        return await cached(f"events:{c}", 45, lambda: build_events(*c), stale=3600)
    except Exception as ex:
        return _err(ex)


@app.get("/api/food")
async def api_food(lat: float | None = Query(None), lon: float | None = Query(None)):
    try:
        la, lo = _coords(lat, lon)
    except ValueError as ex:
        return _err(ex, 400)
    try:
        near = km_between(la, lo, *SA_CENTER) <= 80
        return await cached(f"foodlist:{near}", 60, lambda: build_food(la, lo), stale=3600)
    except Exception as ex:
        return _err(ex)


@app.get("/api/sports")
async def api_sports():
    try:
        return await cached("sports", 3 * 60, build_sports, stale=6 * 3600)
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


def app_build() -> str:
    """Build number from sw.js VERSION ("chisme-v22" -> "22"): the one place it's defined."""
    m = re.search(r'VERSION\s*=\s*"chisme-v(\d+)"', (BASE / "static" / "sw.js").read_text())
    return m.group(1) if m else "0"


@app.get("/")
async def index():
    # app.js / style.css are requested with ?v=<build>, so the page never runs with an older cached script
    page = (BASE / "static" / "index.html").read_text().replace("__BUILD__", app_build())
    return HTMLResponse(page, headers={"Cache-Control": "no-cache"})


@app.middleware("http")
async def cache_headers(request, call_next):
    """Code/styles/data must revalidate (cheap 304s via ETag) so phones never run a stale app.js;
    images can be cached for a day. Without this, browsers cache /static/* heuristically."""
    resp = await call_next(request)
    resp.headers["X-Chisme"] = "1"   # lets the service worker tell our responses from a host "waking up" page
    path = request.url.path
    if path.startswith("/static/") and "cache-control" not in resp.headers:
        resp.headers["Cache-Control"] = ("public, max-age=86400" if re.search(r"\.(png|webp|jpe?g|ico|svg)$", path)
                                         else "no-cache")
    elif path.startswith("/api/") and "cache-control" not in resp.headers:
        resp.headers["Cache-Control"] = "no-store"
    return resp


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


@app.on_event("startup")
async def warm():
    async def _w():  # warm caches for the default location
        await asyncio.gather(api_news(DEFAULT_LAT, DEFAULT_LON), api_weather(DEFAULT_LAT, DEFAULT_LON), api_radar(),
                             api_events(DEFAULT_LAT, DEFAULT_LON),
                             api_food(DEFAULT_LAT, DEFAULT_LON), api_sports(),
                             return_exceptions=True)
    asyncio.create_task(_w())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 8211)))
