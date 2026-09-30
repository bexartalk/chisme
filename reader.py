"""In-app reader: may a page be shown in an <iframe> inside Chisme, and what's its headline card?

GET /api/reader?url=...  ->  {url, final_url, host, frame, why, title, description, image, site, published}

- frame is decided server-side from the page's own X-Frame-Options / CSP frame-ancestors (cached 12 h per host,
  6 h per URL). Plain-http pages never frame (a https app can't show them).
- description is the page's own short summary (og:description / meta description, clipped to 300 characters).
  The article text itself is never copied.
- Safety: only http(s) on ports 80/443, public IP addresses only (checked on every redirect hop), at most
  512 KB read, 8 s timeout, and a per-IP limit.
"""
import asyncio, html, ipaddress, re, socket, time, urllib.parse

import httpx

MAX_BYTES = 512 * 1024
DESC_MAX = 300
NEVER_FRAME = re.compile(r"(^|\.)(news\.google\.com|instagram\.com|tiktok\.com|facebook\.com|x\.com|twitter\.com|reddit\.com|"
                         r"maps\.apple\.com|google\.com|cash\.app)$", re.I)


class Blocked(Exception):
    pass


async def _public(host: str) -> None:
    if not host or host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise Blocked("private host")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise Blocked("unknown host")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise Blocked("private address")


def _check_url(url: str) -> urllib.parse.SplitResult:
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
        raise Blocked("not a web link")
    if u.port not in (None, 80, 443):
        raise Blocked("unusual port")
    return u


def frame_verdict(headers: httpx.Headers, final_url: str) -> tuple[bool, str]:
    if not final_url.startswith("https://"):
        return False, "not https"
    xfo = (headers.get("x-frame-options") or "").lower()
    if "deny" in xfo or "sameorigin" in xfo:
        return False, "x-frame-options"
    for csp in headers.get_list("content-security-policy"):
        m = re.search(r"frame-ancestors([^;]*)", csp, re.I)
        if m and "*" not in m.group(1).split():
            return False, "frame-ancestors"
    return True, "allowed"


_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR = re.compile(r'([\w:-]+)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)


def _meta(doc: str) -> dict:
    out: dict[str, str] = {}
    for tag in _META.findall(doc):
        a = {m.group(1).lower(): (m.group(3) if m.group(3) is not None else m.group(4) if m.group(4) is not None else m.group(5))
             for m in _ATTR.finditer(tag)}
        k = (a.get("property") or a.get("name") or "").lower()
        if k and a.get("content") and k not in out:
            out[k] = html.unescape(a["content"]).strip()
    t = re.search(r"<title[^>]*>(.*?)</title>", doc, re.I | re.S)
    if t:
        out.setdefault("<title>", html.unescape(re.sub(r"\s+", " ", t.group(1))).strip())
    return out


def _clip(s: str | None, n: int) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def _published(m: dict) -> float | None:
    from email.utils import parsedate_to_datetime
    from datetime import datetime
    for k in ("article:published_time", "og:published_time", "datepublished", "date", "pubdate", "parsely-pub-date"):
        v = m.get(k)
        if not v:
            continue
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            try:
                return parsedate_to_datetime(v).timestamp()
            except Exception:
                pass
    return None


async def inspect(client: httpx.AsyncClient, url: str) -> dict:
    u = _check_url(url)
    base = {"url": url, "final_url": url, "host": (u.hostname or "").removeprefix("www."), "frame": False, "why": "",
            "title": None, "description": None, "image": None, "site": None, "published": None}
    if NEVER_FRAME.search(u.hostname or ""):
        # these never allow framing (and Google News / social pages have no useful card data for us)
        return dict(base, why="site never allows framing")
    cur, resp, body = url, None, b""
    for _hop in range(6):
        cu = _check_url(cur)
        await _public(cu.hostname)
        async with client.stream("GET", cur, follow_redirects=False, timeout=httpx.Timeout(8.0),
                                 headers={"Accept": "text/html,application/xhtml+xml"}) as r:
            if r.is_redirect and r.headers.get("location"):
                cur = urllib.parse.urljoin(cur, r.headers["location"])
                continue
            resp = r
            if r.status_code < 400 and "html" in (r.headers.get("content-type") or "html"):
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) >= MAX_BYTES or b"</head>" in body[-4096 - len(chunk):]:
                        break
            break
    if resp is None:
        return dict(base, why="too many redirects")
    out = dict(base, final_url=cur, host=(urllib.parse.urlsplit(cur).hostname or "").removeprefix("www."))
    if resp.status_code >= 400:
        return dict(out, why=f"HTTP {resp.status_code}")
    out["frame"], out["why"] = frame_verdict(resp.headers, cur)
    m = _meta(body.decode(resp.encoding or "utf-8", "replace"))
    img = m.get("og:image") or m.get("twitter:image")
    if img:
        img = urllib.parse.urljoin(cur, img)
        out["image"] = img if img.startswith("https://") else None
    out.update(title=_clip(m.get("og:title") or m.get("twitter:title") or m.get("<title>"), 200),
               description=_clip(m.get("og:description") or m.get("description") or m.get("twitter:description"), DESC_MAX),
               site=_clip(m.get("og:site_name"), 80), published=_published(m))
    return out
