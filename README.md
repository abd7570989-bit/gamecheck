# GameCheck 2.0

> **الحالة: قيد التطوير — المرحلة الثانية.** يوجد هيكل التطبيق (التنقل بين الأقسام السبعة، العربية والإنجليزية). الميزات تُضاف مرحلةً بعد مرحلة.

GameCheck تطبيق Windows مجاني يفحص مواصفات جهازك، ويكتشف الألعاب والبرامج المثبتة،
ويتصفح كتالوج Steam، ثم يقارن متطلبات أي لعبة بجهازك.

- التقنيات المخططة: Tauri 2 · Rust · React + TypeScript · SQLite
- المعمارية وخطة التنفيذ: [docs/v2/01-architecture.md](docs/v2/01-architecture.md)
- سجل الاختبارات: [docs/v2/testing.md](docs/v2/testing.md)

## تنزيل نسخة التجربة

كل تحديث للكود يبني تلقائيًا مثبّت Windows على جهاز Windows حقيقي (GitHub Actions)، ويشغّله ويختبره.
افتح تبويب **Actions** ← آخر تشغيل ناجح لـ **CI** ← قسم **Artifacts** ← `GameCheck-windows-installer`.

## للمطوّر

المتطلبات: Node.js 22، pnpm 10، Rust (stable). على Linux أيضًا مكتبات WebKitGTK.

```bash
pnpm install
```

```bash
pnpm dev
```

```bash
pnpm test
```

| المسار | المحتوى |
|---|---|
| `apps/desktop/src` | الواجهة (React + TypeScript) |
| `apps/desktop/src-tauri` | تطبيق Tauri وأوامر Rust |
| `crates/gc-core` | الأنواع المشتركة، ومنها `Probed` (قيمة معروفة أو «غير متاح» مع السبب) |
| `scripts/smoke-test.ps1` | يشغّل البرنامج المبني ويتأكد أن واجهته حُمّلت واتصلت بـ Rust |

## النسخة السابقة (1.0 — Python)

استُبدلت النسخة 1.0 بهذا المشروع. كودها الكامل محفوظ دون تغيير في الفرع
[`backup/v1-python`](https://github.com/abd7570989-bit/gamecheck/tree/backup/v1-python).

---

GameCheck غير مرتبط بشركة Valve أو Steam.
