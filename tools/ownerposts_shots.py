"""Screenshots of the owner-posts feature (iPhone 13 size, WebKit; one desktop 1280×800, Chromium) against a LOCAL server
started with ADMIN_TOKEN=$OWNER_TOKEN and local storage (never the live site). Creates the DeeWillie's BBQ test post from
the draft in POSTS_DIR (default /workspace/chisme-posts), never sends a notification.
  BASE=http://localhost:8450 OWNER_TOKEN=… OUT=/workspace/chisme-ownerposts-shots python tools/ownerposts_shots.py"""
import asyncio, html, json, os, re, sys, urllib.request
from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://localhost:8450").rstrip("/")
TOKEN = os.environ["OWNER_TOKEN"]
OUT = os.environ.get("OUT", "/workspace/chisme-ownerposts-shots")
POSTS = os.environ.get("POSTS_DIR", "/workspace/chisme-posts")
os.makedirs(OUT, exist_ok=True)

# the draft, as written (stabbing-post-draft.md): headline, text, where, map, photos, source
HEADLINE = "Man stabbed outside DeeWillie's BBQ on O'Connor Road; suspect still at large"
BODY = """A man was taken to the hospital after a disturbance outside DeeWillie's BBQ on the Northeast Side turned into a stabbing Friday night (Oct. 2), San Antonio police said. The suspect ran off and has not been caught.

**What police say happened**
- Around 8:04 p.m. Friday, a suspect caused a disturbance with an employee outside the business.
- The confrontation escalated, and the suspect stabbed the victim and ran.
- The suspect later went back into the building, then left the area.
- The victim was taken to a hospital with injuries. The victim's condition was not immediately known.
- The suspect was still at large.

**Suspect:** police have not released a description.
**Tips:** the article doesn't list a tip line. If you know something, contact SAPD."""
WHERE = "outside DeeWillie's BBQ, 12100 block of O'Connor Road, Northeast Side (78233)"
MAPQ = "12100 O'Connor Rd, San Antonio, TX 78233"
PIN = "29.5496, -98.3758"
PHOTOS = [("stabbing-1-storefront.webp", "Storefront"), ("stabbing-2-scene-tape.webp", "Crime-scene tape"), ("stabbing-3-police-lights.webp", "Police lights")]
CREDIT = "Photo: News 4 San Antonio"
SRC_URL = "https://news4sanantonio.com/news/local/suspect-at-large-after-business-employee-stabbed-police-say"
SRC_NAME = "News 4 San Antonio, by Victoria Arredondo, Sat., Oct. 3, 2026, 8:59 PM CT"

# a SAMPLE paid spotlight (made up for the screenshot, says so; local server only): Events, Paid / Sponsored, pinned 1 week
SP_HEADLINE = "Sample sponsored spotlight: Fiesta night market"
SP_BODY = "This is a sample paid event spotlight, made only to test the Sponsored label. It is not a real event."
SP_IMG = "/tmp/op-dev/sample-spotlight.jpg"


def sample_photo():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1200, 800), (0, 201, 205)); d = ImageDraw.Draw(im)
    for i, col in enumerate([(255, 26, 127), (255, 106, 11), (75, 31, 158), (255, 255, 255)]):
        d.rectangle((0, 120 + i * 140, 1200, 200 + i * 140), fill=col)
    d.rectangle((380, 300, 820, 500), fill=(0, 0, 0)); d.text((430, 380), "SAMPLE IMAGE", fill=(255, 255, 255), font_size=48)
    os.makedirs(os.path.dirname(SP_IMG), exist_ok=True); im.save(SP_IMG, quality=88)


async def shot(pg, name, full=False):
    p = os.path.join(OUT, name + ".png")
    await pg.screenshot(path=p, full_page=full)
    print("  ", p)


async def sign_in(pg):
    await pg.goto(BASE + "/stats")
    await pg.fill("#key", TOKEN)
    await pg.click("#login-go")
    await pg.wait_for_url(BASE + "/stats")


async def to(pg, sel, pad=70):
    await pg.evaluate("([s,p]) => { const e = document.querySelector(s); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - p); }", [sel, pad])
    await pg.wait_for_timeout(250)


async def og_card(pg, name):
    """The page's Open Graph tags drawn as a phone link preview (+ the raw tags)."""
    page_html = await pg.content()
    og = dict(re.findall(r'<meta (?:property|name)="((?:og|twitter|article):[^"]+)" content="([^"]*)"', page_html))
    og = {k: html.unescape(v) for k, v in og.items()}
    json.dump(og, open(os.path.join(OUT, name + ".json"), "w"), indent=2, ensure_ascii=False)
    host = re.sub(r"^https?://", "", BASE).split("/")[0]
    card = f"""<!doctype html><meta name=viewport content="width=device-width"><body style="margin:0;background:#e9eef0;font:15px -apple-system,system-ui,sans-serif;padding:18px">
<p style="margin:0 0 8px;font-weight:700;color:#333">Link preview from the page's Open Graph tags (what iMessage / Facebook / X read)</p>
<div style="max-width:340px;margin-left:auto;background:#00C9CD;padding:3px;border-radius:20px"><div style="background:#fff;border-radius:18px;overflow:hidden">
<img src="{html.escape(og.get('og:image',''))}" style="display:block;width:100%;aspect-ratio:1.91/1;object-fit:cover">
<div style="padding:10px 12px"><div style="font-weight:700;line-height:1.25">{html.escape(og.get('og:title',''))}</div>
<div style="color:#444;font-size:13px;margin-top:4px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">{html.escape(og.get('og:description',''))}</div>
<div style="color:#666;font-size:12px;margin-top:6px">{html.escape(host)}</div></div></div></div>
<pre style="white-space:pre-wrap;font-size:11px;background:#fff;border:1px solid #c4ced4;border-radius:10px;padding:10px;margin-top:16px">{html.escape(chr(10).join(f'{k}: {v}' for k, v in og.items()))}</pre></body>"""
    await pg.set_content(card)
    await pg.wait_for_timeout(800)
    await shot(pg, name)


async def main():
    async with async_playwright() as p:
        wk = await p.webkit.launch()
        dev = p.devices["iPhone 13"]
        dev = {**dev, "viewport": {"width": 390, "height": 844}, "device_scale_factor": 2}
        ctx = await wk.new_context(**dev, color_scheme="light")
        pg = await ctx.new_page()
        await sign_in(pg)
        # start clean: remove an earlier run's test post (local server only)
        await pg.goto(BASE + "/stats/posts")
        gone = await pg.evaluate("""async (hl) => { const j = await (await fetch('/stats/posts/list')).json(); let n = 0;
          for (const p of j.posts || []) if (hl.includes(p.headline)) { await fetch('/stats/posts/' + p.id, {method: 'DELETE', headers: {'Content-Type': 'application/json'}, body: '{"confirm":"DELETE"}'}); n++; }
          return n; }""", [HEADLINE, SP_HEADLINE])
        print("   removed earlier test posts:", gone)
        await pg.goto(BASE + "/stats")
        await to(pg, "#op-entry", 80); await shot(pg, "stats-entry-card")

        await pg.goto(BASE + "/stats/posts")
        await pg.wait_for_selector("#op-form")
        await shot(pg, "composer-empty")

        # ---- the DeeWillie's draft
        await pg.click('#op-cats [data-cat="news"]')
        await pg.fill("#op-head", HEADLINE)
        await pg.fill("#op-body", BODY)
        await pg.set_input_files("#op-file", [os.path.join(POSTS, f) for f, _ in PHOTOS])
        await pg.wait_for_function("() => document.querySelectorAll('.op-pr .op-pst.ok').length === 3", timeout=60000)
        rows = await pg.query_selector_all(".op-pr")
        for i, row in enumerate(rows):
            ins = await row.query_selector_all("input.inp")
            await ins[0].fill(CREDIT)
            await ins[1].fill(PHOTOS[i][1])
        await pg.click("#op-where-d > summary")
        await pg.fill("#op-loc", WHERE)
        await pg.fill("#op-mapq", MAPQ)
        await pg.fill("#op-pinpaste", PIN)
        await pg.dispatch_event("#op-pinpaste", "change")
        await pg.wait_for_function("() => { const i = document.getElementById('op-mapimg'); return i.hidden || (i.complete && i.naturalWidth > 0); }", timeout=30000)
        await pg.click("#op-src-d > summary")
        await pg.fill("#op-srcu", SRC_URL)
        await pg.fill("#op-srcn", SRC_NAME)
        await pg.click("label[for=op-pin-on]")
        await pg.select_option("#op-pin-for", "24")
        if not await pg.is_disabled("#op-push"):
            await pg.check("#op-push")
        await pg.evaluate("window.scrollTo(0,0)")
        await shot(pg, "composer-filled")
        await shot(pg, "composer-filled-full", full=True)
        await to(pg, "#op-photos", 130); await shot(pg, "photo-credits")
        await to(pg, "#op-where-d", 70); await shot(pg, "composer-location-map")
        await to(pg, ".op-pv", 60); await shot(pg, "composer-live-preview")
        await to(pg, "label[for=op-pin-on]", 260); await shot(pg, "pinned-setting")

        # ---- publish: the notification preview first (we publish WITHOUT sending)
        await pg.click("#op-publish")
        try:
            await pg.wait_for_selector("#op-push-dlg[open]", timeout=8000)
            await pg.wait_for_timeout(300)
            await shot(pg, "push-preview")
            await pg.click("#op-push-skip")
        except Exception:
            print("   (no push preview: push isn't set up on this server)")
        await pg.wait_for_selector(".op-done", timeout=30000)
        await pg.wait_for_timeout(300)
        await shot(pg, "published-banner")
        posts = json.loads(urllib.request.urlopen(BASE + "/api/posts").read())["posts"]
        post = next(x for x in posts if x["headline"] == HEADLINE)
        slug, pid = post["slug"], post["id"]
        print("   slug", slug)
        await to(pg, "#op-mine-s", 70); await shot(pg, "your-posts-list")

        # ---- the feed
        await pg.goto(BASE + "/#chisme")
        await pg.wait_for_selector("#view-chisme .op-strip .op-card", timeout=30000)
        await pg.wait_for_timeout(1500)
        await to(pg, "#view-chisme .op-strip", 120); await shot(pg, "pinned")
        await pg.click("#view-chisme .op-strip .op-card .op-read")
        await pg.wait_for_selector("#op-sheet[open]")
        await pg.wait_for_timeout(600)
        await shot(pg, "feed-post-sheet")
        await pg.evaluate("document.getElementById('op-sheet').scrollTop = 1400")
        await pg.wait_for_timeout(400)
        await shot(pg, "feed-post-sheet-where")
        await pg.click("#op-sheet .op-x")
        await pg.goto(BASE + "/#news")
        await pg.wait_for_selector("#view-news .op-strip .op-card", timeout=30000)
        await pg.wait_for_timeout(1500)
        await to(pg, "#view-news .op-strip", 120); await shot(pg, "feed-with-post")

        # ---- its own page + the link preview
        await pg.goto(BASE + "/p/" + slug)
        await pg.wait_for_timeout(800)
        await shot(pg, "post-page")
        await shot(pg, "post-page-full", full=True)
        await og_card(pg, "share-preview-og")

        # ---- edit + delete confirm (cancelled: the post stays)
        await pg.goto(BASE + "/stats/posts?edit=" + pid)
        await pg.wait_for_selector(".op-editing")
        await pg.wait_for_timeout(500)
        await shot(pg, "edit")
        await pg.click("#op-delete")
        await pg.wait_for_selector("#op-del-dlg[open]")
        await pg.wait_for_timeout(300)
        await shot(pg, "delete-confirm")
        await pg.click("#op-del-no")

        # ---- a paid spotlight: Events + Paid / Sponsored + pinned 1 week (a clearly-labeled SAMPLE, local only)
        sample_photo()
        await pg.goto(BASE + "/stats/posts")
        await pg.wait_for_selector("#op-form")
        await pg.click('#op-cats [data-cat="events"]')
        await pg.fill("#op-head", SP_HEADLINE)
        await pg.fill("#op-body", SP_BODY)
        await pg.set_input_files("#op-file", [SP_IMG])
        await pg.wait_for_function("() => document.querySelectorAll('.op-pr .op-pst.ok').length === 1", timeout=60000)
        ins = await (await pg.query_selector(".op-pr")).query_selector_all("input.inp")
        await ins[0].fill("Sample image"); await ins[1].fill("Sample image in fiesta colors")
        await pg.check("#op-spon")
        await pg.click("label[for=op-pin-on]")
        await pg.select_option("#op-pin-for", "168")
        await to(pg, "#op-spon-l", 300); await shot(pg, "sponsored-composer")
        await pg.click("#op-publish")
        await pg.wait_for_selector(".op-done", timeout=30000)
        posts = json.loads(urllib.request.urlopen(BASE + "/api/posts").read())["posts"]
        sp = next(x for x in posts if x["headline"] == SP_HEADLINE)
        print("   sponsored:", sp["sponsored"], "pinned:", sp["pinned"], sp["pinned_until"])
        await pg.goto(BASE + "/#chisme")
        await pg.wait_for_selector("#view-chisme .op-strip .op-sponsored", timeout=30000)
        await pg.wait_for_timeout(1500)
        await to(pg, "#view-chisme .op-strip", 120); await shot(pg, "sponsored-spotlight")
        await pg.goto(BASE + "/p/" + sp["slug"])
        await pg.wait_for_timeout(800)
        await shot(pg, "sponsored-page")
        await og_card(pg, "sponsored-og")

        # ---- a visitor
        vctx = await wk.new_context(**dev)
        vp = await vctx.new_page()
        await vp.goto(BASE + "/stats/posts")
        await vp.wait_for_timeout(400)
        await shot(vp, "visitor-blocked")
        r = await vp.evaluate("""async () => { const out = [];
          for (const [m, u, b] of [["POST", "/stats/posts", {category: "news", headline: "x"}], ["PATCH", "/stats/posts/x", {headline: "x"}], ["DELETE", "/stats/posts/x", {confirm: "DELETE"}], ["POST", "/stats/posts/photo", {data: "x"}], ["GET", "/stats/posts/list"]]) {
            const r = await fetch(u, {method: m, headers: {"Content-Type": "application/json"}, body: b ? JSON.stringify(b) : undefined}); out.push(m + " " + u + " → " + r.status + " " + (await r.text()).slice(0, 60)); }
          return out; }""")
        await vp.set_content("<meta name=viewport content='width=device-width'><body style='font:15px system-ui;padding:16px'><h2>A visitor (not signed in) calling the owner API</h2><ul>"
                             + "".join(f"<li style='margin:8px 0'><code>{html.escape(x)}</code></li>" for x in r) + "</ul></body>")
        await shot(vp, "visitor-blocked-api")
        print("  ", r)
        await vctx.close(); await ctx.close(); await wk.close()

        # ---- desktop
        cr = await p.chromium.launch()
        dctx = await cr.new_context(viewport={"width": 1280, "height": 800})
        dp = await dctx.new_page()
        await dp.goto(BASE + "/p/" + slug)
        await dp.wait_for_timeout(1000)
        await shot(dp, "post-page-desktop")
        await dp.goto(BASE + "/")
        await dp.wait_for_selector(".op-strip .op-card", timeout=30000)
        await dp.wait_for_timeout(2500)
        await to(dp, ".op-strip", 170); await shot(dp, "feed-desktop")
        await dctx.close(); await cr.close()
    print("slug:", slug, "id:", pid)

asyncio.run(main())
