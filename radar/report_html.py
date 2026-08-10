#!/usr/bin/env python3
"""Interactive single-page dashboard (self-contained, vanilla JS). Fast filter/sort, views, shortlists."""
import json, html
from collections import Counter

CAT_LABELS = {
    "noutbuklar": "💻 Noutbuklar",
    "komputerler": "🖥 Komputerlər",
    "komputer-avadanliqi": "🧩 Komponent/Monitor",
    "komputer-aksesuarlari": "🖱 Aksesuarlar",
    "ofis-avadanliqi": "🖨 Ofis avadanlığı",
}


def build_html(listings, new_now, run_ts, path, public=False):
    """public=True → seller phone numbers omitted (privacy for online/GitHub Pages deploy)."""
    new_ids = {r["ad_id"] for r in new_now}
    keys = ("id", "name", "brand", "price", "band", "spec_score", "value_score", "cpu", "cpu_fam",
            "ram", "storage", "screen", "gpu", "os", "usage", "condition", "category", "subcategory",
            "seller_type", "seller", "phones", "link", "params")
    data = []
    for r in listings:
        d = {k: r.get(k) for k in keys}
        if public:
            d["phones"] = ""  # do not expose seller phone numbers on a public URL
        d["new"] = 1 if r["ad_id"] in new_ids else 0
        data.append(d)
    cats = [c for c in Counter(r.get("category") for r in listings).keys() if c]
    cat_meta = [{"slug": c, "label": CAT_LABELS.get(c, c), "n": sum(1 for r in listings if r.get("category") == c)} for c in cats]
    meta = {
        "cats": cat_meta,
        "subs": {c: sorted({r.get("subcategory") for r in listings if r.get("category") == c and r.get("subcategory")}) for c in cats},
        "brands": sorted({r.get("brand") for r in listings if r.get("brand")}),
        "run_ts": run_ts, "n_total": len(listings), "n_new": len(new_now),
    }
    doc = _TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)) \
                   .replace("__META__", json.dumps(meta, ensure_ascii=False)) \
                   .replace("__RUNTS__", html.escape(run_ts))
    open(path, "w", encoding="utf-8").write(doc)
    return path


_TEMPLATE = r"""<!doctype html><html lang="az"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>tap.az Radar — __RUNTS__</title>
<style>
:root{--bg:#f3f6fb;--panel:#ffffff;--panel2:#f7f9fd;--ink:#0f172a;--muted:#64748b;--line:#e6ecf5;--acc:#1d4ed8;--acc2:#2563eb;
 --acc-soft:#e9f0fe;--good:#15803d;--bad:#b91c1c;--warn:#b45309;--chip:#eef2f9;
 --shadow:0 1px 2px rgba(15,23,42,.05),0 2px 8px rgba(15,23,42,.05);--radius:14px}
@media(prefers-color-scheme:dark){:root{--bg:#070c15;--panel:#0f1826;--panel2:#0c1421;--ink:#e6eef8;--muted:#8aa0b8;--line:#1d2b3f;
 --acc:#3b82f6;--acc2:#60a5fa;--acc-soft:#14243a;--chip:#152131;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.4)}}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);font-size:13px;-webkit-font-smoothing:antialiased}
.app{display:grid;grid-template-columns:224px 1fr;height:100vh}
.side{background:var(--panel);border-right:1px solid var(--line);padding:16px 12px;overflow:auto}
.brand{font-weight:800;font-size:15px;padding:4px 8px 14px;letter-spacing:.3px}
.brand .logo{display:flex;align-items:center;gap:8px}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--acc2);box-shadow:0 0 0 3px var(--acc-soft)}
.brand small{display:block;color:var(--muted);font-weight:500;font-size:11px;margin-top:6px;letter-spacing:0}
.nav{display:flex;flex-direction:column;gap:2px}
.nav button{all:unset;cursor:pointer;padding:9px 11px;border-radius:9px;color:var(--ink);font-size:13px;display:flex;justify-content:space-between;align-items:center;transition:background .12s}
.nav button:hover{background:var(--chip)}.nav button.on{background:var(--acc2);color:#fff;box-shadow:var(--shadow)}
.nav button.on .cnt{color:#fff;opacity:.9}
.nav .cnt{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}
.nav .sep{margin:12px 8px 4px;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:700}
.main{overflow:auto;padding:18px 22px}
.top{display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.top h1{font-size:19px;margin:0;font-weight:800;letter-spacing:-.3px}.top .sub{color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:11px;margin-bottom:18px}
@media(max-width:1050px){.kpis{grid-template-columns:repeat(3,1fr)}}
@media(max-width:900px){.app{grid-template-columns:1fr}.side{position:fixed;z-index:20;height:100%;transform:translateX(-100%);transition:.2s;box-shadow:var(--shadow)}.side.open{transform:none}}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 13px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--acc2);opacity:.85}
.kpi .l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.kpi .n{font-size:22px;font-weight:800;margin-top:3px;letter-spacing:-.5px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:15px 16px;margin-bottom:16px;box-shadow:var(--shadow)}
.panel h2{font-size:14px;margin:0 0 12px;font-weight:750;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.panel h3{font-size:12px;margin:2px 0 8px;font-weight:700;color:var(--muted)}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
input,select{padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font-size:12.5px;transition:border-color .12s,box-shadow .12s}
input:focus,select:focus{outline:none;border-color:var(--acc2);box-shadow:0 0 0 3px var(--acc-soft)}
select{cursor:pointer}
.qs{display:flex;gap:5px;flex-wrap:wrap}
.qs button,.chip{all:unset;cursor:pointer;padding:7px 11px;border:1px solid var(--line);border-radius:20px;font-size:12px;background:var(--panel);transition:.12s}
.qs button:hover,.chip:hover{border-color:var(--acc2)}
.qs button.on,.chip.on{background:var(--acc2);color:#fff;border-color:transparent}
.subtabs{display:flex;gap:4px;margin:2px 0 14px;border-bottom:1px solid var(--line)}
.stab{all:unset;cursor:pointer;padding:9px 15px;font-size:12.5px;font-weight:650;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;transition:.12s}
.stab:hover{color:var(--ink)}.stab.on{color:var(--acc2);border-bottom-color:var(--acc2)}
table{width:100%;border-collapse:collapse}
th,td{padding:8px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;z-index:2;background:var(--panel2);cursor:pointer;user-select:none;font-size:10.5px;text-transform:uppercase;color:var(--muted);white-space:nowrap;font-weight:700;letter-spacing:.03em;box-shadow:inset 0 -1px 0 var(--line)}
th:hover{color:var(--acc2)}
th.arrow::after{content:' ▾';color:var(--acc2)}th.arrowup::after{content:' ▴';color:var(--acc2)}
tbody tr{transition:background .08s}
tbody tr:nth-child(even){background:var(--panel2)}
tbody tr:hover{background:var(--acc-soft)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.small{color:var(--muted);font-size:11.5px}
.val{font-weight:800;padding:2px 7px;border-radius:6px;color:#fff;display:inline-block;min-width:34px;text-align:center;font-variant-numeric:tabular-nums}
.shop{color:var(--good);font-weight:600}.priv{color:var(--warn);font-weight:600}
.tg{border-radius:6px;padding:1px 6px;font-size:10px;font-weight:700;white-space:nowrap}
.tg.new{background:#dcfce7;color:#15803d}.tg.g{background:#f3e8ff;color:#7e22ce}.tg.o{background:#dbeafe;color:#1d4ed8}
a{color:var(--acc2);text-decoration:none}a:hover{text-decoration:underline}
.star{cursor:pointer;color:#cbd5e1;font-size:15px;transition:transform .1s}.star:hover{transform:scale(1.25)}.star.on{color:#f59e0b}
.tblwrap{max-height:calc(100vh - 330px);overflow:auto;border:1px solid var(--line);border-radius:11px}
.bars .bar{display:grid;grid-template-columns:132px 1fr 42px;gap:8px;align-items:center;margin:3px 0;font-size:12px}
.bars .bt{background:var(--chip);border-radius:6px;height:14px;overflow:hidden}.bars .bt i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:6px;transition:width .3s}
.bars .bv{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.cbar{cursor:pointer;border-radius:7px;padding:3px 6px;margin:1px 0;transition:background .12s}.cbar:hover{background:var(--chip)}.cbar:hover .bt i{filter:brightness(1.15)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.catcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:12px}
.catcard{background:linear-gradient(160deg,var(--acc-soft),var(--panel));border:1px solid var(--line);border-radius:14px;padding:16px;cursor:pointer;transition:transform .12s,border-color .12s,box-shadow .12s}
.catcard:hover{border-color:var(--acc2);transform:translateY(-3px);box-shadow:0 10px 24px rgba(37,99,235,.16)}.catcard .b{font-size:25px;font-weight:800;margin:5px 0;letter-spacing:-.5px}
.muted{color:var(--muted)}.hide{display:none}
.count{color:var(--muted);font-weight:400;font-size:12px}
.pager{display:flex;gap:5px;align-items:center;flex-wrap:wrap;padding:12px 2px 2px}
.pg{all:unset;cursor:pointer;min-width:18px;text-align:center;padding:6px 10px;border:1px solid var(--line);border-radius:8px;font-size:12px;background:var(--panel);transition:.12s;font-variant-numeric:tabular-nums}
.pg:hover:not([disabled]){border-color:var(--acc2)}
.pg.on{background:var(--acc2);color:#fff;border-color:transparent;font-weight:700}
.pg[disabled]{opacity:.4;cursor:default}
.pgdots{color:var(--muted);padding:0 2px}
.pgmeta{color:var(--muted);font-size:11.5px;margin-left:8px}
.pgsize{margin-left:auto}
.an-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin:0 0 14px;padding-bottom:11px;border-bottom:1px solid var(--line)}
.an-head h2{margin:0;font-size:15px}
.an-stats{font-size:11.5px;color:var(--muted);font-weight:600}.an-stats b{color:var(--ink)}
.an-col h3{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:var(--acc2);margin:0 0 10px}
.chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}
.spec{font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;background:var(--chip);color:var(--muted);white-space:nowrap;letter-spacing:.2px}
.spec.cpu{background:rgba(37,99,235,.13);color:#2563eb}
.spec.ram{background:rgba(13,148,136,.15);color:#0d9488}
.spec.ssd{background:rgba(124,58,237,.15);color:#7c3aed}
.spec.gpu{background:rgba(219,39,119,.15);color:#db2777}
@media(prefers-color-scheme:dark){.spec.cpu{color:#7aa5ff}.spec.ram{color:#2dd4bf}.spec.ssd{color:#a78bfa}.spec.gpu{color:#f472b6}}
.bt-tbl td{padding:9px 8px;vertical-align:middle}
.bt-tbl .bandc{white-space:nowrap}.bt-tbl .bandc b{font-size:13px}
.ptag{color:var(--good);font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap;margin-left:4px}
.pwwrap{display:flex;align-items:center;gap:8px;min-width:96px}
.pw{flex:1;height:8px;background:var(--chip);border-radius:5px;overflow:hidden;min-width:52px}
.pw i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:5px}
.pwn{font-size:11.5px;font-weight:800;font-variant-numeric:tabular-nums;min-width:22px;text-align:right}
.pgroup{margin-bottom:13px}
.pgh{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);display:flex;align-items:center;gap:6px;margin:0 0 6px}
.pgrid{display:grid;grid-template-columns:auto 1fr auto;gap:5px 12px;align-items:baseline}
.pgrid .pv{font-weight:800;font-size:12px;white-space:nowrap}.pgrid .pv small{color:var(--muted);font-weight:600;margin-left:4px;font-size:10px}
.pgrid .pm{color:var(--muted);font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.pgrid .pp{color:var(--good);font-weight:800;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bandpager{display:flex;gap:6px;align-items:center;justify-content:flex-end;padding:10px 2px 0}
.mtoggle{display:none}@media(max-width:900px){.mtoggle{display:inline-block}}
</style></head><body>
<div class="app">
 <aside class="side" id="side">
  <div class="brand"><span class="logo"><span class="dot"></span>tap.az RADAR</span><small id="brsub"></small></div>
  <div class="nav" id="nav"></div>
 </aside>
 <div class="main">
  <div class="top">
   <button class="chip mtoggle" onclick="document.getElementById('side').classList.toggle('open')">☰</button>
   <h1 id="vtitle">İcmal</h1><span class="sub" id="vsub"></span>
   <span style="flex:1"></span>
   <input id="q" placeholder="🔎 Axtar (ad, parametr, satıcı)…" style="min-width:240px">
  </div>
  <div id="root"></div>
 </div>
</div>
<script>
const DATA=__DATA__, META=__META__;
const $=(s,e=document)=>e.querySelector(s);
const fmt=n=>n==null?'':(''+Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,',');
const esc=s=>(s==null?'':(''+s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const store={get(){try{return new Set(JSON.parse(localStorage.getItem('radar_star')||'[]'))}catch(e){return new Set()}},
 set(s){localStorage.setItem('radar_star',JSON.stringify([...s]))}};
let STAR=store.get();
$('#brsub').textContent=`${META.n_total} elan · ${META.n_new} 🆕 · ${META.run_ts.slice(0,10)}`;

const state={view:'overview',cat:'',sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,q:'',
 pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:'',sortKey:'value_score',sortDir:-1,page:0,ps:50,catTab:'table',bandPages:{},paramTab:'ram',condMode:'yeni'};
function distinct(field,cat){const s=new Set();DATA.forEach(r=>{if(cat&&r.category!==cat)return;const v=r[field];if(v!=null&&v!=='')s.add(v);});return [...s];}

// ---------- navigation ----------
const NAV=[['overview','📊 İcmal'],['best','⭐ Ən uyğun'],['new','🆕 Yeni'],['SEP','Kateqoriyalar'],
 ...META.cats.map(c=>['cat:'+c.slug,c.label,c.n]),['SEP','Alətlər'],
 ['analysis','📈 Parametr analizi'],['stars','⭐ Seçilmişlər']];
function buildNav(){
 const n=$('#nav');n.innerHTML='';
 NAV.forEach(item=>{
  if(item[0]==='SEP'){const d=document.createElement('div');d.className='sep';d.textContent=item[1];n.appendChild(d);return;}
  const b=document.createElement('button');b.dataset.k=item[0];
  b.innerHTML=`<span>${item[1]}</span>`+(item[2]!=null?`<span class="cnt">${item[2]}</span>`:'');
  b.onclick=()=>go(item[0]);n.appendChild(b);
 });
}
function go(k){
 if(k.startsWith('cat:')){state.view='table';state.cat=k.slice(4);state.catTab='table';
  Object.assign(state,{sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:''});}
 else {state.view=k;if(k!=='table')state.cat='';}
 state.page=0;
 [...$('#nav').children].forEach(b=>b.classList&&b.classList.toggle('on',b.dataset&&b.dataset.k===k));
 render();window.scrollTo(0,0);
}

// ---------- filtering / sorting ----------
function filtered(base,skipSub,skipCond){
 const q=state.q.toLowerCase();
 return base.filter(r=>{
  if(state.cat&&r.category!==state.cat)return false;
  if(!skipSub&&state.sub&&r.subcategory!==state.sub)return false;
  if(!skipCond&&state.cond&&r.condition!==state.cond)return false;
  if(state.seller&&r.seller_type!==state.seller)return false;
  if(state.usage&&r.usage!==state.usage)return false;
  if(state.brand&&r.brand!==state.brand)return false;
  if(state.pram&&(''+r.ram)!==state.pram)return false;
  if(state.pcpu&&r.cpu_fam!==state.pcpu)return false;
  if(state.pcgen&&cpuGen(r)!==state.pcgen)return false;
  if(state.pcser&&cpuSer(r)!==state.pcser)return false;
  if(state.pstor&&r.storage!==state.pstor)return false;
  if(state.pscr&&(''+r.screen)!==state.pscr)return false;
  if(state.pgpu==='__has'&&!r.gpu)return false;
  if(state.pgpu==='__no'&&r.gpu)return false;
  if(state.pgpu&&state.pgpu!=='__has'&&state.pgpu!=='__no'&&r.gpu!==state.pgpu)return false;
  if(state.pmin!==''&&(r.price||0)<+state.pmin)return false;
  if(state.pmax!==''&&(r.price||1e9)>+state.pmax)return false;
  if(state.onlyNew&&!r.new)return false;
  if(q&&!((r.name||'')+(r.params||'')+(r.seller||'')+(r.brand||'')).toLowerCase().includes(q))return false;
  return true;
 });
}
function sortRows(rows){
 const k=state.sortKey,d=state.sortDir;
 return rows.slice().sort((a,b)=>{let x=a[k],y=b[k];if(x==null)x=(typeof y==='number'?-1:'');if(y==null)y=(typeof x==='number'?-1:'');
  if(typeof x==='string'||typeof y==='string')return d*(((''+x)>(''+y))-((''+x)<(''+y)));return d*(x-y);});
}
const valColor=v=>{if(v==null)return 'background:#94a3b8';const t=Math.max(0,Math.min(1,v/120));
 const r=Math.round(248-(248-21)*t),g=Math.round(113+(128-113)*t),b=Math.round(107-(107-61)*t);return `background:rgb(${r},${g},${b})`;};

// ---------- table ----------
const COLS=[['','',36],['name','Ad',null],['brand','Brend',null],['price','Qiymət',null],['value_score','Dəyər',null],
 ['gpu','Video kart',null],['params','Parametrlər',null],['usage','İstifadə',null],['condition','Vəziyyət',null],['seller_type','Satıcı',null],
 ['seller','Mağaza/Şəxs',null],['phones','Telefon',null]];
function tableHTML(rows){
 const ps=state.ps,pages=Math.max(1,Math.ceil(rows.length/ps));
 if(state.page>=pages)state.page=pages-1;if(state.page<0)state.page=0;
 const start=state.page*ps,shown=rows.slice(start,start+ps);
 const head='<tr>'+COLS.map(c=>{if(c[0]==='')return '<th></th>';const ar=state.sortKey===c[0]?(state.sortDir<0?'arrow':'arrowup'):'';
  return `<th class="${ar}" data-k="${c[0]}">${c[1]}</th>`;}).join('')+'</tr>';
 const body=shown.map(r=>{
  const st=STAR.has(r.id);
  const ub=r.usage==='Gaming'?'<span class="tg g">Gaming</span>':(r.usage==='Ofis / Gündəlik'?'<span class="tg o">Ofis</span>':esc(r.usage||''));
  return `<tr>
   <td><span class="star ${st?'on':''}" data-id="${r.id}">${st?'★':'☆'}</span></td>
   <td><a href="${esc(r.link)}" target="_blank">${esc(r.name)}</a>${r.new?' <span class="tg new">🆕</span>':''}<div class="small">${esc(r.subcategory||'')}</div></td>
   <td>${esc(r.brand)}</td>
   <td class="num">${r.price!=null?fmt(r.price)+' ₼':''}</td>
   <td class="num">${r.value_score!=null?`<span class="val" style="${valColor(r.value_score)}">${r.value_score}</span>`:''}</td>
   <td>${r.gpu?`<b style="color:#7e22ce">${esc(r.gpu)}</b>`:(r.usage==='Gaming'?'<span class="small" style="color:#b45309">GPU?</span>':'<span class="small">—</span>')}</td>
   <td class="small">${esc(r.params)}</td>
   <td>${ub}</td>
   <td class="small">${esc(r.condition)}</td>
   <td class="${r.seller_type==='Mağaza'?'shop':'priv'}">${esc(r.seller_type)}</td>
   <td class="small">${esc(r.seller)}</td>
   <td class="small">${esc(r.phones)}</td></tr>`;}).join('');
 return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
}
function pager(total){
 const ps=state.ps,pages=Math.max(1,Math.ceil(total/ps));
 let p=state.page;if(p>=pages)p=pages-1;if(p<0)p=0;
 const btn=(lbl,pg,dis,on)=>`<button class="pg ${on?'on':''}" data-pg="${pg}" ${dis?'disabled':''}>${lbl}</button>`;
 let nums='';const win=2,st=Math.max(0,p-win),en=Math.min(pages-1,p+win);
 const add=i=>nums+=btn(i+1,i,false,i===p);
 if(st>0){add(0);if(st>1)nums+='<span class="pgdots">…</span>';}
 for(let i=st;i<=en;i++)add(i);
 if(en<pages-1){if(en<pages-2)nums+='<span class="pgdots">…</span>';add(pages-1);}
 return `<div class="pager">${btn('‹ Əvvəl',p-1,p===0)}${nums}${btn('Sonra ›',p+1,p>=pages-1)}
  <span class="pgmeta">Səhifə ${p+1} / ${pages} · ${fmt(total)} nəticə</span>
  <select id="pgsize" class="pgsize">${[25,50,100,200].map(s=>`<option value="${s}" ${s===ps?'selected':''}>${s}/səhifə</option>`).join('')}</select></div>`;
}
function bindPager(){
 $('#root').querySelectorAll('.pg').forEach(b=>{if(b.hasAttribute('disabled'))return;
  b.onclick=()=>{state.page=+b.dataset.pg;render();const w=$('#root .tblwrap');if(w)w.scrollTop=0;};});
 const ss=$('#pgsize');if(ss)ss.onchange=()=>{state.ps=+ss.value;state.page=0;render();};
}
function bindSubtabs(){$('#root').querySelectorAll('.stab').forEach(b=>b.onclick=()=>{state.catTab=b.dataset.tab;state.page=0;render();window.scrollTo(0,0);});}
function bindTable(){
 $('#root').querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;
  if(state.sortKey===k)state.sortDir*=-1;else{state.sortKey=k;state.sortDir=(k==='name'||k==='brand'||k==='seller_type')?1:-1;}state.page=0;render();});
 $('#root').querySelectorAll('.star').forEach(s=>s.onclick=()=>{const id=s.dataset.id;
  if(STAR.has(id))STAR.delete(id);else STAR.add(id);store.set(STAR);render();});
}
function filtersBar(withCat,hideCond){
 const subs=(state.cat&&META.subs[state.cat])||[];
 const cat=state.cat;
 const psel=(id,field,label,cur,numeric,suffix='')=>{let vals=distinct(field,cat);if(!vals.length)return '';
  vals.sort(numeric?((a,b)=>b-a):((a,b)=>(''+a).localeCompare(''+b,'az')));
  return `<select id="${id}"><option value="">${label}: hamısı</option>`+vals.map(v=>`<option value="${esc(''+v)}" ${cur===(''+v)?'selected':''}>${esc(''+v)}${suffix}</option>`).join('')+`</select>`;};
 const gpuVals=distinct('gpu',cat).sort((a,b)=>(''+a).localeCompare(''+b));
 const gpuSel=gpuVals.length?`<select id="f_pgpu"><option value="">Video kart: hamısı</option><option value="__has" ${state.pgpu==='__has'?'selected':''}>✓ var (diskret)</option><option value="__no" ${state.pgpu==='__no'?'selected':''}>— yox</option>${gpuVals.map(v=>`<option value="${esc(v)}" ${state.pgpu===v?'selected':''}>${esc(v)}</option>`).join('')}</select>`:'';
 const pselFn=(id,fn,label,cur)=>{let vals=distinctFn(fn,cat);if(!vals.length)return '';vals.sort((a,b)=>(''+a).localeCompare(''+b,'az',{numeric:true}));
  return `<select id="${id}"><option value="">${label}: hamısı</option>`+vals.map(v=>`<option value="${esc(v)}" ${cur===v?'selected':''}>${esc(v)}</option>`).join('')+`</select>`;};
 const paramRow=`<div class="controls" style="margin-top:-4px">
  <span class="small" style="align-self:center;font-weight:700">⚙️ Parametrlər:</span>
  ${psel('f_pram','ram','RAM',state.pram,true,' GB')}
  ${psel('f_pcpu','cpu_fam','CPU',state.pcpu,false)}
  ${pselFn('f_pcgen',cpuGen,'Nəsil',state.pcgen)}
  ${pselFn('f_pcser',cpuSer,'Seriya',state.pcser)}
  ${psel('f_pstor','storage','Yaddaş',state.pstor,false)}
  ${psel('f_pscr','screen','Ekran',state.pscr,true,'"')}
  ${gpuSel}
 </div>`;
 return `<div class="controls">
  ${withCat?`<select id="f_cat"><option value="">Kateqoriya: hamısı</option>${META.cats.map(c=>`<option value="${c.slug}" ${state.cat===c.slug?'selected':''}>${c.label}</option>`).join('')}</select>`:''}
  ${subs.length?`<select id="f_sub"><option value="">Alt-kateqoriya: hamısı</option>${subs.map(s=>`<option ${state.sub===s?'selected':''}>${esc(s)}</option>`).join('')}</select>`:''}
  <select id="f_usage"><option value="">İstifadə</option><option>Gaming</option><option>Ofis / Gündəlik</option></select>
  ${hideCond?'':`<select id="f_cond"><option value="">Vəziyyət</option><option>Yeni</option><option>İkinci əl</option></select>`}
  <select id="f_seller"><option value="">Satıcı</option><option>Mağaza</option><option>Şəxsi</option></select>
  <select id="f_brand"><option value="">Brend</option>${META.brands.map(b=>`<option ${state.brand===b?'selected':''}>${esc(b)}</option>`).join('')}</select>
  <input id="f_pmin" type="number" placeholder="min ₼" style="width:82px" value="${state.pmin}">
  <input id="f_pmax" type="number" placeholder="max ₼" style="width:82px" value="${state.pmax}">
  <label class="chip"><input type="checkbox" id="f_new" ${state.onlyNew?'checked':''}> 🆕 yeni</label>
  <span class="qs">
   <button data-sort="value_score">⭐ Ən yaxşı dəyər</button>
   <button data-sort="price_asc">↑ Ən ucuz</button>
   <button data-sort="price_desc">↓ Ən bahalı</button>
  </span>
  <button class="chip" id="f_clear">Təmizlə</button>
 </div>${paramRow}`;
}
function bindFilters(){
 const set=(id,key)=>{const e=$('#'+id);if(e)e.onchange=()=>{state[key]=e.value;state.page=0;
  if(key==='cat')Object.assign(state,{sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:'',catTab:'table'});render();};};
 set('f_cat','cat');set('f_sub','sub');set('f_usage','usage');set('f_cond','cond');set('f_seller','seller');set('f_brand','brand');
 set('f_pram','pram');set('f_pcpu','pcpu');set('f_pcgen','pcgen');set('f_pcser','pcser');set('f_pstor','pstor');set('f_pscr','pscr');set('f_pgpu','pgpu');
 const pn=$('#f_pmin'),px=$('#f_pmax');if(pn)pn.oninput=()=>{state.pmin=pn.value;state.page=0;render();};if(px)px.oninput=()=>{state.pmax=px.value;state.page=0;render();};
 const fn=$('#f_new');if(fn)fn.onchange=()=>{state.onlyNew=fn.checked;state.page=0;render();};
 $('#root').querySelectorAll('.qs button').forEach(b=>b.onclick=()=>{const s=b.dataset.sort;
  if(s==='price_asc'){state.sortKey='price';state.sortDir=1;}else if(s==='price_desc'){state.sortKey='price';state.sortDir=-1;}
  else{state.sortKey='value_score';state.sortDir=-1;}state.page=0;render();});
 const cl=$('#f_clear');if(cl)cl.onclick=()=>{Object.assign(state,{sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,
  pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:'',page:0});render();};
 [['f_usage','usage'],['f_cond','cond'],['f_seller','seller']].forEach(([id,k])=>{const e=$('#'+id);if(e)e.value=state[k];});
}

// ---------- bars ----------
function bars(counter,order,fmtk=x=>x,limit){
 let items=(order||Object.keys(counter).sort((a,b)=>counter[b]-counter[a]));if(limit)items=items.slice(0,limit);
 const mx=Math.max(1,...items.map(k=>counter[k]));
 return '<div class="bars">'+items.map(k=>`<div class="bar"><span>${esc(fmtk(k))}</span><span class="bt"><i style="width:${Math.round(counter[k]/mx*100)}%"></i></span><span class="bv">${counter[k]}</span></div>`).join('')+'</div>';
}
function countBy(rows,key){const c={};rows.forEach(r=>{const v=r[key];if(v!=null&&v!=='')c[v]=(c[v]||0)+1;});return c;}

// ---------- views ----------
function scoredCat(rows){return rows.filter(r=>r.value_score!=null && (r.price||0)>=noPriceFloor(r));}
function noPriceFloor(r){return r.category==='noutbuklar'?130:(r.category==='komputerler'?150:8);}
function bestList(rows,k){return sortRows(rows.filter(r=>r.value_score!=null).filter(r=>(r.price||0)>=noPriceFloor(r)))
  .filter((r,i)=>true).slice(0,k);}
function miniTable(rows,showGpu){
 return `<table><thead><tr><th>Ad</th><th>Qiymət</th><th>Dəyər</th>${showGpu?'<th>Video kart</th>':''}<th>Parametrlər</th><th>Satıcı</th><th>Telefon</th></tr></thead><tbody>`+
 rows.map(r=>`<tr><td><a href="${esc(r.link)}" target="_blank">${esc(r.name)}</a>${r.new?' <span class="tg new">🆕</span>':''}</td>
  <td class="num">${fmt(r.price)} ₼</td><td class="num"><span class="val" style="${valColor(r.value_score)}">${r.value_score}</span></td>
  ${showGpu?`<td>${r.gpu?`<b style="color:#7e22ce">${esc(r.gpu)}</b>`:'<span class="small" style="color:#b45309">GPU?</span>'}</td>`:''}
  <td class="small">${esc(r.params)}</td><td class="${r.seller_type==='Mağaza'?'shop':'priv'}">${esc(r.seller_type)}</td>
  <td class="small">${esc(r.phones)}</td></tr>`).join('')+`</tbody></table>`;
}
function kpiStrip(rows){
 const sc=rows.filter(r=>r.value_score!=null);const pr=sc.map(r=>r.price).filter(Boolean);
 const g=sc.filter(r=>r.usage==='Gaming').length,o=sc.filter(r=>r.usage==='Ofis / Gündəlik').length;
 const sh=sc.filter(r=>r.seller_type==='Mağaza').length;
 const nn=rows.filter(r=>r.new).length;
 const K=(l,n)=>`<div class="kpi"><div class="l">${l}</div><div class="n">${n}</div></div>`;
 return `<div class="kpis">${K('Elan',rows.length)}${K('🆕 Yeni',nn)}
  ${K('Orta qiymət',pr.length?fmt(pr.reduce((a,b)=>a+b,0)/pr.length):0)}
  ${K('🏪 Mağaza',sh)}${K('🎮 Gaming',g)}${K('💼 Ofis',o)}</div>`;
}

// 200-AZN price buckets (istifadəçi: intervallar 200 ₼ səviyyəsində). ≥2000 → "2000+".
function band200(price){if(price==null||price==='')return null;const w=200;if(price>=2000)return '2000+';const lo=Math.floor(price/w)*w;return lo+'–'+(lo+w);}
function bandDist(scored){const c={};scored.forEach(r=>{const b=band200(r.price);if(!b)return;c[b]=(c[b]||0)+1;});
 const ord=Object.keys(c).sort((a,b)=>(a==='2000+'?1e9:parseInt(a))-(b==='2000+'?1e9:parseInt(b)));return {c,ord};}
function cbars(counter,order,fmtk,type,limit){let items=(order||Object.keys(counter).sort((a,b)=>counter[b]-counter[a]));if(limit)items=items.slice(0,limit);
 const mx=Math.max(1,...items.map(k=>counter[k]));
 return '<div class="bars">'+items.map(k=>`<div class="bar cbar" data-type="${type}" data-val="${esc(''+k)}"><span>${esc(fmtk(k))}</span><span class="bt"><i style="width:${Math.round(counter[k]/mx*100)}%"></i></span><span class="bv">${counter[k]}</span></div>`).join('')+'</div>';}
function pick(type,val){Object.assign(state,{cat:'',sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:'',onlyNew:false,page:0,catTab:'table'});
 if(type==='brand')state.brand=val; else if(type==='usage')state.usage=val; else if(type==='cond')state.cond=val;
 else if(type==='band'){const m=(''+val).match(/\d+/g);if(m){state.pmin=m[0];state.pmax=(''+val).includes('+')?'':(m[1]||'');}}
 else if(type==='ram')state.pram=val; else if(type==='cpu')state.pcpu=val; else if(type==='storage')state.pstor=val; else if(type==='gpu')state.pgpu=val;
 state.view='table';[...$('#nav').children].forEach(b=>b.classList&&b.classList.remove('on'));render();window.scrollTo(0,0);}
function bindCbars(){$('#root').querySelectorAll('.cbar').forEach(b=>b.onclick=()=>pick(b.dataset.type,b.dataset.val));}
// CPU nəsil (generation) + seriya (suffix) — cpu mətnindən parse, hər sətir üçün keşlənir.
const VALID_SUF=/^(U|H|HX|HK|HS|HQ|G|K|KF|KS|F|T|P|Y|M|MQ|QM|X|XT|GE|E)$/i;
function _cpuCompute(r){const cpu=(r.cpu||'');let gen='',ser='',m,apple=false;
 if(/apple|\bM[1-4]\b/i.test(cpu)&&(m=cpu.match(/\bM([1-4])\b/i))){apple=true;gen='Apple M'+m[1];const s=(cpu.match(/\b(Pro|Max|Ultra)\b/i)||[])[1];ser=s?s[0].toUpperCase()+s.slice(1).toLowerCase():'';}
 else if((m=cpu.match(/i[3579]-(\d{3,5})([A-Za-z]{0,3})/i))){const num=m[1];ser=(m[2]||'').toUpperCase();
  let g;if(num.length>=5)g=num.slice(0,2);else if(num[0]==='1'&&num.length===4)g=num.slice(0,2);else g=num.slice(0,1);gen='Intel '+g+'-ci nəsil';}
 else if((m=cpu.match(/Core\s+(?:Ultra\s+)?[3579]\s+(\d{3})([A-Za-z]{0,3})/i))){ser=(m[2]||'').toUpperCase();gen='Intel Core Ultra Seriya '+m[1][0];}
 else if((m=cpu.match(/Ryzen\s+(?:AI\s+)?[3579]\s+(\d{3,4})([A-Za-z]{0,3})/i))){const num=m[1];ser=(m[2]||'').toUpperCase();gen='Ryzen '+(num.length===4?num[0]+'000':num[0]+'00')+' seriya';}
 if(!apple&&!VALID_SUF.test(ser))ser=''; // drop mis-captured suffixes (GB, UU, SS…)
 r.__cg=gen;r.__cs=ser;}
function cpuGen(r){if(r.__cg===undefined)_cpuCompute(r);return r.__cg;}
function cpuSer(r){if(r.__cs===undefined)_cpuCompute(r);return r.__cs;}
function distinctFn(fn,cat){const s=new Set();DATA.forEach(r=>{if(cat&&r.category!==cat)return;const v=fn(r);if(v)s.add(v);});return [...s];}
function render(){
 $('#q').oninput=()=>{state.q=$('#q').value;state.page=0;render1();};
 render1();
}
// ---------- per-category / per-subcategory analysis ----------
function bestBandsFor(rows){const g={};rows.forEach(r=>{const b=band200(r.price);if(!b)return;(g[b]=g[b]||[]).push(r);});
 return Object.keys(g).sort((a,b)=>(a==='2000+'?1e9:parseInt(a))-(b==='2000+'?1e9:parseInt(b))).map(b=>({band:b,n:g[b].length,best:g[b].slice().sort((x,y)=>(y.spec_score||0)-(x.spec_score||0))[0]}));}
function relevantParams(rows){const cand=[['ram','RAM',true,' GB'],['cpu_fam','CPU',false,''],['storage','Yaddaş',false,''],['gpu','Video kart',false,''],['screen','Ekran',true,'″']];
 const n=rows.length;return cand.filter(c=>rows.filter(r=>r[c[0]]!=null&&r[c[0]]!=='').length>=Math.max(3,n*0.12));}
function cheapestForField(rows,field,numeric){const g={};rows.forEach(r=>{if(!r.price||r[field]==null||r[field]==='')return;(g[r[field]]=g[r[field]]||[]).push(r);});
 let ks=Object.keys(g);ks.sort(numeric?((a,b)=>b-a):((a,b)=>g[b].length-g[a].length));
 return ks.map(k=>({val:k,n:g[k].length,cheap:g[k].slice().sort((a,b)=>a.price-b.price)[0]}));}
// Component parameter extractor — components keep specs in the parsed `params` string, not structured fields.
// Parse params (clean) first; use name only for GPU model. Sanity-bound capacities to reject model-number noise.
function compKey(r){
 const p=(r.params||'');const nm=(r.name||'');const sub=(r.subcategory||'');
 const gpuRe=/\b(RTX|GTX|RX|Arc|Radeon)\s*\d{3,4}\s*(?:Ti|Super|XT)?\b/i;
 const cap=s=>{const c=(s||'').match(/(\d+(?:\.\d+)?)\s*(TB|GB)\b/i);if(!c)return null;const tb=/tb/i.test(c[2]);const gb=+c[1]*(tb?1024:1);
  if(gb<1||gb>16384)return null;return{k:(+c[1])+(tb?' TB':' GB'),lab:'Tutum',num:gb};};
 if(/video|gpu|kart/i.test(sub)){const g=p.match(gpuRe)||nm.match(gpuRe);return g?{k:g[0].toUpperCase().replace(/\s+/g,' ').trim(),lab:'Model'}:null;}
 if(/monitor/i.test(sub)){const s=p.match(/(\d{2}(?:\.\d)?)\s*(?:"|″|inch|inç)/i);return s&&+s[1]>=15&&+s[1]<=90?{k:s[1]+'″',lab:'Ölçü',num:+s[1]}:null;}
 if(/disk|ssd|hdd|ram|yaddaş|yaddash/i.test(sub))return cap(p);
 const g=p.match(gpuRe)||nm.match(gpuRe);if(g)return{k:g[0].toUpperCase().replace(/\s+/g,' ').trim(),lab:'Model'};
 return cap(p);
}
const COMP_JUNK=/\b(protector|qoruyucu|kabel|adapter|perexod|stend|stand|mount|kron|lamp|lampa|işıq|çexol|klaviatura|mouse|siçan|çanta|sumka|kalonka|dinamik|şləyf|şleyf)\b/i;
function cheapestByComp(rows){const g={};rows.forEach(r=>{if(!r.price)return;if(COMP_JUNK.test(r.name||''))return;const ck=compKey(r);if(!ck)return;const e=g[ck.k]||(g[ck.k]={lab:ck.lab,items:[]});e.items.push(r);});
 let ks=Object.keys(g);if(!ks.length)return{lab:'',list:[]};
 ks.sort((a,b)=>g[b].items.length-g[a].items.length); // popularity — surface mainstream values first
 return {lab:g[ks[0]].lab||'Parametr',list:ks.slice(0,12).map(k=>({val:k,n:g[k].items.length,cheap:g[k].items.slice().sort((a,b)=>a.price-b.price)[0]}))};}
// Parsed spec chips — structured fields for laptop/desktop, else split the params string.
function specChips(r){let c=[];
 if(r.cpu||r.ram||r.storage||r.gpu||r.screen){
  if(r.cpu)c.push(['cpu',r.cpu]);
  if(r.ram)c.push(['ram',r.ram+' GB']);
  if(r.storage)c.push(['ssd',r.storage]);
  if(r.gpu)c.push(['gpu',r.gpu]);
  if(r.screen)c.push(['scr',r.screen+'″']);
 } else if(r.params){c=r.params.split(/[·,]/).map(s=>s.trim()).filter(Boolean).slice(0,5).map(s=>['scr',s]);}
 return c.length?'<div class="chips">'+c.map(x=>`<span class="spec ${x[0]}">${esc(x[1])}</span>`).join('')+'</div>':'';}
const PICON={'RAM':'🧠','CPU':'⚙️','Yaddaş':'💾','Video kart':'🎮','Ekran':'🖥️','Tutum':'💾','Model':'🎮','Ölçü':'🖥️','Təzələnmə':'🔄','Parametr':'🔧'};
function catAnalysis(cat){
 const base=filtered(DATA,!state.sub);
 const g={};base.forEach(r=>{const k=r.subcategory||'(digər)';(g[k]=g[k]||[]).push(r);});
 const order=Object.keys(g).sort((a,b)=>g[b].length-g[a].length);
 let out='';
 order.forEach(sc=>{
  const rows=g[sc];const scored=rows.filter(r=>r.value_score!=null);
  const maxSpec=Math.max(1,...scored.map(r=>r.spec_score||0));
  const wp=rows.filter(r=>r.price);const avg=wp.length?wp.reduce((a,b)=>a+b.price,0)/wp.length:0;
  const nnew=rows.filter(r=>r.new).length,nshop=rows.filter(r=>r.seller_type==='Mağaza').length;
  const bands=bestBandsFor(scored);
  const bandTbl=bands.length?`<table class="bt-tbl"><thead><tr><th>Büdcə</th><th>Ən güclü konfiqurasiya</th><th>Güc</th></tr></thead><tbody>`+
   bands.map(x=>{const sp=x.best.spec_score||0,pct=Math.max(4,Math.round(sp/maxSpec*100));
    return `<tr><td class="bandc"><b>${esc(x.band)} ₼</b><div class="small">${x.n} model</div></td>
    <td><a href="${esc(x.best.link)}" target="_blank">${esc((x.best.name||'').slice(0,46))}</a>${x.best.new?' <span class="tg new">🆕</span>':''}<span class="ptag">${fmt(x.best.price)} ₼</span>${specChips(x.best)}</td>
    <td><div class="pwwrap"><div class="pw"><i style="width:${pct}%"></i></div><span class="pwn">${pct}</span></div></td></tr>`;}).join('')+`</tbody></table>`:'<div class="small muted">Kifayət qədər data yoxdur.</div>';
  const cheapGroup=(label,list)=>{if(!list.length)return '';
   return `<div class="pgroup"><div class="pgh"><span>${PICON[label]||'🔧'}</span> ${esc(label)}</div><div class="pgrid">`+
    list.map(x=>`<span class="pv">${esc(''+x.val)}<small>${x.n}</small></span><span class="pm"><a href="${esc(x.cheap.link)}" target="_blank">${esc(x.cheap.name||'')}</a></span><span class="pp">${fmt(x.cheap.price)} ₼</span>`).join('')+`</div></div>`;};
  const params=relevantParams(rows);
  let cheap;
  if(params.length){ // laptop/desktop structured fields
   cheap=params.map(pf=>cheapGroup(pf[1],cheapestForField(scored.length?scored:rows,pf[0],pf[2]).slice(0,6).map(x=>({val:x.val+pf[3],n:x.n,cheap:x.cheap})))).join('');
  } else { // components — param from free-text params/name
   const cb=cheapestByComp(scored.length?scored:rows);cheap=cheapGroup(cb.lab||'Parametr',cb.list);
  }
  if(!cheap)cheap='<div class="small muted">Uyğun parametr datası yoxdur.</div>';
  out+=`<div class="panel">
   <div class="an-head"><h2>📂 ${esc(sc)}</h2><div class="an-stats"><b>${fmt(rows.length)}</b> elan · orta <b>${fmt(avg)} ₼</b> · <b>${nnew}</b> 🆕 · <b>${nshop}</b> 🏪</div></div>
   <div class="grid2">
    <div class="an-col"><h3>💰 Büdcəyə görə ən güclü konfiqurasiya</h3>${bandTbl}</div>
    <div class="an-col"><h3>🎯 Parametrə görə ən sərfəli qiymət</h3>${cheap}</div>
   </div></div>`;
 });
 return out||'<div class="panel muted">Bu seçim üçün data yoxdur.</div>';
}
// Budget browser — each 200₼ range as its own paginated panel. Defaults to «Yeni» condition (used → Vəziyyət filter).
function budgetView(cat){
 const sig=JSON.stringify(['B',state.condMode,state.cat,state.sub,state.seller,state.usage,state.brand,state.pmin,state.pmax,state.onlyNew,state.pram,state.pcpu,state.pcgen,state.pcser,state.pstor,state.pscr,state.pgpu,state.q,state.sortKey,state.sortDir]);
 if(state._bsig!==sig){state.bandPages={};state._bsig=sig;}
 let base=applyCondMode(filtered(DATA,!state.sub,true).filter(r=>r.value_score!=null));
 const g={};base.forEach(r=>{const b=band200(r.price);if(!b)return;(g[b]=g[b]||[]).push(r);});
 const bands=Object.keys(g).sort((a,b)=>(a==='2000+'?1e9:parseInt(a))-(b==='2000+'?1e9:parseInt(b)));
 const note=`<div class="panel" style="padding:12px 14px;margin-bottom:12px">${condModeBar()}<span class="small">💡 Yuxarıdan vəziyyət seç: <b>Yalnız Yeni</b>, <b>Yeni + İkinci əl</b> (qarışıq) və ya <b>Yalnız İkinci əl</b>. Hər qiymət aralığı ayrıca səhifələnir.</span></div>`;
 if(!bands.length)return note+'<div class="panel muted">Bu seçim üçün məhsul yoxdur.</div>';
 const maxSpec=Math.max(1,...base.map(r=>r.spec_score||0));
 const PS=15;
 const bhead=`<thead><tr><th>Model</th><th>Qiymət</th><th>Güc</th><th>Vəziyyət</th><th>Satıcı</th><th>Telefon</th></tr></thead>`;
 let out=note;
 bands.forEach(b=>{
  const items=sortRows(g[b]);
  const pages=Math.max(1,Math.ceil(items.length/PS));
  let pg=state.bandPages[b]||0;if(pg>=pages)pg=pages-1;if(pg<0)pg=0;
  const slice=items.slice(pg*PS,pg*PS+PS);
  const wp=items.filter(r=>r.price);const avg=wp.length?wp.reduce((a,c)=>a+c.price,0)/wp.length:0;
  const rows=slice.map(r=>{const sp=r.spec_score||0,pct=Math.max(4,Math.round(sp/maxSpec*100));
   return `<tr>
    <td><a href="${esc(r.link)}" target="_blank">${esc((r.name||'').slice(0,52))}</a>${r.new?' <span class="tg new">🆕</span>':''}${specChips(r)}</td>
    <td class="num"><b>${fmt(r.price)} ₼</b></td>
    <td><div class="pwwrap"><div class="pw"><i style="width:${pct}%"></i></div><span class="pwn">${pct}</span></div></td>
    <td class="small">${esc(r.condition||'')}</td>
    <td class="${r.seller_type==='Mağaza'?'shop':'priv'}">${esc(r.seller_type||'')}</td>
    <td class="small">${esc(r.phones||'')}</td></tr>`;}).join('');
  const pager=pages>1?`<div class="bandpager" data-band="${esc(b)}">
     <button class="pg" data-bp="prev" ${pg===0?'disabled':''}>‹ Əvvəl</button>
     <span class="pgmeta">Səhifə ${pg+1} / ${pages}</span>
     <button class="pg" data-bp="next" ${pg>=pages-1?'disabled':''}>Sonra ›</button></div>`:'';
  out+=`<div class="panel"><div class="an-head"><h2>💰 ${esc(b)} ₼</h2>
     <div class="an-stats"><b>${fmt(items.length)}</b> məhsul · orta <b>${fmt(avg)} ₼</b> · <b>${pg*PS+1}–${Math.min(items.length,pg*PS+PS)}</b> göstərilir</div></div>
    <table>${bhead}<tbody>${rows}</tbody></table>${pager}</div>`;
 });
 return out;
}
function bindBandPagers(){$('#root').querySelectorAll('.bandpager').forEach(bp=>{const band=bp.dataset.band;
 bp.querySelectorAll('.pg').forEach(btn=>{if(btn.hasAttribute('disabled'))return;btn.onclick=()=>{
  const cur=state.bandPages[band]||0;state.bandPages[band]=cur+(btn.dataset.bp==='next'?1:-1);render();};});});}
// Parameter browser — CPU / RAM / VGA only. Each value = its own panel with the cheapest top-15 (paginated).
function paramView(cat){
 const dim=state.paramTab||'ram';
 const sig=JSON.stringify(['P',dim,state.condMode,state.cat,state.sub,state.seller,state.usage,state.brand,state.pmin,state.pmax,state.onlyNew,state.pram,state.pcpu,state.pcgen,state.pcser,state.pstor,state.pscr,state.pgpu,state.q]);
 if(state._bsig!==sig){state.bandPages={};state._bsig=sig;}
 const sel=`<div class="controls" style="margin-bottom:12px"><span class="small" style="align-self:center;font-weight:700">Parametr növü:</span>
   <button class="chip ${dim==='cpu'?'on':''}" data-pt="cpu">⚙️ CPU</button>
   <button class="chip ${dim==='ram'?'on':''}" data-pt="ram">🧠 RAM</button>
   <button class="chip ${dim==='vga'?'on':''}" data-pt="vga">🎮 VGA (Video kart)</button></div>`;
 let base=applyCondMode(filtered(DATA,!state.sub,true).filter(r=>r.value_score!=null));
 const field=dim==='cpu'?'cpu_fam':(dim==='ram'?'ram':'gpu');
 const g={};base.forEach(r=>{const v=r[field];if(v==null||v==='')return;(g[v]=g[v]||[]).push(r);});
 let keys=Object.keys(g);
 if(dim==='ram')keys.sort((a,b)=>(+b)-(+a));
 else {keys=keys.filter(k=>g[k].length>=2).sort((a,b)=>g[b].length-g[a].length);if(dim==='vga')keys=keys.slice(0,40);}
 if(!keys.length)return sel+'<div class="panel muted">Bu kateqoriyada CPU/RAM/VGA parametri strukturlaşmayıb (əsasən noutbuk/masaüstü üçün mövcuddur).</div>';
 const maxSpec=Math.max(1,...base.map(r=>r.spec_score||0));const PS=15;const icon=dim==='cpu'?'⚙️':(dim==='ram'?'🧠':'🎮');
 const bhead=`<thead><tr><th>Model</th><th>Qiymət</th><th>Güc</th><th>Vəziyyət</th><th>Satıcı</th><th>Telefon</th></tr></thead>`;
 let out=sel+`<div class="panel" style="padding:12px 14px;margin-bottom:12px">${condModeBar()}<span class="small">💡 Seçilmiş parametrin hər dəyəri ayrıca — ən <b>sərfəli qiymətli məhsullar öndə</b> (ən ucuz → bahalı). Yuxarıdan Yalnız Yeni / qarışıq / Yalnız İkinci əl seç. Hər qrup müstəqil səhifələnir.</span></div>`;
 keys.forEach(v=>{
  const items=g[v].slice().sort((a,b)=>(a.price||1e9)-(b.price||1e9));
  const key='p|'+dim+'|'+v;
  const pages=Math.max(1,Math.ceil(items.length/PS));
  let pg=state.bandPages[key]||0;if(pg>=pages)pg=pages-1;if(pg<0)pg=0;
  const slice=items.slice(pg*PS,pg*PS+PS);
  const wp=items.filter(r=>r.price);const avg=wp.length?wp.reduce((a,c)=>a+c.price,0)/wp.length:0;
  const label=dim==='ram'?(v+' GB'):v;
  const rows=slice.map(r=>{const sp=r.spec_score||0,pct=Math.max(4,Math.round(sp/maxSpec*100));
   return `<tr>
    <td><a href="${esc(r.link)}" target="_blank">${esc((r.name||'').slice(0,52))}</a>${r.new?' <span class="tg new">🆕</span>':''}${specChips(r)}</td>
    <td class="num"><b>${fmt(r.price)} ₼</b></td>
    <td><div class="pwwrap"><div class="pw"><i style="width:${pct}%"></i></div><span class="pwn">${pct}</span></div></td>
    <td class="small">${esc(r.condition||'')}</td>
    <td class="${r.seller_type==='Mağaza'?'shop':'priv'}">${esc(r.seller_type||'')}</td>
    <td class="small">${esc(r.phones||'')}</td></tr>`;}).join('');
  const pgr=pages>1?`<div class="bandpager" data-band="${esc(key)}">
     <button class="pg" data-bp="prev" ${pg===0?'disabled':''}>‹ Əvvəl</button>
     <span class="pgmeta">Səhifə ${pg+1} / ${pages}</span>
     <button class="pg" data-bp="next" ${pg>=pages-1?'disabled':''}>Sonra ›</button></div>`:'';
  out+=`<div class="panel"><div class="an-head"><h2>${icon} ${esc(label)}</h2>
     <div class="an-stats"><b>${fmt(items.length)}</b> məhsul · ən ucuz <b>${fmt(items[0]?items[0].price:0)} ₼</b> · orta <b>${fmt(avg)} ₼</b></div></div>
    <table>${bhead}<tbody>${rows}</tbody></table>${pgr}</div>`;
 });
 return out;
}
function bindParamSel(){$('#root').querySelectorAll('[data-pt]').forEach(b=>b.onclick=()=>{state.paramTab=b.dataset.pt;render();});}
// Condition mode toggle for budget/param views: only-new / mixed / only-used
function condModeBar(){return `<div class="controls" style="margin-bottom:0"><span class="small" style="align-self:center;font-weight:700">Vəziyyət:</span>
  <button class="chip ${state.condMode==='yeni'?'on':''}" data-cm="yeni">🆕 Yalnız Yeni</button>
  <button class="chip ${state.condMode==='all'?'on':''}" data-cm="all">🔀 Yeni + İkinci əl</button>
  <button class="chip ${state.condMode==='used'?'on':''}" data-cm="used">♻️ Yalnız İkinci əl</button></div>`;}
function applyCondMode(rows){return state.condMode==='yeni'?rows.filter(r=>r.condition==='Yeni'):(state.condMode==='used'?rows.filter(r=>r.condition==='İkinci əl'):rows);}
function bindCondMode(){$('#root').querySelectorAll('[data-cm]').forEach(b=>b.onclick=()=>{state.condMode=b.dataset.cm;render();});}
function render1(){
 const root=$('#root');const v=state.view;
 let title='İcmal',sub='';
 if(v==='overview'){
  title='İcmal';sub=`${META.n_total} elan · ${META.n_new} yeni · qrafiklərə klikləyib filtrlə`;
  const scored=DATA.filter(r=>r.value_score!=null);
  const bd=bandDist(scored);
  const usageC={'Gaming':scored.filter(r=>r.usage==='Gaming').length,'Ofis / Gündəlik':scored.filter(r=>r.usage==='Ofis / Gündəlik').length};
  const condC=countBy(scored,'condition');
  root.innerHTML=kpiStrip(DATA)+
   `<div class="panel"><h2>Kateqoriyalar <span class="small">— klikləyib bax · hər kateqoriyada «📊 Alt-kateqoriya analizi» tabı</span></h2><div class="catcards">${META.cats.map(c=>`<div class="catcard" onclick="go('cat:${c.slug}')"><div>${c.label}</div><div class="b">${c.n}</div><div class="muted">bax →</div></div>`).join('')}</div></div>`+
   `<div class="grid2">
     <div class="panel"><h2>💰 Qiymət aralığı <span class="small">(200 ₼ · klik→filtr)</span></h2>${cbars(bd.c,bd.ord,k=>k+' ₼','band')}</div>
     <div class="panel"><h2>🏷 Brend <span class="small">(klik→filtr)</span></h2>${cbars(countBy(scored,'brand'),null,x=>x,'brand',10)}</div></div>`+
   `<div class="grid2">
     <div class="panel"><h2>🎮 İstifadə <span class="small">(klik→filtr)</span></h2>${cbars(usageC,['Gaming','Ofis / Gündəlik'],k=>k==='Gaming'?'🎮 Gaming':'💼 Ofis','usage')}</div>
     <div class="panel"><h2>🔄 Vəziyyət <span class="small">(klik→filtr)</span></h2>${cbars(condC,['Yeni','İkinci əl'],x=>x,'cond')}</div></div>`+
   `<div class="panel muted" style="text-align:center;line-height:1.6">💡 <b>«Büdcəyə görə ən yaxşı parametrlər»</b> və <b>«parametrə görə ən ucuz məhsullar»</b> artıq hər kateqoriyanın <b>«📊 Alt-kateqoriya analizi»</b> tabındadır — hər alt-kateqoriya ayrıca. Yuxarıdakı kateqoriyaya klikləyib bax.</div>`;
  bindCbars();
 } else if(v==='best'){
  title='⭐ Ən uyğun modellər';sub='hər kateqoriya üçün ən yaxşı dəyər';
  let hInner='';
  META.cats.forEach(c=>{
   const rows=DATA.filter(r=>r.category===c.slug);
   const gaming=bestList(rows.filter(r=>r.usage==='Gaming'),8);
   const ofis=bestList(rows.filter(r=>r.usage!=='Gaming'),8);
   hInner+=`<div class="panel"><h2>${c.label}</h2>`;
   if(gaming.length)hInner+=`<h3 class="small">🎮 Gaming</h3>${miniTable(gaming,true)}`;
   hInner+=`<h3 class="small" style="margin-top:10px">${gaming.length?'💼 Ofis / digər':'Ən yaxşı dəyər'}</h3>${miniTable(ofis)}</div>`;
  });
  root.innerHTML=hInner;
 } else if(v==='new'){
  title='🆕 Yeni məhsullar';const base=DATA.filter(r=>r.new);const fr=filtered(base);const rows=sortRows(fr);sub=`${base.length} elan bu skanda · ${rows.length} göstərilir`;
  root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true)}<div class="tblwrap">${tableHTML(rows)}</div>${pager(rows.length)}</div>`;
  bindFilters();bindTable();bindPager();
 } else if(v==='table'){
  const cm=META.cats.find(c=>c.slug===state.cat);title=cm?cm.label:'Bütün elanlar';
  const fr=filtered(DATA);
  const tabs=cm?`<div class="subtabs">
    <button class="stab ${state.catTab==='table'?'on':''}" data-tab="table">📋 Cədvəl</button>
    <button class="stab ${state.catTab==='budget'?'on':''}" data-tab="budget">💰 Büdcə üzrə</button>
    <button class="stab ${state.catTab==='param'?'on':''}" data-tab="param">🎯 Parametr üzrə</button>
    <button class="stab ${state.catTab==='analiz'?'on':''}" data-tab="analiz">📊 Alt-kateqoriya analizi</button></div>`:'';
  if(cm&&state.catTab==='analiz'){
   sub=`${fr.length} nəticə · alt-kateqoriyalar üzrə ən yaxşılar`;
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true)}${tabs}</div>`+catAnalysis(state.cat);
   bindFilters();bindSubtabs();
  } else if(cm&&state.catTab==='budget'){
   sub=`hər qiymət aralığı ayrıca`;
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true,true)}${tabs}</div>`+budgetView(state.cat);
   bindFilters();bindSubtabs();bindCondMode();bindBandPagers();
  } else if(cm&&state.catTab==='param'){
   sub=`CPU / RAM / VGA üzrə ən sərfəli qiymət`;
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true,true)}${tabs}</div>`+paramView(state.cat);
   bindFilters();bindSubtabs();bindParamSel();bindCondMode();bindBandPagers();
  } else {
   const rows=sortRows(fr);sub=`${rows.length} nəticə`;
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true)}${tabs}<div class="tblwrap">${tableHTML(rows)}</div>${pager(rows.length)}</div>`;
   bindFilters();bindSubtabs();bindTable();bindPager();
  }
 } else if(v==='analysis'){
  title='📈 Parametr analizi';sub='hər dəyər üçün ən ucuz / orta / ən bahalı';
  const scoped=DATA.filter(r=>r.value_score!=null && (state.cat?r.category===state.cat:true));
  root.innerHTML=`<div class="panel">${filtersBar(true)}</div>`+
   analysisPanel('RAM (GB)','ram',scoped,v=>v+' GB',(a,b)=>b-a)+
   analysisPanel('CPU ailəsi','cpu_fam',scoped)+
   analysisPanel('Yaddaş','storage',scoped);
  bindFilters();
 } else if(v==='stars'){
  title='⭐ Seçilmişlər';const rows=sortRows(DATA.filter(r=>STAR.has(r.id)));sub=`${rows.length} qeyd olunmuş`;
  root.innerHTML=rows.length?`<div class="panel"><div class="tblwrap">${tableHTML(rows)}</div>${pager(rows.length)}</div>`:'<div class="panel muted">Hələ heç nə seçməmisən. Cədvəldə ★ ulduza kliklə.</div>';
  bindTable();if(rows.length)bindPager();
 }
 $('#vtitle').textContent=title;$('#vsub').textContent=sub;
}
function analysisPanel(title,key,rows,fmtk=x=>x,cmp){
 const groups={};rows.forEach(r=>{const v=r[key];if(v==null||v===''||v===0)return;if(r.price)(groups[v]=groups[v]||[]).push(r);});
 let ks=Object.keys(groups);ks.sort(cmp||((a,b)=>groups[b].length-groups[a].length));
 const body=ks.map(k=>{const g=groups[k].slice().sort((a,b)=>a.price-b.price);const lo=g[0],mid=g[(g.length/2)|0],hi=g[g.length-1];
  const cell=r=>`<a href="${esc(r.link)}" target="_blank">${fmt(r.price)}₼</a><div class="small">${esc((r.name||'').slice(0,28))}</div>`;
  return `<tr><td><b>${esc(fmtk(k))}</b></td><td class="num">${g.length}</td><td>${cell(lo)}</td><td>${cell(mid)}</td><td>${cell(hi)}</td></tr>`;}).join('');
 return `<div class="panel"><h2>${title} üzrə</h2><table><thead><tr><th>Dəyər</th><th>Say</th><th>Ən ucuz</th><th>Orta</th><th>Ən bahalı</th></tr></thead><tbody>${body}</tbody></table></div>`;
}
buildNav();go('overview');
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==$('#q')){e.preventDefault();$('#q').focus();}});
</script></body></html>"""
