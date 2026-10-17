"""Phone typography regression: real local accounts, both browser engines, 1x/1.3x.
Run with ./venv/bin/python typography_test.py; PORT defaults to 8486.
"""
import asyncio, math, os, re, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
import pw_csp  # noqa: F401
from popup_quiet import QUIET
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get('PORT', '8486'))
fails = 0
INIT = "localStorage.setItem('chisme-season-pin','muertos');localStorage.setItem('chisme-default-tab','chisme');localStorage.setItem('chisme-location-setup','done');" + QUIET

def check(ok, label):
    global fails
    print(('PASS ' if ok else 'FAIL ') + label, flush=True)
    fails += not ok

def start():
    if not 8480 <= PORT <= 8490: raise ValueError('PORT must be 8480–8490')
    # Fail promptly in managed sandboxes that prohibit localhost sockets.
    with socket.socket() as probe: probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); probe.bind(('127.0.0.1', PORT))
    tmp = tempfile.TemporaryDirectory(prefix='chisme-type-')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('SOCIAL_', 'UPSTASH_', 'SUPABASE_', 'R2_', 'TURNSTILE_', 'CSAM_', 'RENDER'))}
    env.update(SOCIAL_FAKE_AUTH='1', SOCIAL_DIR=tmp.name+'/social', SIGNUPS_PUBLIC='1', NEW_USER_REVIEW='0', PUSH_STORE_FILE=tmp.name+'/push.json', STATS_STORE_FILE=tmp.name+'/stats.json', OWNER_POSTS_DIR=tmp.name+'/posts', AUTO_PUSH_WAKE_DELAY='9999', ADMIN_TOKEN='typography-owner-test', PYTHONUNBUFFERED='1')
    log = Path(tmp.name)/'server.log'
    proc = subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(PORT)],cwd=HERE,env=env,stdout=log.open('w'),stderr=subprocess.STDOUT)
    url = f'http://127.0.0.1:{PORT}/'
    for _ in range(120):
        try:
            if urllib.request.urlopen(url+'healthz',timeout=1).status == 200: return proc,tmp,url,log
        except Exception: time.sleep(.25)
    proc.terminate(); proc.wait(); detail=log.read_text(); tmp.cleanup(); raise RuntimeError('Local server could not be reached. '+detail)

LONG_POST = ("¡Qué alegría ver a nuestra comunidad reunida otra vez! Mi abuela preparó tamales de puerco, champurrado y pan de muerto "
  "para toda la cuadra, y los niños decoraron la ofrenda con cempasúchil, velas, papel picado y fotos de los bisabuelos. "
  "Después caminamos juntos hasta la plaza para escuchar el mariachi, platicar con los vecinos y recordar historias viejas del barrio. "
  "Supercalifragilisticoespialidosoconcempasuchilytamalesdepuercoyrajasconqueso")
LONG_COMMENTS = ["¡Saludos a toda la familia desde el Westside! Qué bonita quedó esa ofrenda, me trae muchos recuerdos de mi tía Chayo y sus buñuelos. "
  "Gracias por compartir, nos vemos el sábado. Muchísimasfelicidadesatodalafamiliaydesdeelbarrioconcariño",
  "Yo llevo las conchas y el café de olla para la próxima reunión del vecindario, avísenme a qué hora empiezan."]

async def seed(ctx,url,log,user='maria_angeles_hdz'):
    cfg = await (await ctx.request.get(url+'api/social/config')).json()
    a,b = map(int,re.findall(r'\d+',cfg['challenge']['question']))
    await asyncio.sleep(2.2)
    h={'origin':url.rstrip('/')}
    email=user+'@example.com'
    r=await ctx.request.post(url+'api/social/signup',headers=h,data={'email':email,'password':'Tamales&Tea42','password2':'Tamales&Tea42','display_name':'María de los Ángeles Hernández García','username':user,'birthday':'1990-05-05','tos':True,'challenge':{'id':cfg['challenge']['id'],'answer':str(a+b)}})
    assert r.ok, await r.text()
    for _ in range(30):
        codes=re.findall('code for '+re.escape(email)+r': (\S+)',log.read_text())
        if codes: break
        await asyncio.sleep(.1)
    r=await ctx.request.post(url+'api/social/verify',headers=h,data={'email':email,'code':codes[-1]})
    assert r.status==200, await r.text()
    ids=[]
    for text in [LONG_POST, 'Nos vemos en la ofrenda. 🌺', 'Café y pan dulce con los vecinos.']:
        r=await ctx.request.post(url+'api/social/chismes',headers=h,data={'text':text,'audience':'everyone'})
        d=await r.json(); assert r.ok,d
        ids.append(d['chisme']['id'])
    for i in range(2):
        r=await ctx.request.post(url+f'api/social/chismes/{ids[0]}/comments',headers=h,data={'text':LONG_COMMENTS[i]})
        assert r.ok,await r.text()
    return ids[0]

async def settle(pg):
    await pg.evaluate('document.fonts.ready')
    await pg.wait_for_timeout(250)

async def visit(pg,url,view,post):
    if view == 'moderation':
        await pg.goto(url+'stats/social')
        try: await pg.wait_for_selector('body.sx-plain #view .h2', timeout=5000)
        except Exception: pass
        await settle(pg); return
    await pg.goto(url+{'feed':'#s/feed/sananto','comments':'#s/c/'+post,'profile':'#s/me','signup':'#s/signup','signin':'#s/signin','games':'#juegos'}.get(view,'#chisme'))
    await pg.wait_for_function('window.__chisme && __chisme.ready')
    await pg.wait_for_timeout(650)
    if view=='menu': await pg.click('#fb-menu')
    if view=='settings':
        await pg.click('#fb-menu'); await pg.click('#menu-settings')
    if view=='chat':
        await pg.click('#tab-tia'); await pg.wait_for_selector('#tia[open]')
    if view == 'profile':
        try: await pg.wait_for_selector('.sx .profile', timeout=5000)
        except Exception: pass
    await settle(pg)

AUDIT = r"""() => {
 const selector=n=>n.id?'#'+n.id:n.tagName.toLowerCase()+'.'+[...n.classList].join('.');
 const rect=r=>({x:r.x,y:r.y,width:r.width,height:r.height});
 const detail=(n,r=n.getBoundingClientRect(),c=n.closest('.card,.profile,.tia-bub')||document.documentElement)=>selector(n)+' '+JSON.stringify(n.textContent.trim().slice(0,30))+' rect='+JSON.stringify(rect(r))+' container='+selector(c)+' '+JSON.stringify(rect(c.getBoundingClientRect()));
 const visible=n=>{if(n.closest('[hidden],[inert],[aria-hidden="true"],.sr-only,dialog:not([open])'))return false;for(let a=n;a;a=a.parentElement){let s=getComputedStyle(a);if(s.visibility==='hidden'||s.display==='none')return false}const r=n.getBoundingClientRect();for(let a=n.parentElement;a&&a!==document.body;a=a.parentElement){const s=getComputedStyle(a),b=a.getBoundingClientRect();if(/auto|scroll|hidden|clip/.test(s.overflowX)&&(r.right<=b.left||r.left>=b.right))return false}return r.width>2&&r.height>2};
 const pageText=n=>{for(let a=n.parentElement;a&&a!==document.body&&a!==document.documentElement;a=a.parentElement)if(/auto|scroll|hidden|clip/.test(getComputedStyle(a).overflowX))return false;return true};
 const text=[...document.querySelectorAll('body *')].filter(n=>visible(n)&&[...n.childNodes].some(c=>c.nodeType===3&&c.textContent.trim())&&!n.closest('svg,#game-stage'));
 const art=n=>/Chisme.*Display/.test(getComputedStyle(n).fontFamily);
 const small=text.filter(n=>!art(n)&&parseFloat(getComputedStyle(n).fontSize)<11.99).map(selector);
 const spill=text.filter(n=>pageText(n)&&(()=>{const r=n.getBoundingClientRect();return r.left< -1||r.right>innerWidth+1})()).map(selector);
 const samples={};for(const [key,sel] of Object.entries({post:'.sx .chisme .sx-txt',name:'.sx .who b',comment:'.sx .comment .sx-txt',input:'input:not([type=checkbox]):not([type=hidden]),textarea',tab:'.tab-l',time:'.sx .who small',title:'#menu-title,#settings h2,.sx .auth h1',section:'.sx .h2'})){
 const n=[...document.querySelectorAll(sel)].find(n=>visible(n)&&!art(n));if(n){const s=getComputedStyle(n);samples[key]=[parseFloat(s.fontSize),parseInt(s.fontWeight)]}}
 const overlap=[];
 // Range rectangles measure actual text, avoiding parent boxes containing their children.
 const boxes=[];for(const n of text){const card=n.closest('.chisme,.comment,.mix-item,.game-pick,.p-homies,.tia-bub');if(!card)continue;for(const t of n.childNodes)if(t.nodeType===3&&t.textContent.trim()){const range=document.createRange();range.selectNodeContents(t);for(const raw of range.getClientRects()){let r={left:raw.left,right:raw.right,top:raw.top,bottom:raw.bottom};for(let a=n;a&&a!==card;a=a.parentElement){if(/hidden|clip/.test(getComputedStyle(a).overflowY)){const c=a.getBoundingClientRect();r={left:Math.max(r.left,c.left),right:Math.min(r.right,c.right),top:Math.max(r.top,c.top),bottom:Math.min(r.bottom,c.bottom)}}}if(r.right>r.left&&r.bottom>r.top)boxes.push({n,card,r:{...r,x:r.left,y:r.top,width:r.right-r.left,height:r.bottom-r.top}})}}}
 for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];if(a.n===b.n||a.card!==b.card||a.n.contains(b.n)||b.n.contains(a.n))continue;if(Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>2&&Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>2)overlap.push(detail(a.n,a.r,a.card)+' / '+detail(b.n,b.r,b.card))}
 const reactions=[],reactionBounds=[];
 for(const row of [...document.querySelectorAll('.react')].filter(visible)){
   const buttons=[...row.querySelectorAll('.rx')].filter(visible), bounds=row.getBoundingClientRect(),card=row.closest('.card')||row;
   const tops=buttons.map(n=>n.getBoundingClientRect().top);
   if(Math.max(...tops)-Math.min(...tops)>2)reactions.push(detail(row));
   for(let i=0;i<buttons.length;i++){
     const n=buttons[i],a=n.getBoundingClientRect(),c=card.getBoundingClientRect();
     if(a.width<39.9||a.height<39.9||a.left<bounds.left-1||a.right>bounds.right+1||a.top<bounds.top-1||a.bottom>bounds.bottom+1||a.left<c.left-1||a.right>c.right+1||a.bottom>c.bottom+1||n.scrollWidth>n.clientWidth+1)reactionBounds.push(detail(n,a,row));
     for(const other of buttons.slice(i+1)){const b=other.getBoundingClientRect();if(Math.min(a.right,b.right)>Math.max(a.left,b.left)+.5&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+.5)reactionBounds.push(detail(n,a,row)+' / '+detail(other,b,row));}
   }
 }
 const picker=[...document.querySelectorAll('.game-pick')].filter(visible).filter(n=>{const a=n.querySelector('.gp-emo').getBoundingClientRect(),b=n.querySelector('span:not(.gp-emo)').getBoundingClientRect();return a.right>b.left+1}).map(selector);
 const rgb=s=>(s.match(/[\d.]+/g)||[]).map(Number);
 const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((v,c,i)=>v+c*[.2126,.7152,.0722][i],0);
 const contrast=[...document.querySelectorAll('.sx .h2')].filter(visible).filter(n=>{let bg=[1,6,59,1];for(let a=n;a;a=a.parentElement){let c=rgb(getComputedStyle(a).backgroundColor);if(c.length>=3&&(c.length<4||c[3]===1)){bg=c;break}}const a=lum(rgb(getComputedStyle(n).color)),b=lum(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)<4.5}).map(selector);
 return {small,spill,overlap,reactions,reactionBounds,picker,contrast,samples,family:getComputedStyle(document.body).fontFamily,overflow:document.scrollingElement.scrollWidth>innerWidth+1};
}"""

async def main():
    proc,tmp,url,log=start()
    try:
      async with async_playwright() as p:
        for engine in ('chromium','webkit'):
          browser=await getattr(p,engine).launch(**({'executable_path':'/usr/bin/google-chrome','args':['--no-sandbox']} if engine=='chromium' else {}))
          seedctx=await browser.new_context();post=await seed(seedctx,url,log,'maria_'+engine+'_hdz');login=await seedctx.request.post(url+'stats/login',form={'key':'typography-owner-test'},headers={'origin':url.rstrip('/')});assert login.ok,await login.text();state=await seedctx.storage_state();await seedctx.close()
          for w,h in ((320,568),(375,667),(390,844),(430,932)):
            for scale in (1,1.3):
              ctx=await browser.new_context(viewport={'width':w,'height':h},is_mobile=True,has_touch=True,storage_state=state)
              await ctx.add_init_script(INIT)
              for view in ('feed','comments','chat','profile','menu','settings','games','signup','signin','moderation'):
                viewctx = await browser.new_context(viewport={'width':w,'height':h},is_mobile=True,has_touch=True) if view in ('signup','signin') else ctx
                if viewctx is not ctx: await viewctx.add_init_script(INIT)
                pg=await viewctx.new_page()
                try:
                  await visit(pg,url,view,post)
                  if scale!=1:
                    await pg.evaluate("document.documentElement.style.fontSize='130%';document.documentElement.style.setProperty('--t-scale','1');document.documentElement.classList.add('text-large')")
                    await settle(pg)
                  expected={'feed':'.sx .chisme','comments':'.sx .comment','chat':'#tia[open] input','profile':'.sx .profile','menu':'#menu[open]','settings':'#settings[open]','games':'.game-pick','signup':'.sx input[type=password]','signin':'.sx input[type=password]','moderation':'body.sx-plain #view .h2'}
                  errors=[]
                  if not await pg.locator(expected[view]).count(): errors.append('content '+expected[view]+' '+await pg.locator('body').evaluate("n=>n.tagName+' '+n.className+' '+JSON.stringify(n.innerText.slice(0,30))+' rect='+JSON.stringify(n.getBoundingClientRect().toJSON())+' container='+JSON.stringify(document.documentElement.getBoundingClientRect().toJSON())"))
                  d=await pg.evaluate(AUDIT)
                  for k in ('small','spill','overlap','picker','contrast','reactionBounds','overflow'):
                    if d[k]: errors.extend([k+':'+str(v) for v in (d[k] if isinstance(d[k],list) else ['page'])])
                  if scale==1 and w>=375: errors.extend('reaction-wrap:'+v for v in d['reactions'])
                  if not d['family'].startswith('-apple-system'): errors.append('body font-family')
                  ranges={'post':(16,16),'name':(16,16),'comment':(15,16),'input':(16,26),'tab':(12,16),'time':(12,13),'title':(22,24),'section':(18,20)}
                  for key,(size,weight) in d['samples'].items():
                    lo,hi=ranges[key]
                    if not (lo*scale-.15<=size<=hi*scale+.15 and (key!='name' or weight>=600)): errors.append(f'{key}:{size}px/{weight}')
                  check(not errors,f'{engine} {w}x{h} {scale} {view}'+(': '+', '.join(dict.fromkeys(errors[:8])) if errors else ''))
                except Exception as e:
                  check(False,f'{engine} {w}x{h} {scale} {view}: '+str(e).splitlines()[0][:240])
                finally:
                  await pg.close()
                  if viewctx is not ctx: await viewctx.close()
              await ctx.close()
          desktop=await browser.new_context(viewport={'width':1280,'height':800})
          await desktop.add_init_script(INIT+"localStorage.setItem('chisme-font-px','24');localStorage.setItem('chisme-font-version','2');")
          dp=await desktop.new_page();await dp.goto(url);await dp.wait_for_function('window.__chisme && __chisme.ready');await settle(dp)
          root=await dp.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
          check(abs(root-math.floor(24*19/16 + 0.5)*.84)<.1,engine+f' desktop saved size: {root}')
          await desktop.close()
          await browser.close()
    finally:
      proc.terminate();proc.wait();tmp.cleanup()
    print('ALL PASS' if not fails else f'{fails} FAIL(S)')
    return bool(fails)

if __name__=='__main__':
    try: sys.exit(asyncio.run(main()))
    except Exception as e: print('FAIL typography runner: '+str(e), flush=True); sys.exit(1)
