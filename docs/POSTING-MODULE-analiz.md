I have everything needed — all confirmed by live GraphQL introspection, JS bundle inspection, and DOM analysis of public pages (no login performed, no OTP/phone/password entered). Here is the full technical analysis.

---

# tap.az "Yeni elan + OTP login" modulu — Texniki Analiz

> Bütün tapıntılar **public müşahidə** ilə əldə olunub: GraphQL introspection (açıqdır), JS bundle qrepi, DOM/localStorage baxışı. **Heç bir hesaba login olunmayıb, heç bir OTP/telefon/parol daxil edilməyib, heç bir SMS tetiklənməyib.** Aşağıda "TƏSDİQLƏNDİ" = bilavasitə müşahidə; "EHTİMAL" = məntiqi nəticə.

---

## 0. Əsas kəşflər (bir baxışda)

| Komponent | Tapıntı | Status |
|---|---|---|
| Auth host | `hello.tap.az` (paylaşılan SSO) | TƏSDİQLƏNDİ |
| OTP backend | `https://api.digit-u.id` (`/auth`, `/auth/verify`) — Turbo/Bina/Tap ortaq "Digit" identity | TƏSDİQLƏNDİ |
| Session mübadiləsi | GraphQL `loginUser(accessToken: String!)` | TƏSDİQLƏNDİ |
| Session saxlama | httpOnly cookie + `localStorage._tapaz_auth_storage` (Zustand persist: `csrfToken`+`userInfo`) | TƏSDİQLƏNDİ |
| Elan yaratma | GraphQL `createAd(adParams: CreateAdAttributes!)` | TƏSDİQLƏNDİ |
| Şəkil yükləmə | `POST https://photos.tap.az/pond` (multipart `images[]`, FilePond) → `[{id, thumbnail_url}]` | TƏSDİQLƏNDİ |
| Elan yerləşdirmə səhifəsi | `/elanlar/new` (public görünür, submit-də auth) | TƏSDİQLƏNDİ |
| Yerli məhdudiyyət | Cloudflare — yalnız Mac residential IP keçir (radar ilə eyni) | TƏSDİQLƏNDİ (memory) |

---

## 1. OTP Login axını

### Endpoint-lər və mutation-lar (TƏSDİQLƏNDİ)
- Auth UI: `https://hello.tap.az/?return_to=<b64(dest)>&back_to=<b64(origin)>&phone=<opt>`
  - Telefon input `tel`, düymə "SMS-kod göndərilsin". Telefon validasiyası: regex `0(10|50|51|55|60|70|77|99)` (AZ operator prefiksləri).
- OTP API bazası: `https://api.digit-u.id` (production), `staging.digit-u.id/api`
  - `POST /auth` → SMS kod göndərir (telefon ilə)
  - `POST /auth/verify` → kodu yoxlayır → **accessToken** qaytarır
  - Cəhd limiti var: kodda `codeAttemptsExhausted`, `wrongCode`, `smsCodeIsComplete` state-ləri (kobud güc mühafizəsi).
  - `allowedHosts: [turbo.az, bina.az, tap.az]` — redirect yalnız whitelist host-lara.
- Session qurma (tap.az tərəfi): `mutation($accessToken:String!){ loginUser(accessToken:$accessToken){ entity … } }`
  - App accessToken-i **redirect URL query-sindən** (`?accessToken=…`) oxuyur və `loginUser`-ə ötürür.

### Axın (mətn diaqram)
```
İstifadəçi (bizim UI)
   │  telefon nömrəsi
   ▼
POST https://api.digit-u.id/auth            ──▶ tap.az SMS kod göndərir
   │  (istifadəçi telefonuna 6 rəqəmli kod gəlir)
   ▼
İstifadəçi kodu bizim UI-a daxil edir
   ▼
POST https://api.digit-u.id/auth/verify     ──▶ { accessToken }
   ▼
POST https://tap.az/graphql  loginUser(accessToken)
   ▼
tap.az: Set-Cookie (httpOnly session)  +  { entity: User, csrfToken }
   ▼
Session hazır → _tapaz_auth_storage-a (csrfToken, userInfo) yazılır
```

### Session modeli (TƏSDİQLƏNDİ + EHTİMAL)
- `localStorage._tapaz_auth_storage` = Zustand persist store. Anonim şəkli:
  `{state:{isAuthenticated, authStatus, userId, userInfo{id,legacyId,authenticationPhone,phone,name,email,emailConfirmed,shop,…}, csrfToken}, version:0}`
- **EHTİMAL:** əsl session — `loginUser` cavabındakı **httpOnly cookie** (document.cookie-də görünmür). `csrfToken` isə mutation-larda header kimi göndərilir (`X-CSRF-Token` tipli). Yəni sonrakı `createAd` üçün **həm cookie, həm csrfToken** lazımdır.
- Cookie ömrü/yeniləmə mexanizmi introspection-la görünmür → open question (aşağıda).

---

## 2. Elan yaratma axını

### Səhifə strukturu (`/elanlar/new`, TƏSDİQLƏNDİ)
Public görünür, addım-addım: **Kateqoriya seç → alt-kateqoriya → leaf** (kateqoriya ağacı + hər kateqoriyanın atribut sxemi SSR/apolloState-də öncədən yüklənir, əlavə sorğu yoxdur). Leaf seçiləndə forma açılır.

Noutbuklar kateqoriyası üçün müşahidə olunan sahələr (real `name` atributları):
| Etiket | Sahə | Tip |
|---|---|---|
| Kateqoriya * | categoryId | seçim |
| Marka * | collection atribut | dropdown (kateqoriya-spesifik) |
| Yeni? | `boolean.769` | checkbox |
| Çatdırılma? | `boolean.858` | checkbox |
| Şəhər * | regionId (default Bakı) | dropdown |
| Qiymət, AZN * | `price` | text |
| Elanın başlığı * | `title` | text |
| (təsvir) | `body` | textarea (placeholder "Üstünlüklərini və vacib məqamları qeyd edin") |
| Adınız * | `contact.name` | text |
| E-mail * | `contact.email` | email |
| Mobil nömrə * | `contact.phones.0` | tel |
| razılaşma | checkbox | "İstifadəçi razılaşması ilə razı" |
| — | "Elanı əlavə et" | submit |

> Qeyd: bu **guest** formasında şəkil sahəsi YOXDUR (`input[type=file]`=0). Şəkil yükləmə auth-lu/ayrı addımdadır.

### Mutation (TƏSDİQLƏNDİ, introspection + bundle)
```graphql
mutation($adParams: CreateAdAttributes!){
  createAd(adParams:$adParams){ entity{ id … } errors{ message path } }
}
```
`CreateAdAttributes` input sahələri (dəqiq sxem):
```
categoryId:  ID!          # məcburi
regionId:    ID!          # məcburi (şəhər)
title:       String
body:        String
price:       Float
photoIds:    [ID!]        # /pond-dan qayıdan şəkil ID-ləri
propertySet: PropertySetAttributes!   # kateqoriya atributları
contactAttributes: ContactAdAttributes!
source:      SourceEnum!  # DESKTOP | MOBILE | API | APP
flowId:      ID           # createAdSubmission-dan
```
`ContactAdAttributes`:
```
contactType: ContactTypeEnum!   # CALLS_AND_MESSAGES | ONLY_CALLS | ONLY_MESSAGES
name:  String!
email: String!
phones:[String!]!
jwt:   String            # (guest üçün telefon-sahiblik sübutu; login-də session var)
```
`PropertySetAttributes` (**atribut kopyalamanın açarı**):
```
boolean:    [{ legacyId: ID!, value: Boolean }]   # məs {legacyId:"769", value:true}  ("Yeni?")
collection: [{ legacyId: ID!, value: String! }]   # məs Marka → {legacyId:<attrId>, value:<optionId>}
range:      [{ legacyId: ID!, value: Float! }]     # ədədi atributlar
```
> `legacyId` = formadakı `boolean.769`-dakı **769**. Yəni köhnə elanın hər property-si `legacyId + value` kimi birbaşa bura map olunur.

### Yardımçı flow mutation (TƏSDİQLƏNDİ)
```
createAdSubmission(flowId:ID, status:AdSubmissionStatusEnum!, source:SourceEnum!, categoryId:ID)
   AdSubmissionStatusEnum = START | CATEGORY_SELECT | RELOAD | CANCELLED
```
Bu, çox-addımlı sessiyanı izləyir; `flowId` → `sessionStorage.adSubmissionFlowId`-də saxlanır, sonra `createAd.flowId`-ə ötürülür (analitik/anti-abuse korrelyasiya). **EHTİMAL:** `createAd` üçün mütləq deyil, amma real klient axınına uyğun olmaq üçün göndərmək daha təhlükəsizdir.

### Digər lifecycle mutation-ları (TƏSDİQLƏNDİ, mövcuddur)
`updateAd`, `destroyAd`, **`prolongAd`** (köhnə elanı uzatma/bərpa — bax risklər), `createPayment`/`payForAdByPrepaidBundle` (VIP/premium).

### Köməkçi query-lər (TƏSDİQLƏNDİ)
`categories`/`category`/`categoryEntities`, `regions`, `formElements` (kateqoriyanın atribut sxemi — legacyId+options), `property`/`propertyOptions` (option legacyId axtarışı), `currentUser`/`userDetails` (login-dən sonra profil), `phoneConfirmationExistence`, `ad`/`adDetails` (köhnə elanı oxumaq), `templatePhotos`.

---

## 3. Şəkil yükləmə axını (TƏSDİQLƏNDİ)

GraphQL-də **upload mutation YOXDUR**. Ayrı REST servis:
```
POST https://photos.tap.az/pond?lang=az
  Content-Type: multipart/form-data
  body: images[] = <fayl>          (FilePond kitabxanası, /pond endpoint)
  → cavab: [{ id: <photoId>, thumbnail_url: <url> }]
```
- Qayıdan `id` → `createAd.photoIds` massivinə düşür.
- CDN/göstərmə: `tap.azstatic.com` (assetHost), şəkil host `photos.tap.az`.
- **EHTİMAL:** `/pond` authlu-dur (session cookie tələb edir) — real axında istifadəçi login olub yükləyir. Yoxlanmalıdır (open question).
- Köhnə elanın şəkilləri `adDetails.photos { id url }`-da gəlir → **yenidən post üçün köhnə photoId-lər YARAMIR**; şəkilləri `url`-dən **endirib yenidən `/pond`-a yükləmək** lazımdır (yeni ID-lər alınır).

---

## 4. Auth/sessiya modeli (yekun)

```
[Digit SSO: api.digit-u.id]  ──accessToken──▶  [tap.az GraphQL loginUser]
        ▲ phone+OTP                                   │
        │                                             ▼
[hello.tap.az UI]                        httpOnly session cookie (əsas)
                                         + _tapaz_auth_storage {csrfToken, userInfo}
                                         ──▶ hər mutation: cookie + csrfToken header
```
- Bir hesab = bir telefon (`authenticationPhone`).
- Bizim modul üçün: accessToken → loginUser → **cookie jar + csrfToken**-u saxlayıb bütün sonrakı `createAd`/`/pond` çağırışlarında istifadə etmək kifayətdir.

---

## 5. ToS / hüquqi / təhlükəsizlik

**tap.az qaydalarından (public, /pages/rules, /pages/terms):**
- **Avtomatlaşdırma/bot/scraping/API açıq şəkildə QADAĞAN EDİLMİR** — nə rules, nə terms-də sərbəst müşahidə olunan hissədə belə bənd tapılmadı. (Yəni açıq ToS pozuntusu yoxdur, amma "yoxluq ≠ icazə".)
- ‼️ **Dublikat elan qaydası (ƏSAS RİSK):** "Tamamilə eyni məzmunlu və ya məna baxımından oxşar elanlar" **30 gün ərzində** qadağandır. Silinmiş/bitmiş elanı eyni məzmunla təkrar yerləşdirmək pozuntudur → **elanın silinməsi + istifadəçinin bloklanması**. Yeni əlaqə/hesablardan təkrar cəhdlər xüsusi cəzalandırılır.
- **Tək hesab:** bir şəxs = bir hesab; çoxlu hesab avtomatik bloklanır.
- **Aylıq kateqoriya limiti:** hər kateqoriyada aylıq elan limiti var (`/profile/ad-placement-limits` route + `packagesList`); aşırmaq üçün ödənişli xidmət.
- **Terms 3.3:** istifadəçi doğrulama kodlarının məxfiliyinə cavabdehdir, icazəsiz girişə yol verməməlidir → **session/OTP saxlanması riski bizim üzərimizdə**.
- **Terms 2.11:** başqa şəxs/təşkilat adından hərəkət qadağandır → modul **YALNIZ istifadəçinin ÖZ hesabı** üçün istifadə olunmalıdır (istənilən use-case elə budur — legitimdir).

**Nəticə (legitimlik):** İstifadəçi öz telefonu ilə öz hesabına login olub öz elanını yenidən post edir — bu, prinsipcə legitim şəxsi avtomatlaşdırmadır. **Amma iki real təhlükə var:**
1. **Duplikat-detektor → blok.** Köhnə elanı **eyni məzmunla, 30 gün içində, yeni `createAd` kimi** post etmək = birbaşa "oxşar elan" qaydasını pozur. tap.az-ın öz **`prolongAd` (bərpa/uzatma)** funksiyası artıq var — bitmiş elanı 30 gün içində pulsuz bərpa edir. Modul bunu nəzərə almalıdır.
2. **Session/OTP saxlama.** accessToken/cookie/csrfToken plaintext saxlanarsa oğurluq riski.

**CAPTCHA/rate-limit:** OTP-də cəhd limiti TƏSDİQLƏNDİ (`codeAttemptsExhausted`). digit-u/Cloudflare tərəfində CAPTCHA və ya SMS-send rate-limit **EHTİMAL** var (birbaşa görünmədi — open question). Cloudflare bütün 3 hostda (tap.az, api.digit-u.id, photos.tap.az) var → **datacenter/VPS IP bloklanır**, yalnız Mac residential IP işləyir.

---

## 6. Təklif olunan modul arxitekturası

**Prinsip:** radar sistemi ilə eyni — **Mac-local backend** (Cloudflare residential IP tələbi). VPS scrape/post edə bilmir.

```
┌───────────────────────── Mac (residential IP) ─────────────────────────┐
│                                                                          │
│  UI (local web / mövcud dashboard-a tab)                                 │
│   ├─ "Login" paneli: telefon → [Kod göndər] → kod → [Təsdiqlə]           │
│   └─ "Repost" paneli: köhnə elan nömrəsi → önizləmə → [Yenidən post et]  │
│         │                                                                 │
│  Local backend (Python, mövcud radar/ paketinə əlavə: poster.py)         │
│   ├─ AuthClient:  /auth, /auth/verify (digit-u) → loginUser → cookie jar │
│   │               session-i şifrəli saxla (keyring / macOS Keychain)      │
│   ├─ AdReader:    adDetails(gid) → categoryId, regionId, title, body,    │
│   │               price, properties(legacyId+value), photos[url]          │
│   │               (mövcud __NEXT_DATA__/apolloState metodu ilə)           │
│   ├─ PhotoReuploader: hər url → endir → POST /pond → yeni photoIds        │
│   ├─ PropertyMapper:  köhnə property → PropertySetAttributes             │
│   │                    (boolean/collection/range; option legacyId üçün     │
│   │                     formElements/propertyOptions ilə uyğunlaşdır)      │
│   └─ Poster: createAdSubmission → createAd(adParams) → entity.id / errors │
│                                                                          │
│  requests.Session (cookie jar) + X-CSRF-Token header + realistik UA      │
└──────────────────────────────────────────────────────────────────────────┘
        │ tap.az/graphql, photos.tap.az/pond, api.digit-u.id  (hamısı residential IP-dən)
        ▼
```

**OTP-ni istifadəçidən almaq (UI):** İki-addımlı forma — (1) telefon → "Kod göndər" düyməsi backend-i `/auth`-a vurur; (2) istifadəçi telefonuna gələn 6 rəqəmli kodu bizim UI-a yazır → backend `/auth/verify` → accessToken → `loginUser`. **Kod heç yerdə hardcode edilmir, hər dəfə istifadəçidən canlı alınır.** (Bu, təhlükəsizlik qaydalarına da uyğundur: kodu biz "daxil etmirik", istifadəçi öz sistemində öz koduну verir.)

**Session saxlama:** cookie + csrfToken → **macOS Keychain** (və ya `keyring` modulu), plaintext fayl YOX. Müddət bitəndə yenidən OTP.

**"Köhnə elanı seç → kopyala → post" axını:**
```
1. İstifadəçi elan nömrəsi (numeric ID) yazır
2. gid = base64("gid://tap/Ad/<id>")  → adDetails(gid) oxu
3. Sahələri çıxar: categoryId, regionId, title, body, price, contact, properties, photos[]
4. Şəkilləri endir → /pond → photoIds[]
5. propertySet qur (legacyId+value; collection üçün option legacyId həll et)
6. Önizləmə göstər (istifadəçi başlıq/qiymət/mətn redaktə edə bilsin — DUBLİKAT riskini azaltmaq üçün TÖVSİYƏ olunur)
7. istifadəçi təsdiqləyir → createAd(adParams, source:DESKTOP) → entity.id
8. Nəticə: yeni elan linki / xəta mesajı
```

---

## 7. Mərhələli icra planı

- **M0 — Auth PoC (read-only doğrulama):** `loginUser` axınını manual capture ilə təsdiqlə (istifadəçi öz brauzerində login olarkən DevTools Network-dən accessToken/cookie/csrfToken header adını görmək). CAPTCHA olub-olmadığını yoxla.
- **M1 — Login moduluru:** `/auth` + `/auth/verify` + `loginUser`; session-i Keychain-ə yaz; `currentUser` ilə "kiməm" yoxlaması.
- **M2 — AdReader:** mövcud extraction metodu ilə köhnə elanı tam oxu (properties + photo url-lər). (Bu hissə artıq həll olunub — radar-dan yenidən istifadə.)
- **M3 — PhotoReuploader:** `/pond`-a bir şəkil yüklə, `id` al (əvvəl test hesabı ilə TƏK şəkil).
- **M4 — PropertyMapper + createAd (dry-run):** `createAd`-ı əvvəl **`source:API` və ya real klik-önizləmə** ilə TƏK test elanı üzərində sına; `errors` massivini analiz et.
- **M5 — UI inteqrasiyası:** dashboard-a "Repost" paneli; önizləmə + redaktə (duplikat riskini azaltmaq).
- **M6 — Təhlükəsizlik cilası:** rate-limit özümüz (gündə N), session şifrələmə, log-larda token maskalama, "yalnız öz hesabı" bərkitməsi.

---

## 8. Açıq suallar (implementasiyadan əvvəl aydınlaşmalı)

1. **csrfToken header adı** (`X-CSRF-Token`?) və `loginUser` cavabının dəqiq sahələri — canlı login-də DevTools ilə təsdiq lazımdır (introspection response tipini gizlədir).
2. **`/pond` auth tələbi** — cookie/session lazımdırmı, yoxsa açıqdır? Multipart cavabın tam sxemi.
3. **CAPTCHA** — `api.digit-u.id/auth` SMS-send-də hCaptcha/turnstile və ya IP başına SMS rate-limit varmı?
4. **`collection` value semantikası** — `value:String!` option-un **legacyId**-sidir yoxsa mətnidir? (`propertyOptions`/`formElements` ilə yoxla.)
5. **`prolongAd` vs `createAd`** — istifadəçinin əsl niyyəti "bitmiş elanı bərpa" (onda `prolongAd`, dublikat riski YOX) yoxsa "yeni surət yarat"? Bu, məhsulun semantikasını və ToS riskini kökündən dəyişir.
6. **`createAd` üçün `flowId`/`createAdSubmission` məcburidirmi**, yoxsa birbaşa `createAd` keçir?
7. **Session ömrü** — cookie nə qədər yaşayır, refresh mexanizmi varmı (yoxsa hər dəfə OTP)?
8. **Duplikat-detektor həssaslığı** — nə qədər mətn dəyişikliyi "oxşar deyil" sayılır (blok riskini idarə etmək üçün).

---

### Yekun qiymət
Texniki cəhətdən modul **tam mümkündür** və mövcud endpoint-lər (loginUser, createAd, /pond) bunu birbaşa dəstəkləyir. Ən böyük risk **texniki deyil, siyasətdir**: eyni elanı 30 gün içində yeni `createAd` kimi post etmək tap.az-ın dublikat qaydasını pozub **hesab blokuna** apara bilər — ona görə (a) `prolongAd` alternativini, (b) məcburi önizləmə+redaktə, (c) öz rate-limitimizi daxil etmək kritikdir. Arxitektura radar ilə eyni səbəbdən **Mac-local** olmalıdır (Cloudflare residential IP).