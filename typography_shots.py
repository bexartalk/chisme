"""Settled, 3x phone screenshots. SHOTS defaults to /workspace/typography-shots/."""
import asyncio, os
from pathlib import Path
from playwright.async_api import async_playwright
from typography_test import start, seed, visit, INIT

async def main():
    out=Path(os.environ.get('SHOTS','/workspace/typography-shots/'));out.mkdir(parents=True,exist_ok=True)
    proc,tmp,url,log=start()
    try:
      async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,reduced_motion='reduce')
        animation_off = """(() => { const install=()=>{const s=document.createElement('style');s.textContent='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';document.documentElement.append(s)};if(document.documentElement)install();else new MutationObserver((_,o)=>{if(document.documentElement){install();o.disconnect()}}).observe(document,{childList:true,subtree:true}) })();"""
        await ctx.add_init_script(INIT+animation_off)
        post=await seed(ctx,url,log)
        for view,width,height in [('feed',390,844),('comments',390,844),('chat',390,844),('profile',390,844),('menu',390,844),('feed',320,568)]:
          pg=await ctx.new_page()
          await pg.set_viewport_size({'width':width,'height':height})
          await visit(pg,url,view,post)
          try: await pg.wait_for_load_state('networkidle',timeout=5000)
          except Exception: pass
          await pg.evaluate('document.fonts.ready')
          # lazy images below the fold never load until scrolled to, so only wait for the ones on screen
          try: await pg.wait_for_function('[...document.images].filter(i=>{const r=i.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight&&r.width>0}).every(i=>i.complete)',timeout=15000)
          except Exception: pass
          await pg.wait_for_timeout(3500)   # the sync toast ("Up to date ✓") fades out
          tall=await pg.evaluate('document.scrollingElement.scrollHeight')
          # full page only when it's a sensible length (the feed is endless; a 3x capture of it would pass Chrome's size cap)
          await pg.screenshot(path=str(out/f'{view}-{width}.png'),full_page=view in ('comments','profile') and tall<=3000)
          await pg.close()
        await b.close()
    finally: proc.terminate();proc.wait();tmp.cleanup()

if __name__=='__main__': asyncio.run(main())
