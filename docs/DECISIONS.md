# tap.az Radar — Memarlıq Qərarları (append-only)

> Yalnız memarlıq səviyyəli qərarlar. Xırda düzəlişlər STATE.md-də. Ən yenisi sonda.

---

## 2026-08-08 · Feed enumersiyası: `adSearch` GraphQL, SSR `?page=N` DEYİL

- **Qərar:** Kateqoriya elanlarını GraphQL `adSearch(filters:{categoryId}, source:DESKTOP).ads(first:100, after:cursor)` ilə çək; kursor = `base64(offset)`, bitiş `pageInfo.hasNextPage`.
- **Səbəb:** SSR `?page=N` səhifələri **VIP elanları hər səhifədə təkrarlayır** → dublikat + natamam əhatə. GraphQL feed təmiz, dublikatsız, `totalCount` verir.
- **Rədd edilən:** HTML `?page=N` skreypi.
- **Toxunulan:** `radar/tap.py` (`FEED_Q`, `crawl_category`).
- **⚠️ Dəyişmə xəbərdarlığı:** `source: DESKTOP` MÜTLƏQ (başqa source fərqli/boş nəticə verir). `totalCount`-u əhatə auditi üçün saxla.

## 2026-08-08 · Detail çıxarma: `__NEXT_DATA__` apolloState

- **Qərar:** Elan detalını `__NEXT_DATA__` → `props.pageProps.apolloState` → `Ad:<gid>` obyektindən oxu. Alt-kateqoriya = ad-ın `Məhsul kateqoriyası` property-si; vəziyyət = `Yeni?` (Bəli→Yeni, Xeyr→İkinci əl).
- **Səbəb:** DOM parse kövrək; apolloState struktur data verir. Alt-kateqoriya **avtomatik** gəlir — əl ilə ayırmağa ehtiyac yox.
- **Toxunulan:** `radar/tap.py` (`fetch_detail`). Metod detalları: memory `tapaz-extraction-method`.
- **⚠️** Telefon = `createCall` mutation, `adId = base64("gid://tap/Ad/<id>")`, `source: DESKTOP`.

## 2026-08-08 · "Yalnız yeni" = SQLite seen-set diff

- **Qərar:** `seen(category, ad_id, first_seen)` cədvəli; hər run `diff_new()` = cari feed ∖ görülmüş.
- **Səbəb:** Dashboard "🆕 yeni" ayrıca göstərməlidir; timestamp etibarsız, ID-diff dəqiqdir.
- **Toxunulan:** `radar/store.py`, `data/radar.db`.
- **⚠️** `seen` cədvəlini SİLMƏ — bütün "yeni" tarixçəsi ora bağlıdır. DB `.gitignore`-dadır.

## 2026-08-08 · Dəyər skoru təmizliyi (value_score guard)

- **Qərar:** `value_score` yalnız **real məhsul** üçün hesablanır: CPU var **VƏ** qiymət döşəməsindən yuxarı (noutbuk 130₼, masaüstü 150₼, komponent per-sub FLOOR) **VƏ** icarə deyil (icar/kiray yoxlanışı). Yoxsa `None`.
- **Səbəb:** Ucuz parça/aksesuar/icarə astronomik "dəyər" alıb reytinqi zibilləyirdi (məs. 30₼ GTX1650 → dəyər 1826).
- **Rədd edilən:** Bütün elanlara düz value formulu.
- **Toxunulan:** `radar/enrich.py` (FLOORS), `desktop.py`, `components.py`.
- **⚠️** Skorlama kateqoriyaya görə fərqlidir: noutbuk `0.40CPU+0.28RAM+0.22Yaddaş+0.10GPU`; masaüstü GPU-mərkəzli `0.35+0.20+0.18+0.27GPU`; komponent per-sub.

## 2026-08-09 · Dashboard: self-contained vanilla-JS SPA

- **Qərar:** Dashboard tək HTML faylı — data JSON kimi inline, vanilla JS SPA (naviqasiya/filtr/sort hamısı client-side). Build alət YOX.
- **Səbəb:** GitHub Pages + `python http.server` hər ikisi statik servis edir; heç bir backend/framework asılılığı olmamalıdır. Fayl özü-özünə yetər.
- **Rədd edilən:** React/Vue build; server-side render.
- **Toxunulan:** `radar/report_html.py`.
- **⚠️** Fayl ~17 MB (31k elan inline). Cədvəldə perf üçün ilk 400 sətir render olunur. Data strukturunu dəyişsən JS `DATA` sxemini də yenilə.

## 2026-08-09 · Telefon nömrələri public dashboard-da SAXLANIR

- **Qərar:** Satıcı telefonları həm lokal, həm public (VPS + Pages) versiyada göstərilir.
- **Səbəb:** İstifadəçi açıq təsdiq etdi — "satıcılar özləri nömrələrini public olsun deyə qoyublar".
- **Toxunulan:** `report_html.py` `build_html(..., public=)` — `public=True` telefonları boşaldır, amma **istifadəçi KEEP seçdi** (deploy-da `public=False`).
- **⚠️** Bu istifadəçinin şüurlu qərarıdır. Dəyişmədən əvvəl soruş.

## 2026-08-09 · Deploy: 2 yer, tək-commit force-push

- **Qərar:** (1) VPS-ə `scp out/dashboard.html out/tapaz_radar.xlsx`; (2) Pages-ə `deploy_github.sh` = `git commit --amend` + `git push --force`.
- **Səbəb:** Pages repo-su hər run 17 MB fayl alır — tarixçə saxlansa repo şişər. Tək-commit amend repo-nu kiçik saxlayır.
- **Rədd edilən:** Normal commit tarixçəsi (repo şişərdi); Git LFS (əlavə mürəkkəblik).
- **Toxunulan:** `deploy_github.sh`, `run_daily.sh`. Repo: github.com/ilkin016/tapaz-radar (Pages), github.com/ilkin016/tapaz-radar-app (kod).
- **⚠️** Pages repo tarixçəsi qəsdən 1 commit-dir. `git log` boş görünsə panik etmə.

## 2026-08-10 · 🔴 KRİTİK: Mac çəkir, VPS servis edir (Cloudflare)

- **Qərar:** Skreyp YALNIZ Mac-də (residential IP). VPS heç vaxt scrape etmir — yalnız hazır dashboard-u servis edir. VPS `tapaz-radar.timer` söndürülüb.
- **Səbəb:** tap.az Cloudflare arxasındadır; **datacenter IP-lərini (VPS) `cf-mitigated: challenge` ilə bloklayır** (403). Təsdiqləndi. Residential Mac IP keçir.
- **Rədd edilən:** VPS-də müstəqil skan (403 ilə uğursuz).
- **Toxunulan:** arxitektura; `radar/tap.py` (403/429/503 backoff `sleep(min(90,20*(i+1)))`); `run.py` (kateqoriya try/except — bir kateqoriya uğursuzluğu run-u dağıtmır).
- **⚠️** VPS-də `run.py` İŞLƏTMƏ — 403 alacaq. VPS yalnız `out/`-u servis edir.

## 2026-08-10 · Layihə Desktop→`~/tapaz-radar` (TCC)

- **Qərar:** Layihə `~/tapaz-radar/`-a köçürüldü (əvvəl `~/Desktop/tapaz-radar`).
- **Səbəb:** launchd Desktop-a TCC-görə girə bilmir → `Operation not permitted` (exit 126). Home qovluğu keçir.
- **Toxunulan:** plist yolları (sed ilə), `run_daily.sh` (`cd` script dir).
- **⚠️** plist-i dəyişəndə `launchctl unload && load` et — yoxsa köhnə tərif yüklü qalır. `logs/launchd.err`-də hələ köhnə Desktop-yol xətaları var (zərərsiz, köçürmədən əvvəlki).

## 2026-08-10 · VPS-də port 8090, mövcud xidmətlərə TOXUNMA

- **Qərar:** VPS dashboard `python http.server` port **8090**-da; `ufw allow 8090`. Port 80 (Caddy) və digər PM2/node xidmətlərinə toxunulmadı.
- **Səbəb:** VPS-də çoxlu mövcud production xidmət var (Caddy:80, PM2 node app-lar). Onları pozmamaq.
- **Rədd edilən:** nginx:80, Caddy reverse-proxy (mövcudu pozardı).
- **Toxunulan:** VPS `tapaz-radar-web.service` (systemd), ufw. Deploy açarı `~/.ssh/tapaz_radar_deploy`.
- **⚠️** VPS-də 80/443/mövcud portlara TOXUNMA. Yalnız 8090 bizimdir.

## 2026-08-10 · Planlayıcı: həftədə 2 dəfə (B.e + C.axş 09:00)

- **Qərar:** launchd `StartCalendarInterval` array — Weekday 1 və 4, saat 09:00.
- **Səbəb:** İstifadəçi "həftədə 2 dəfə sync" istədi (gündəlikdən azaldıldı).
- **Toxunulan:** `~/Library/LaunchAgents/com.tapaz.radar.plist`.

## 2026-08-10 · İcmal səhifəsi: kompakt + interaktiv (kliklənən qrafiklər)

- **Qərar:** İcmal-dakı qrafiklər kliklənən filtr girişinə çevrildi (bara klik → filtr + cədvələ keç). Qiymət bandları ≥2000 tək banda birləşdirildi. "Büdcəyə görə ən yaxşı parametrlər" + "parametrə görə ən ucuz" siyahıları əlavə olundu.
- **Səbəb:** İstifadəçi "uzun uzadı gedən qrafiklər"dən şikayət etdi, sürətli qərar üçün interaktivlik istədi.
- **Rədd edilən:** statik uzun bar siyahıları.
- **Toxunulan:** `radar/report_html.py` (`cbars`/`pick`/`bindCbars`/`bandDist`/`bestPerBand`/`cheapestPerParam`; parametr filtrləri `distinct`/`psel`; kateqoriya-reset `bindFilters`).
- **⚠️** Kateqoriya dəyişəndə bütün filtrlər QƏSDƏN sıfırlanır (`if(key==='cat')`). Bu istifadəçi tələbidir.

## 2026-08-10 · Alt-kateqoriya analizi + komponent parametr çıxarıcısı + pagination

- **Qərar (analiz):** Hər kateqoriya səhifəsində sub-tab ("Cədvəl" / "Alt-kateqoriya analizi"). Analiz tabı hər alt-kateqoriyanı **ayrıca panel** kimi göstərir: qiymət-bandına görə ən güclü (`bestBandsFor`, max `spec_score`) + parametrə görə ən ucuz.
- **Qərar (komponent parametrləri):** Noutbuk/masaüstü struktur sahələrdən oxunur; **komponentlərdə struktur sahələr BOŞDUR** (ram/cpu_fam/storage/gpu/screen = 0) — spec `params` mətnindədir. `compKey(r)` `params`-dan çıxarır: GPU model (RTX/GTX/RX regex), SSD/RAM tutum (TB/GB, 1–16384 GB sanity), monitor ölçü (yalnız `params`-dan, çünki elan başlığındakı dırnaq `241V8B/89"`→89″ yanlış tutulur). `COMP_JUNK` regex aksesuarları (protector/kabel/stand/lamp…) atır. Populyarlığa görə sıralanır (əsas dəyərlər üstdə, nadir böyük deyil).
- **Səbəb:** İstifadəçi "hər kateqoriya altında ona uyğun parametrlərə görə ən yaxşı qiymət və qiymətə görə ən yaxşı parametr, hər alt-kateqoriya ayrı" istədi. Komponentlər üçün struktur sahə olmadığından mətn-parser lazım oldu.
- **Rədd edilən:** `name`-dən parse (model nömrələrini tutur: "1200 TB", empty-box 40₼); tutuma görə sıralama (nadir 12TB/89″ üstə çıxırdı).
- **Qərar (pagination):** Cədvəl səhifələnir (`state.ps` 25/50/100/200, `state.page`), əvvəlki "ilk 400" limiti əvəzinə. Filtr/sort/axtarış/kateqoriya dəyişəndə `page=0`.
- **Toxunulan:** `radar/report_html.py` (`catAnalysis`/`bestBandsFor`/`relevantParams`/`compKey`/`cheapestByComp`/`COMP_JUNK`; `pager`/`bindPager`; `bindSubtabs`; `state.page/ps/catTab`; `filtered(base,skipSub)`).
- **⚠️** `compKey` monitor ölçüsünü YALNIZ `params`-dan oxu (name-dəki dırnaq artefaktı). Komponent skorları `spec_score`-a əsaslanır — komponent enrichment-i dəyişsən analiz də dəyişər.
