# GameCheck 2.0 — المرحلة الأولى: التحليل والمعمارية وخطة التنفيذ

> الحالة: **مسودة بانتظار الموافقة**. لم يُكتب أي كود تنفيذي بعد.
> تاريخ: 2026-11-06

---

## 0. ملاحظة صريحة عن بيئة التطوير

أعمل حاليًا داخل حاوية **Linux سحابية مؤقتة**، وليس على Windows. هذا يعني:

| ما أستطيع بناءه واختباره هنا فعليًا | ما يحتاج Windows حقيقيًا |
|---|---|
| محلل متطلبات Steam، محرك التوافق، قاعدة البيانات، المزامنة (مع خوادم وهمية للاختبار وخوادم Steam الحقيقية)، محللات ملفات المنصات (VDF/ACF/JSON) على عينات حقيقية، الواجهة كاملة | قراءة WMI وDXGI والسجل Registry، اكتشاف Microsoft Store، بناء المثبّت النهائي، اختبار كروت شاشة حقيقية |

**الحل المقترح:**
1. مستودع GitHub للمشروع (الحاوية تُحذف عند انتهاء الجلسة، فالمستودع هو النسخة الاحتياطية الحقيقية).
2. **GitHub Actions على `windows-latest`**: Windows حقيقي يُبنى عليه التطبيق ويُشغَّل عليه اختبار WMI/Registry/DXGI فعليًا. (ملاحظة: أجهزة CI لا تملك كرت شاشة حقيقيًا — تظهر "Microsoft Basic Render Driver" — وهذا بحد ذاته اختبار مفيد لحالة "لا يوجد GPU مخصص").
3. **اختبار على جهازك أنت**: لكل مرحلة تخص العتاد سأعطيك ملف تشغيل وأداة صغيرة تطبع ما قرأته من جهازك، لنقارنه بـ Task Manager / dxdiag.
4. لن أكتب "الاختبار نجح" إلا لما شُغِّل فعلًا، وسأذكر أين شُغِّل (Linux / Windows CI / جهازك).

---

## 1. معمارية المشروع

### 1.1 الصورة العامة

```
┌──────────────────────────── GameCheck.exe (Tauri 2) ─────────────────────────────┐
│                                                                                   │
│  ┌─────────────── WebView2: React + TypeScript ───────────────┐                   │
│  │ Home · Store · Library · My PC · Compatibility · Perf · Settings              │
│  │ TanStack Query (cache/استدعاءات) · i18next (AR/EN, RTL/LTR)                   │
│  └──────────────────────┬─────────────────────────────────────┘                   │
│                         │  IPC: أوامر Tauri مُنمّطة (tauri-specta)  + Events        │
│  ┌──────────────────────▼─────────────────────────────────────┐                   │
│  │                Rust Core (طبقة الأوامر + الخدمات)            │                   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │                   │
│  │  │ hardware  │ │  library  │ │   steam   │ │   compat    │  │                   │
│  │  │ WMI/DXGI/ │ │ ماسحات    │ │ sync +    │ │ requirements│  │                   │
│  │  │ Registry  │ │ المنصات   │ │ providers │ │ parser +    │  │                   │
│  │  └───────────┘ └───────────┘ └─────┬─────┘ │ engine+hwdb │  │                   │
│  │  ┌───────────┐ ┌──────────────┐    │       └─────────────┘  │                   │
│  │  │   perf    │ │  db (SQLite) │    │                        │                   │
│  │  │ tiers +   │ │ catalog.db + │    │                        │                   │
│  │  │ PresentMon│ │ user.db      │    │                        │                   │
│  │  └───────────┘ └──────────────┘    │                        │                   │
│  └────────────────────────────────────┼────────────────────────┘                   │
└───────────────────────────────────────┼───────────────────────────────────────────┘
                                        │ HTTPS
        ┌───────────────────────────────┼─────────────────────────────────┐
        ▼                               ▼                                 ▼
 Steam Store (بدون مفتاح)      GameCheck Steam Proxy               Steam OpenID
 appdetails / GetItems          (Cloudflare Worker، يحمل            steamcommunity.com/openid
 featuredcategories             مفتاح Web API كسرّ)                 
                                 GetAppList / GetOwnedGames /
                                 GetPlayerSummaries
```

### 1.2 مبادئ التصميم

1. **كل منطق حقيقي في Rust.** الواجهة لا تتصل بالإنترنت ولا بقاعدة البيانات مباشرة؛ تطلب من Rust عبر أوامر محددة. هذا يحمي المفاتيح، ويجعل المنطق قابلًا للاختبار دون واجهة.
2. **طبقة "مزوّدين" (Providers) معزولة لكل مصدر خارجي.** كل واجهة Steam غير رسمية وكل ماسح منصة له `trait` خاص، مع مستوى ثقة معلن (`Official` / `Unofficial` / `Heuristic`). استبدال مصدر لا يمس بقية التطبيق.
3. **Offline-first.** كل شاشة تقرأ من SQLite أولًا، ثم تُحدَّث من الشبكة إن توفرت. كل بيانة تحمل `fetched_at` وتُعرض "آخر تحديث".
4. **"غير متاح" قيمة صريحة.** كل حقل عتاد أو متطلب نوعه `Known(value) | Unavailable(reason)` — لا أصفار ولا قيم افتراضية مُخترعة.
5. **قاعدتا بيانات منفصلتان:**
   - `catalog.db` = بيانات Steam (قابلة لإعادة التنزيل؛ إن تلفت تُعاد بناؤها).
   - `user.db` = بيانات المستخدم (ألعاب مضافة يدويًا، عناصر مخفية، الإعدادات، لقطات العتاد، قياسات FPS). يُنسخ احتياطيًا تلقائيًا.
6. **صفر صلاحيات Administrator.** كل ما سأقرؤه متاح للمستخدم العادي (HKLM للقراءة، ProgramData، WMI، DXGI). الاستثناء الوحيد اختياري وموضّح (قياس FPS — انظر §6).
7. **قراءة فقط لملفات الألعاب.** لا كتابة ولا حذف ولا تشغيل لأي ملف تنفيذي للعبة. "حذف من القائمة" = إخفاء في `user.db` فقط.

### 1.3 نموذج البيانات (مختصر)

**catalog.db**
| جدول | الغرض |
|---|---|
| `apps` | appid، name، type (game/application/dlc/…)، last_modified، price_change_number، details_state |
| `app_details` | الوصف، الصور، تاريخ الإصدار، المطور/الناشر، is_free، JSON الخام + `raw_hash` لتجنب إعادة المعالجة |
| `app_requirements` | min/rec الخام (HTML) + الحقول المستخرجة (OS، CPU، RAM، GPU، VRAM، DirectX، Storage، SSD، ملاحظات) + `parser_version` |
| `prices` | (appid, country_code) → currency، initial، final، discount%، fetched_at |
| `genres`, `categories`, `app_genres`, `app_categories` | التصنيفات |
| `apps_fts` | فهرس بحث FTS5 للأسماء (يعمل Offline، يدعم العربية والإنجليزية) |
| `sync_state` / `sync_jobs` | مؤشرات المزامنة، الطوابير، المحاولات، آخر خطأ |
| `hw_cpus`, `hw_gpus`, `hw_aliases` | قاعدة مرجعية للعتاد (انظر §6) |

**user.db**
| جدول | الغرض |
|---|---|
| `hardware_snapshots` | لقطة JSON لكل فحص مع وقته (لعرض التغيرات) |
| `local_items` | الألعاب/البرامج المكتشفة: source، external_id، name، install_path، is_game، classification_reason، hidden، manual، steam_appid_match |
| `steam_account` | steamid64، persona، avatar_url، آخر مزامنة للمكتبة (لا كلمات مرور ولا رموز Steam) |
| `owned_games` | appid، playtime، last_played |
| `perf_measurements` | قياسات FPS الحقيقية من جهاز المستخدم (إن فعّلها) |
| `settings` | اللغة، المنطقة/العملة، فترات المزامنة… |

---

## 2. التقنيات والمكتبات

أوافق على المقترح (Tauri 2 + Rust + React/TS + SQLite) ولا أرى بديلًا أفضل:
- **Electron**: حجم ~150MB وذاكرة أعلى، والوصول لـ WMI/DXGI يحتاج إضافات C++ أصلية. Tauri يعطينا Rust مباشرة مع مثبت ~10MB.
- **WinUI/.NET**: ممتاز للوصول للنظام، لكن دعم RTL ثنائي اللغة وتصميم Dashboard مخصص أصعب، ولن نستفيد من نظام React.

### 2.1 Rust (src-tauri + crates)

| المكتبة | الاستخدام | ملاحظة |
|---|---|---|
| `tauri` 2.x | الإطار | |
| `tauri-plugin-opener` | فتح صفحة Steam، فتح مجلد التثبيت في Explorer | مقيّد عبر Capabilities بنطاقات محددة |
| `tauri-plugin-dialog` | اختيار مجلد/ملف عند "إضافة لعبة يدويًا" | |
| `tauri-plugin-log` + `tracing` + `tracing-appender` | سجلات أخطاء دوّارة في `%LOCALAPPDATA%\GameCheck\logs` | بدون بيانات شخصية |
| `tauri-plugin-single-instance` | نسخة واحدة + استقبال callback | |
| `tauri-plugin-updater` | تحديث التطبيق نفسه (موقّع) | المرحلة 9 |
| `tauri-specta` + `specta` | توليد أنواع TypeScript من أوامر Rust تلقائيًا | يمنع عدم التطابق بين الطرفين |
| `windows` (windows-rs) | DXGI، D3D11/12 feature level، Registry، Display، WinRT PackageManager | الحزمة الرسمية من Microsoft |
| `wmi` | Win32_Processor / VideoController / OperatingSystem / MSFT_PhysicalDisk | |
| `sysinfo` | ذاكرة، أقراص، معالج (مصدر احتياطي ومتعدد المنصات) | |
| `raw-cpuid` | اسم المعالج وميزاته (AVX2…) بدقة من CPUID | بعض الألعاب تتطلب AVX/AVX2 |
| `winreg` | قراءة السجل بأسلوب بسيط | |
| `rusqlite` (bundled, FTS5) + `rusqlite_migration` | SQLite + ترحيل المخطط | أفضل من tauri-plugin-sql لأن الواجهة لا تلمس القاعدة |
| `reqwest` (rustls) + `tokio` | HTTP غير متزامن | |
| `governor` + `backoff` | تحديد معدل الطلبات وإعادة المحاولة الأسية | |
| `keyvalues-parser` / `steamlocate` | قراءة VDF/ACF الخاصة بـ Steam | |
| `scraper` + `ammonia` | تحليل HTML المتطلبات + تعقيم الوصف قبل عرضه | حماية من XSS داخل WebView |
| `prost` | قراءة `product.db` الخاص بـ Battle.net (protobuf) | غير رسمي — انظر §5 |
| `keyring` | حفظ مفتاح Steam API الخاص بالمستخدم (إن اختار) في Windows Credential Manager | |
| `serde`, `serde_json`, `thiserror`, `anyhow`, `chrono`, `url` | أساسيات | |
| اختبارات: `wiremock`, `insta`, `proptest`, `tempfile` | محاكاة Steam/انقطاع/429، لقطات المحللات | |

### 2.2 الواجهة

| المكتبة | الاستخدام |
|---|---|
| React 19 + TypeScript + Vite | الأساس |
| TanStack Router | توجيه مُنمّط بين الأقسام السبعة |
| TanStack Query | تخزين مؤقت لنتائج الأوامر، حالات التحميل/الخطأ/Offline |
| TanStack Virtual | عرض كتالوج فيه عشرات آلاف العناصر بسلاسة |
| Zustand | حالة واجهة بسيطة (الفلاتر، اللغة) |
| Tailwind CSS v4 | التنسيق؛ استخدام **الخصائص المنطقية** (`ms-`/`me-`/`ps-`/`pe-`/`start`/`end`) لدعم RTL تلقائيًا |
| Radix UI (primitives) | قوائم، حوارات، تبويبات — قابلية وصول + `DirectionProvider` للـ RTL |
| i18next + react-i18next + ICU | الترجمة، الجمع العربي (مفرد/مثنى/جمع)، تنسيق أرقام وتواريخ وعملات عبر `Intl` |
| motion (Framer Motion) | انتقالات خفيفة فقط، مع احترام `prefers-reduced-motion` |
| lucide-react | أيقونات |
| خطوط مضمّنة محليًا: Inter + IBM Plex Sans Arabic | تعمل Offline، بلا اتصال بـ Google Fonts |
| Vitest + Testing Library | اختبارات الواجهة |

### 2.3 الخادم الوسيط (Steam Proxy)
- **Cloudflare Worker (TypeScript)** — مجاني حتى 100 ألف طلب/يوم.
- يحمل مفتاح Steam Web API كـ Secret، ولا يصل المفتاح للتطبيق أبدًا.
- انظر §3.4 للتفاصيل والبديل.

---

## 3. طريقة ربط Steam

### 3.1 خريطة الواجهات ومستوى ثقتها

| الحاجة | الواجهة | النوع | يحتاج مفتاح؟ | ملاحظات |
|---|---|---|---|---|
| قائمة كل التطبيقات + اكتشاف الجديد والمتغيّر | `IStoreService/GetAppList/v1` | **رسمية** (Steam Web API موثّقة) | نعم ⇒ عبر Proxy | ترقيم صفحات (`last_appid`, `max_results` حتى 50k)، فلترة `include_games/software/dlc`، **`if_modified_since`** و`last_modified` و`price_change_number` ⇒ تحديث تزايدي حقيقي. (البديل القديم `ISteamApps/GetAppList/v2` بدون مفتاح أُعلن إيقافه — لن نعتمد عليه) |
| تفاصيل لعبة: الوصف، الصور، الإصدار، التصنيفات، **المتطلبات min/rec**، السعر | `store.steampowered.com/api/appdetails` | **غير رسمية/غير موثّقة** | لا | مستقرة منذ سنوات لكنها غير مضمونة. حد معدل تقريبي **~200 طلب / 5 دقائق** لكل IP. التفاصيل الكاملة لتطبيق واحد في كل طلب. المتطلبات تأتي **HTML حرًا** |
| بيانات مختصرة لعدة ألعاب دفعة واحدة (اسم، صور، سعر، خصم) لقوائم المتجر | `IStoreBrowseService/GetItems/v1` | واجهة Web API لكنها غير موثّقة رسميًا بالكامل | لا (حسب الاختبار) | **سأتحقق منها فعليًا في المرحلة 4** قبل الاعتماد؛ إن لم تعمل نرجع لـ appdetails مع `filters=price_overview` الذي يقبل عدة appids |
| الأقسام المميزة/التخفيضات/الأكثر مبيعًا للصفحة الرئيسية | `store.steampowered.com/api/featuredcategories` | غير رسمية | لا | تُعرض كـ "لقطة وقت المزامنة"، لا كبيانات لحظية |
| تسجيل الدخول | Steam OpenID 2.0 | **رسمية** | لا | |
| اسم الحساب والصورة | `ISteamUser/GetPlayerSummaries/v2` | رسمية | نعم ⇒ Proxy | |
| مكتبة الألعاب المملوكة | `IPlayerService/GetOwnedGames/v1` | رسمية | نعم ⇒ Proxy | تحترم خصوصية الحساب تلقائيًا |
| صفحة اللعبة | `https://store.steampowered.com/app/{appid}` و `steam://store/{appid}` | — | — | زران: المتصفح / عميل Steam |

**العزل:** في الكود سيكون هناك `trait CatalogSource` و`trait DetailsSource` و`trait PriceSource`؛ كل واجهة غير رسمية في مجلد `steam/unofficial/` مع وسم `Reliability::Unofficial`، ويُعرض في الإعدادات مصدر كل بيانة. إذا تغيّر شكل الاستجابة: يُسجَّل الخطأ، تبقى البيانات المخزنة، ولا ينهار التطبيق.

### 3.2 نظام المزامنة

```
                 ┌──────────── Scheduler (Rust, background tokio task) ────────────┐
                 │                                                                  │
 [1] App List   ─┤ GetAppList عبر Proxy، صفحات 50k، if_modified_since = آخر مزامنة │
     (سريع)      │ ⇒ upsert في apps، يكتشف الجديد، يعلّم المتغيّر (last_modified↑)    │
                 │ ⇒ price_change_number تغيّر ⇒ السعر قديم                         │
                 │                                                                  │
 [2] Details    ─┤ طابور أولويات، وليس "تحميل الكل":                               │
     (بطيء، محدود│   P0: ما يفتحه المستخدم الآن (فوري)                              │
      بالمعدل)   │   P1: المملوكة + المثبتة محليًا                                    │
                 │   P2: الظاهرة في Featured/التخفيضات                              │
                 │   P3: المتغيّرة منذ آخر جلب (last_modified > details_fetched_at)  │
                 │   P4: الباقي تدريجيًا في الخلفية (اختياري، قابل للإيقاف)          │
                 │ governor: ≤ 1 طلب/1.6 ثانية تقريبًا (تحت الحد بهامش)            │
                 │ 429/5xx ⇒ backoff أسي + jitter؛ 3 محاولات ثم تأجيل             │
                 │ raw_hash مطابق ⇒ لا إعادة معالجة                                 │
                 │                                                                  │
 [3] Prices     ─┤ حسب منطقة المستخدم (cc)، تُحدّث عند تغيّر price_change_number    │
                 │ أو بعد مدة صلاحية (مثلًا 12 ساعة) للمعروضة                         │
                 └──────────────────────────────────────────────────────────────────┘
```

- **حقيقة يجب قولها بوضوح:** Steam فيه أكثر من 200 ألف تطبيق (مع DLC وغيره). بحد ~200 طلب/5 دقائق، جلب **التفاصيل الكاملة للكل** يستغرق أيامًا. لذلك: **القائمة الكاملة (الاسم + النوع) تُزامن في دقائق**، والتفاصيل تُجلب حسب الأولوية وعند الطلب. البحث بالاسم يعمل على الكتالوج كاملًا Offline عبر FTS5.
- **لا ادعاء لتحديث لحظي:** الواجهة تعرض "آخر مزامنة: منذ X" لكل نوع بيانات، و"السعر كما في <تاريخ>".
- **حالة الاتصال:** فحص دوري خفيف + اكتشاف فشل الطلبات ⇒ شارة `Online / Offline / Syncing / Rate-limited / Error` في الشريط العلوي.
- **الأسعار والعملات:** Steam يعيد السعر بعملة المنطقة (`cc`). المستخدم يختار المنطقة؛ لا نحوّل العملات بأنفسنا (لتجنب أرقام غير موثوقة). السعر غير المتوفر ⇒ "غير متاح في منطقتك".

### 3.3 Connect Steam (OpenID)

```
1. المستخدم يضغط Connect Steam
2. Rust يفتح خادم loopback مؤقت على 127.0.0.1:<منفذ عشوائي>
3. يُفتح متصفح النظام (وليس نافذة داخل التطبيق ⇒ المستخدم يرى عنوان steamcommunity.com الحقيقي)
   على https://steamcommunity.com/openid/login?openid.mode=checkid_setup&openid.return_to=http://127.0.0.1:<port>/cb&nonce...
4. المستخدم يسجّل الدخول في Steam نفسه (التطبيق لا يرى كلمة المرور إطلاقًا)
5. Steam يعيد التوجيه إلى loopback ⇒ Rust يستقبل الاستجابة
6. التحقق الإلزامي: إرسال openid.mode=check_authentication إلى Steam ⇒ is_valid:true
   + التحقق من return_to و nonce و claimed_id = https://steamcommunity.com/openid/id/<SteamID64>
7. إغلاق الخادم المؤقت فورًا
8. جلب الاسم والصورة والمكتبة عبر Proxy
```

- **الخصوصية:** إن كانت "تفاصيل الألعاب" خاصة، `GetOwnedGames` تعيد استجابة فارغة ⇒ نعرض رسالة واضحة: "مكتبتك خاصة في إعدادات Steam" + زر لصفحة إعدادات الخصوصية، ولا نخمّن الملكية.
- **بديل Offline:** إن كان Steam مثبتًا، `loginusers.vdf` يكشف الحسابات المسجلة على الجهاز، و`userdata/<id>/config/localconfig.vdf` يكشف الألعاب التي لُعبت. هذه بيانات **جزئية** (ليست كل المملوكات) وستُعرض بهذا الوصف.
- **تسجيل الخروج:** يحذف بيانات الحساب من `user.db`.

### 3.4 مشكلة مفتاح Steam Web API — قرار يحتاج موافقتك

مفتاح Steam Web API مرتبط بحساب Steam لصاحبه، وشروط Valve تمنع مشاركته، ولا يجوز وضعه داخل التطبيق (يمكن استخراجه من أي exe).

| الخيار | الوصف | المزايا | العيوب |
|---|---|---|---|
| **A. Proxy (موصى به)** | Cloudflare Worker تملكه أنت، يحمل المفتاح كـ Secret. التطبيق يطلب `/v1/owned-games` مثلًا. الـ Proxy يتحقق من OpenID ويصدر رمز جلسة قصير العمر، مع حد طلبات لكل IP وتخزين مؤقت | المستخدم النهائي لا يحتاج أي إعداد | يحتاج حساب Cloudflare مجاني ومفتاح Steam من حسابك؛ وجود خدمة يجب صيانتها |
| **B. مفتاح المستخدم** | في الإعدادات: "أدخل مفتاح Steam API الخاص بك" ⇒ يُحفظ في Windows Credential Manager | لا خادم | تجربة سيئة لغير المحترفين |
| **A + B** | Proxy افتراضيًا، مع خيار متقدم للمفتاح الشخصي | مرونة كاملة | أكثر عملًا قليلًا |

بدون مفتاح إطلاقًا: الكتالوج والتفاصيل والأسعار والمتطلبات **تعمل** (واجهات المتجر لا تحتاج مفتاحًا)، لكن قائمة التطبيقات التزايدية والمكتبة المملوكة لن تعمل.

---

## 4. طريقة فحص الجهاز

كل قراءة لها **مصدر أساسي + مصدر احتياطي**، وإن فشلا تُعرض "غير متاح" مع السبب في السجل.

| المعلومة | المصدر الأساسي | الاحتياطي | ملاحظات وتحديات |
|---|---|---|---|
| اسم المعالج | CPUID brand string (`raw-cpuid`) | WMI `Win32_Processor.Name` | |
| الأنوية/الخيوط | `GetLogicalProcessorInformationEx` | WMI `NumberOfCores` / `NumberOfLogicalProcessors` | معالجات Intel الهجينة (P-cores/E-cores) ⇒ نعرض التفصيل إن أمكن |
| ميزات المعالج | CPUID: SSE4.2، AVX، AVX2، AVX-512 | — | ألعاب حديثة تتطلب AVX2 |
| الذاكرة RAM | `GlobalMemoryStatusEx` | WMI `Win32_PhysicalMemory` (السعة، السرعة) | النظام يرى أقل قليلًا من المركّب (محجوز للـ iGPU) ⇒ نقارن بالمركّب فعليًا |
| كرت الشاشة | **DXGI** `IDXGIFactory6::EnumAdapterByGpuPreference` → `GetDesc1` | WMI `Win32_VideoController` | تجاهل `DXGI_ADAPTER_FLAG_SOFTWARE` (Basic Render Driver). عرض **كل** الكروت (لابتوب: Intel/AMD مدمج + NVIDIA) واختيار عالي الأداء للمقارنة |
| VRAM | DXGI `DedicatedVideoMemory` (64-bit دقيق) | Registry `HardwareInformation.qwMemorySize` | ⚠️ WMI `AdapterRAM` معطوب: 32-bit ويتوقف عند 4GB ⇒ **لن نستخدمه** للـ VRAM. الكروت المدمجة: ذاكرة مشتركة ⇒ تُعرض "مشتركة" لا "مخصصة" |
| إصدار التعريف | WMI `DriverVersion` / `DriverDate` | — | مفيد للتحذير من التعريفات القديمة |
| نظام التشغيل | `RtlGetVersion` (رقم البناء الحقيقي) + Registry `DisplayVersion` (مثل 24H2) | WMI `Win32_OperatingSystem` | `GetVersionEx` يكذب بسبب manifests ⇒ لن نستخدمه. Windows 11 = Build ≥ 22000 |
| 32/64-bit | `IsWow64Process2` / `GetNativeSystemInfo` | WMI `OSArchitecture` | دعم ARM64 أيضًا (Windows on ARM) |
| DirectX | إنشاء جهاز D3D12 ثم D3D11 واستعلام **أعلى Feature Level** (مثل 12_1، 12_2/Ultimate) | — | "DirectX 12" في dxdiag هو إصدار الـ runtime فقط وليس قدرة الكرت؛ ما يهم الألعاب هو Feature Level. لن نشغّل dxdiag (بطيء ~10 ثوانٍ وينشئ عمليات) |
| التخزين | `GetDiskFreeSpaceExW` لكل محرك | `sysinfo` | نوع القرص SSD/HDD/NVMe من WMI `MSFT_PhysicalDisk.MediaType/BusType` (namespace `root\Microsoft\Windows\Storage`) — لأن ألعابًا كثيرة "تتطلب SSD" |
| دقة الشاشة | `EnumDisplayDevices` + `EnumDisplaySettingsEx` لكل شاشة | — | الدقة الحقيقية + معدل التحديث، والتطبيق DPI-aware حتى لا يرى دقة مُصغّرة |

- **التنفيذ:** `trait HardwareProbe` مع `WindowsProbe` الحقيقي، و`FixtureProbe` يقرأ لقطات JSON حقيقية من أجهزة مختلفة (NVIDIA/AMD/Intel/لابتوب هجين/بدون GPU/VM) لاختبار المحرك على Linux وCI.
- **الأداء:** الفحص في خيط خلفي مع مهلة لكل مصدر (WMI قد يعلق أحيانًا) — الواجهة لا تتجمد.
- **Refresh Hardware:** يعيد الفحص ويحفظ لقطة جديدة، ويبين ما تغيّر.
- **أداة تشخيص:** `gamecheck-probe.exe` (سطر أوامر) تطبع كل ما قُرئ ومصدره — لنتحقق معًا على جهازك.

---

## 5. طريقة اكتشاف الألعاب الخارجية

كل ماسح مستقل (`trait LibraryScanner`) يُرجع عناصر مع `source` و`confidence` و`reason`. فشل ماسح لا يوقف الباقي.

| المنصة | المصدر | الموثوقية | ملاحظات |
|---|---|---|---|
| **Steam** | Registry `HKCU\Software\Valve\Steam\SteamPath` ⇒ `steamapps\libraryfolders.vdf` ⇒ `appmanifest_<appid>.acf` في كل مكتبة | عالية (صيغة مستقرة منذ سنوات) | يعطي appid مباشرة ⇒ ربط فوري بالكتالوج والمتطلبات. استبعاد الأدوات (Proton، Steamworks Redistributables appid 228980…) |
| **Epic Games** | `%ProgramData%\Epic\EpicGamesLauncher\Data\Manifests\*.item` (JSON) | عالية | `DisplayName`, `InstallLocation`, `LaunchExecutable`, `AppCategories` (للتمييز بين لعبة/إضافة) |
| **GOG** | Registry `HKLM\SOFTWARE\WOW6432Node\GOG.com\Games\<id>` | عالية | اختياريًا قاعدة GOG Galaxy (`galaxy-2.0.db`) — تُفتح **للقراءة فقط** وبنسخة مؤقتة كي لا نقفلها |
| **Ubisoft Connect** | Registry `HKLM\SOFTWARE\WOW6432Node\Ubisoft\Launcher\Installs\<id>\InstallDir` + مدخلات Uninstall `Uplay Install <id>` للاسم | متوسطة | ملف الكاش الخاص بهم ثنائي وغير موثق ⇒ لن نعتمد عليه |
| **EA App** | مدخلات Uninstall بناشر Electronic Arts + `__Installer\installerdata.xml` داخل مجلد اللعبة + `%ProgramData%\EA Desktop\` | متوسطة | EA تغيّر الصيغ كثيرًا (Origin ⇒ EA App)، لذا نجمع عدة مؤشرات |
| **Battle.net** | `%ProgramData%\Battle.net\Agent\product.db` (protobuf) | متوسطة/غير رسمية | المخطط موثق من المجتمع وليس من Blizzard ⇒ احتياطي: مدخلات Uninstall بناشر Blizzard |
| **Microsoft Store / Xbox** | WinRT `PackageManager.FindPackagesForUser("")` (المستخدم الحالي، بدون admin) | عالية للحزم | **التمييز لعبة/تطبيق:** وجود `MicrosoftGame.config` (ألعاب Gaming Services في `XboxGames`) + ملف `.GamingRoot` في جذر المحركات. حزم المتجر الأخرى تُصنّف "تطبيقات". مجلد `WindowsApps` محمي ⇒ لا نحاول دخوله |
| **البرامج العادية** | `HKLM\…\Uninstall`، `HKLM\WOW6432Node\…\Uninstall`، `HKCU\…\Uninstall` | عالية للوجود | استبعاد `SystemComponent=1`، التحديثات (`ParentKeyName`, `ReleaseType`)، والمكررات |

### التصنيف (لعبة أم برنامج) — بدون افتراضات
1. مصدره منصة ألعاب (Steam/Epic/GOG/…) ونوعه "لعبة" في بياناتها ⇒ **لعبة** (ثقة عالية).
2. برنامج عادي يطابق اسمه لعبة في كتالوج Steam (type=game) مطابقة قوية ⇒ **"لعبة محتملة"** — تظهر في قسم منفصل والمستخدم يؤكد أو يرفض.
3. غير ذلك ⇒ **برنامج**. يظهر في تبويب "البرامج" وليس في الألعاب.
4. المستخدم يستطيع دائمًا تغيير التصنيف يدويًا، ويُحفظ اختياره.

### العمليات
- **تحديث القائمة:** إعادة تشغيل الماسحات بالتوازي مع عرض التقدم.
- **فتح موقع التثبيت:** `explorer.exe /select,<path>` عبر opener — بعد التحقق أن المسار موجود ومجلد/ملف حقيقي.
- **إضافة يدوية:** اختيار مجلد أو ملف exe + الاسم + ربط اختياري بلعبة Steam (للحصول على المتطلبات). **لا نشغّل الملف**؛ نقرأ فقط معلومات الإصدار من ترويسته (VersionInfo) لاقتراح الاسم.
- **حذف من القائمة:** `hidden=1` في `user.db`، قابل للاسترجاع من الإعدادات. لا يلمس الملفات.
- **عرض المصدر:** شارة بالمنصة لكل عنصر.

---

## 6. محرك التوافق، الأداء، والإعدادات (التصميم)

### 6.1 تحليل المتطلبات
متطلبات Steam نص HTML يكتبه المطور بحرية، مثل:
`<strong>Processor:</strong> Intel Core i5-4460 / AMD FX-6300 or better<br><strong>Graphics:</strong> NVIDIA GTX 970 4GB or AMD RX 480`

المحلل (`gc-requirements`):
1. تقسيم حسب التسميات (OS، Processor، Memory، Graphics، DirectX، Storage، Additional Notes) — مع دعم التسميات المترجمة إن جُلبت بلغة أخرى (سنجلب المتطلبات دائمًا بالإنجليزية لتوحيد التحليل).
2. استخراج الوحدات: `8 GB RAM`، `50 GB available space`، `Version 12`، `64-bit`، `SSD required`.
3. استخراج **بدائل** المعالج/الكرت (`/`, `or`, `,`) ثم مطابقتها بقاعدة العتاد المرجعية.
4. كل حقل يحمل `confidence` و`raw_text`. ما لا يُفهم يبقى `Unparsed(raw)` ويُعرض نصه الأصلي بدل تخمينه.
5. اختبارات لقطات على **مئات العينات الحقيقية** من Steam.

### 6.2 قاعدة العتاد المرجعية (أصعب جزء من حيث البيانات)
لمقارنة "GTX 1060" بـ "RX 6600" نحتاج درجات أداء نسبية. التحدي: قواعد مثل PassMark وTechPowerUp لها شروط استخدام تمنع النسخ/الكشط.

**المقترح:**
- بناء قاعدة مفتوحة من **مواصفات علنية** (الجيل/المعمارية، عدد الأنوية/وحدات التظليل، الترددات، عرض نطاق الذاكرة، VRAM، Feature Level، سنة الإصدار) — مصادرها موثقة في `data/hwdb/SOURCES.md`.
- حساب **درجة تقريبية** (مثل TFLOPS معدّلة بعامل المعمارية للكروت، والأنوية × التردد × عامل IPC للجيل للمعالجات) ⇒ تُستخدم لتحديد **فئات** (أقل/مقارب/أعلى) وليس أرقامًا دقيقة، ومع وسم "تقريبي".
- أداة `tools/hwdb` لإعادة بناء القاعدة، وتُحدّث مع التطبيق أو عبر المزامنة.
- عتاد غير موجود في القاعدة ⇒ المكوّن "غير معروف" بدل التخمين.

### 6.3 منطق الحكم
لكل مكوّن: `Fail` (أقل من الأدنى) / `NearMin` / `MeetsMin` / `MeetsRec` / `ExceedsRec` / `Unknown`.

| النتيجة النهائية | الشرط |
|---|---|
| **غير مناسب** | أي متطلب أساسي `Fail` مؤكد: نظام 64-bit، إصدار Windows، RAM، GPU، VRAM، Feature Level، مساحة، CPU، تعليمات CPU (AVX2) |
| **غير معروف** | CPU أو GPU أو RAM (الأساسية) `Unknown`، أو لا توجد متطلبات أصلًا — مع عرض ما أمكن فحصه جزئيًا |
| **محدود** | كل شيء ≥ الأدنى، لكن مكوّن أساسي واحد على الأقل قريب من الحد الأدنى أو بين الأدنى والموصى بفارق كبير |
| **جيد** | كل شيء ≥ الأدنى ومعظم الأساسي ≥ الموصى به |
| **ممتاز** | كل الأساسي يتجاوز الموصى به بهامش واضح (مثلًا ≥ 30% في الدرجة) |

- كرت الشاشة **عامل أساسي إلزامي** — لا حكم "جيد" بناءً على CPU وRAM فقط.
- النتيجة تُعرض دائمًا مع **أضعف حلقة** ("كرت الشاشة هو العامل المحدد") ومستوى الثقة.
- نص صريح: "تحقيق الحد الأدنى يعني عادةً التشغيل على إعدادات منخفضة ودقة 720p–1080p، ولا يضمن سلاسة".
- المساحة: تُقارن بأكبر مساحة حرة **أو** بالمحرك الذي يختاره المستخدم.

### 6.4 تقدير الأداء — بدون أرقام مخترعة
- **لا توجد** واجهة مجانية مفتوحة موثوقة لـ FPS لكل (لعبة × معالج × كرت × إعدادات). لن نعرض FPS تقديريًا محسوبًا.
- **ما سنعرضه:**
  1. **قياسات حقيقية من جهاز المستخدم نفسه** (اختياري): دمج **PresentMon** من Intel (مفتوح المصدر، MIT، يقيس الإطارات عبر ETW). نشغّل الملف الرسمي الموقّع فقط بعد التحقق من توقيعه (وليس "ملفًا مجهولًا"). ⚠️ يحتاج صلاحية Administrator **أو** عضوية مجموعة "Performance Log Users" — سنشرح ذلك للمستخدم ولن نطلب admin تلقائيًا. النتيجة: متوسط FPS و1% Low مع الإعدادات المسجّلة، ومصدرها "قياسك أنت بتاريخ X".
  2. **مستوى وصفي** عندما يوجد أساس (نتيجة التوافق + فرق الدرجة عن الموصى به): مثل "متوقع أن يكون قريبًا من تجربة المتطلبات الموصى بها عند 1080p"، مع ذكر الأساس.
  3. **غير متاح** صراحةً في غير ذلك، مع العوامل المؤثرة (عنق الزجاجة، VRAM، نوع القرص، الدقة، التعريف، الحرارة في اللابتوب).
- اختيار الدقة (720p/1080p/1440p) والإعداد (Low/Medium/High/Ultra) يغيّر **المستوى الوصفي والعوامل**، ويفلتر القياسات الحقيقية المطابقة — ولا يولّد رقمًا.

### 6.5 اقتراح الإعدادات
- **طبقة عامة (مُعلَمة "إرشاد عام"):** الدقة المقترحة، Preset عام، توصيات حسب VRAM للخامات، V-Sync/حدّ الإطارات حسب معدل تحديث الشاشة، توصية الظلال والإضاءة حسب الهامش.
- **طبقة خاصة باللعبة (مُعلَمة "مؤكد"):** فقط عندما تأتي من مصدر موثوق عن اللعبة نفسها:
  - وصف API الرسومي من المتطلبات.
  - مصدر اختياري: **PCGamingWiki API** (يذكر دعم DLSS/FSR/XeSS، HDR، أنواع Anti-Aliasing…). ⚠️ ترخيصه **CC BY-NC-SA** (غير تجاري) — إن كان التطبيق تجاريًا لا يمكن استخدامه. قرار لك.
  - ملفات إعدادات منسقة يدويًا في `data/settings-profiles/` مع مصدرها.
- خيار مثل DLSS يُعرض فقط إذا: الكرت يدعمه (RTX) **و** اللعبة مؤكد دعمها. غير ذلك لا يظهر كخيار مؤكد.

---

## 7. التحديات التقنية والحلول

| # | التحدي | الحل |
|---|---|---|
| 1 | التطوير على Linux وهدف Windows | Windows CI حقيقي + أداة probe على جهازك + Fixtures حقيقية + تجميع تجريبي بـ `cargo-xwin` |
| 2 | مفتاح Steam API لا يجوز كشفه | Proxy على Cloudflare (أو مفتاح المستخدم في Credential Manager) |
| 3 | `appdetails` غير رسمي ومحدود المعدل | عزل في طبقة، governor، backoff، طابور أولويات، تخزين دائم، hash لتجنب التكرار |
| 4 | حجم الكتالوج (200k+) | قائمة كاملة خفيفة + تفاصيل عند الطلب/بالأولوية + FTS5 + قوائم افتراضية Virtualized |
| 5 | متطلبات Steam نص حر فوضوي | محلل متعدد المراحل + اختبارات على عينات حقيقية + "Unparsed" بدل التخمين |
| 6 | مقارنة العتاد تحتاج درجات أداء | قاعدة مرجعية من مواصفات علنية بمصادر موثقة، فئات تقريبية معلنة |
| 7 | VRAM من WMI خاطئ فوق 4GB | DXGI أساسي + Registry احتياطي |
| 8 | لابتوبات بكرتين | تعداد DXGI بتفضيل الأداء العالي وعرض الكل |
| 9 | DirectX "الإصدار" مضلل | Feature Level الفعلي عبر D3D12/D3D11 |
| 10 | صيغ المنصات تتغير (EA/Battle.net) | ماسحات مستقلة، مؤشرات متعددة، فشل معزول، وسم الثقة |
| 11 | التمييز بين لعبة وبرنامج | تصنيف بأسباب + "لعبة محتملة" بتأكيد المستخدم |
| 12 | FPS بدون بيانات | قياس حقيقي بـ PresentMon اختياري + وصفي فقط + "غير متاح" |
| 13 | تلف قاعدة البيانات | WAL، `PRAGMA quick_check` عند التشغيل، نسخ يومية `VACUUM INTO` (آخر 5)، عند التلف: إعادة تسمية `.corrupt-<time>` ⇒ استعادة آخر نسخة ⇒ وإلا إعادة بناء (الكتالوج يُعاد تنزيله) |
| 14 | XSS من وصف الألعاب HTML | `ammonia` لتعقيم HTML في Rust + CSP صارم في Tauri + حظر التنقل الخارجي داخل WebView |
| 15 | RTL مع أرقام/أسماء إنجليزية داخل نص عربي | خصائص CSS المنطقية، `dir="auto"` لأسماء الألعاب، عزل bidi (`<bdi>`) |
| 16 | WebView2 على Windows 10 | مثبت Tauri يضمّن bootstrapper لـ WebView2 |
| 17 | تحذير SmartScreen | يحتاج شهادة توقيع كود (تكلفة سنوية) أو Azure Trusted Signing — قرار في المرحلة 9 |
| 18 | التثبيت بدون admin | NSIS بوضع `currentUser` (تثبيت في `%LOCALAPPDATA%`) |
| 19 | الشروط القانونية | ذكر "غير مرتبط بـ Valve"، الالتزام بشروط Steam Web API، عدم استخدام شعار Steam بشكل مضلل |

---

## 8. هيكل مجلدات المشروع

```
GameCheck/
├── Cargo.toml                      # Rust workspace
├── package.json                    # pnpm workspace
├── pnpm-workspace.yaml
├── README.md
├── docs/
│   ├── 01-architecture.md          # هذا الملف
│   ├── steam-endpoints.md          # كل واجهة، نوعها، حدودها، تاريخ آخر تحقق
│   ├── testing.md                  # ما اختُبر وأين
│   └── decisions/                  # سجل القرارات (ADR)
│
├── apps/desktop/
│   ├── index.html
│   ├── vite.config.ts
│   ├── src/                        # الواجهة React + TS
│   │   ├── main.tsx
│   │   ├── app/                    # router, providers, layout (sidebar, topbar, status)
│   │   ├── pages/
│   │   │   ├── home/  store/  library/  my-pc/
│   │   │   ├── compatibility/  performance/  settings/
│   │   ├── components/
│   │   │   ├── ui/                 # أزرار، بطاقات، شارات... (Radix + Tailwind)
│   │   │   └── game/               # GameCard, RequirementsTable, VerdictBadge...
│   │   ├── features/               # hooks لكل مجال (useHardware, useCatalog...)
│   │   ├── lib/
│   │   │   ├── ipc/bindings.ts     # مُولّد تلقائيًا من Rust (tauri-specta)
│   │   │   ├── i18n/
│   │   │   └── format/             # أرقام، تواريخ، عملات عبر Intl
│   │   ├── locales/{ar,en}/*.json
│   │   ├── assets/fonts/           # خطوط محلية
│   │   └── styles/
│   └── src-tauri/
│       ├── tauri.conf.json
│       ├── capabilities/default.json   # أقل صلاحيات ممكنة
│       ├── icons/
│       └── src/
│           ├── main.rs  lib.rs  state.rs  error.rs
│           └── commands/           # hardware.rs, steam.rs, library.rs, compat.rs...
│
├── crates/
│   ├── gc-core/            # أنواع المجال المشتركة، Known/Unavailable، الأخطاء
│   ├── gc-db/              # مخطط SQLite، ترحيلات، مستودعات، نسخ احتياطي واستعادة
│   ├── gc-hardware/        # windows/ (wmi, dxgi, registry, display, storage) + fixture/
│   ├── gc-steam/
│   │   ├── official/       # Web API عبر Proxy، OpenID
│   │   ├── unofficial/     # appdetails, GetItems, featured — معزولة
│   │   └── sync/           # scheduler, queue, rate limit, backoff
│   ├── gc-library/         # scanners/{steam,epic,gog,ubisoft,ea,battlenet,msstore,uninstall}
│   ├── gc-requirements/    # تحليل HTML المتطلبات
│   ├── gc-hwdb/            # قاعدة العتاد المرجعية والمطابقة
│   ├── gc-compat/          # محرك التوافق
│   ├── gc-perf/            # المستوى الوصفي، الإعدادات، تكامل PresentMon
│   └── gc-probe-cli/       # gamecheck-probe.exe أداة التشخيص
│
├── services/steam-proxy/   # Cloudflare Worker (TypeScript) + اختبارات
│
├── data/
│   ├── hwdb/{cpus,gpus}.json + SOURCES.md
│   └── settings-profiles/
│
├── fixtures/               # عينات حقيقية للاختبار
│   ├── steam/ (acf, vdf, appdetails json)
│   ├── epic/ gog/ ubisoft/ ea/ battlenet/
│   └── hardware/ (لقطات: nvidia, amd, intel, hybrid-laptop, no-gpu, vm)
│
├── tools/                  # سكربتات: بناء hwdb، التقاط fixtures من Windows
└── .github/workflows/
    ├── ci.yml              # ubuntu: اختبارات المنطق | windows-latest: بناء + اختبارات النظام
    └── release.yml         # بناء المثبّت الموقّع (المرحلة 9)
```

---

## 9. خطة التنفيذ ومعايير القبول لكل مرحلة

| المرحلة | المخرجات | معيار "مكتملة" (اختبار فعلي) |
|---|---|---|
| 2. هيكل المشروع | Workspace، Tauri 2 + React، الشريط الجانبي بالأقسام السبعة (صفحات فارغة مُعلَمة "قيد البناء" دون أزرار وهمية)، AR/EN + RTL، CI | البناء ينجح على Windows CI، ونسخة `.exe` تعمل على جهازك |
| 3. فحص الجهاز | gc-hardware + صفحة My PC (قسم العتاد) + Refresh + probe CLI | اختبارات CI على Windows حقيقي + مطابقة مخرجات جهازك مع Task Manager/dxdiag + اختبارات fixtures لأنواع الكروت |
| 4. قاعدة البيانات وSteam | gc-db، gc-steam، المزامنة، Proxy، OpenID، صفحة Store | اختبارات ضد Steam الحقيقي + wiremock (انقطاع، 429، JSON معطوب) + اختبار قاعدة تالفة |
| 5. Library وMy PC | كل الماسحات، الإضافة اليدوية، الإخفاء، فتح المجلد | Fixtures لكل منصة + جهاز بلا ألعاب + تشغيل على جهازك |
| 6. محرك التوافق | gc-requirements، gc-hwdb، gc-compat، صفحة Compatibility | لقطات على مئات المتطلبات الحقيقية + حالات حدّية |
| 7. الأداء والإعدادات | gc-perf، PresentMon، صفحة Performance | قياس فعلي على جهاز Windows، حالة "غير متاح" |
| 8. التصميم واللغات والاختبارات | صقل الواجهة، ترجمة كاملة، اختبارات شاملة | مراجعة RTL لكل الصفحات، تقرير اختبارات `docs/testing.md` |
| 9. المثبّت | NSIS (+MSI اختياري)، Updater، توقيع | تثبيت/إزالة على Windows نظيف بدون admin |

---

## 10. سجل القرارات

| # | القرار | الحالة |
|---|---|---|
| 4 | التطبيق **مجاني غير تجاري** ⇒ يمكن استخدام PCGamingWiki API (CC BY-NC-SA) مع ذكر المصدر داخل التطبيق، وأي بيانات مشتقة منه تبقى بنفس الترخيص | ✅ معتمد (2026-11-06) |
| 6 | قياس FPS الحقيقي عبر **PresentMon** كميزة اختيارية يفعّلها المستخدم | ✅ معتمد (2026-11-06) |
| 1 | مستودع GitHub | ⏳ بانتظار إنشائه |
| 2 | مفتاح Steam API: مقترح A+B | ⏳ بانتظار التأكيد |
| 3 | قاعدة العتاد من مواصفات علنية بدرجات تقريبية | ⏳ بانتظار التأكيد |
| 5 | المنطقة/العملة: مقترح تلقائي من إعدادات Windows مع إمكانية التغيير | ⏳ بانتظار التأكيد |

### الأسئلة الأصلية

1. **مستودع GitHub**: هل لديك مستودع أضعه فيه المشروع؟ (ضروري للحفظ ولـ Windows CI).
2. **مفتاح Steam API**: الخيار A (Proxy)، B (مفتاح المستخدم)، أم A+B (موصى به)؟
3. **قاعدة العتاد المرجعية** من مواصفات علنية بدرجات تقريبية معلنة — موافق؟
4. **هل التطبيق تجاري؟** يحدد إمكانية استخدام PCGamingWiki (ترخيص غير تجاري).
5. **المنطقة/العملة الافتراضية** للأسعار (مثلًا السعودية SAR، أو US USD، أو تُحدد من إعدادات Windows).
6. **قياس FPS عبر PresentMon** (اختياري، يحتاج صلاحيات خاصة يمنحها المستخدم بنفسه) — موافق على إدراجه؟
