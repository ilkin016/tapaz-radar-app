# tap.az Radar — Cari Vəziyyət

**Son yenilənmə:** 2026-08-10 (v3: qiymət 200₼ interval + CPU nəsil/seriya filtri + büdcə siyahıları İcmaldan alt-kateqoriya analizinə; əvvəl v2: alt-kat analizi + pagination + dizayn)

## 🆕 Ən son (v3)
- **Qiymət aralığı intervalları 200₼** oldu (İcmal qrafiki + alt-kat analizi cədvəlləri) — `band200(price)`.
- **CPU Nəsil + Seriya filtri** (yalnız noutbuk/masaüstü): Apple M1-4, Intel N-ci nəsil, Core Ultra Seriya, Ryzen N000; suffix U/H/HX/HS/HK/HQ/G/K/F/T/P/Y/M/MQ/QM. `cpuGen`/`cpuSer` cpu mətnindən parse+keş, `VALID_SUF` whitelist. Test: Intel 13-cü+HX → 148 (i7-13650HX).
- **«Büdcəyə görə ən yaxşı» + «parametrə görə ən ucuz» İcmaldan SİLİNDİ** — istifadəçi tələbi ilə artıq yalnız hər kateqoriyanın «Alt-kateqoriya analizi» tabında (hər alt-kat ayrı). İcmalda yönləndirici hint qaldı → İcmal indi kompakt (KPI + kart + 4 qrafik).
- **Alt-kateqoriya analizi peşəkarlaşdırıldı:** parametrlər rəngli **spec çiplərinə** (`specChips` — CPU/RAM/SSD/GPU/ekran; komponentlərdə params-split), «ən güclü» cədvəldə yanıldıcı dəyər badge yerinə **0-100 normallaşdırılmış Güc barı** (spec_score/maxSpec), panel başlığında **statistika** (elan·orta qiymət·yeni·mağaza), sərfəli-qiymət **ikonlu qruplar** + hizalanmış grid.

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
