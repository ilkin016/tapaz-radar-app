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
:root{--bg:#eef2f7;--panel:#fff;--ink:#111827;--muted:#6b7280;--line:#e3e8ef;--acc:#1f4e79;--acc2:#2563eb;
 --good:#15803d;--bad:#b91c1c;--warn:#b45309;--chip:#f1f5f9}
@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--panel:#111a29;--ink:#e5edf6;--muted:#93a1b3;--line:#1f2c3f;
 --acc:#5b9bd5;--acc2:#60a5fa;--chip:#182234}}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink);font-size:13px}
.app{display:grid;grid-template-columns:210px 1fr;height:100vh}
.side{background:var(--panel);border-right:1px solid var(--line);padding:14px 10px;overflow:auto}
.brand{font-weight:800;font-size:15px;padding:6px 8px 12px;letter-spacing:.2px}
.brand small{display:block;color:var(--muted);font-weight:500;font-size:11px;margin-top:2px}
.nav{display:flex;flex-direction:column;gap:2px}
.nav button{all:unset;cursor:pointer;padding:9px 10px;border-radius:8px;color:var(--ink);font-size:13px;display:flex;justify-content:space-between;align-items:center}
.nav button:hover{background:var(--chip)}.nav button.on{background:var(--acc);color:#fff}
.nav .cnt{font-size:11px;opacity:.7}
.nav .sep{margin:8px 6px 4px;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}
.main{overflow:auto;padding:16px 18px}
.top{display:flex;gap:12px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.top h1{font-size:18px;margin:0}.top .sub{color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:16px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}.app{grid-template-columns:1fr}.side{position:fixed;z-index:9;height:100%;transform:translateX(-100%);transition:.2s}.side.open{transform:none}}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.kpi .l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.kpi .n{font-size:22px;font-weight:800;margin-top:3px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:16px}
.panel h2{font-size:14px;margin:0 0 10px}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
input,select{padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink);font-size:12.5px}
input:focus,select:focus{outline:2px solid var(--acc2);border-color:transparent}
.qs{display:flex;gap:4px;flex-wrap:wrap}
.qs button,.chip{all:unset;cursor:pointer;padding:6px 10px;border:1px solid var(--line);border-radius:20px;font-size:12px;background:var(--chip)}
.qs button.on,.chip.on{background:var(--acc2);color:#fff;border-color:transparent}
table{width:100%;border-collapse:collapse}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--panel);cursor:pointer;user-select:none;font-size:10.5px;text-transform:uppercase;color:var(--muted);white-space:nowrap}
th.arrow::after{content:' ▾';color:var(--acc2)}th.arrowup::after{content:' ▴';color:var(--acc2)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.small{color:var(--muted);font-size:11.5px}
.val{font-weight:800;padding:2px 6px;border-radius:6px;color:#fff;display:inline-block;min-width:34px;text-align:center}
.shop{color:var(--good);font-weight:600}.priv{color:var(--warn);font-weight:600}
.tg{border-radius:6px;padding:1px 6px;font-size:10px;font-weight:700}
.tg.new{background:#dcfce7;color:#15803d}.tg.g{background:#f3e8ff;color:#7e22ce}.tg.o{background:#dbeafe;color:#1d4ed8}
a{color:var(--acc2);text-decoration:none}a:hover{text-decoration:underline}
.star{cursor:pointer;color:#cbd5e1;font-size:15px}.star.on{color:#f59e0b}
.tblwrap{max-height:calc(100vh - 250px);overflow:auto;border:1px solid var(--line);border-radius:10px}
.bars .bar{display:grid;grid-template-columns:130px 1fr 44px;gap:8px;align-items:center;margin:4px 0;font-size:12px}
.bars .bt{background:var(--chip);border-radius:6px;height:13px;overflow:hidden}.bars .bt i{display:block;height:100%;background:var(--acc)}
.bars .bv{text-align:right;color:var(--muted)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.catcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}
.catcard{background:var(--chip);border:1px solid var(--line);border-radius:12px;padding:14px;cursor:pointer}
.catcard:hover{border-color:var(--acc2)}.catcard .b{font-size:22px;font-weight:800}
.muted{color:var(--muted)}.hide{display:none}
.count{color:var(--muted);font-weight:400;font-size:12px}
.mtoggle{display:none}@media(max-width:900px){.mtoggle{display:inline-block}}
</style></head><body>
<div class="app">
 <aside class="side" id="side">
  <div class="brand">tap.az RADAR<small id="brsub"></small></div>
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
 pram:'',pcpu:'',pstor:'',pscr:'',pgpu:'',sortKey:'value_score',sortDir:-1};
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
 if(k.startsWith('cat:')){state.view='table';state.cat=k.slice(4);state.sub='';}
 else {state.view=k;if(k!=='table')state.cat='';}
 [...$('#nav').children].forEach(b=>b.classList&&b.classList.toggle('on',b.dataset&&b.dataset.k===k));
 render();window.scrollTo(0,0);
}

// ---------- filtering / sorting ----------
function filtered(base){
 const q=state.q.toLowerCase();
 return base.filter(r=>{
  if(state.cat&&r.category!==state.cat)return false;
  if(state.sub&&r.subcategory!==state.sub)return false;
  if(state.cond&&r.condition!==state.cond)return false;
  if(state.seller&&r.seller_type!==state.seller)return false;
  if(state.usage&&r.usage!==state.usage)return false;
  if(state.brand&&r.brand!==state.brand)return false;
  if(state.pram&&(''+r.ram)!==state.pram)return false;
  if(state.pcpu&&r.cpu_fam!==state.pcpu)return false;
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
 const shown=rows.slice(0,400);
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
 return `<table><thead>${head}</thead><tbody>${body}</tbody></table>`
  +(rows.length>400?`<div class="small" style="padding:8px">${rows.length} nəticədən ilk 400 göstərilir — filtrlə daralt.</div>`:'');
}
function bindTable(){
 $('#root').querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;
  if(state.sortKey===k)state.sortDir*=-1;else{state.sortKey=k;state.sortDir=(k==='name'||k==='brand'||k==='seller_type')?1:-1;}render();});
 $('#root').querySelectorAll('.star').forEach(s=>s.onclick=()=>{const id=s.dataset.id;
  if(STAR.has(id))STAR.delete(id);else STAR.add(id);store.set(STAR);render();});
}
function filtersBar(withCat){
 const subs=(state.cat&&META.subs[state.cat])||[];
 const cat=state.cat;
 const psel=(id,field,label,cur,numeric,suffix='')=>{let vals=distinct(field,cat);if(!vals.length)return '';
  vals.sort(numeric?((a,b)=>b-a):((a,b)=>(''+a).localeCompare(''+b,'az')));
  return `<select id="${id}"><option value="">${label}: hamısı</option>`+vals.map(v=>`<option value="${esc(''+v)}" ${cur===(''+v)?'selected':''}>${esc(''+v)}${suffix}</option>`).join('')+`</select>`;};
 const gpuVals=distinct('gpu',cat).sort((a,b)=>(''+a).localeCompare(''+b));
 const gpuSel=gpuVals.length?`<select id="f_pgpu"><option value="">Video kart: hamısı</option><option value="__has" ${state.pgpu==='__has'?'selected':''}>✓ var (diskret)</option><option value="__no" ${state.pgpu==='__no'?'selected':''}>— yox</option>${gpuVals.map(v=>`<option value="${esc(v)}" ${state.pgpu===v?'selected':''}>${esc(v)}</option>`).join('')}</select>`:'';
 const paramRow=`<div class="controls" style="margin-top:-4px">
  <span class="small" style="align-self:center;font-weight:700">⚙️ Parametrlər:</span>
  ${psel('f_pram','ram','RAM',state.pram,true,' GB')}
  ${psel('f_pcpu','cpu_fam','CPU',state.pcpu,false)}
  ${psel('f_pstor','storage','Yaddaş',state.pstor,false)}
  ${psel('f_pscr','screen','Ekran',state.pscr,true,'"')}
  ${gpuSel}
 </div>`;
 return `<div class="controls">
  ${withCat?`<select id="f_cat"><option value="">Kateqoriya: hamısı</option>${META.cats.map(c=>`<option value="${c.slug}" ${state.cat===c.slug?'selected':''}>${c.label}</option>`).join('')}</select>`:''}
  ${subs.length?`<select id="f_sub"><option value="">Alt-kateqoriya: hamısı</option>${subs.map(s=>`<option ${state.sub===s?'selected':''}>${esc(s)}</option>`).join('')}</select>`:''}
  <select id="f_usage"><option value="">İstifadə</option><option>Gaming</option><option>Ofis / Gündəlik</option></select>
  <select id="f_cond"><option value="">Vəziyyət</option><option>Yeni</option><option>İkinci əl</option></select>
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
 const set=(id,key)=>{const e=$('#'+id);if(e)e.onchange=()=>{state[key]=e.value;
  if(key==='cat'){state.sub='';state.pram='';state.pcpu='';state.pstor='';state.pscr='';state.pgpu='';}render();};};
 set('f_cat','cat');set('f_sub','sub');set('f_usage','usage');set('f_cond','cond');set('f_seller','seller');set('f_brand','brand');
 set('f_pram','pram');set('f_pcpu','pcpu');set('f_pstor','pstor');set('f_pscr','pscr');set('f_pgpu','pgpu');
 const pn=$('#f_pmin'),px=$('#f_pmax');if(pn)pn.oninput=()=>{state.pmin=pn.value;render();};if(px)px.oninput=()=>{state.pmax=px.value;render();};
 const fn=$('#f_new');if(fn)fn.onchange=()=>{state.onlyNew=fn.checked;render();};
 $('#root').querySelectorAll('.qs button').forEach(b=>b.onclick=()=>{const s=b.dataset.sort;
  if(s==='price_asc'){state.sortKey='price';state.sortDir=1;}else if(s==='price_desc'){state.sortKey='price';state.sortDir=-1;}
  else{state.sortKey='value_score';state.sortDir=-1;}render();});
 const cl=$('#f_clear');if(cl)cl.onclick=()=>{Object.assign(state,{sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,
  pram:'',pcpu:'',pstor:'',pscr:'',pgpu:''});render();};
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

function render(){
 $('#q').oninput=()=>{state.q=$('#q').value;render1();};
 render1();
}
function render1(){
 const root=$('#root');const v=state.view;
 let title='İcmal',sub='';
 if(v==='overview'){
  title='İcmal';sub=`${META.n_total} elan · ${META.n_new} yeni`;
  const scored=DATA.filter(r=>r.value_score!=null);
  const bandc=countBy(scored,'band');const bandord=Object.keys(bandc).sort((a,b)=>(parseInt(a)||0)-(parseInt(b)||0));
  root.innerHTML=kpiStrip(DATA)+
   `<div class="panel"><h2>Kateqoriyalar</h2><div class="catcards">${META.cats.map(c=>`<div class="catcard" onclick="go('cat:${c.slug}')"><div>${c.label}</div><div class="b">${c.n}</div><div class="muted">bax →</div></div>`).join('')}</div></div>`+
   `<div class="grid2"><div class="panel"><h2>Qiymət aralığı üzrə</h2>${bars(bandc,bandord,k=>k+' ₼')}</div>
    <div class="panel"><h2>Brend üzrə</h2>${bars(countBy(scored,'brand'),null,x=>x,10)}</div></div>`;
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
  title='🆕 Yeni məhsullar';const rows=DATA.filter(r=>r.new);sub=`${rows.length} elan bu skanda`;
  root.innerHTML=kpiStrip(rows)+`<div class="panel">${filtersBar(true)}<div class="tblwrap">${tableHTML(sortRows(filtered(rows)))}</div></div>`;
  bindFilters();bindTable();
 } else if(v==='table'){
  const cm=META.cats.find(c=>c.slug===state.cat);title=cm?cm.label:'Bütün elanlar';
  const rows=sortRows(filtered(DATA));sub=`${rows.length} nəticə`;
  root.innerHTML=kpiStrip(filtered(DATA))+`<div class="panel">${filtersBar(true)}<div class="tblwrap">${tableHTML(rows)}</div></div>`;
  bindFilters();bindTable();
 } else if(v==='analysis'){
  title='📈 Parametr analizi';sub='hər dəyər üçün ən ucuz / orta / ən bahalı';
  const scoped=DATA.filter(r=>r.value_score!=null && (state.cat?r.category===state.cat:true));
  root.innerHTML=`<div class="panel">${filtersBar(true)}</div>`+
   analysisPanel('RAM (GB)','ram',scoped,v=>v+' GB',(a,b)=>b-a)+
   analysisPanel('CPU ailəsi','cpu_fam',scoped)+
   analysisPanel('Yaddaş','storage',scoped);
  bindFilters();
 } else if(v==='stars'){
  title='⭐ Seçilmişlər';const rows=DATA.filter(r=>STAR.has(r.id));sub=`${rows.length} qeyd olunmuş`;
  root.innerHTML=rows.length?`<div class="panel"><div class="tblwrap">${tableHTML(sortRows(rows))}</div></div>`:'<div class="panel muted">Hələ heç nə seçməmisən. Cədvəldə ★ ulduza kliklə.</div>';
  bindTable();
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
