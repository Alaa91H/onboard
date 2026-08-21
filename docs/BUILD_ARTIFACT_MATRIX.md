# مصفوفة بناء وحزم Onboard

هذه الوثيقة هي عقد المخرجات القابلة للبناء في CI. يظل **Onboard Classic** منتج Linux المستقر أثناء الانتقال، بينما يمثل `onboard-next` نواة Rust وجسوراً تجريبية لـWindows وmacOS. لا يتحول artifact إلى إصدار مستقر لمجرد نجاح بنائه.

تُنفَّذ جميع نقاط البناء والتحقق والتغليف من الواجهة الموحدة [`tools/build.py`](UNIFIED_BUILD.md). تبقى وصفات كل مدير حزم خلفيات أصلية لضمان توافقها مع نظامها، ولا تُستدعى مباشرةً من workflows.

## أهداف Linux

| العائلة | المعماريات | artifact المطلوب في CI | مستوى النشر | بوابة التحقق |
|---|---:|---|---|---|
| Debian / Ubuntu | x64، ARM64 | حزم `.deb` من الشجرة المصدرية | مرشح قابل للتنزيل | `dpkg-buildpackage`، فحص محتوى `dpkg-deb`، واختبارات المصدر والترجمة |
| Fedora / RHEL | x64، ARM64 | RPM وSRPM من `onboard.spec` | مرشح قابل للتنزيل | `rpmbuild` داخل Fedora أصلي، فحص RPM واختبارات المصدر |
| openSUSE | x64، ARM64 | وصفة RPM متوافقة ومتحقق من صحتها | وصفة جاهزة للموزع | تدقيق spec وبناء openSUSE أصلي عندما تتوفر صورة/runner مدعومة |
| Arch / مشتقاتها | x64، ARM64 | حزمة pacman من `PKGBUILD` | مرشح قابل للتنزيل | `makepkg` غير الجذري، checksum للمصدر، وفحص محتوى الحزمة |
| Flatpak | x64، ARM64 | Flatpak bundle | معاينة sandbox | `flatpak-builder` وبناء bundle وفحص manifest والصلاحيات |
| توزيعات أخرى | x64، ARM64 | source tarball وwheel | مرشح قابل للتنزيل | PEP 517 وSBOM وSHA-256 وبيان الإصدار |

## أهداف سطح المكتب غير Linux

| المنصة | المعماريات | artifact الحالي | حالة الميزة | شرط الترقية إلى مستقر |
|---|---:|---|---|---|
| Windows | x64، ARM64 | portable ZIP غير موقّع | `onboard-next` bootstrap؛ جسر SendInput فقط | واجهة GTK4، تخطيط صغير، TSF، اختبارات فعلية، Authenticode |
| macOS | x64، ARM64 | `.app` وZIP/DMG preview غير موقعين | `onboard-next` bootstrap؛ Quartz مع إذن Accessibility | واجهة GTK4، TIS، status item، codesign وnotarization |

## قواعد الأمان والنشر

1. لا يحتوي workflow التجريبي على أسرار توقيع ولا ينشر GitHub Release.
2. يرفق كل artifact ببيان provenance وتجزئة SHA-256؛ تضاف SBOM إلى المخرجات التي تستخدم مخطط المصدر Python/Rust الحالي.
3. يجب أن يبنى كل artifact على نظامه ومعماريته الأصليين، ولا يكفي التحقق العابر للمنصات للنشر.
4. يمكن أن تفشل وظائف ARM64 ذات البنية المستضافة التجريبية كتحذير موثق فقط، لكن لا تصبح artifact مستقرة قبل نجاح اختبار ARM64 أصلي.
5. لا يدعي دليل البناء دعم format ما لم تنفذ CI مخرجه وفحصه فعلياً.

## مراجع التنفيذ

تدعم وثائق Flatpak الرسمية إنشاء single-file bundle من مستودع build عبر `flatpak build-bundle`، مع إمكانية تضمين مرجع runtime؛ لذا تعتمد المصفوفة bundle تجريبياً قابلاً للتنزيل ولا تدّعي أنه مستودع تحديثات دائم.[1] كما توثق GitHub runners متاحة لـUbuntu ARM64 وWindows ARM64 وmacOS Intel وApple Silicon، وهي أهداف بناء أصلية للمصفوفة.[2]

[1]: https://docs.flatpak.org/en/latest/single-file-bundles.html "Flatpak single-file bundles"
[2]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners "GitHub-hosted runners reference"

لتوفير ملف `dconf.pc` الذي يحتاجه امتداد Onboard داخل GNOME SDK، يضيف Flatpak module مبنياً من أرشيف dconf 0.49.0 المقفل بالتجزئة `16a47e49a58156dbb96578e1708325299e4c19eea9be128d5bd12fd0963d6c36`. اختير المصدر من manifest Flathub الخاص بـDconf Editor الذي يعمل على GNOME Platform 50.[3]

[3]: https://github.com/flathub/ca.desrt.dconf-editor/blob/master/ca.desrt.dconf-editor.json "Flathub Dconf Editor manifest"

تؤكد مراجعة مستودع Flathub shared-modules وجود وصفة `libcanberra/libcanberra.json` وpatch مرافق مخصص لبناء Flatpak، مع تحديث للوصفة في يناير 2026. ستُورَّد الوصفة في الشجرة أو تُقفل بمصدرها قبل استخدامها؛ لا يعتمد مرشح البناء على `master` متحرك.[4]

[4]: https://github.com/flathub/shared-modules/tree/master/libcanberra "Flathub shared module for libcanberra"

يبني Flatpak أيضاً libcanberra 0.30 من أرشيف مقفل بالتجزئة `c2b671e67e0c288a69fc33dc1b6f1b534d07882c2aceed37004bf48c601afa72`، مع patch Wayland المورّد محلياً من shared-modules؛ وتُحفظ ملفات pkg-config حتى يكتمل تجميع امتداد Onboard.[5]

[5]: https://raw.githubusercontent.com/flathub/shared-modules/master/libcanberra/libcanberra.json "Flathub libcanberra module"

تستخدم وظيفة Arch ARM64 صورة `agners/archlinuxarm` متعددة المعماريات بدلاً من صورة Arch الرسمية غير المتاحة على runner ARM64. توثق الصورة دعماً صريحاً لـAArch64 ونشراً بوسم `latest`؛ لذلك تظل الوظيفة مرشحاً قابلاً للتحقق وتُراجع دورياً قبل أي ترقية للنشر.[6]

[6]: https://github.com/agners/archlinuxarm-docker "Arch Linux ARM Docker images"

يبني dconf الحديث بوحدة Meson ويستخدم تكامل pkg-config داخل شجرة المصدر؛ لذلك تضبط خطوة Onboard في Flatpak مسار pkg-config من أدلة `/app` التي ولّدها البناء، بدلاً من افتراض مسار SDK ثابت.[7]

[7]: https://github.com/GNOME/dconf/blob/main/meson.build "GNOME dconf Meson build"

يولّد عميل dconf ملف pkg-config من مكتبة `dconf` مباشرةً عبر `pkg.generate`، ولذلك يُتوقع أن ينجح `pkg-config dconf` بعد ضم دليل pkgconfig الناتج إلى بيئة module Onboard.[8]

[8]: https://github.com/GNOME/dconf/blob/main/client/meson.build "GNOME dconf client build"
