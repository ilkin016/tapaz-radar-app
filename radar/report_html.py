#!/usr/bin/env python3
"""Interactive single-page dashboard (self-contained, vanilla JS). Fast filter/sort, views, shortlists."""
import json, html, re
from collections import Counter

_GAMING_MON_KW = re.compile(r"gaming|oyun|curved|\brog\b|\btuf\b|odyssey|predator|\bnitro\b|\bmag\b|aorus|g.?sync|freesync|\bvg\d|\bxg\b", re.I)


def _monitor_usage(name, params):
    """Monitoru Gaming (≥100Hz və ya gaming işarələri) vs Ofis olaraq təsnif et."""
    text = (name or "") + " " + (params or "")
    m = re.search(r"(\d{2,3})\s*hz", text, re.I)
    hz = int(m.group(1)) if m else 0
    if hz >= 100:
        return "Gaming"
    if 0 < hz <= 75:
        return "Ofis / Gündəlik"
    return "Gaming" if _GAMING_MON_KW.search(text) else "Ofis / Gündəlik"


CAT_LABELS = {
    "noutbuklar": "💻 Noutbuklar",
    "komputerler": "🖥 Komputerlər",
    "komputer-avadanliqi": "🧩 Komponent/Monitor",
    "komputer-aksesuarlari": "🖱 Aksesuarlar",
    "ofis-avadanliqi": "🖨 Ofis avadanlığı",
}


def build_html(listings, new_now, run_ts, path, public=False, cat_last=None):
    """public=True → seller phone numbers omitted (privacy for online/GitHub Pages deploy).
    cat_last: {category: son_uğurlu_run_ts} — hər kateqoriya üzrə freshness göstərmək üçün."""
    from radar import comp_specs
    cat_last = cat_last or {}
    new_ids = {r["ad_id"] for r in new_now}
    keys = ("id", "name", "brand", "price", "band", "spec_score", "value_score", "cpu", "cpu_fam",
            "ram", "storage", "screen", "gpu", "os", "usage", "condition", "category", "subcategory",
            "seller_type", "seller", "phones", "link", "params")
    data = []
    for r in listings:
        d = {k: r.get(k) for k in keys}
        if r.get("category") == "komputer-avadanliqi":
            if r.get("subcategory") == "Monitor":
                d["usage"] = _monitor_usage(r.get("name"), r.get("params"))  # monitorları Gaming/Ofis-ə ayır
            cs = comp_specs.component_specs(r.get("subcategory"), r.get("name"), r.get("params"))
            if cs:
                d.update(cs)  # kateqoriya-spesifik filtr sahələri (cpu/ram/gpu/ssd/mobo/monitor)
        if public:
            d["phones"] = ""  # do not expose seller phone numbers on a public URL
        d["new"] = 1 if r["ad_id"] in new_ids else 0
        data.append(d)
    cats = [c for c in Counter(r.get("category") for r in listings).keys() if c]
    cat_meta = [{"slug": c, "label": CAT_LABELS.get(c, c),
                 "n": sum(1 for r in listings if r.get("category") == c),
                 "last": (cat_last.get(c) or "")[:10]} for c in cats]
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
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#070c15;--panel:#0f1826;--panel2:#0c1421;--ink:#e6eef8;--muted:#8aa0b8;--line:#1d2b3f;
 --acc:#3b82f6;--acc2:#60a5fa;--acc-soft:#14243a;--chip:#152131;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.4)}}
:root[data-theme="dark"]{--bg:#070c15;--panel:#0f1826;--panel2:#0c1421;--ink:#e6eef8;--muted:#8aa0b8;--line:#1d2b3f;
 --acc:#3b82f6;--acc2:#60a5fa;--acc-soft:#14243a;--chip:#152131;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.4)}
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
.stpill{display:inline-flex;align-items:center;gap:9px;background:var(--panel2);border:1.5px solid var(--line);border-radius:13px;padding:8px 13px;cursor:pointer;transition:all .12s;font-weight:600;font-size:13.5px}
.stpill:hover{border-color:var(--acc2);transform:translateY(-1px)}
.stpill.on{border-color:var(--acc2);background:var(--acc-soft);box-shadow:0 0 0 3px rgba(47,86,224,.12)}
.stpill img{width:28px;height:28px;border-radius:50%;object-fit:cover;background:#fff;flex-shrink:0}
.stpill .cnt{background:var(--chip);border-radius:20px;padding:1px 9px;font-size:11px;font-weight:700}
.stpill .rm{opacity:.35;font-size:13px;padding:0 2px;transition:opacity .12s}
.stpill:hover .rm{opacity:.75}
.stcat{background:var(--panel2);border:1px solid var(--line);border-radius:22px;padding:6px 14px;cursor:pointer;font-size:12.5px;font-weight:600;transition:all .1s;white-space:nowrap}
.stcat:hover{border-color:var(--acc2)}
.stcat.on{background:var(--acc2);border-color:var(--acc2);color:#fff}
.stcat .cnt{opacity:.7;font-weight:700;margin-left:4px}
.stcard{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:var(--panel);transition:transform .12s,box-shadow .12s,border-color .12s;position:relative}
.stcard:hover{transform:translateY(-3px);box-shadow:0 10px 22px rgba(37,99,235,.14);border-color:var(--acc2)}
.stcard .iw{height:150px;background:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden;cursor:zoom-in}
.stcard .iw img{width:100%;height:100%;object-fit:contain}
.stcard .ck{position:absolute;top:9px;left:9px;z-index:2;width:20px;height:20px;cursor:pointer}
.stcard .zm{position:absolute;top:8px;right:8px;z-index:2;background:rgba(15,23,42,.62);color:#fff;border-radius:8px;padding:3px 8px;font-size:11px;font-weight:600;opacity:0;transition:opacity .12s;pointer-events:none}
.stcard:hover .zm{opacity:1}
.stbody{padding:9px 11px}
.stbody .t{font-weight:700;line-height:1.25;height:34px;overflow:hidden;font-size:13px;cursor:pointer}
.stbody .p{font-weight:800;color:var(--acc2);margin-top:3px;font-size:15px}
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
   <input id="q" placeholder="🔎 Axtar (ad, parametr, satıcı)…" style="min-width:200px">
   <button class="chip" id="themebtn" title="Tema" onclick="cycleTheme()" style="font-size:15px">🌓</button>
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
function applyTheme(t){const r=document.documentElement;if(t==='light'||t==='dark')r.setAttribute('data-theme',t);else r.removeAttribute('data-theme');const b=document.getElementById('themebtn');if(b)b.textContent=t==='light'?'☀️':(t==='dark'?'🌙':'🌓');}
function cycleTheme(){const c=localStorage.getItem('radar_theme')||'system';const n=c==='system'?'light':(c==='light'?'dark':'system');localStorage.setItem('radar_theme',n);applyTheme(n);}
applyTheme(localStorage.getItem('radar_theme')||'system');
function daysAgo(d){if(!d)return null;const t=new Date(d+'T00:00:00'),n=new Date();return Math.floor((n-t)/86400000);}
function staleBadge(d){const a=daysAgo(d);if(a==null)return '';return a>2?` <span style="color:var(--bad);font-weight:700">⚠️ ${a} gün köhnə</span>`:(a<=0?` <span style="color:var(--good);font-weight:700">✓ bu gün</span>`:` <span class="muted">${a} gün əvvəl</span>`);}
{const dts=META.cats.map(c=>c.last).filter(Boolean).sort();const oldest=dts[0]||META.run_ts.slice(0,10),newest=dts[dts.length-1]||oldest;
 $('#brsub').innerHTML=`${fmt(META.n_total)} elan · ${META.n_new} 🆕 · son skan ${newest}`+(oldest!==newest?` <span style="color:var(--bad)">(ən köhnə ${oldest})</span>`:'');}

const state={view:'overview',cat:'',sub:'',cond:'',seller:'',usage:'',brand:'',pmin:'',pmax:'',onlyNew:false,q:'',
 pram:'',pcpu:'',pcgen:'',pcser:'',pstor:'',pscr:'',pgpu:'',sortKey:'value_score',sortDir:-1,page:0,ps:50,catTab:'table',bandPages:{},paramTab:'ram',condMode:'yeni',budgetSub:'',cf:{}};
function distinct(field,cat){const s=new Set();DATA.forEach(r=>{if(cat&&r.category!==cat)return;const v=r[field];if(v!=null&&v!=='')s.add(v);});return [...s];}

// ---------- navigation ----------
const NAV=[['overview','📊 İcmal'],['best','⭐ Ən uyğun'],['new','🆕 Yeni'],['SEP','Kateqoriyalar'],
 ...META.cats.map(c=>['cat:'+c.slug,c.label,c.n]),['SEP','Alətlər'],
 ['analysis','📈 Parametr analizi'],['stars','⭐ Seçilmişlər'],['SEP','İdarəetmə (backend)'],
 ['admin','🛠 Repost / Yenilə'],['stores','🏪 Mağazalar'],['design','🎨 Kart dizaynı'],['settings','⚙️ Tənzimləmələr'],['users','👥 İstifadəçilər']];
function buildNav(){
 const n=$('#nav');n.innerHTML='';
 const _isAdm=BACKEND&&BACKEND.sys&&BACKEND.sys.role==='admin';
 NAV.forEach(item=>{
  if(!BACKEND && (item[0]==='admin'||item[0]==='stores'||item[0]==='settings'||item[0]==='users'||item[0]==='design' || item[1]==='İdarəetmə (backend)'))return; // backend yoxdursa gizlət
  if((item[0]==='settings'||item[0]==='users'||item[0]==='design')&&!_isAdm)return; // yalnız admin girişində
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
function filtered(base,skipSub,skipCond,skipBrand){
 const q=state.q.toLowerCase();
 return base.filter(r=>{
  if(state.cat&&r.category!==state.cat)return false;
  if(!skipSub&&state.sub&&r.subcategory!==state.sub)return false;
  if(!skipCond&&state.cond&&r.condition!==state.cond)return false;
  if(state.seller&&r.seller_type!==state.seller)return false;
  if(state.usage&&r.usage!==state.usage)return false;
  if(!skipBrand&&state.brand&&r.brand!==state.brand)return false;
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
function filtersBar(withCat,hideCond,hideSub){
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
  ${hideSub||!subs.length?'':`<select id="f_sub"><option value="">Alt-kateqoriya: hamısı</option>${subs.map(s=>`<option ${state.sub===s?'selected':''}>${esc(s)}</option>`).join('')}</select>`}
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
function usageTag(r){return r.usage==='Gaming'?'<span class="tg g">🎮 Gaming</span>':(r.usage==='Ofis / Gündəlik'?'<span class="tg o">💼 Ofis</span>':'');}
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
 const subsAll=META.subs[cat]||[];
 let base=applyCondMode(filtered(DATA,true,true).filter(r=>+r.price>=1)); // sub+cond burada idarə olunur; <1₼ = metrlə kabel küy
 // Alt-kateqoriya ayrımı — çox-alt-kateqoriyalı kateqoriyalarda (məs. Komponent/Monitor) hər alt-kat AYRICA
 let subSel='',bsub=state.budgetSub;
 if(subsAll.length>1){
  const cnt={};base.forEach(r=>{const s=r.subcategory||'Digər';cnt[s]=(cnt[s]||0)+1;});
  const ord=Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]);
  if(bsub!=='__all'&&!ord.includes(bsub))bsub=ord[0]; // default: ən böyük alt-kateqoriya (qarışıq deyil)
  subSel=`<div class="panel" style="padding:11px 14px;margin-bottom:12px"><div class="controls" style="margin:0"><span class="small" style="align-self:center;font-weight:700">📂 Alt-kateqoriya:</span>`
   +`<button class="chip ${bsub==='__all'?'on':''}" data-bs="__all">🔀 Hamısı</button>`
   +ord.map(s=>`<button class="chip ${bsub===s?'on':''}" data-bs="${esc(s)}">${esc(s)} <span class="small">${cnt[s]}</span></button>`).join('')
   +`</div></div>`;
  if(bsub!=='__all')base=base.filter(r=>(r.subcategory||'Digər')===bsub);
 }
 const sig=JSON.stringify(['B',state.condMode,bsub,state.cat,state.seller,state.usage,state.brand,state.pmin,state.pmax,state.onlyNew,state.pram,state.pcpu,state.pcgen,state.pcser,state.pstor,state.pscr,state.pgpu,state.q,state.sortKey,state.sortDir]);
 if(state._bsig!==sig){state.bandPages={};state._bsig=sig;}
 const scoredCat=base.some(r=>r.value_score!=null); // laptop/desktop/spec'd komponent → keyfiyyət filtri; aksesuar/ofis → hamısı
 if(scoredCat)base=base.filter(r=>r.value_score!=null);
 const g={};base.forEach(r=>{const b=band200(r.price);if(!b)return;(g[b]=g[b]||[]).push(r);});
 const bands=Object.keys(g).sort((a,b)=>(a==='2000+'?1e9:parseInt(a))-(b==='2000+'?1e9:parseInt(b)));
 const note=subSel+`<div class="panel" style="padding:12px 14px;margin-bottom:12px">${condModeBar()}<span class="small">💡 Alt-kateqoriya + vəziyyət seç: <b>Yalnız Yeni</b> / <b>Yeni + İkinci əl</b> (qarışıq) / <b>Yalnız İkinci əl</b>. Hər qiymət aralığı ayrıca səhifələnir.</span></div>`;
 if(!bands.length)return note+'<div class="panel muted">Bu seçim üçün məhsul yoxdur.</div>';
 const maxSpec=Math.max(1,...base.map(r=>r.spec_score||0));
 const PS=15;
 const bhead=`<thead><tr><th>Model</th><th>Qiymət</th><th>Güc</th><th>Vəziyyət</th><th>Satıcı</th><th>Telefon</th></tr></thead>`;
 let out=note;
 bands.forEach(b=>{
  const items=scoredCat?sortRows(g[b]):g[b].slice().sort((x,y)=>(x.price||1e9)-(y.price||1e9));
  const pages=Math.max(1,Math.ceil(items.length/PS));
  let pg=state.bandPages[b]||0;if(pg>=pages)pg=pages-1;if(pg<0)pg=0;
  const slice=items.slice(pg*PS,pg*PS+PS);
  const wp=items.filter(r=>r.price);const avg=wp.length?wp.reduce((a,c)=>a+c.price,0)/wp.length:0;
  const rows=slice.map(r=>{const guc=(scoredCat&&r.spec_score)?`<div class="pwwrap"><div class="pw"><i style="width:${Math.max(4,Math.round(r.spec_score/maxSpec*100))}%"></i></div><span class="pwn">${Math.round(r.spec_score/maxSpec*100)}</span></div>`:'<span class="small">—</span>';
   return `<tr>
    <td><a href="${esc(r.link)}" target="_blank">${esc((r.name||'').slice(0,52))}</a>${r.new?' <span class="tg new">🆕</span>':''} ${usageTag(r)}${specChips(r)}</td>
    <td class="num"><b>${fmt(r.price)} ₼</b></td>
    <td>${guc}</td>
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
 if(!keys.length)return sel+'<div class="panel muted">CPU/RAM/VGA struktur parametrləri yalnız <b>noutbuk və masaüstü</b> üçün mövcuddur. Komponentlərdə (monitor, SSD, video kart və s.) parametrə görə ən ucuz məhsullar üçün <b>«📊 Alt-kateqoriya analizi»</b> tabından istifadə et.</div>';
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
    <td><a href="${esc(r.link)}" target="_blank">${esc((r.name||'').slice(0,52))}</a>${r.new?' <span class="tg new">🆕</span>':''} ${usageTag(r)}${specChips(r)}</td>
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
function bindBudgetSub(){$('#root').querySelectorAll('[data-bs]').forEach(b=>b.onclick=()=>{state.budgetSub=b.dataset.bs;state.bandPages={};state.brand='';state.cf={};state.page=0;render();});}
// Kateqoriya-spesifik kaskad filtrlər (komponentlər üçün) — comp_specs.py sahələri üzərində
const COMP_FACETS={
 'CPU':[{f:'c_brand',l:'Brend'},{f:'c_series',l:'Seriya'},{f:'c_model',l:'Model',lim:24}],
 'Ana plata':[{f:'mb_plat',l:'Platforma'}],
 'RAM':[{f:'ram_type',l:'Tip'},{f:'ram_bucket',l:'Tutum'}],
 'Video kart (GPU)':[{f:'gpu_series',l:'Seriya'},{f:'gpu_model',l:'Model',lim:24}],
 'Sərt disk (SSD/HDD)':[{f:'ssd_iface',l:'Növ'},{f:'ssd_bucket',l:'Həcm'}],
 'Monitor':[{f:'usage',l:'Model'},{f:'mon_oled',l:'Panel',bool:true},{f:'mon_size_b',l:'Ölçü'},{f:'mon_res',l:'Keyfiyyət'},{f:'mon_hz_b',l:'Tezlik'}]
};
function compFacets(bsub, rows0){
 const defs=COMP_FACETS[bsub]||[];if(!defs.length)return {html:'',rows:rows0};
 let s=rows0, html='';
 defs.forEach(d=>{
  const cnt={};
  s.forEach(r=>{let v=r[d.f];if(d.bool){if(!v)return;v='1';}else{if(v==null||v==='')return;v=''+v;}cnt[v]=(cnt[v]||0)+1;});
  let vals=Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]);if(d.lim)vals=vals.slice(0,d.lim);
  if(!vals.length)return;
  const sel=state.cf[d.f]||'';
  const chip=(val,lab,c,on)=>`<button class="chip ${on?'on':''}" data-cf="${d.f}" data-cfv="${esc(val)}">${esc(lab)}${c!=null?` <span class="small">${c}</span>`:''}</button>`;
  html+=`<div class="controls" style="margin:0 0 5px"><span class="small" style="align-self:center;font-weight:700;min-width:78px">${d.l}:</span>`
   +(d.bool?'':chip('','Hamısı',null,!sel))
   +vals.map(v=>chip(v, d.bool?'✓ OLED':v, cnt[v], sel===v)).join('')+`</div>`;
  if(sel)s=s.filter(r=>{let v=r[d.f];if(d.bool)return !!v;if(v==null||v==='')return false;return (''+v)===sel;});
 });
 return {html:html?`<div class="panel" style="padding:11px 14px 6px;margin-bottom:12px"><div class="small" style="font-weight:800;margin-bottom:7px">⚙️ ${esc(bsub)} filtrləri</div>${html}</div>`:'', rows:s};
}
function bindCompFacets(){$('#root').querySelectorAll('[data-cf]').forEach(b=>b.onclick=()=>{const f=b.dataset.cf,v=b.dataset.cfv;state.cf[f]=(state.cf[f]===v)?'':v;state.page=0;render();});}
// Component table view: sub-category chips → brand breakdown → kaskad filtrlər → paginated table
function componentTable(cat){
 let base=filtered(DATA,true,false,true); // alt-kat + brend burada; cond/usage/seller/qiymət/param saxlanır
 const cnt={};base.forEach(r=>{const s=r.subcategory||'Digər';cnt[s]=(cnt[s]||0)+1;});
 const ord=Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]);
 let bsub=state.budgetSub;if(bsub!=='__all'&&!ord.includes(bsub))bsub=ord[0];
 const subChips=`<div class="panel" style="padding:11px 14px;margin-bottom:12px"><div class="controls" style="margin:0"><span class="small" style="align-self:center;font-weight:700">📂 Alt-kateqoriya:</span>`
  +`<button class="chip ${bsub==='__all'?'on':''}" data-bs="__all">🔀 Hamısı</button>`
  +ord.map(s=>`<button class="chip ${bsub===s?'on':''}" data-bs="${esc(s)}">${esc(s)} <span class="small">${cnt[s]}</span></button>`).join('')+`</div></div>`;
 const scoped=(bsub==='__all')?base:base.filter(r=>(r.subcategory||'Digər')===bsub);
 const bcnt={};scoped.forEach(r=>{const b=r.brand||'Digər';bcnt[b]=(bcnt[b]||0)+1;});
 const bord=Object.keys(bcnt).sort((a,b)=>bcnt[b]-bcnt[a]).slice(0,16);
 const brandChips=`<div class="panel" style="padding:11px 14px;margin-bottom:12px"><div class="controls" style="margin:0"><span class="small" style="align-self:center;font-weight:700">🏷 Brend üzrə:</span>`
  +`<button class="chip ${!state.brand?'on':''}" data-brk="">Hamısı ${scoped.length}</button>`
  +bord.map(b=>`<button class="chip ${state.brand===b?'on':''}" data-brk="${esc(b)}">${esc(b)} <span class="small">${bcnt[b]}</span></button>`).join('')+`</div></div>`;
 const afterBrand=state.brand?scoped.filter(r=>r.brand===state.brand):scoped;
 const fac=compFacets(bsub, afterBrand);
 let rows=sortRows(fac.rows);
 return subChips+brandChips+fac.html+`<div class="panel"><div class="tblwrap">${tableHTML(rows)}</div>${pager(rows.length)}</div>`;
}
function bindBrandBreak(){$('#root').querySelectorAll('[data-brk]').forEach(b=>b.onclick=()=>{state.brand=b.dataset.brk;state.cf={};state.page=0;render();});}
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
   `<div class="panel"><h2>Kateqoriyalar <span class="small">— klikləyib bax · 🕒 son yenilənmə tarixi</span></h2><div class="catcards">${META.cats.map(c=>`<div class="catcard" onclick="go('cat:${c.slug}')" style="position:relative"><div>${c.label}</div><div class="b">${fmt(c.n)}</div><div class="muted" style="font-size:11px">🕒 ${c.last||'—'}${staleBadge(c.last)}</div>${BACKEND?`<button onclick="event.stopPropagation();catSync('${c.slug}',this)" title="Bu kateqoriyanı indi yenilə" style="position:absolute;top:10px;right:10px;background:var(--chip);border:1px solid var(--line);border-radius:8px;padding:3px 8px;cursor:pointer;font-size:13px">🔄</button>`:''}</div>`).join('')}</div></div>`+
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
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true,true,true)}${tabs}</div>`+budgetView(state.cat);
   bindFilters();bindSubtabs();bindCondMode();bindBudgetSub();bindBandPagers();
  } else if(cm&&state.catTab==='param'){
   sub=`CPU / RAM / VGA üzrə ən sərfəli qiymət`;
   root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true,true)}${tabs}</div>`+paramView(state.cat);
   bindFilters();bindSubtabs();bindParamSel();bindCondMode();bindBandPagers();
  } else {
   const subsAll=META.subs[state.cat]||[];
   if(cm&&subsAll.length>1){ // komponent kimi çox-alt-kateqoriyalı: alt-kat seçimi + brend təsnifatı + cədvəl
    sub=`alt-kateqoriya + brend + parametr filtrləri`;
    root.innerHTML=kpiStrip(filtered(DATA,true,false,true))+`<div class="panel">${filtersBar(true,false,true)}${tabs}</div>`+componentTable(state.cat);
    bindFilters();bindSubtabs();bindBudgetSub();bindBrandBreak();bindCompFacets();bindTable();bindPager();
   } else {
    const rows=sortRows(fr);sub=`${rows.length} nəticə`;
    root.innerHTML=kpiStrip(fr)+`<div class="panel">${filtersBar(true)}${tabs}<div class="tblwrap">${tableHTML(rows)}</div>${pager(rows.length)}</div>`;
    bindFilters();bindSubtabs();bindTable();bindPager();
   }
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
 } else if(v==='admin'){
  title='🛠 Repost / Yenilə';sub='köhnə elan → draft → təsdiq';
  root.innerHTML=adminView();bindAdmin();
 } else if(v==='settings'){
  title='⚙️ Tənzimləmələr';sub='OpenAI açarı (admin)';
  root.innerHTML=settingsView();bindAdmin();
 } else if(v==='users'){
  title='👥 İstifadəçilər';sub='giriş və rollar (admin)';
  root.innerHTML=usersView();bindAdmin();
 } else if(v==='design'){
  title='🎨 Kart dizaynı';sub='logo · nömrə · rəng · ikon (admin)';
  root.innerHTML=designView();bindDesign();
 } else if(v==='stores'){
  title='🏪 Mağazalar';sub='mağaza məhsulları → birbaşa PCTECH-ə';
  root.innerHTML=storesView();bindStores();
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
// ---------- Backend (Mac-local): auto-refresh + posting ----------
let BACKEND=null;
async function api(path,opts){try{const r=await fetch(path,opts);return await r.json();}catch(e){return {error:''+e};}}
async function checkBackend(){const s=await api('/api/status');BACKEND=(s&&s.ok)?s:false;return BACKEND;}
function _sysGate(){ // authorized olmayanda HTML qaytarır, olanda ''
 if(!BACKEND)return `<div class="panel muted" style="line-height:1.7">⚠️ Bu funksiya yalnız <b>Mac-local backend</b> ilə işləyir (Cloudflare VPS-i tap.az-a buraxmır).<br>Terminalda: <code>./run_backend.sh</code> → <b>http://127.0.0.1:8091/</b> (və ya sslip URL).</div>`;
 if(!BACKEND.sys)return `<div class="panel"><h2>🔐 Sistemə giriş</h2>
   <div class="controls"><input id="s_user" value="admin" placeholder="istifadəçi adı" style="width:160px"><input id="s_pw" type="password" placeholder="parol" style="width:160px" onkeydown="if(event.key==='Enter')document.getElementById('s_login').click()"><button class="chip on" id="s_login">Giriş</button></div>
   <div class="small" id="s_msg" style="margin-top:6px"></div>
   <div class="small muted">İstifadəçi adı: <b>admin</b> · parol Mac-də <code>data/first_admin.txt</code> faylındadır.<br>⚠️ Bu <b>telefon girişi deyil</b> — telefon+SMS tap.az bölməsi bu girişdən <b>sonra</b> görünür.</div></div>`;
 return '';
}
function _sysHead(){const su=BACKEND.sys;return `<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px"><div>👤 <b>${esc(su.username)}</b> <span class="chip" style="cursor:default;background:var(--acc-soft)">${esc(su.role)}</span></div><button class="chip" id="s_logout">Sistemdən çıxış</button></div></div>`;}
function _adminOnly(what){return `<div class="panel muted">🔒 <b>${what}</b> yalnız <b>admin</b> rolu üçündür. Sən <b>operator</b> kimi girmisən.</div>`;}
// ---- 1) Repost / Yenilə səhifəsi ----
function adminView(){
 const gate=_sysGate();if(gate)return gate;
 const _lasts=META.cats.map(c=>c.last).filter(Boolean).sort();const _newestL=_lasts[_lasts.length-1]||'—';const _rr=BACKEND.refresh&&BACKEND.refresh.running;
 const refresh=`<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
   <div><h2 style="margin:0">🔄 Məlumatları yenilə</h2><div class="small muted">tap.az-dan bütün kateqoriyalar yenidən taranır · 🕒 son skan: <b>${esc(_newestL)}</b></div></div>
   <button class="chip on" id="r_now"${_rr?' disabled':''}>${_rr?'🔄 Yenilənir…':'🔄 İndi yenilə'}</button>
  </div><div class="small" id="r_msg" style="margin-top:6px">${_rr?'🔄 Hazırda yenilənir… (bir neçə dəqiqə çəkə bilər)':''}</div></div>`;
 const li=BACKEND.logged_in;
 const tlogin=li
  ?`<div class="panel"><h2>🔓 tap.az girişi edilib</h2><div class="controls"><span class="small">tap.az: <b>${esc(BACKEND.user||'—')}</b></span><button class="chip" id="a_logout">tap.az çıxış</button></div></div>`
  :`<div class="panel"><h2>🔑 tap.az girişi (OTP)</h2>
     <div class="controls"><input id="a_phone" placeholder="0XX XXX XX XX" style="width:180px"><button class="chip on" id="a_send">📩 Kod göndər</button></div>
     <div class="controls" id="a_coderow" style="display:none"><input id="a_code" placeholder="SMS kodu" style="width:140px"><button class="chip on" id="a_verify">✓ Təsdiqlə</button></div>
     <div class="small" id="a_authmsg" style="margin-top:4px"></div>
     <div class="small muted">Kod SƏNİN telefonuna gəlir və SƏN daxil edirsən (təhlükəsizlik).</div></div>`;
 const repost=`<div class="panel"><h2>📥 Elan gətir — BİZİM sistemə</h2>
   <div class="controls"><input id="a_lid" placeholder="Tək elan nömrəsi (məs 48251733)" style="width:230px">
    <button class="chip" id="a_preview">👁 Önizləmə</button><button class="chip on" id="a_post">📥 Gətir</button></div>
   <div id="a_result" style="margin-top:8px"></div>
   <details style="margin-top:12px"><summary style="cursor:pointer;font-weight:700">📚 Toplu əlavə (çoxlu link/kod) + Excel import</summary>
    <div style="margin-top:8px"><textarea id="a_bulk" placeholder="Bir neçə link və ya kod — hər sətirdə bir, və ya vergüllə&#10;48251733&#10;https://tap.az/elanlar/.../48443132&#10;48123456, 48987654" style="width:100%;min-height:88px;font-family:monospace;font-size:12px"></textarea>
     <div class="controls" style="margin-top:6px"><button class="chip on" id="a_bulkgo">📥 Hamısını gətir</button>
      <label class="chip" style="cursor:pointer;margin:0">📊 Excel-dən import<input type="file" id="a_xls" accept=".xlsx" style="display:none"></label></div>
     <div class="small muted" style="margin-top:4px">Mətndən/linkdən 6–9 rəqəmli nömrələr avtomatik tanınır · təkrarlar və mövcud draftlar ötürülür.</div>
     <div class="small" id="a_bulkmsg" style="margin-top:6px"></div></div></details>
   <div class="small muted" style="margin-top:8px">Elan <b>BİZİM sistemə</b> gəlir → AI PCTECH → yoxlama → <b>təsdiqdən sonra</b> tap.az.</div></div>
   <div class="panel"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
     <h2 style="margin:0">📋 Draftlar</h2><input id="a_dq" placeholder="🔎 axtar (ad / nömrə)" style="width:200px"></div>
    <div class="controls" id="a_dfilters" style="margin-top:8px;gap:6px"></div>
    <div id="a_dbulkbar" style="margin-top:6px;display:none;align-items:center;gap:12px">
      <label class="small" style="cursor:pointer"><input type="checkbox" id="a_dall"> hamısını seç</label>
      <button class="chip" id="a_ddel" disabled>🗑 Seçilənləri sil</button><span class="small muted" id="a_dselc"></span></div>
    <div id="a_drafts" class="muted" style="margin-top:8px">Yüklənir…</div></div>`;
 return _sysHead()+refresh+tlogin+repost;
}
// ---- 2) Tənzimləmələr səhifəsi ----
function settingsView(){
 const gate=_sysGate();if(gate)return gate;
 if(BACKEND.sys.role!=='admin')return _sysHead()+_adminOnly('Tənzimləmələr');
 return _sysHead()+`<div class="panel"><h2>⚙️ Tənzimləmələr</h2>
   <div class="controls"><span class="small" style="align-self:center;font-weight:700">OpenAI açarı:</span><input id="s_aikey" type="password" placeholder="sk-..." style="width:280px"><button class="chip on" id="s_savekey">💾 Saxla</button></div>
   <div class="small" id="s_keymsg">${BACKEND.ai_key?'✅ OpenAI açarı təyin olunub':'⚠️ Açar yoxdur — AI (PCTECH) üçün lazımdır'}</div>
   <div class="small muted" style="margin-top:6px">Açar <code>data/secrets.json</code> faylında (0600, git-ə düşmür) saxlanır. AI PCTECH mətn + şəkil generasiyası üçün lazımdır.</div></div>`;
}
// ---- 3) İstifadəçilər səhifəsi ----
function usersView(){
 const gate=_sysGate();if(gate)return gate;
 if(BACKEND.sys.role!=='admin')return _sysHead()+_adminOnly('İstifadəçilər');
 return _sysHead()+`<div class="panel"><h2>👥 İstifadəçilər <span class="small">(admin)</span></h2>
   <div class="controls"><input id="u_name" placeholder="username" style="width:130px"><input id="u_pw" type="password" placeholder="parol" style="width:130px"><select id="u_role"><option value="operator">operator</option><option value="admin">admin</option></select><button class="chip on" id="u_add">➕ Əlavə et</button></div>
   <div id="u_list" class="muted" style="margin-top:8px">Yüklənir…</div>
   <div class="small muted" style="margin-top:8px"><b>admin</b> = hər şey · <b>operator</b> = yalnız Repost/Yenilə + draft (Tənzimləmələr və İstifadəçilər yox).</div></div>`;
}
// ---- 4) Kart dizaynı səhifəsi (Canva kimi sadə redaktor) ----
function designView(){
 const gate=_sysGate();if(gate)return gate;
 if(BACKEND.sys.role!=='admin')return _sysHead()+_adminOnly('Kart dizaynı');
 return _sysHead()+`<div class="panel"><h2>🎨 Kart dizaynı <span class="small">— dəyiş → canlı önizlə → saxla</span></h2>
   <div class="grid2" style="gap:20px">
    <div>
     <div class="small" style="font-weight:700">Brend adı <span class="muted">(aşağıda görünür)</span></div><input id="bd_name" style="width:100%" placeholder="PCTECH">
     <div class="small" style="font-weight:700;margin-top:10px">Telefon</div><input id="bd_phone" style="width:100%" placeholder="+994 ...">
     <div class="small" style="font-weight:700;margin-top:10px">Zəmanət mətni</div><input id="bd_guar" style="width:100%" placeholder="Rəsmi zəmanət">
     <div class="small" style="font-weight:700;margin-top:10px">Əsas rəng</div><div class="controls"><input type="color" id="bd_color" style="width:56px;height:38px;padding:2px;border:1px solid var(--line);border-radius:8px"><input id="bd_colorhex" style="width:130px" placeholder="#2F56E0"></div>
     <div class="small" style="font-weight:700;margin-top:10px">Promo yazı <span class="muted">(məs 24 ayadək kredit)</span></div><input id="bd_badge" style="width:100%" placeholder="24 ayadək kredit və taksit">
     <div class="small" style="font-weight:700;margin-top:8px">Promo mövqe</div>
     <select id="bd_badgepos" style="width:100%"><option value="none">Yoxdur</option><option value="top-left">Yuxarı sol</option><option value="top-center">Yuxarı mərkəz</option><option value="top-right">Yuxarı sağ</option></select>
     <div class="small" style="font-weight:700;margin-top:10px">Yuxarı-sağ ikon <span class="muted">(istəsən)</span></div><div id="bd_icons" class="controls" style="flex-wrap:wrap;gap:6px;margin-top:2px"></div>
     <div class="small" style="font-weight:700;margin-top:10px">Öz logon <span class="muted">(ikonu əvəz edir)</span></div>
     <div class="controls"><label class="chip on" style="cursor:pointer;margin:0">📤 Logo yüklə<input type="file" id="bd_logo" accept="image/*" style="display:none"></label><button class="chip" id="bd_logoclear">🗑 Logonu sil</button></div>
     <div class="small" id="bd_logomsg" style="margin-top:4px"></div>
     <div style="margin-top:16px"><button class="chip on" id="bd_save">💾 Saxla</button> <span class="small" id="bd_savemsg"></span></div>
    </div>
    <div>
     <div class="small" style="font-weight:700">Canlı önizləmə</div>
     <img id="bd_prev" style="width:100%;border:1px solid var(--line);border-radius:12px;margin-top:4px" src="/api/brand/preview">
     <div class="small muted" style="margin-top:6px">Nümunə məhsul göstərilir. Real kart hər draftın «🟩 Techbar kart» düyməsi ilə yaranır.</div>
    </div>
   </div></div>`;
}
async function bindDesign(){const g=id=>document.getElementById(id);const J={'Content-Type':'application/json'};
 if(!g('bd_name'))return;
 const b=await api('/api/brand/get');
 g('bd_name').value=b.name||'';g('bd_phone').value=b.phone||'';g('bd_guar').value=b.guarantee||'';
 g('bd_color').value=b.card_color||'#2F56E0';g('bd_colorhex').value=b.card_color||'#2F56E0';
 g('bd_badge').value=b.card_badge||'';g('bd_badgepos').value=b.card_badge_pos||'none';
 let curIcon=b.card_icon||'none';
 const labels={none:'🚫 Yoxdur',chip:'🔲 Çip',monitor:'🖥 Monitor',code:'&lt;/&gt; Kod',laptop:'💻 Laptop',power:'⏻ Power',headset:'🎧 Qulaqlıq',gear:'⚙️ Dişli',cloud:'☁️ Bulud'};
 const icg=g('bd_icons');
 icg.innerHTML=['none'].concat(b.icons||[]).map(k=>`<button class="chip${k===curIcon?' on':''}" data-ic="${k}">${labels[k]||k}</button>`).join('');
 const prev=()=>{const qs=new URLSearchParams({name:g('bd_name').value,phone:g('bd_phone').value,guarantee:g('bd_guar').value,card_color:g('bd_colorhex').value,card_icon:curIcon,card_badge:g('bd_badge').value,card_badge_pos:g('bd_badgepos').value});g('bd_prev').src='/api/brand/preview?'+qs.toString()+'&t='+Date.now();};
 icg.querySelectorAll('[data-ic]').forEach(bt=>bt.onclick=()=>{curIcon=bt.dataset.ic;icg.querySelectorAll('[data-ic]').forEach(x=>x.classList.toggle('on',x.dataset.ic===curIcon));prev();});
 let tmr;const deb=()=>{clearTimeout(tmr);tmr=setTimeout(prev,450);};
 ['bd_name','bd_phone','bd_guar','bd_badge'].forEach(id=>g(id).oninput=deb);
 g('bd_badgepos').onchange=prev;
 g('bd_color').oninput=()=>{g('bd_colorhex').value=g('bd_color').value;prev();};
 g('bd_colorhex').oninput=()=>{if(/^#[0-9a-fA-F]{6}$/.test(g('bd_colorhex').value))g('bd_color').value=g('bd_colorhex').value;deb();};
 g('bd_logoclear').onclick=async()=>{const r=await api('/api/brand/logo-clear',{method:'POST'});g('bd_logomsg').textContent=r.ok?'✅ İkona qayıdıldı':'⚠️ xəta';prev();};
 g('bd_logo').onchange=async(e)=>{const f=e.target.files[0];if(!f)return;g('bd_logomsg').textContent='Yüklənir…';const b64=await new Promise(r=>{const rd=new FileReader();rd.onload=()=>r(rd.result);rd.readAsDataURL(f);});const r=await api('/api/brand/logo',{method:'POST',headers:J,body:JSON.stringify({b64})});g('bd_logomsg').textContent=r.ok?'✅ Logo təyin olundu (ikonu əvəz edir)':('⚠️ '+esc(r.error||''));prev();e.target.value='';};
 g('bd_save').onclick=async()=>{const r=await api('/api/brand/set',{method:'POST',headers:J,body:JSON.stringify({name:g('bd_name').value,phone:g('bd_phone').value,guarantee:g('bd_guar').value,card_color:g('bd_colorhex').value,card_icon:curIcon,card_badge:g('bd_badge').value,card_badge_pos:g('bd_badgepos').value})});g('bd_savemsg').innerHTML=r.ok?'✅ Saxlanıldı — bütün yeni kartlara tətbiq olunur':('⚠️ '+esc(JSON.stringify(r).slice(0,120)));};
}
// ---- 5) Mağazalar səhifəsi (kateqoriya filtri + gündəlik/əl sync + PCTECH import) ----
function storesView(){
 const gate=_sysGate();if(gate)return gate;
 return _sysHead()+`<div class="panel"><h2>🏪 Mağaza əlavə et</h2>
   <div class="controls"><input id="st_url" placeholder="tap.az/shops/... (mağaza linki)" style="width:340px"><button class="chip on" id="st_add">➕ Əlavə et</button></div>
   <div class="small muted" style="margin-top:4px">Link → məhsullar avtomatik sync olunur (gündəlik yenilənir). Kateqoriya filtri + əl ilə «Sync et».</div>
   <div class="small" id="st_addmsg" style="margin-top:4px"></div>
   <div id="st_list" class="controls" style="flex-wrap:wrap;gap:8px;margin-top:10px">Yüklənir…</div></div>
   <div class="panel" id="st_panel" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
     <div><h2 style="margin:0" id="st_title">Məhsullar</h2><div class="small muted" id="st_synced"></div></div>
     <div class="controls" style="margin:0"><button class="chip" id="st_sync">🔄 Sync et</button><label class="small" style="cursor:pointer"><input type="checkbox" id="st_all"> seç</label><button class="chip on" id="st_import" disabled>📥 Seçilənləri PCTECH-ə</button></div></div>
    <div class="controls" id="st_cats" style="flex-wrap:wrap;gap:6px;margin-top:8px"></div>
    <div class="small" id="st_msg" style="margin-top:4px"></div>
    <div id="st_grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:10px;margin-top:10px"></div>
    <div style="text-align:center;margin-top:12px"><button class="chip" id="st_more" style="display:none">↓ Daha çox</button></div>
   </div>`;
}
let STCUR=null,STCAT='all',STOFF=0,STTOTAL=0;
async function loadStores(){const el=document.getElementById('st_list');if(!el)return;const r=await api('/api/stores/list');const ss=r.stores||[];
 el.innerHTML=ss.length?ss.map(s=>`<div class="stpill${s.slug===STCUR?' on':''}" data-store="${esc(s.slug)}">${s.logo_url?`<img src="${esc(s.logo_url)}">`:'<span style="width:28px;height:28px;border-radius:50%;background:var(--chip);display:inline-block"></span>'}<span>${esc(s.name||s.slug)}</span> <span class="cnt">${s.cached||s.ads_count||0}</span> <span class="rm" data-rmstore="${esc(s.slug)}" title="sil">🗑</span></div>`).join(''):'<span class="muted">Hələ mağaza yoxdur — yuxarıdan link əlavə et.</span>';
 el.querySelectorAll('[data-store]').forEach(c=>c.onclick=(e)=>{if(e.target.dataset.rmstore!==undefined)return;openStore(c.dataset.store);});
 el.querySelectorAll('[data-rmstore]').forEach(b=>b.onclick=async(e)=>{e.stopPropagation();if(!confirm('Mağaza silinsin?'))return;await api('/api/stores/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slug:b.dataset.rmstore})});if(STCUR===b.dataset.rmstore){STCUR=null;document.getElementById('st_panel').style.display='none';}loadStores();});}
async function openStore(slug){STCUR=slug;STCAT='all';STOFF=0;const p=document.getElementById('st_panel');p.style.display='block';document.getElementById('st_all').checked=false;document.getElementById('st_msg').textContent='';loadStores();await loadStoreCats();await loadStoreProducts(true);}
async function loadStoreCats(){const el=document.getElementById('st_cats');if(!el)return;const r=await api('/api/stores/categories?slug='+encodeURIComponent(STCUR));const cats=r.cats||[];
 el.innerHTML=`<div class="stcat${STCAT==='all'?' on':''}" data-cat="all">Hamısı <span class="cnt">${r.total||0}</span></div>`+cats.map(c=>`<div class="stcat${STCAT===c.id?' on':''}" data-cat="${esc(c.id)}">${esc(c.name||'—')} <span class="cnt">${c.count}</span></div>`).join('');
 el.querySelectorAll('[data-cat]').forEach(b=>b.onclick=()=>{STCAT=b.dataset.cat;el.querySelectorAll('[data-cat]').forEach(x=>x.classList.toggle('on',x.dataset.cat===STCAT));loadStoreProducts(true);});}
async function loadStoreProducts(reset){const grid=document.getElementById('st_grid');if(!grid)return;if(reset){STOFF=0;grid.innerHTML='<span class="muted">Yüklənir…</span>';}
 const r=await api('/api/stores/products?slug='+encodeURIComponent(STCUR)+'&category='+encodeURIComponent(STCAT)+'&offset='+STOFF+'&limit=24');
 if(r.error){grid.innerHTML='<span class="muted">⚠️ '+esc(r.error)+'</span>';return;}
 if(reset){grid.innerHTML='';STTOTAL=r.total||0;document.getElementById('st_title').textContent=((r.store&&r.store.name)||'Məhsullar');
   const ls=(r.store&&r.store.last_sync);document.getElementById('st_synced').innerHTML=(ls?('🕒 son sync: '+esc(ls)):'⚠️ hələ sync olunmayıb')+' · '+STTOTAL+' məhsul';}
 if(reset&&r.need_sync&&!STTOTAL){grid.innerHTML='<span class="muted">İlk sync gedir… bir neçə saniyə.</span>';pollSync();return;}
 (r.items||[]).forEach(p=>{const card=document.createElement('div');card.className='stcard';
   card.innerHTML=`<input type="checkbox" class="ck st_ck" value="${p.id}" ${p.already?'disabled':''}>
    <div class="zm">🔍 bax</div>
    <div class="iw" data-prev="${p.id}">${p.photo?`<img src="${esc(p.photo)}">`:''}</div>
    <div class="stbody"><div class="t" data-prev="${p.id}" title="${esc(p.title||'')}">${esc((p.title||'').slice(0,62))}</div>
     <div class="p">${p.price||0} ₼</div>
     <div style="margin-top:7px">${p.already?'<span class="small" style="color:var(--good);font-weight:700">✓ sistemdə</span>':`<button class="chip on" data-imp="${p.id}" style="width:100%;font-size:11.5px;padding:5px">📥 PCTECH-ə</button>`}</div></div>`;
   grid.appendChild(card);});
 grid.querySelectorAll('[data-prev]').forEach(e=>{if(e._b)return;e._b=1;e.onclick=()=>openStorePreview(e.dataset.prev);});
 grid.querySelectorAll('[data-imp]').forEach(b=>{if(b._b)return;b._b=1;b.onclick=async()=>{b.textContent='⏳…';b.disabled=true;const r=await api('/api/stores/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({listing_id:b.dataset.imp})});if(r.ok){b.textContent='✓ əlavə';b.style.background='var(--good)';}else{b.textContent='⚠️';b.disabled=false;}};});
 grid.querySelectorAll('.st_ck').forEach(c=>{if(c._b)return;c._b=1;c.onchange=updStSel;});
 STOFF+=(r.items||[]).length;const mb=document.getElementById('st_more');if(mb)mb.style.display=(STOFF<STTOTAL)?'inline-block':'none';
 updStSel();}
async function openStorePreview(id){let ov=document.getElementById('stprev');
 if(!ov){ov=document.createElement('div');ov.id='stprev';ov.style.cssText='position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:20px';document.body.appendChild(ov);ov.onclick=e=>{if(e.target===ov)ov.style.display='none';};}
 ov.style.display='flex';
 ov.innerHTML='<div style="background:var(--panel);border-radius:16px;max-width:920px;width:100%;max-height:88vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.5)"><div style="padding:24px"><span class="muted">Yüklənir…</span></div></div>';
 const box=ov.firstChild;
 const d=await api('/api/stores/preview?id='+encodeURIComponent(id));
 if(d.error){box.innerHTML='<div style="padding:22px"><div class="small">⚠️ '+esc(d.error)+'</div><button class="chip" style="margin-top:8px" onclick="document.getElementById(\'stprev\').style.display=\'none\'">Bağla</button></div>';return;}
 const ph=d.photos||[];
 box.innerHTML=`<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:18px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);z-index:1">
    <div style="min-width:0"><div style="font-size:19px;font-weight:800;line-height:1.25">${esc(d.title||'')}</div><div style="font-size:22px;font-weight:800;color:var(--acc2);margin-top:3px">${d.price||0} ₼</div></div>
    <button class="chip" onclick="document.getElementById('stprev').style.display='none'">✕ Bağla</button></div>
  <div style="padding:18px 22px">
   ${ph.length?`<img id="stpv_main" src="${esc(ph[0])}" style="width:100%;max-height:360px;object-fit:contain;background:#fff;border-radius:12px">
    <div style="display:flex;gap:7px;overflow-x:auto;margin-top:8px;padding-bottom:4px">${ph.map((u,i)=>`<img src="${esc(u)}" data-pv="${i}" style="width:62px;height:62px;object-fit:cover;border-radius:8px;border:2px solid ${i?'transparent':'var(--acc2)'};cursor:pointer;flex-shrink:0;background:#fff">`).join('')}</div>`:''}
   ${Object.keys(d.params||{}).length?`<div style="margin-top:16px"><div style="font-weight:700;margin-bottom:6px">Xüsusiyyətlər</div><table style="width:100%;border-collapse:collapse;font-size:13px">${Object.entries(d.params).map(([k,v])=>`<tr><td style="padding:4px 10px 4px 0;color:var(--muted);white-space:nowrap;vertical-align:top">${esc(k)}</td><td style="padding:4px 0;font-weight:600">${esc(String(v))}</td></tr>`).join('')}</table></div>`:''}
   ${d.body?`<div style="margin-top:16px"><div style="font-weight:700;margin-bottom:6px">Təsvir</div><div class="small" style="white-space:pre-wrap;line-height:1.55">${esc(d.body)}</div></div>`:''}
   <div id="stpv_msg" class="small" style="margin-top:14px;min-height:16px"></div>
   <div class="controls" id="stpv_act" style="margin-top:6px"></div>
  </div>`;
 box.querySelectorAll('[data-pv]').forEach(t=>t.onclick=()=>{document.getElementById('stpv_main').src=t.src;box.querySelectorAll('[data-pv]').forEach(x=>x.style.borderColor='transparent');t.style.borderColor='var(--acc2)';});
 renderPvActions(d,id);}
function pvMsg(h){const el=document.getElementById('stpv_msg');if(el)el.innerHTML=h;}
function pvShowCard(did){const m=document.getElementById('stpv_main');if(m)m.src='/drafts_media/'+did+'/ai_0.jpg?v='+Date.now();}
function renderPvActions(d,id){const el=document.getElementById('stpv_act');if(!el)return;const JH={'Content-Type':'application/json'};const g=x=>document.getElementById(x);
 let h='';
 if(d.draft_status==='posted')h='<span class="chip" style="cursor:default;background:var(--good);color:#fff">✓ tap.az-a göndərilib</span>';
 else if(d.draft_id)h=`<button class="chip on" id="stpv_card">${(d.n_ai_photos>0)?'🔄 AI PCTECH kart (yenidən)':'🟩 AI PCTECH kart'}</button><button class="chip on" id="stpv_appr" style="background:var(--good)">✅ Təsdiqlə → tap.az</button>`;
 else h='<button class="chip on" id="stpv_imp">📥 PCTECH-ə əlavə et</button>';
 h+=`<a class="chip" href="${esc(d.link||'#')}" target="_blank" style="text-decoration:none">↗ tap.az-da aç</a>`;
 el.innerHTML=h;
 if(g('stpv_imp'))g('stpv_imp').onclick=async()=>{g('stpv_imp').textContent='⏳…';g('stpv_imp').disabled=true;const r=await api('/api/stores/import',{method:'POST',headers:JH,body:JSON.stringify({listing_id:id})});if(r.ok){d.draft_id=r.draft_id;d.draft_status='pending';d.n_ai_photos=0;pvMsg('✅ Sistemə əlavə olundu — draft #'+r.draft_id);renderPvActions(d,id);loadStoreProducts(true);}else{g('stpv_imp').textContent='⚠️';g('stpv_imp').disabled=false;}};
 if(g('stpv_card'))g('stpv_card').onclick=async()=>{const b=g('stpv_card');b.textContent='⏳ Kart yaradılır (~30s)…';b.disabled=true;pvMsg('🟩 AI PCTECH kartı yaradılır (məhsul təmizlənir + montaj)…');const r=await api('/api/draft/make-card',{method:'POST',headers:JH,body:JSON.stringify({id:d.draft_id,index:0})});if(r.ok){d.n_ai_photos=Math.max(1,d.n_ai_photos||1);pvShowCard(d.draft_id);pvMsg('✅ AI PCTECH kart hazırdır — indi «Təsdiqlə» edə bilərsən.');loadStoreProducts(true);}else pvMsg('⚠️ '+esc((r.error||JSON.stringify(r)).slice(0,140)));renderPvActions(d,id);};
 if(g('stpv_appr'))g('stpv_appr').onclick=async()=>{if(!confirm('Bu məhsul tap.az moderasiyasına göndərilsin?'))return;const b=g('stpv_appr');b.textContent='Göndərilir…';b.disabled=true;const r=await api('/api/draft/approve',{method:'POST',headers:JH,body:JSON.stringify({id:d.draft_id})});if(r.ok){d.draft_status='posted';pvMsg('✅ tap.az-a göndərildi · status: '+esc(((r.status||{}).label||(r.status||{}).status||'')));renderPvActions(d,id);loadStoreProducts(true);}else{pvMsg('⚠️ '+esc(JSON.stringify(r).slice(0,160)));renderPvActions(d,id);}};
}
function updStSel(){const cks=[...document.querySelectorAll('.st_ck:not(:disabled)')];const sel=cks.filter(c=>c.checked);const btn=document.getElementById('st_import');if(btn){btn.disabled=!sel.length;btn.textContent='📥 Seçilənləri PCTECH-ə'+(sel.length?' ('+sel.length+')':'');}}
async function pollSync(){const el=document.getElementById('st_synced');const b=document.getElementById('st_sync');const r=await api('/api/stores/sync-status');
 if(r.running){if(el)el.innerHTML='🔄 sync gedir… ('+r.count+' məhsul)';setTimeout(pollSync,1500);}
 else{if(b){b.disabled=false;b.textContent='🔄 Sync et';}loadStores();if(STCUR){await loadStoreCats();await loadStoreProducts(true);}}}
async function pollStoreBulk(){const el=document.getElementById('st_msg');const r=await api('/api/draft/bulk-status');if(!r||!r.total)return;
 if(r.running){if(el)el.innerHTML='🔄 '+r.done+'/'+r.total+' — ✅'+r.ok+' yeni · ⏭'+r.skip+' mövcud · ⚠️'+r.fail;setTimeout(pollStoreBulk,1500);}
 else{if(el)el.innerHTML='✅ Bitdi: ✅'+r.ok+' yeni · ⏭'+r.skip+' mövcud'+(r.fail?' · ⚠️'+r.fail+' xəta':'');if(STCUR)loadStoreProducts(true);}}
function bindStores(){const g=id=>document.getElementById(id);const J={'Content-Type':'application/json'};
 if(!g('st_url'))return;
 g('st_add').onclick=async()=>{const u=g('st_url').value.trim();if(!u)return;g('st_addmsg').textContent='Yoxlanılır…';const r=await api('/api/stores/add',{method:'POST',headers:J,body:JSON.stringify({url:u})});if(r.ok){g('st_addmsg').innerHTML='✅ '+esc(r.store.name)+' — sync başladı…';g('st_url').value='';loadStores();}else g('st_addmsg').innerHTML='⚠️ '+esc(r.error||JSON.stringify(r));};
 g('st_more').onclick=()=>loadStoreProducts(false);
 g('st_all').onchange=()=>{document.querySelectorAll('.st_ck:not(:disabled)').forEach(c=>c.checked=g('st_all').checked);updStSel();};
 g('st_sync').onclick=async()=>{if(!STCUR)return;const b=g('st_sync');b.disabled=true;b.textContent='🔄 Sync gedir…';await api('/api/stores/sync',{method:'POST',headers:J,body:JSON.stringify({slug:STCUR})});pollSync();};
 g('st_import').onclick=async()=>{const ids=[...document.querySelectorAll('.st_ck:checked')].map(c=>c.value);if(!ids.length)return;g('st_msg').textContent='📥 '+ids.length+' məhsul gətirilir…';const r=await api('/api/stores/import-bulk',{method:'POST',headers:J,body:JSON.stringify({ids})});if(r.ok)pollStoreBulk();else g('st_msg').innerHTML='⚠️ '+esc(r.error||'');};
 loadStores();
}
function bindAdmin(){const g=id=>document.getElementById(id);const J={'Content-Type':'application/json'};
 if(g('r_now'))g('r_now').onclick=async()=>{const b=g('r_now');b.disabled=true;b.textContent='🔄 Yenilənir…';g('r_msg').innerHTML='🔄 tap.az yenilənir… (bir neçə dəqiqə çəkə bilər)';const r=await api('/api/refresh',{method:'POST',headers:J,body:'{}'});if(r&&r.error){g('r_msg').innerHTML='⚠️ '+esc(JSON.stringify(r).slice(0,200));b.disabled=false;b.textContent='🔄 İndi yenilə';return;}banner('🔄 tap.az məlumatları yenilənir…');setTimeout(pollRefresh,3000);};
 if(BACKEND&&BACKEND.refresh&&BACKEND.refresh.running){setTimeout(pollRefresh,2000);}
 if(g('s_login'))g('s_login').onclick=async()=>{const r=await api('/api/user/login',{method:'POST',headers:J,body:JSON.stringify({username:g('s_user').value,password:g('s_pw').value})});if(r.ok){await checkBackend();buildNav();render();}else g('s_msg').innerHTML='⚠️ '+esc(r.error||'giriş alınmadı');};
 if(g('s_logout'))g('s_logout').onclick=async()=>{await api('/api/user/logout',{method:'POST'});await checkBackend();buildNav();render();};
 if(g('s_savekey'))g('s_savekey').onclick=async()=>{const r=await api('/api/settings/set',{method:'POST',headers:J,body:JSON.stringify({openai_key:g('s_aikey').value.trim()})});g('s_keymsg').innerHTML=r.ok?'✅ Açar saxlanıldı':('⚠️ '+esc(JSON.stringify(r).slice(0,150)));await checkBackend();};
 if(g('u_add'))g('u_add').onclick=async()=>{const r=await api('/api/user/create',{method:'POST',headers:J,body:JSON.stringify({username:g('u_name').value,password:g('u_pw').value,role:g('u_role').value})});if(r.ok){g('u_name').value='';g('u_pw').value='';loadUsers();}else alert(r.error||'xəta');};
 if(g('u_list'))loadUsers();
 if(g('a_send'))g('a_send').onclick=async()=>{const p=g('a_phone').value.trim();if(!p)return;g('a_authmsg').textContent='Göndərilir…';const r=await api('/api/auth/send-code',{method:'POST',headers:J,body:JSON.stringify({phone:p})});g('a_coderow').style.display='flex';g('a_authmsg').innerHTML=r.ok?'✅ Kod göndərildi — telefonuna bax':('⚠️ '+esc(JSON.stringify(r).slice(0,220)));};
 if(g('a_verify'))g('a_verify').onclick=async()=>{g('a_authmsg').textContent='Yoxlanılır…';const r=await api('/api/auth/verify',{method:'POST',headers:J,body:JSON.stringify({phone:g('a_phone').value.trim(),code:g('a_code').value.trim()})});if(r.ok&&r.login&&r.login.ok){await checkBackend();render();}else g('a_authmsg').innerHTML='⚠️ '+esc(JSON.stringify(r).slice(0,220));};
 if(g('a_logout'))g('a_logout').onclick=async()=>{await api('/api/auth/logout',{method:'POST'});await checkBackend();render();};
 if(g('a_preview'))g('a_preview').onclick=async()=>{const id=g('a_lid').value.trim();if(!id)return;g('a_result').innerHTML='Oxunur…';const r=await api('/api/repost',{method:'POST',headers:J,body:JSON.stringify({listing_id:id,dry_run:true,contact:{}})});if(r.stage==='dry_run'){const a=r.ad;g('a_result').innerHTML=`<div class="panel" style="margin:0"><b>${esc(a.title||'')}</b><div class="small">Kateqoriya: ${esc(a.category_slug)} · Qiymət: ${a.price}₼ · Şəkil: ${a.n_photos} · Atributlar: ${a.properties.collection.length+a.properties.boolean.length}</div></div>`;}else g('a_result').innerHTML='<div class="small">⚠️ '+esc(JSON.stringify(r).slice(0,300))+'</div>';};
 if(g('a_post'))g('a_post').onclick=async()=>{const id=g('a_lid').value.trim();if(!id)return;g('a_result').innerHTML='Sistemə gətirilir (şəkillər endirilir)…';const r=await api('/api/draft/create',{method:'POST',headers:J,body:JSON.stringify({listing_id:id})});if(r.ok){g('a_result').innerHTML='✅ Draft #'+r.draft_id+' BİZİM sistemə gətirildi — aşağıda yoxla';g('a_lid').value='';loadDrafts();}else g('a_result').innerHTML='⚠️ '+esc(JSON.stringify(r).slice(0,220));};
 if(g('a_bulkgo'))g('a_bulkgo').onclick=async()=>{const t=g('a_bulk').value.trim();if(!t){g('a_bulkmsg').innerHTML='⚠️ Mətn boşdur';return;}g('a_bulkmsg').innerHTML='🔄 Başladılır…';const r=await api('/api/draft/bulk-create',{method:'POST',headers:J,body:JSON.stringify({text:t})});if(r.ok){g('a_bulkmsg').innerHTML='🔄 '+r.total+' nömrə tapıldı — gətirilir…';pollBulk();}else g('a_bulkmsg').innerHTML='⚠️ '+esc(r.error||JSON.stringify(r));};
 if(g('a_xls'))g('a_xls').onchange=async(e)=>{const f=e.target.files[0];if(!f)return;g('a_bulkmsg').innerHTML='📊 Excel oxunur: '+esc(f.name);const b64=await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result);rd.readAsDataURL(f);});const r=await api('/api/draft/import-excel',{method:'POST',headers:J,body:JSON.stringify({b64})});if(r.ok){g('a_bulkmsg').innerHTML='🔄 Excel-də '+r.total+' nömrə — gətirilir…';pollBulk();}else g('a_bulkmsg').innerHTML='⚠️ '+esc(r.error||JSON.stringify(r));e.target.value='';};
 if(g('a_dq'))g('a_dq').oninput=()=>{DQ=g('a_dq').value;renderDrafts();};
 (async()=>{const r=await api('/api/draft/bulk-status');if(r&&r.running)pollBulk();})();
 loadDrafts();
}
async function pollBulk(){const el=document.getElementById('a_bulkmsg');const r=await api('/api/draft/bulk-status');if(!r||!r.total)return;
 if(r.running){if(el)el.innerHTML='🔄 '+r.done+'/'+r.total+' — ✅'+r.ok+' yeni · ⏭'+r.skip+' mövcud · ⚠️'+r.fail+' xəta';setTimeout(pollBulk,1500);}
 else{if(el)el.innerHTML='✅ Bitdi: ✅'+r.ok+' yeni · ⏭'+r.skip+' mövcud'+(r.fail?' · ⚠️'+r.fail+' xəta':'')+((r.errors&&r.errors.length)?' <span class="muted">('+esc(r.errors.slice(0,3).join('; '))+')</span>':'');loadDrafts();}}
let DRAFTSCACHE=[],DFILTER='all',DQ='';
function _dstat(d){if(d.status==='posted')return 'posted';if(d.status==='rejected')return 'rejected';if(d.adapted_title||(d.n_ai_photos||0)>0)return 'ai';return 'pending';}
const _DTAB={all:'Hamısı',pending:'⏳ Gözləyən',ai:'✨ AI hazır',posted:'📤 Göndərilmiş',rejected:'❌ Rədd'};
function _dbadge(d){const s=_dstat(d);const m={pending:['⏳ gözləyən','var(--chip)','var(--ink)'],ai:['✨ AI hazır','var(--acc-soft)','var(--acc2)'],posted:['📤 tap.az: '+esc(d.tapaz_status||'?'),'rgba(34,197,94,.18)','var(--good)'],rejected:['❌ rədd','rgba(239,68,68,.16)','var(--bad)']}[s];
 return `<span style="display:inline-block;font-size:10px;font-weight:700;padding:1px 7px;border-radius:20px;background:${m[1]};color:${m[2]}">${m[0]}</span>`;}
async function loadDrafts(){const el=document.getElementById('a_drafts');if(!el)return;const r=await api('/api/draft/list');DRAFTSCACHE=(r.drafts||[]);renderDrafts();}
function renderDrafts(){const el=document.getElementById('a_drafts');if(!el)return;
 const counts={all:DRAFTSCACHE.length};['pending','ai','posted','rejected'].forEach(k=>counts[k]=DRAFTSCACHE.filter(d=>_dstat(d)===k).length);
 const fb=document.getElementById('a_dfilters');if(fb){fb.innerHTML=Object.keys(_DTAB).map(k=>`<button class="chip${DFILTER===k?' on':''}" data-df="${k}">${_DTAB[k]} <span class="cnt">${counts[k]||0}</span></button>`).join('');
  fb.querySelectorAll('[data-df]').forEach(b=>b.onclick=()=>{DFILTER=b.dataset.df;renderDrafts();});}
 let rows=DRAFTSCACHE.filter(d=>DFILTER==='all'||_dstat(d)===DFILTER);
 const q=DQ.toLowerCase().trim();if(q)rows=rows.filter(d=>(''+d.id).includes(q)||(''+(d.source_id||'')).includes(q)||(d.title||'').toLowerCase().includes(q));
 const bar=document.getElementById('a_dbulkbar');if(bar)bar.style.display=rows.length?'flex':'none';
 if(!DRAFTSCACHE.length){el.innerHTML='<span class="muted">Hələ draft yoxdur. Yuxarıdan tək nömrə və ya toplu əlavə et.</span>';return;}
 if(!rows.length){el.innerHTML='<span class="muted">Bu filtrdə draft yoxdur.</span>';return;}
 el.innerHTML=rows.map(d=>`<div style="margin:0 0 6px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel2)">
   <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div style="display:flex;align-items:center;gap:9px;min-width:0"><input type="checkbox" class="dck" value="${d.id}" style="flex-shrink:0">
     <div style="min-width:0"><span style="font-weight:700">#${d.id}</span> ${esc((d.title||'').slice(0,58))} ${_dbadge(d)}
      <div class="small muted">${d.price||0}₼ · ${esc(d.category_slug||'—')} · ${d.n_photos||0}📷${(d.n_ai_photos||0)?' · ✨'+d.n_ai_photos:''}${d.tapaz_ad_id?' · tap.az #'+esc(d.tapaz_ad_id):''}</div></div></div>
    <div class="controls" style="margin:0;flex-shrink:0"><button class="chip" data-dv="${d.id}">👁</button>${d.status==='pending'?`<button class="chip on" data-da="${d.id}">✅ Təsdiqlə</button>`:''}<button class="chip" data-dd="${d.id}">🗑</button></div>
   </div><div id="dv_${d.id}" style="display:none;margin-top:8px"></div></div>`).join('');
 bindDrafts();bindDraftSelect();
}
function bindDraftSelect(){const cks=[...document.querySelectorAll('.dck')];
 const upd=()=>{const sel=cks.filter(c=>c.checked);const del=document.getElementById('a_ddel'),c=document.getElementById('a_dselc'),all=document.getElementById('a_dall');
  if(del)del.disabled=!sel.length;if(c)c.textContent=sel.length?sel.length+' seçilib':'';if(all)all.checked=cks.length>0&&sel.length===cks.length;};
 cks.forEach(c=>c.onchange=upd);
 const all=document.getElementById('a_dall');if(all)all.onchange=()=>{cks.forEach(c=>c.checked=all.checked);upd();};
 const del=document.getElementById('a_ddel');if(del)del.onclick=async()=>{const ids=cks.filter(c=>c.checked).map(c=>+c.value);if(!ids.length||!confirm(ids.length+' draft silinsin?'))return;del.disabled=true;del.textContent='Silinir…';for(const id of ids){await api('/api/draft/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});}loadDrafts();};
 upd();
}
async function loadUsers(){const el=document.getElementById('u_list');if(!el)return;const r=await api('/api/user/list');const us=(r.users||[]);
 el.innerHTML=us.map(u=>`<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--line)"><span><b>${esc(u.username)}</b> <span class="chip" style="cursor:default;font-size:10px">${esc(u.role)}</span> <span class="small">${esc(u.created_at||'')}</span></span><button class="chip" data-udel="${esc(u.username)}">🗑</button></div>`).join('')||'<span class="muted">yox</span>';
 el.querySelectorAll('[data-udel]').forEach(b=>b.onclick=async()=>{if(!confirm('İstifadəçi «'+b.dataset.udel+'» silinsin?'))return;await api('/api/user/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:b.dataset.udel})});loadUsers();});}
function openLightbox(src,ctx){
 ctx=ctx||{};
 let ov=document.getElementById('lightbox');
 if(!ov){ov=document.createElement('div');ov.id='lightbox';ov.style.cssText='position:fixed;inset:0;z-index:1000;background:rgba(0,0,0,.86);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;padding:24px';document.body.appendChild(ov);}
 ov.onclick=e=>{if(e.target===ov)ov.style.display='none';};
 ov.style.display='flex';
 const base=src.split('?')[0];
 const act=(ctx.id!=null&&ctx.index!=null);
 const btns=act?`<button class="chip on" id="lb_card">🟩 Techbar kart</button>${ctx.isOrig?'':`<button class="chip" id="lb_regen">🤖 AI təmizlə</button>`}<label class="chip" style="cursor:pointer;margin:0">📤 Öz şəklini yüklə<input type="file" id="lb_up" accept="image/*" style="display:none"></label>`:'';
 ov.innerHTML=`<img id="lb_img" src="${base+'?v='+Date.now()}" style="max-width:92vw;max-height:74vh;object-fit:contain;border-radius:12px;box-shadow:0 12px 48px rgba(0,0,0,.6)">
   <div class="controls" style="margin:0;justify-content:center">${btns}<a class="chip" href="${base}" target="_blank" style="text-decoration:none">↗ Tam ölçü</a><button class="chip" id="lb_close">✕ Bağla</button></div>
   <div class="small" id="lb_msg" style="color:#fff;min-height:16px"></div>`;
 document.getElementById('lb_close').onclick=()=>ov.style.display='none';
 if(!act)return;
 const did=ctx.id,idx=ctx.index,msg=m=>{document.getElementById('lb_msg').innerHTML=m;};
 const showResult=index=>{document.getElementById('lb_img').src='/drafts_media/'+did+'/ai_'+index+'.jpg?v='+Date.now();if(ctx.refresh)ctx.refresh();};
 document.getElementById('lb_card').onclick=async()=>{const b=document.getElementById('lb_card');b.disabled=true;b.textContent='⏳ Kart (~30s)…';msg('🟩 Techbar sabit-dizayn kartı yaradılır (məhsul təmizlənir + montaj)…');
   const r=await api('/api/draft/make-card',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:did,index:idx})});
   if(r.ok){showResult(r.index);msg('✅ Techbar kart hazırdır');}else msg('⚠️ '+((r.error||JSON.stringify(r))+'').slice(0,150));b.disabled=false;b.textContent='🟩 Techbar kart';};
 if(document.getElementById('lb_regen'))document.getElementById('lb_regen').onclick=async()=>{const b=document.getElementById('lb_regen');b.disabled=true;b.textContent='⏳…';msg('🤖 AI real fotonu təmizləyir…');
   const r=await api('/api/draft/rebrand-one',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:did,index:idx})});
   if(r.ok){showResult(idx);msg('✅ Təmizləndi');}else msg('⚠️ '+((r.error||JSON.stringify(r))+'').slice(0,150));b.disabled=false;b.textContent='🤖 AI təmizlə';};
 document.getElementById('lb_up').onchange=async(e)=>{const f=e.target.files[0];if(!f)return;msg('📤 Yüklənir: '+f.name+' …');
   const b64=await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result);rd.readAsDataURL(f);});
   const r=await api('/api/draft/replace-photo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:did,index:idx,b64})});
   if(r.ok){showResult(r.index);msg('✅ Öz şəklin əlavə olundu');}else msg('⚠️ '+((r.error||JSON.stringify(r))+'').slice(0,150));e.target.value='';};
}
async function renderDraftDetail(id,box){const g=x=>document.getElementById(x);const J={'Content-Type':'application/json'};
  const d=await api('/api/draft/get?id='+id);
  const aiOn=(d.n_ai_photos||0)>0||d.adapted_title;
  const orig=`<div class="grid2"><div><div class="small" style="font-weight:700">📄 Orijinal başlıq</div><input value="${esc(d.title||'')}" id="dt_${id}" style="width:100%"><div class="small" style="font-weight:700;margin-top:6px">Orijinal təsvir</div><textarea id="db_${id}" style="width:100%;min-height:80px">${esc(d.body||'')}</textarea><div style="margin-top:6px"><span class="small" style="font-weight:700">Qiymət </span><input value="${d.price||''}" id="dp_${id}" style="width:110px"> <button class="chip" data-dsave="${id}">💾 Saxla</button></div><div class="small muted" style="margin-top:6px">Atributlar: ${(d.properties.collection||[]).map(c=>esc(c.text||c.value)).join(', ')||'—'}</div></div>
   <div><div class="small" style="font-weight:700">📷 Orijinal şəkillər (${d.n_photos}) <span class="muted" style="font-weight:400">— kliklə: 🟩 kart düzəlt</span></div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">${(d.photos||[]).map((u,i)=>`<img class="dimg" data-full="${u}" data-idx="${i}" data-orig="1" src="${u}" style="width:82px;height:82px;object-fit:cover;border-radius:8px;border:1px solid var(--line);cursor:zoom-in">`).join('')||'<span class="muted">yox</span>'}</div></div></div>`;
  const aiSection=`<div class="panel" style="margin:10px 0 0;background:var(--acc-soft)"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px"><b>🟩 Techbar brend-versiyası</b><button class="chip on" data-aiadapt="${id}">${aiOn?'🔄 Mətni yenilə':'✨ Techbar-a çevir (mətn)'}</button></div>
    ${aiOn?`<div class="grid2" style="margin-top:8px"><div><div class="small" style="font-weight:700;color:var(--acc2)">✨ Techbar başlıq</div><div style="font-weight:700">${esc(d.adapted_title||'—')}</div><div class="small" style="font-weight:700;margin-top:6px;color:var(--acc2)">✨ Techbar təsvir</div><div class="small" style="white-space:pre-wrap;max-height:140px;overflow:auto">${esc(d.adapted_body||'—')}</div></div>
     <div><div class="small" style="font-weight:700;color:var(--acc2);display:flex;align-items:center;gap:8px;flex-wrap:wrap">✨ Brendli şəkillər (${d.n_ai_photos||0}) <span class="muted" style="font-weight:400">— kliklə: kart / əvəz</span><label class="chip" style="cursor:pointer;font-size:10px;padding:2px 8px;margin:0">📤 Öz şəklini əlavə et<input type="file" id="aiadd_${id}" accept="image/*" style="display:none"></label></div><div id="aiimgs_${id}" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px">${(d.ai_photos||[]).map((u,i)=>`<img class="dimg" data-full="${u}" data-idx="${i}" src="${u}" style="width:82px;height:82px;object-fit:cover;border-radius:8px;border:2px solid var(--acc2);cursor:zoom-in">`).join('')||'<span class="muted">şəkil yox</span>'}</div></div></div>
     <div class="small muted" style="margin-top:6px">✅ «Təsdiqlə → tap.az» — hər şəkil üçün brendli/kart varsa onu, yoxsa orijinalı göndərir (hər şəkli ayrı seçirsən).</div>`:(BACKEND.ai_key?'<div class="small muted" style="margin-top:6px">✨ mətni Techbar-a çevirir. Sonra hər şəkli kliklə: <b>🟩 Techbar kart</b>, 📤 öz şəklin, və ya orijinalı saxla.</div>':'<div class="small" style="margin-top:6px;color:var(--bad)">⚠️ OpenAI açarı yoxdur — <b>⚙️ Tənzimləmələr</b> səhifəsindən əlavə et.</div>')}
    <div id="aimsg_${id}" class="small" style="margin-top:6px"></div></div>`;
  box.innerHTML=orig+aiSection;
  const refresh=()=>renderDraftDetail(id,box);
  box.querySelectorAll('.dimg').forEach(img=>img.onclick=()=>openLightbox(img.dataset.full,{id:+id,index:+img.dataset.idx,isOrig:img.dataset.orig==='1',refresh}));
  if(g('aiadd_'+id))g('aiadd_'+id).onchange=async(e)=>{const f=e.target.files[0];if(!f)return;g('aimsg_'+id).textContent='📤 Yüklənir: '+f.name+' …';const b64=await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result);rd.readAsDataURL(f);});const r=await api('/api/draft/replace-photo',{method:'POST',headers:J,body:JSON.stringify({id:+id,index:-1,b64})});if(r.ok){refresh();}else g('aimsg_'+id).textContent='⚠️ '+((r.error||JSON.stringify(r))+'').slice(0,140);e.target.value='';};
  box.querySelector('[data-dsave]').onclick=async()=>{await api('/api/draft/update',{method:'POST',headers:J,body:JSON.stringify({id:+id,title:g('dt_'+id).value,body:g('db_'+id).value,price:parseFloat(g('dp_'+id).value)||0})});g('aimsg_'+id).textContent='💾 Saxlanıldı';};
  box.querySelector('[data-aiadapt]').onclick=async(ev)=>{ev.target.textContent='⏳ Mətn Techbar-a çevrilir…';ev.target.disabled=true;const r=await api('/api/draft/ai-adapt',{method:'POST',headers:J,body:JSON.stringify({id:+id})});if(r.ok){refresh();}else g('aimsg_'+id).innerHTML='⚠️ '+esc((r.error||JSON.stringify(r)).slice(0,220));};
}
function bindDrafts(){const g=id=>document.getElementById(id);const J={'Content-Type':'application/json'};
 document.querySelectorAll('[data-dv]').forEach(b=>b.onclick=()=>{const id=b.dataset.dv,box=g('dv_'+id);if(box.style.display==='block'){box.style.display='none';return;}box.style.display='block';box.innerHTML='<span class="muted">Yüklənir…</span>';renderDraftDetail(id,box);});
 document.querySelectorAll('[data-da]').forEach(b=>b.onclick=async()=>{if(!confirm('Bu draft-ı yoxladın? tap.az moderasiyasına göndərilsin?'))return;b.textContent='Göndərilir…';b.disabled=true;const r=await api('/api/draft/approve',{method:'POST',headers:J,body:JSON.stringify({id:+b.dataset.da})});alert(r.ok?('✅ tap.az-a göndərildi · status: '+((r.status||{}).label||'')):('⚠️ '+JSON.stringify(r).slice(0,240)));loadDrafts();});
 document.querySelectorAll('[data-dd]').forEach(b=>b.onclick=async()=>{if(!confirm('Draft silinsin?'))return;await api('/api/draft/delete',{method:'POST',headers:J,body:JSON.stringify({id:+b.dataset.dd})});loadDrafts();});
}
// Auto-refresh on entry (stale olduqda)
function banner(html){let b=document.getElementById('refbanner');if(!b){b=document.createElement('div');b.id='refbanner';b.style.cssText='position:fixed;top:0;left:0;right:0;z-index:99;background:var(--acc2);color:#fff;padding:8px 16px;font-size:13px;text-align:center;box-shadow:var(--shadow)';document.body.appendChild(b);}b.innerHTML=html;b.style.display=html?'block':'none';}
async function pollRefresh(){const r=await api('/api/refresh-status');if(r.running){banner('🔄 tap.az məlumatları yenilənir… (bu, bir neçə dəqiqə çəkə bilər)');setTimeout(pollRefresh,4000);}else{banner('✅ Yeniləndi! Ən son məlumatları görmək üçün <b>səhifəni yenilə</b> → <button onclick="location.reload()" style="background:#fff;color:var(--acc2);border:none;border-radius:6px;padding:3px 10px;font-weight:700;cursor:pointer">Yenilə</button> <span onclick="banner(\'\')" style="cursor:pointer;margin-left:10px">✕</span>');}}
async function catSync(slug,btn){if(!BACKEND){banner('⚠️ Sync üçün Mac-local backend lazımdır');return;}if(btn){btn.disabled=true;btn.textContent='⏳';}
 const r=await api('/api/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({only:slug})});
 if(r&&r.error){banner('⚠️ '+esc(JSON.stringify(r).slice(0,120)));if(btn){btn.disabled=false;btn.textContent='🔄';}return;}
 banner('🔄 <b>'+esc(slug)+'</b> kateqoriyası yenilənir…');setTimeout(pollRefresh,3000);}
async function maybeAutoRefresh(){
 if(!BACKEND)return;
 const dts=META.cats.map(c=>c.last).filter(Boolean).sort();const oldest=dts[0]||'';
 const stale = !oldest || daysAgo(oldest)>0;   // bugün deyilsə → köhnə
 if(stale && !BACKEND.refresh.running){banner('🔄 Sistemə giriş — tap.az məlumatları avtomatik yenilənir…');await api('/api/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});setTimeout(pollRefresh,3000);}
 else if(BACKEND.refresh.running){setTimeout(pollRefresh,2000);}
}
async function initBackend(){await checkBackend();buildNav();maybeAutoRefresh();}
buildNav();go('overview');initBackend();
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==$('#q')){e.preventDefault();$('#q').focus();}});
</script></body></html>"""
