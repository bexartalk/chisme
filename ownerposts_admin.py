"""The owner's composer at /stats/posts (ownerposts.py has the storage, the checks and the routes; this only renders).

Phone-first (Goonie posts from his iPhone), in the /stats look (admin.HEAD's styles): category chips, headline, text,
up to 3 photos (picked from the camera roll, shrunk on the phone, re-encoded by the server: no EXIF), a credit line
each, where it happened (Google Maps link + an optional OpenStreetMap pin and map), the source, pin to the top for a
while, "also send a notification" with a lock-screen preview before anything is sent, a live preview of the feed card,
and the list of posts with Edit / Delete (a confirm sheet) / Copy link."""
from __future__ import annotations

import html
import json

import admin

e = html.escape

CSS = """
.op-cats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:4px 0 2px}
.op-cats button{min-height:52px;border-radius:12px;border:2px solid var(--ink);background:#fff;font-weight:900;font-size:.98rem;cursor:pointer;padding:0 4px}
.op-cats button[aria-checked=true]{background:var(--ink);color:#fff}
.op-tone{margin:8px 2px 0;font-size:.85rem;font-weight:700;border-left:5px solid var(--ink);padding:2px 8px}
.op-ph{display:grid;gap:10px;margin:6px 0 0}
.op-pr{display:grid;grid-template-columns:84px 1fr;gap:8px 10px;align-items:start;border:2px solid var(--line);border-radius:14px;padding:10px}
.op-pr img{width:84px;height:84px;object-fit:cover;border-radius:10px;background:var(--silverl)}
.op-pr .op-ptop{display:grid;gap:6px;align-content:start}
.op-pr .op-pn{font-weight:900;font-size:.95rem}
.op-pr .op-pst{font-size:.85rem;font-weight:800;color:var(--muted)}.op-pr .op-pst.bad{color:var(--pinkd)}.op-pr .op-pst.ok{color:var(--turqd)}
.op-pr .op-pf{grid-column:1/-1}
.op-pr label{display:block;font-weight:800;font-size:.85rem;margin:0 0 3px}
.op-pr .inp{min-height:46px;padding:8px 10px;font-size:16px}
.op-pb{display:flex;gap:6px}.op-pb button{flex:1;min-height:44px;border-radius:10px;border:2px solid var(--ink);background:#fff;font-weight:800;font-size:.9rem;cursor:pointer;padding:0 8px}
.op-pb .op-rm{color:var(--pinkd);border-color:var(--pinkd)}
.op-add{border-style:dashed}
.op-opt{border:2px solid var(--line);border-radius:14px;margin:14px 0 0;padding:0 12px}
.op-opt>summary{min-height:52px;display:flex;align-items:center;font-weight:900;cursor:pointer;list-style:none}
.op-opt>summary::-webkit-details-marker{display:none}.op-opt>summary::after{content:"+";margin-left:auto;font-size:1.4rem;font-weight:900}
.op-opt[open]>summary::after{content:"−"}.op-opt>div{padding:0 0 12px}
.op-opt>summary small{font-weight:600;color:var(--muted);margin-left:8px}
.op-pinrow{display:flex;gap:8px;align-items:center;margin-top:8px}.op-pinrow .inp{flex:1}
.op-mapimg{display:block;width:100%;height:auto;border-radius:10px;border:2px solid var(--ink);margin-top:8px}
.op-row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.op-btn{min-height:48px;border-radius:12px;border:2px solid var(--ink);background:#fff;font-weight:900;cursor:pointer;padding:0 12px}
.op-go2{display:grid;grid-template-columns:1fr;gap:0}
.big.sec{background:#fff;color:var(--ink)}
.big.danger{background:#fff;color:var(--pinkd);border-color:var(--pinkd)}
.op-pv{margin:14px 0 0;padding:10px;border-radius:16px;background:var(--silverl)}
.op-pv h3{margin:0 0 8px;font-size:.95rem;font-weight:900}
.op-mine{list-style:none;margin:6px 0 0;padding:0}
.op-mi{display:grid;grid-template-columns:64px 1fr;gap:4px 10px;padding:10px 0;border-bottom:1px solid var(--silverl)}
.op-mi img,.op-mi .op-noimg{width:64px;height:64px;border-radius:10px;object-fit:cover;background:var(--silverl);grid-row:span 2}
.op-mi .op-mt{font-weight:800;overflow-wrap:anywhere}.op-mi .op-mm{font-size:.8rem;color:var(--muted)}
.op-mb{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.op-mb a,.op-mb button{display:flex;align-items:center;justify-content:center;min-height:44px;border-radius:10px;border:2px solid var(--ink);background:#fff;font-weight:800;font-size:.9rem;color:var(--ink);text-decoration:none;cursor:pointer}
.op-mb .op-del{color:var(--pinkd);border-color:var(--pinkd)}
.op-editing{border-top-color:var(--orange)!important}
.op-done{border-color:var(--turqd);background:#e5fbfb}
.op-pushst{font-size:.85rem;color:var(--muted);margin:4px 2px 0}
.op-chk{display:flex;align-items:center;gap:12px;min-height:56px;margin-top:12px;padding:8px 12px;border:2px solid var(--line);border-radius:14px;font-weight:900}
.op-chk input{width:28px;height:28px;accent-color:var(--turqd);margin:0;flex:0 0 auto}
.op-chk.off{opacity:.6}
.sheet .three{display:grid;gap:8px}.sheet .three .big{margin-top:0}
.op-delh{font-weight:800;margin:6px 0 0;overflow-wrap:anywhere}
.sheet-b{max-height:88dvh;overflow:auto}
"""


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def page(posts: list | None, storage: dict, push: dict, nonce: str = "", error: str = "", edit: str = "") -> str:
    head = admin.HEAD.replace("%%TITLE%%", "Post your own chisme · Chisme Admin").replace(
        "</style></head><body>", CSS + '</style><link rel="stylesheet" href="/static/ownerposts.css"></head><body>')
    top = ('<header class="top"><div class="top-r"><a class="hb" href="/stats" aria-label="Back to Chisme Admin">‹ Admin</a>'
           '<div class="ht"><h1>Post your own chisme</h1><p>Shows in the Chisme feed as “From Chisme”</p></div>'
           '<a class="hb" href="/" aria-label="Open the Chisme app">App</a></div><div class="picado" aria-hidden="true"></div></header>')
    banners = []
    if not storage.get("durable"):
        banners.append('<div class="ban warn" role="note"><b>Temporary storage:</b> posts and photos are saved on this server only and '
                       'disappear on the next redeploy. Set <code>SUPABASE_URL</code> and <code>SUPABASE_SERVICE_KEY</code> on Render to keep them.</div>')
    if error:
        banners.append(f'<div class="ban warn" role="alert">{e(error)}</div>')
    push_on = bool(push.get("enabled"))
    n = int(push.get("phones") or 0)
    push_txt = (f'{n:,} {"phone" if n == 1 else "phones"} with alerts on will get it. You see a preview first.' if push_on
                else "Not set up yet: " + (push.get("why") or "push isn't configured on this server."))
    cats = "".join(f'<button type="button" role="radio" aria-checked="false" data-cat="{k}">{(em + " ") if em else ""}{e(lab)}</button>'
                   for k, (lab, em) in [("news", ("News", "")), ("weather", ("Weather", "🌤️")), ("events", ("Events", "🎉")),
                                         ("sports", ("Sports", "🏀")), ("food", ("Food", "🌮")), ("other", ("Other", "👀"))])
    form = f"""<section class="card" id="op-compose" aria-labelledby="op-h"><h2 id="op-h">✍️ New post</h2>
<p class="sub" id="op-sub" style="margin:0 0 6px">Weather, news, events, anything. Fields with * are required.</p>
<form id="op-form" novalidate autocomplete="off">
<p class="f" id="op-cat-l">Category *</p><div class="op-cats" role="radiogroup" aria-labelledby="op-cat-l" id="op-cats">{cats}</div>
<p class="op-tone" id="op-tone" hidden>News posts stay straight: plain styling, no emoji. Stick to what's confirmed and say where it came from.</p>
<label class="f" for="op-head">Headline * <small id="op-hc">0 / 140</small></label>
<input class="inp" id="op-head" maxlength="140" required enterkeyhint="next" autocapitalize="sentences" spellcheck="true">
<label class="f" for="op-body">Text <small id="op-bc">0 / 6,000</small></label>
<textarea class="inp" id="op-body" maxlength="6000" rows="8" autocapitalize="sentences" spellcheck="true"></textarea>
<p class="help">A blank line starts a new paragraph. Start a line with “- ” for a bullet. **Two stars** make bold.</p>

<p class="f">Photos <small id="op-pc">0 / 3</small></p>
<div class="op-ph" id="op-photos"></div>
<input type="file" id="op-file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,image/*" multiple hidden>
<button type="button" class="big sec op-add" id="op-add"><span aria-hidden="true">📷</span> Add photos</button>
<p class="help">Up to 3. The first one is the main photo (and the link preview). Location data and other hidden info are removed. Give each one a credit line.</p>

<details class="op-opt" id="op-where-d"><summary>📍 Location <small>optional</small></summary><div>
<label class="f" for="op-loc">Where (shown on the post)</label>
<input class="inp" id="op-loc" maxlength="200" placeholder="e.g. 12100 block of O'Connor Road" autocapitalize="sentences">
<label class="f" for="op-mapq">Address for the Google Maps link</label>
<input class="inp" id="op-mapq" maxlength="200" placeholder="Same as above if empty" autocapitalize="words">
<p class="help" id="op-glink"></p>
<p class="f">Map pin <small>optional: adds a small map</small></p>
<div class="op-row2"><button type="button" class="op-btn" id="op-find">🔎 Find it on the map</button><button type="button" class="op-btn" id="op-nopin" hidden>Remove pin</button></div>
<div class="op-pinrow"><input class="inp" id="op-pinpaste" placeholder="or paste: 29.5496, -98.3758 (or an OpenStreetMap link)" inputmode="text" autocapitalize="off" spellcheck="false"></div>
<p class="help" id="op-pinst" aria-live="polite">No pin.</p>
<img class="op-mapimg" id="op-mapimg" alt="Map preview" hidden>
</div></details>

<details class="op-opt" id="op-src-d"><summary>🔗 Source link <small>optional</small></summary><div>
<label class="f" for="op-srcu">Link (http:// or https:// only)</label>
<input class="inp" id="op-srcu" type="url" inputmode="url" maxlength="1800" placeholder="https://…" autocapitalize="off" spellcheck="false">
<label class="f" for="op-srcn">Source name</label>
<input class="inp" id="op-srcn" maxlength="160" placeholder="e.g. News 4 San Antonio" autocapitalize="words">
</div></details>

<label class="sw" for="op-pin-on" style="margin-top:14px"><span>📌 Pin to the top</span><input type="checkbox" role="switch" id="op-pin-on"></label>
<div id="op-pin-w" hidden><label class="f" for="op-pin-for">Keep it pinned for</label>
<select class="inp" id="op-pin-for"><option value="6">6 hours</option><option value="12">12 hours</option><option value="24" selected>1 day</option><option value="48">2 days</option><option value="72">3 days</option><option value="168">1 week</option></select>
<p class="help" id="op-pin-until"></p></div>

<label class="op-chk" for="op-spon" id="op-spon-l"><input type="checkbox" id="op-spon"><span>💲 Paid / Sponsored</span></label>
<p class="op-pushst" id="op-sponst">For paid event spotlights and sponsor posts. Shows a “Sponsored” label on the feed card, the post’s page and link previews (the FTC requires it). Not for News.</p>

<label class="op-chk{'' if push_on else ' off'}" for="op-push"><input type="checkbox" id="op-push"{'' if push_on else ' disabled'}><span>📣 Also send a notification</span></label>
<p class="op-pushst" id="op-pushst">{e(push_txt)}</p>

<div class="op-pv" aria-label="Preview"><h3>How it looks in the feed</h3><div id="op-preview"></div></div>
<p class="err" id="op-err" role="alert" hidden></p>
<div class="op-go2"><button type="submit" class="big go" id="op-publish">Publish</button>
<button type="button" class="big sec" id="op-draft">Save as draft (only you see it)</button>
<button type="button" class="big sec" id="op-cancel" hidden>Cancel editing</button>
<button type="button" class="big danger" id="op-delete" hidden>Delete this post…</button></div>
<p class="res" id="op-res" role="status" aria-live="polite"></p>
</form></section>"""
    mine = f"""<section class="card glance-top" id="op-mine-s" aria-labelledby="op-mine-h"><h2 id="op-mine-h">🗂️ Your posts</h2>
<p class="empty" id="op-empty"{' hidden' if posts else ''}>No posts yet. Your first one shows up here.</p><ul class="op-mine" id="op-mine"></ul></section>"""
    dialogs = """<dialog class="sheet" id="op-push-dlg" aria-labelledby="op-push-h"><div class="sheet-b"><h3 id="op-push-h">Send this notification?</h3>
<p class="sub" id="op-push-n"></p>
<div class="phone" aria-label="Notification preview"><div class="clk" id="op-clk">9:41</div><div class="dt" id="op-dt">Today</div>
<div class="ntf"><img src="/static/icons/icon-192.png" alt=""><div class="nb"><div class="nh"><span>Chisme</span><span>now</span></div>
<div class="nt" id="op-pt"></div><div class="nm" id="op-pm"></div></div></div><p class="nl">Tap → opens the post in Chisme</p></div>
<div class="three"><button type="button" class="big go" id="op-push-yes">Publish and send</button><button type="button" class="big sec" id="op-push-skip">Publish without sending</button>
<button type="button" class="big sec" id="op-push-no">Cancel</button></div></div></dialog>
<dialog class="sheet" id="op-del-dlg" aria-labelledby="op-del-h"><div class="sheet-b"><h3 id="op-del-h">Delete this post?</h3>
<p class="op-delh" id="op-del-t"></p>
<p class="sub">It disappears from the feed and its link stops working. Its photos are deleted too. This can't be undone.</p>
<div class="two"><button type="button" class="big" id="op-del-no">Cancel</button><button type="button" class="big go" id="op-del-yes">Yes, delete it</button></div></div></dialog>"""
    data = {"posts": posts or [], "storage": storage, "push": push, "edit": edit}
    sc = f'<script nonce="{e(nonce)}">' if nonce else "<script>"
    return (head + top + "<main>" + "".join(banners) + '<div id="op-donebox"></div>' + form + mine + "</main>" + dialogs
            + '<div class="toast" id="toast" role="status" aria-live="polite"></div>'
            + f'<script type="application/json" id="op-data">{_json(data)}</script>'
            + '<script src="/static/ownerposts.js"></script>'
            + sc + JS + "</script></body></html>")


JS = r"""(function(){
"use strict";
var $=function(id){return document.getElementById(id)};
var D=JSON.parse($('op-data').textContent),P=window.__chismePosts;
var CATS={news:'News',weather:'Weather',events:'Events',sports:'Sports',food:'Food',other:'Other'};
var EMOJI=/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{2300}-\u{23FF}\u{FE0F}\u{200D}\u{20E3}]/u;
var st={cat:'',photos:[],lat:null,lon:null,editing:null,busy:false};
var toastT;function toast(m,bad){var t=$('toast');t.textContent=m;t.className='toast show'+(bad?' bad':'');clearTimeout(toastT);toastT=setTimeout(function(){t.className='toast'},bad?7000:4500)}
function h(tag,props){var n=document.createElement(tag),p=props||{};Object.keys(p).forEach(function(k){var v=p[k];if(v==null||v===false)return;if(k==='text')n.textContent=v;else if(k==='on')Object.keys(v).forEach(function(ev){n.addEventListener(ev,v[ev])});else n.setAttribute(k,v===true?'':String(v))});
  for(var i=2;i<arguments.length;i++){var c=arguments[i];if(c==null||c===false)continue;(Array.isArray(c)?c:[c]).forEach(function(x){if(x!=null&&x!==false)n.append(x.nodeType?x:document.createTextNode(String(x)))})}return n}
function api(method,path,body){return fetch(path,{method:method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:body==null?undefined:JSON.stringify(body)})
  .then(function(r){if(r.status===401){toast('You were signed out. Sign in again on the Admin page.',true)}return r.json().catch(function(){return {ok:false,error:'the server answered '+r.status}}).then(function(j){if(!r.ok)j.ok=false;j.status=r.status;return j})})}
function when(iso){var t=Date.parse(iso);return t?new Date(t).toLocaleString('en-US',{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/Chicago'})+' CT':''}
var head=$('op-head'),body=$('op-body'),loc=$('op-loc'),mapq=$('op-mapq'),srcu=$('op-srcu'),srcn=$('op-srcn'),pinOn=$('op-pin-on'),pinFor=$('op-pin-for'),spon=$('op-spon'),push=$('op-push'),err=$('op-err'),res=$('op-res');

// ---- category
document.querySelectorAll('#op-cats [data-cat]').forEach(function(b){b.onclick=function(){setCat(b.dataset.cat)}});
function setCat(c){st.cat=c;document.querySelectorAll('#op-cats [data-cat]').forEach(function(b){b.setAttribute('aria-checked',b.dataset.cat===c?'true':'false')});$('op-tone').hidden=c!=='news';
  spon.disabled=c==='news';if(c==='news')spon.checked=false;$('op-spon-l').classList.toggle('off',c==='news');upd()}

// ---- photos: shrunk on the phone (canvas: also drops EXIF), the server re-encodes them anyway
$('op-add').onclick=function(){if(st.photos.length>=3){toast('Up to 3 photos.',true);return}$('op-file').click()};
$('op-file').onchange=function(){var fs=[].slice.call(this.files||[]);this.value='';var room=3-st.photos.length;if(fs.length>room)toast('Only '+room+' more photo'+(room===1?'':'s')+' fit (3 max).',true);fs.slice(0,room).forEach(addFile)};
function shrink(file){return new Promise(function(ok,no){var u=URL.createObjectURL(file),img=new Image();img.onload=function(){try{var s=Math.min(1,2000/Math.max(img.naturalWidth,img.naturalHeight)),c=document.createElement('canvas');
  c.width=Math.round(img.naturalWidth*s);c.height=Math.round(img.naturalHeight*s);var x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(u);ok(c.toDataURL('image/jpeg',0.9))}catch(e){no(e)}};
  img.onerror=function(){URL.revokeObjectURL(u);no(new Error('not a photo'))};img.src=u})}
function addFile(file){if(file.size>40*1024*1024){toast('That photo is too big.',true);return}
  var ph={name:'',url:'',w:0,h:0,credit:'',alt:'',state:'up',local:URL.createObjectURL(file)};st.photos.push(ph);drawPhotos();
  shrink(file).then(function(data){return api('POST','/stats/posts/photo',{data:data})}).then(function(j){
    if(j.ok){ph.name=j.photo.name;ph.url=j.photo.url;ph.w=j.photo.w;ph.h=j.photo.h;ph.state='ok'}else{ph.state='bad';ph.err=j.error||'upload failed'}drawPhotos()})
  .catch(function(){ph.state='bad';ph.err='Couldn\'t read or upload that photo.';drawPhotos()})}
function drawPhotos(){var box=$('op-photos');box.replaceChildren();st.photos.forEach(function(ph,i){
  var idc='op-cr'+i,ida='op-al'+i;
  var cr=h('input',{class:'inp',id:idc,maxlength:120,placeholder:'e.g. Photo: Goonie / Chisme',value:ph.credit||''});cr.oninput=function(){ph.credit=cr.value;upd()};
  var al=h('input',{class:'inp',id:ida,maxlength:200,placeholder:'e.g. The storefront at night',value:ph.alt||''});al.oninput=function(){ph.alt=al.value;upd()};
  var s=ph.state==='up'?['op-pst','Uploading\u2026']:ph.state==='bad'?['op-pst bad','\u2757 '+ph.err]:['op-pst ok','\u2705 Ready'];
  var btns=h('div',{class:'op-pb'},i>0?h('button',{type:'button',text:'Make main','aria-label':'Make photo '+(i+1)+' the main photo',on:{click:function(){st.photos.splice(i,1);st.photos.unshift(ph);drawPhotos();upd()}}}):null,
    h('button',{type:'button',class:'op-rm',text:'Remove','aria-label':'Remove photo '+(i+1),on:{click:function(){st.photos.splice(i,1);drawPhotos();upd()}}}));
  box.append(h('div',{class:'op-pr'},h('img',{src:ph.url||ph.local,alt:''}),
    h('div',{class:'op-ptop'},h('span',{class:'op-pn',text:i===0?'Photo 1 \u00b7 main photo':'Photo '+(i+1)}),h('span',{class:s[0],text:s[1]}),btns),
    h('div',{class:'op-pf'},h('label',{for:idc,text:'Credit line'}),cr),
    h('div',{class:'op-pf'},h('label',{for:ida,text:'What\u2019s in it (optional, for screen readers)'}),al)))});
  $('op-pc').textContent=st.photos.length+' / 3';$('op-add').hidden=st.photos.length>=3;upd()}

// ---- location
function gq(){return (mapq.value.trim()||loc.value.trim())}
function setPin(lat,lon,how){st.lat=lat;st.lon=lon;var on=lat!=null;$('op-nopin').hidden=!on;$('op-pinst').textContent=on?'Pin: '+lat.toFixed(5)+', '+lon.toFixed(5)+(how?' ('+how+')':''):'No pin.';
  var im=$('op-mapimg');if(on){im.hidden=false;im.src='/stats/posts/map-preview?lat='+lat+'&lon='+lon;im.onerror=function(){im.hidden=true;$('op-pinst').textContent+=' \u00b7 map preview unavailable right now'}}else{im.hidden=true;im.removeAttribute('src')}upd()}
$('op-find').onclick=function(){var q=gq();if(q.length<3){toast('Type the address first.',true);return}var b=this;b.disabled=true;$('op-pinst').textContent='Looking it up\u2026';
  fetch('/api/geocode?q='+encodeURIComponent(q.slice(0,120))).then(function(r){return r.json()}).then(function(j){var r=(j.results||[])[0];if(r)setPin(+r.lat,+r.lon,'found: '+(r.display_name||r.label||'').slice(0,90)+' \u2014 check it\u2019s right');else $('op-pinst').textContent='Couldn\u2019t find that address. Paste the pin instead.'})
  .catch(function(){$('op-pinst').textContent='Couldn\u2019t look it up right now.'}).then(function(){b.disabled=false})};
$('op-nopin').onclick=function(){setPin(null,null)};
$('op-pinpaste').addEventListener('change',function(){var v=this.value.trim(),m=/mlat=(-?\d+\.\d+).*?mlon=(-?\d+\.\d+)/.exec(v)||/@(-?\d+\.\d+),(-?\d+\.\d+)/.exec(v)||/(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)/.exec(v);
  if(!v)return;if(!m){toast('That doesn\u2019t look like a pin. Use “29.5496, -98.3758”.',true);return}var la=+m[1],lo=+m[2];if(Math.abs(la)>85||Math.abs(lo)>180){toast('That pin isn\u2019t a real place.',true);return}setPin(la,lo,'pasted');this.value=''});
[loc,mapq].forEach(function(x){x.addEventListener('input',upd)});

// ---- pin to top
pinOn.addEventListener('change',function(){$('op-pin-w').hidden=!pinOn.checked;upd()});pinFor.addEventListener('change',upd);

// ---- the post as typed
function fields(status){var f={category:st.cat,headline:head.value.trim(),body:body.value,photos:st.photos.filter(function(p){return p.name}).map(function(p){return {name:p.name,w:p.w,h:p.h,credit:p.credit.trim(),alt:p.alt.trim()}}),
  location:loc.value.trim(),map_query:mapq.value.trim(),lat:st.lat,lon:st.lon,source_url:srcu.value.trim(),source_name:srcn.value.trim(),sponsored:spon.checked,status:status||'published'};
  var e=st.editing;if(pinOn.checked){f.pin_hours=pinFor.value===''?null:+pinFor.value}else f.pin_hours=0;
  if(e&&pinOn.checked&&pinFor.value==='')delete f.pin_hours;return f}
function problem(){if(!st.cat)return 'Pick a category.';if(!head.value.trim())return 'Write a headline.';
  if(st.photos.some(function(p){return p.state==='up'}))return 'Wait for the photos to finish uploading.';
  if(st.photos.some(function(p){return p.state==='bad'}))return 'Remove the photo that didn\u2019t upload.';
  var u=srcu.value.trim();if(u&&!/^https?:\/\/[^\s<>"'`\\]{3,}$/i.test(u))return 'The source link must start with http:// or https://';
  if(st.cat==='news'&&spon.checked)return 'Paid posts can\u2019t go in News. Pick Events or Other.';
  if(st.cat==='news'){var all=[head.value,body.value,loc.value,mapq.value,srcn.value].concat(st.photos.map(function(p){return p.credit+p.alt})).join(' ');if(EMOJI.test(all))return 'News posts stay straight: take out the emoji first.'}
  if(st.lat!=null&&!gq())return 'Add the location text for the map pin.';return ''}
function upd(){$('op-hc').textContent=head.value.length+' / 140';$('op-bc').textContent=body.value.length.toLocaleString()+' / 6,000';
  var q=gq();$('op-glink').replaceChildren();if(q){$('op-glink').append('Google Maps link: ',h('a',{href:'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(q).replace(/%20/g,'+'),target:'_blank',rel:'noopener noreferrer',text:'test it \u2197'}))}
  if(pinOn.checked){var v=pinFor.value;$('op-pin-until').textContent=v===''?'':'Pinned until about '+new Date(Date.now()+v*3600e3).toLocaleString('en-US',{weekday:'short',hour:'numeric',minute:'2-digit',timeZone:'America/Chicago'})+' CT, then it moves down like the rest.'}
  var f=fields(),cur=st.editing||{};var pv={slug:cur.slug||'preview',url:'#',category:f.category||'other',headline:f.headline||'Your headline',body:f.body,summary:f.body.replace(/\*\*(.+?)\*\*/g,'$1').replace(/^[-\u2022*]\s+/gm,'').replace(/\s+/g,' ').trim().slice(0,220),
    photos:st.photos.filter(function(p){return p.url||p.local}).map(function(p){return {url:p.url||p.local,credit:p.credit,alt:p.alt,w:p.w,h:p.h}}),location:f.location,pinned:pinOn.checked,sponsored:spon.checked,status:'published',created_at:cur.created_at||new Date().toISOString()};
  if(P){var c=P.card(pv,{preview:true});$('op-preview').replaceChildren(c)}
  if(!err.hidden){var p=problem();err.textContent=p;err.hidden=!p}}
[head,body,srcu,srcn].forEach(function(x){x.addEventListener('input',upd)});spon.addEventListener('change',upd);

// ---- publish / save (with the push preview first when asked)
$('op-form').addEventListener('submit',function(ev){ev.preventDefault();go('published')});
$('op-draft').onclick=function(){go('draft')};
function go(status){if(st.busy)return;var p=problem();if(p){err.textContent=p;err.hidden=false;toast(p,true);return}err.hidden=true;
  var f=fields(status);if(status==='published'&&push.checked&&!push.disabled){
    api('POST','/stats/posts/push-preview',f).then(function(j){if(!j.ok){toast('\u2757 '+(j.error||'Couldn\u2019t preview the notification'),true);return}
      $('op-pt').textContent=j.payload.title;$('op-pm').textContent=j.payload.body;var d=new Date();$('op-clk').textContent=d.toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}).replace(/\s?[AP]M$/i,'');$('op-dt').textContent=d.toLocaleDateString([],{weekday:'long',month:'long',day:'numeric'});
      $('op-push-n').textContent=j.enabled?('Goes to '+j.phones.toLocaleString()+' '+(j.phones===1?'phone':'phones')+' with alerts on. Check it reads right: it can\u2019t be taken back.'):('Not set up yet: '+j.why);
      $('op-push-yes').disabled=!j.enabled;var dl=$('op-push-dlg');dl.showModal();
      $('op-push-yes').onclick=function(){dl.close();save(f,true)};$('op-push-skip').onclick=function(){dl.close();save(f,false)};$('op-push-no').onclick=function(){dl.close()}})
    return}
  save(f,false)}
function save(f,andPush){st.busy=true;var btn=$('op-publish');btn.disabled=true;res.className='res';res.textContent='Saving\u2026';
  var e=st.editing,req=e?api('PATCH','/stats/posts/'+encodeURIComponent(e.id),f):api('POST','/stats/posts',f);
  req.then(function(j){if(!j.ok){res.className='res bad';res.textContent='Not saved: '+(j.error||'error');toast('\u2757 '+res.textContent,true);return null}
    var post=j.post;if(!andPush)return {post:post};res.textContent='Saved. Sending the notification\u2026';
    return api('POST','/stats/posts/'+encodeURIComponent(post.id)+'/push',{confirm:true}).then(function(k){return {post:post,push:k}})})
  .then(function(r){if(!r)return;var post=r.post,msg=(e?'Saved':post.status==='draft'?'Draft saved':'Published')+'.';
    if(r.push)msg+=r.push.ok?' Notification sent to '+r.push.sent+' of '+r.push.total+' phones.':' The notification wasn\u2019t sent: '+(r.push.error||'error')+'.';
    sessionStorage.setItem('op-done',JSON.stringify({msg:msg,slug:post.slug,status:post.status,bad:!!(r.push&&!r.push.ok)}));location.replace('/stats/posts?saved='+Date.now().toString(36))})
  .catch(function(){res.className='res bad';res.textContent='Not saved: no connection';toast('\u2757 Not saved: no connection',true)})
  .then(function(){st.busy=false;btn.disabled=false})}

// ---- the list: edit, delete, copy link
function drawMine(){var ul=$('op-mine');ul.replaceChildren();$('op-empty').hidden=!!D.posts.length;D.posts.forEach(function(p){var ph=(p.photos||[])[0];
  var meta=[CATS[p.category]||'Other',p.status==='draft'?'Draft':'Published',when(p.created_at)];if(p.sponsored)meta.push('Sponsored');if(p.pinned)meta.push('pinned until '+when(p.pinned_until));if(p.push_sent_at)meta.push('notification sent');
  ul.append(h('li',{class:'op-mi','data-id':p.id},ph?h('img',{src:ph.url,alt:''}):h('span',{class:'op-noimg'}),h('span',{class:'op-mt',text:p.headline}),h('span',{class:'op-mm',text:meta.join(' \u00b7 ')}),
    h('div',{class:'op-mb'},h('a',{href:'/stats/posts?edit='+encodeURIComponent(p.id),class:'op-edit',text:'Edit'}),
      p.status==='published'?h('button',{type:'button',class:'op-copy',text:'Copy link',on:{click:function(){copy(p)}}}):h('a',{href:p.url,target:'_blank',rel:'noopener',text:'View'}),
      h('button',{type:'button',class:'op-del',text:'Delete',on:{click:function(){askDelete(p)}}}))))})}
function link(p){var b=document.querySelector('meta[name="chisme-base"]');return location.origin+'/p/'+p.slug}
function copy(p){var u=link(p);(navigator.share&&matchMedia('(pointer:coarse)').matches?navigator.share({title:p.headline,url:u}):navigator.clipboard.writeText(u).then(function(){toast('Link copied: '+u)})).catch(function(){})}
function askDelete(p){var dl=$('op-del-dlg');$('op-del-t').textContent='\u201c'+p.headline+'\u201d';dl.showModal();$('op-del-no').onclick=function(){dl.close()};
  $('op-del-yes').onclick=function(){dl.close();api('DELETE','/stats/posts/'+encodeURIComponent(p.id),{confirm:'DELETE'}).then(function(j){if(j.ok){D.posts=D.posts.filter(function(x){return x.id!==p.id});drawMine();toast('Deleted.');if(st.editing&&st.editing.id===p.id)location.href='/stats/posts'}else toast('\u2757 Not deleted: '+(j.error||'error'),true)})}}
$('op-delete').onclick=function(){if(st.editing)askDelete(st.editing)};
$('op-cancel').onclick=function(){location.href='/stats/posts'};
document.querySelectorAll('dialog.sheet').forEach(function(d){d.addEventListener('click',function(e){if(e.target===d)d.close()})});

// ---- edit mode
function startEdit(p){st.editing=p;$('op-compose').classList.add('op-editing');$('op-h').textContent='\u270f\ufe0f Edit post';$('op-sub').textContent='Changes show in the feed and on the post\u2019s page right away.';
  setCat(p.category);head.value=p.headline;body.value=p.body;loc.value=p.location||'';mapq.value=p.map_query||'';srcu.value=p.source_url||'';srcn.value=p.source_name||'';
  st.photos=(p.photos||[]).map(function(x){var n=(/\/((p\/\d{6}\/[A-Za-z0-9_-]{12})\.webp)$/.exec(x.url)||[])[1]||'';return {name:n,url:x.url,w:x.w,h:x.h,credit:x.credit||'',alt:x.alt||'',state:'ok'}});
  if(p.lat!=null)setPin(+p.lat,+p.lon,'saved');if(p.location||p.lat!=null)$('op-where-d').open=true;if(p.source_url||p.source_name)$('op-src-d').open=true;
  if(p.pinned){pinOn.checked=true;$('op-pin-w').hidden=false;pinFor.prepend(h('option',{value:'',text:'Keep as is (until '+when(p.pinned_until)+')'}));pinFor.value=''}
  spon.checked=!!p.sponsored;
  if(p.push_sent_at){push.checked=false;push.disabled=true;$('op-pushst').textContent='Already sent as a notification ('+when(p.push_sent_at)+').'}
  $('op-publish').textContent=p.status==='draft'?'Publish':'Save changes';$('op-draft').textContent=p.status==='draft'?'Keep as draft':'Move back to drafts';$('op-cancel').hidden=false;$('op-delete').hidden=false;drawPhotos()}
var ed=D.edit&&D.posts.find(function(p){return p.id===D.edit});
if(D.edit&&!ed)toast('That post isn\u2019t there anymore.',true);
if(ed)startEdit(ed);drawPhotos();drawMine();upd();
try{var dn=JSON.parse(sessionStorage.getItem('op-done')||'null');if(dn){sessionStorage.removeItem('op-done');var box=$('op-donebox');
  box.append(h('div',{class:'ban op-done',role:'status'},h('b',{text:(dn.bad?'\u2757 ':'\u2705 ')+dn.msg}),' ',dn.status==='published'?h('a',{href:'/p/'+dn.slug,target:'_blank',rel:'noopener',text:'View the post'}):null,
    dn.status==='published'?' \u00b7 ':null,dn.status==='published'?h('a',{href:'/?post='+dn.slug,text:'See it in Chisme'}):null));toast(dn.msg,dn.bad)}}catch(_){}
})();"""
