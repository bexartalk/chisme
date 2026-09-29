"""PWA check: manifest + installability (Chrome DevTools Protocol), service worker,
offline reload. Usage: ./venv/bin/python pwa_check.py [url]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8211/"
OUT = Path(__file__).parent / "screenshots"

async def main():
    async with async_playwright() as p:
        # persistent (non-incognito) profile: Chrome reports "in-incognito" otherwise
        import tempfile
        ctx = await p.chromium.launch_persistent_context(
            tempfile.mkdtemp(prefix="chisme-pwa-"), executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox"], viewport={"width": 390, "height": 844}, device_scale_factor=2,
            is_mobile=True, has_touch=True, timezone_id="America/Chicago")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        sw_scope = await page.evaluate("navigator.serviceWorker.ready.then(r => r.scope)")
        await page.reload(wait_until="networkidle")  # now controlled by the SW; populates data cache
        await page.wait_for_selector("#city-list .story", timeout=60000)
        controlled = await page.evaluate("!!navigator.serviceWorker.controller")
        cdp = await ctx.new_cdp_session(page)
        inst = await cdp.send("Page.getInstallabilityErrors")
        man = await cdp.send("Page.getAppManifest")
        caches = await page.evaluate("""async () => { const o = {}; for (const k of await caches.keys()) {
            o[k] = (await (await caches.open(k)).keys()).map(r => new URL(r.url).pathname); } return o; }""")
        # offline test
        await ctx.set_offline(True)
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_selector("#city-list .story", timeout=20000)
        await page.wait_for_timeout(1500)
        offline = await page.evaluate("""() => ({
            near: document.querySelectorAll('#near-list .story').length,
            city: document.querySelectorAll('#city-list .story').length,
            forecastDays: document.querySelectorAll('#forecast .day').length,
            currentTemp: document.querySelector('.now-temp')?.textContent,
            banner: document.querySelector('#offline-banner').hidden ? null : document.querySelector('#offline-banner').textContent,
            radar: document.querySelector('#radar-time').textContent })""")
        await page.screenshot(path=str(OUT / "phone-offline.png"))
        await ctx.set_offline(False)
        # Android install button: headless Chrome never fires beforeinstallprompt on its own,
        # so dispatch a stand-in event to check the button UI appears and calls prompt().
        await page.goto(URL, wait_until="networkidle")
        report_install = await page.evaluate("""() => { const e = new Event('beforeinstallprompt');
            window.__prompted = false; e.prompt = () => { window.__prompted = true; }; e.userChoice = Promise.resolve({outcome:'dismissed'});
            window.dispatchEvent(e); return !document.querySelector('#install-card').hidden; }""")
        await page.screenshot(path=str(OUT / "phone-android-install-button.png"))
        await page.click("#install-card-btn")
        prompted = await page.evaluate("window.__prompted")
        # iOS hint: Safari on iPhone user agent
        ios = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ictx = await ios.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
            has_touch=True, timezone_id="America/Chicago",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1")
        ipage = await ictx.new_page()
        await ipage.goto(URL, wait_until="networkidle")
        ios_hint = await ipage.evaluate("!document.querySelector('#ios-hint').hidden")
        await ipage.screenshot(path=str(OUT / "phone-ios-hint.png"))
        await ios.close()
        report = {
            "service_worker_scope": sw_scope, "page_controlled_by_sw": controlled,
            "installability_errors": inst.get("installabilityErrors"),
            "manifest_url": man.get("url"), "manifest_parse_errors": man.get("errors"),
            "caches": caches, "offline_reload": offline,
            "android_install_button_shown": report_install, "install_button_calls_prompt": prompted,
            "ios_hint_shown_on_iphone_ua": ios_hint,
        }
        print(json.dumps(report, indent=2))
        await ctx.close()

asyncio.run(main())
