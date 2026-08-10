# tap.az Radar — Cari Vəziyyət

**Son yenilənmə:** 2026-08-10 (v3: qiymət 200₼ interval + CPU nəsil/seriya filtri + büdcə siyahıları İcmaldan alt-kateqoriya analizinə; əvvəl v2: alt-kat analizi + pagination + dizayn)

## 🆕 Ən son (v3)
- **Qiymət aralığı intervalları 200₼** oldu (İcmal qrafiki + alt-kat analizi cədvəlləri) — `band200(price)`.
- **CPU Nəsil + Seriya filtri** (yalnız noutbuk/masaüstü): Apple M1-4, Intel N-ci nəsil, Core Ultra Seriya, Ryzen N000; suffix U/H/HX/HS/HK/HQ/G/K/F/T/P/Y/M/MQ/QM. `cpuGen`/`cpuSer` cpu mətnindən parse+keş, `VALID_SUF` whitelist. Test: Intel 13-cü+HX → 148 (i7-13650HX).
- **«Büdcəyə görə ən yaxşı» + «parametrə görə ən ucuz» İcmaldan SİLİNDİ** — istifadəçi tələbi ilə artıq yalnız hər kateqoriyanın «Alt-kateqoriya analizi» tabında (hər alt-kat ayrı). İcmalda yönləndirici hint qaldı → İcmal indi kompakt (KPI + kart + 4 qrafik).
- **Alt-kateqoriya analizi peşəkarlaşdırıldı:** parametrlər rəngli **spec çiplərinə** (`specChips` — CPU/RAM/SSD/GPU/ekran; komponentlərdə params-split), «ən güclü» cədvəldə yanıldıcı dəyər badge yerinə **0-100 normallaşdırılmış Güc barı** (spec_score/maxSpec), panel başlığında **statistika** (elan·orta qiymət·yeni·mağaza), sərfəli-qiymət **ikonlu qruplar** + hizalanmış grid.
- **4 alt-tab:** 📋 Cədvəl · 💰 Büdcə üzrə · 🎯 Parametr üzrə · 📊 Alt-kateqoriya analizi.
- **«💰 Büdcə üzrə»** (`budgetView`) — hər 200₼ aralıq **öz panelində**, **15 məhsul/səhifə + per-aralıq müstəqil pagination** (`bindBandPagers`/`state.bandPages`, filtr dəyişəndə imza `_bsig` ilə avto-reset). Standart olaraq **yalnız «Yeni» vəziyyət** (işlənmişlər Vəziyyət filtri «İkinci əl» ilə).
- **«🎯 Parametr üzrə»** (`paramView`/`bindParamSel`/`state.paramTab`) — **CPU/RAM/VGA** seçicisi; hər parametr dəyəri öz panelində (RAM: r.ram 64→2GB; CPU: r.cpu_fam; VGA: r.gpu top-40 saya görə). Hər qrupda məhsullar **ən ucuzdan bahalıya**, 15/səhifə müstəqil pagination (state.bandPages `p|dim|val` açarları ilə paylaşılır). Yalnız struktur sahələr (noutbuk/masaüstü).
- Bütün panel sətirləri: spec çiplər + Güc barı + qiymət + vəziyyət + satıcı + telefon.
- **Vəziyyət seçici (condMode)** Büdcə + Parametr tablarında — seqment toggle: **🆕 Yalnız Yeni · 🔀 Yeni + İkinci əl (qarışıq) · ♻️ Yalnız İkinci əl** (`condModeBar`/`applyCondMode`/`bindCondMode`, default 'yeni'). Bu görünüşlərdə filter-bar-dakı Vəziyyət dropdown gizlənir (`filtersBar(true,true)` + `filtered(...,skipCond)`), toggle onu əvəz edir — təkrar yox.

**📌 Tab-ların kateqoriya üzrə uyğunluğu (yoxlanıldı):**
| Kateqoriya | Cədvəl | Büdcə | Parametr (CPU/RAM/VGA) | Alt-kat analizi |
|---|---|---|---|---|
| Noutbuklar, Komputerlər | ✅ | ✅ (Güc barı) | ✅ struktur sahələr | ✅ |
| Komponent/Monitor | ✅ | ✅ (yarısı skorlu) | ⚠️ boş → analiz tabına yönləndirir | ✅ (compKey) |
| Aksesuarlar, Ofis | ✅ | ✅ (spec yox → Güc «—», ən ucuz sıra) | ⚠️ boş | sınıq/mənasız (spec yox) |

**Büdcə tabı universal edildi** — əvvəl `value_score!=null` tələb edirdi (aksesuar/ofis-də scored=0 → boş). İndi `+r.price>=1`: scored kateqoriyalarda keyfiyyət filtri + Güc barı saxlanır, spec-siz kateqoriyalarda bütün məhsullar ən ucuzdan. `<1₼` küy (metrlə kabel) süzülür. **⚠️ Aksesuar/Ofis-də value_score/spec_score YOXDUR** (enrich onlara skor vermir — spec parse olunmur) → yalnız Cədvəl+Büdcə mənalıdır.

**Büdcə tabında alt-kateqoriya ayrımı** (`state.budgetSub`/`bindBudgetSub`) — çox-alt-kateqoriyalı kateqoriyalarda (Komponent/Monitor 12 alt-kat, Masaüstü 5) əvvəl bütün alt-katlar qiymət aralığında qarışırdı (monitor+SSD+GPU eyni banda — mənasız). İndi **📂 alt-kateqoriya çip seçici**, default **ən böyük alt-kat** (Monitor), «🔀 Hamısı» ilə qarışıq. Hər alt-kat homogen aralıqlar + öz Güc barı (monitor var, keys yox). `filtersBar(,,hideSub)` bu görünüşdə sub dropdown gizli. Tək-alt-kateqoriyalı (noutbuk) → seçici yoxdur.

**Komponent Cədvəl tabı yenidən quruldu** (`componentTable`/`bindBrandBreak`) — çox-alt-kateqoriyalı kateqoriyalarda Cədvəl: (1) 📂 alt-kateqoriya çip seçici (budgetSub, default Monitor), (2) 🏷 **brend üzrə təsnifat** çipləri (say ilə, kliklə filtr — seçilmiş alt-kat üzrə, top 16), (3) həmin alt-katın qiymət+parametr cədvəli. `filtered()` **skipBrand** param (breakdown brend filtrindən asılı deyil). Sub dropdown gizli, Brend dropdown qalır (bütün brendlər). Tək-alt-kateqoriyalı (noutbuk) → köhnə düz cədvəl. **Beləliklə həm Cədvəl, həm Büdcə komponentlərdə alt-kateqoriya-birinci.**

**Monitorlar Gaming/Ofis-ə ayrıldı** (`_monitor_usage` build_html-də, report layer): təzələnmə **≥100Hz və ya gaming açar söz** → Gaming; **≤75Hz/məlumatsız** → Ofis. 2386 monitor → 1282 Gaming / 1104 Ofis. usage='Komponent' → Gaming/Ofis-ə override (mövcud DB ilə dərhal işləyir; hər report-da yenidən hesablanır, DB-dəki köhnə dəyəri korrektləyir). Nəticə: İstifadə filtri + Gaming/Ofis KPI monitorları əhatə edir. Büdcə/Parametr sətirlərində `usageTag` (🎮/💼). ⚠️ Excel-də (report_excel) hələ 'Komponent' — yalnız HTML dashboard-da düzəldilib.

---

## 🟢 Canlıda nə var

| Yer | URL | Vəziyyət |
|-----|-----|----------|
| **VPS (Hostinger)** | http://187.127.91.112:8090/ | ✅ Canlı — bu session dashboard yeniləndi |
| **GitHub Pages** | https://ilkin016.github.io/tapaz-radar/ | ✅ Canlı — bu session yeniləndi |

Hər ikisi eyni `out/dashboard.html`-i servis edir (17.6 MB, self-contained SPA). VPS-də `out/index.html → dashboard.html` symlink.

**Arxitektura (dəyişməz):** Mac çəkir → `scp` VPS-ə + `git push` Pages-ə. **VPS SCRAPE ETMİR** (Cloudflare datacenter IP-ni bloklayır — bax DECISIONS). VPS-in öz `tapaz-radar.timer`-i SÖNDÜRÜLÜB.

---

## 📊 Data (son run: 2026-08-10T12:20:33)

- **31,259 aktiv elan** · bu run-da **847 yeni** · ümumi 13 run
- DB-də ümumi (aktiv+köhnə): 31,954
- Kateqoriyalar (aktiv): noutbuklar 8,632 · komputer-avadanliqi 9,163 · komputer-aksesuarlari 6,888 · ofis-avadanliqi 3,818 · komputerler 2,758
- **Əhatə 100% təsdiqləndi** — tap.az rəsmi sayları ≈ DB aktiv sayları (fərq ±2, elan silinmə/əlavə lag-ı). Bax DECISIONS "adSearch feed enumersiyası".

---

## 🔨 Ən son dəyişikliklər — dizayn v2 + analiz + pagination (`radar/report_html.py`)

1. **Hər kateqoriya səhifəsində "📊 Alt-kateqoriya analizi" tabı** (sub-tab: Cədvəl ⇄ Analiz). Hər alt-kateqoriya **ayrıca panel**:
   - 💰 **Qiymət aralığına görə ən güclü parametrlər** (`bestBandsFor` — hər banda max `spec_score`)
   - 🎯 **Parametrə görə ən yaxşı qiymət** — noutbuk/masaüstü struktur sahələr (RAM/CPU/Yaddaş/GPU/Ekran); komponentlər `compKey` ilə `params` mətnindən (GPU model / SSD-RAM tutum / monitor ölçü), sanity guard + `COMP_JUNK` filtr + populyarlıq sıralaması.
2. **Pagination** — cədvəldə səhifələmə (25/50/100/200 seçimli, ‹Əvvəl 1 2 3 … N Sonra›, səhifə meta). Əvvəl yalnız ilk 400 render olunurdu. Filtr/sort/axtarış dəyişəndə `page=0`.
3. **Dizayn v2** — gölgəli kartlar, accent-zolaqlı KPI, zebra+hover cədvəl, sticky başlıq, sub-tab, gradient bar, cilalı brand-logo, focus-ring. Kateqoriya **nav kliki də** bütün filtrləri sıfırlayır.

Test: pagination (9163→184 səhifə, 100/səhifə→92 səhifə ✓), Komponent analizi (Monitor/SSD/GPU/RAM ayrı-ayrı, əsas dəyərlər üstdə ✓), JS konsol təmiz.

## 🔨 Əvvəlki dəyişikliklər (`radar/report_html.py`)

1. **İcmal səhifəsi tam yenidən quruldu** — kompakt + interaktiv (əvvəl "uzun uzadı gedən qrafiklər" şikayəti):
   - KPI zolağı (Elan/Yeni/Orta qiymət/Mağaza/Gaming/Ofis)
   - Kateqoriya kartları (gradient + hover, kliklə → o kateqoriya)
   - **Kliklənən qrafiklər** (Qiymət aralığı / Brend / İstifadə / Vəziyyət) → bara klik = filtr + cədvələ keç (`cbars`/`pick`/`bindCbars`)
   - Qiymət bandları: ≥2000 tək "2000+" bandına birləşdirildi (`bandDist`)
2. **💰 Büdcəyə görə ən yaxşı parametrlər** cədvəli (`bestPerBand` — hər qiymət bandında max `spec_score` model)
3. **🎯 Parametrə görə ən ucuz məhsullar** kartları (`cheapestPerParam` — RAM/CPU/Yaddaş/GPU üzrə hər dəyər üçün min qiymət)
4. **Parametr filtrləri** — RAM/CPU/Yaddaş/Ekran/GPU dropdown-ları (`distinct`/`psel`); GPU-da "✓ var (diskret)" / "— yox" seçimləri. Test: RAM=16 → 8632→2891 ✓
5. **Kateqoriya dəyişəndə BÜTÜN filtrlər sıfırlanır** (`bindFilters`-də `if(key==='cat')Object.assign(state,{...})`)
6. **Filtrləri təmizlə** düyməsi (`f_clear`)
7. CSS cilası: `.cbar` hover, gradient barlar, `.catcard` translateY+shadow

Vizual + JS təsdiq: bütün bölmələr render olunur, 35 kliklənən bar, JS xətası yoxdur.

---

## ⏰ Planlayıcı (Mac launchd)

- `com.tapaz.radar` — **YÜKLÜDÜR, status 0 (son run uğurlu)**
- Yol: `/Users/ilkin/tapaz-radar/run_daily.sh` ✓ (yüklü tərif təsdiqləndi)
- Cədvəl: **Bazar ertəsi + Cümə axşamı 09:00** (StartCalendarInterval, Weekday 1 və 4)
- `run_daily.sh` axını: `run.py` (tam skan) → `scp` VPS-ə → `deploy_github.sh`

---

## ⚠️ Yarımçıq / açıq suallar

- **Növbədəki tapşırıq:** istifadəçi "növbəti task"-ı sonra bildirəcək (bu session-da tapşırıq verilmədi).
- **`logs/launchd.err`-də köhnə sətirlər var** (`/Users/ilkin/Desktop/tapaz-radar/...: Operation not permitted`) — bunlar plist Desktop→~ köçürülməzdən əvvəlkidir. **Aktiv problem DEYİL** (yüklü tərif düz yoldadır). İstəsən `> logs/launchd.err` ilə təmizlə.
- Hər kateqoriya üçün **dəyər formulu** var, amma komponent alt-kateqoriyaları (aksesuar/ofis) üçün skorlar hələ noutbuk qədər incələnməyib — gələcək təkmilləşdirmə.

## 🔴 Bloker

- **Yoxdur.** Hər iki deploy canlı, planlayıcı işlək, əhatə 100%.

---

## ▶️ Növbədə (təklif)

1. İstifadəçinin "növbəti task"-ını gözlə.
2. (Ops.) `launchd.err`-i təmizlə ki, gələcəkdə köhnə xətalar çaşdırmasın.
3. (Ops.) Cümə axşamı 09:00 avtomatik run-dan sonra `logs/launchd.out`-u yoxla — ilk tam avtomatik dövr təsdiqi.
4. Komponent/aksesuar dəyər skorlarını incələ (istifadəçi istəyərsə).

Rollback təlimatları: `docs/RUNBOOK.md`. Memarlıq qərarları: `docs/DECISIONS.md`.
