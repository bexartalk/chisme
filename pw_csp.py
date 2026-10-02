"""v49.11 test shim: the app now sends a Content-Security-Policy without 'unsafe-eval'. Playwright's wait_for_function
re-checks a plain-expression string ("window.x && x.ready") with eval() inside the page, which that CSP (correctly)
blocks, so the wait fails. Wrapping the expression as an arrow function ("() => (window.x && x.ready)") makes Playwright
poll a real function instead: same meaning, and the page keeps its strict CSP. Every Playwright test imports this."""
import re

from playwright.async_api import Frame, Page
from playwright.sync_api import Frame as SyncFrame, Page as SyncPage

_FN = re.compile(r"^\s*(async\s+)?(function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)")


def _wrap(expression):
    return expression if not isinstance(expression, str) or _FN.match(expression) else f"() => ({expression})"


for _cls in (Page, Frame):
    _orig = _cls.wait_for_function
    if getattr(_orig, "_csp_wrapped", False):
        continue

    def _make(orig):
        async def wait_for_function(self, expression, *a, **kw):
            return await orig(self, _wrap(expression), *a, **kw)
        wait_for_function._csp_wrapped = True
        return wait_for_function
    _cls.wait_for_function = _make(_orig)

for _cls in (SyncPage, SyncFrame):   # (coldstart_test, features_test, … use the sync API)
    _orig = _cls.wait_for_function
    if getattr(_orig, "_csp_wrapped", False):
        continue

    def _make_sync(orig):
        def wait_for_function(self, expression, *a, **kw):
            return orig(self, _wrap(expression), *a, **kw)
        wait_for_function._csp_wrapped = True
        return wait_for_function
    _cls.wait_for_function = _make_sync(_orig)


async def admin_sign_in(pg, base: str, token: str, wait: str = "#f-scores"):
    """v49.11: /stats?key= no longer signs in, so tests sign in the way the owner does: the form on /stats."""
    await pg.goto(base.rstrip("/") + "/stats")
    if await pg.locator("#key").count():   # (already signed in → no form; e.g. two test servers sharing one session store)
        await pg.fill("#key", token)
        async with pg.expect_navigation():
            await pg.click("#login-go")
    if wait:
        await pg.wait_for_selector(wait, timeout=30000)


# v49.11 test infra: keep the once-per-open popups (notifications card, Settings tip) out of the way in every
# Playwright test that isn't about them — same as popup_quiet.QUIET, added first so a test's own init scripts win.
import sys as _sys
from popup_quiet import QUIET as _QUIET
try:
    _src = open(_sys.argv[0], encoding="utf-8").read()
except Exception:
    _src = ""
if not any(k in _src for k in ("push-ask", "chisme-notif", "settings-tip", "NO_AUTO_QUIET")):
    from playwright.async_api import Browser as _AB
    from playwright.sync_api import Browser as _SB

    _a_ctx, _a_page = _AB.new_context, _AB.new_page

    async def _actx(self, *a, **kw):
        c = await _a_ctx(self, *a, **kw); await c.add_init_script(_QUIET); return c

    async def _apage(self, *a, **kw):
        pg = await _a_page(self, *a, **kw); await pg.context.add_init_script(_QUIET); return pg
    _AB.new_context, _AB.new_page = _actx, _apage

    _s_ctx, _s_page = _SB.new_context, _SB.new_page

    def _sctx(self, *a, **kw):
        c = _s_ctx(self, *a, **kw); c.add_init_script(_QUIET); return c

    def _spage(self, *a, **kw):
        pg = _s_page(self, *a, **kw); pg.context.add_init_script(_QUIET); return pg
    _SB.new_context, _SB.new_page = _sctx, _spage
