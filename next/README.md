# Onboard-next bootstrap

`onboard-next` هو بداية التطبيق المستقل المبني بـRust. هذه الشريحة تنفذ عقد حالة محايداً للمنصة وجسرين أصليين لـWindows وmacOS، ثم تُنتج حزم preview غير موقعة قابلة للفحص في CI. لا تستبدل التطبيق الكلاسيكي Linux ولا تُسمى إصداراً مستقراً.

## ما يعمل في هذه الشريحة

| البند | Windows | macOS |
|---|---|---|
| تطبيق مستقل قابل للتشغيل | binary تشخيصي (`onboard-next`) | binary تشخيصي داخل `.app` |
| تقرير القدرات | JSON مع حدود `SendInput` | JSON مع حالة إذن Accessibility |
| إدخال افتراضي | `SendInput` بعملية ضغط/إفلات ضيقة، مع رمز فشل عند المنع | Quartz `CGEvent` بعد تحقق Accessibility |
| اتجاه العربية | `diagnose ar_SA` يعيد `rtl` | `diagnose ar_SA` يعيد `rtl` |
| الحزمة | مجلد Windows portable preview | `Onboard-next.app` preview |
| التوقيع أو التوثيق | غير مفعّل | غير مفعّل |

## حدود مقصودة

- لم تُدمج GTK4 في هذه الشريحة؛ لذلك لا يوجد بعد واجهة لوحة مفاتيح مرئية أو tray/status item أو حافظة وإيموجي على Windows/macOS.
- تبديل مصدر الإدخال معلن `read-only` إلى أن ينفذ Windows TSF وmacOS Text Input Services اختيار المصدر ذي التركيز مع اختبارات جلسة حقيقية.
- لا تحاكي الجسور اختصار تبديل لغة للمستخدم لأن دلالته تعتمد على تفضيلات النظام وقد ينتج سلوكاً غير موثوق.
- حزم preview غير موقعة وغير موثقة؛ لا تنشر كإصدار مستقر.

## أوامر محلية

```bash
cargo test --manifest-path next/Cargo.toml --workspace --locked
cargo run --manifest-path next/Cargo.toml --bin onboard-next -- diagnose ar_SA
```

في Windows، ينشئ `packaging/windows/build-preview.ps1` مجلداً محمولاً. في macOS، ينشئ `packaging/macos/build-preview.sh` بنية `.app` ويؤكد صحة `Info.plist`.

## الخطوة التالية

يضيف `M2` واجهة GTK4 Rust قابلة للوصول، ثم تخطيطات اللوحة المصغرة والحافظة والإيموجي والموضع المحفوظ. لا يبدأ توقيع Windows أو notarization في macOS قبل نجاح حزم الواجهة الأصلية واختبارات التشغيل.
