# واجهة البناء الموحدة

يوفر الملف `tools/build.py` نقطة الدخول العامة الوحيدة لبناء Onboard والتحقق منه وإنتاج مرشحات الحزم والمعاينات الأصلية. تُشغِّل هذه الواجهة وصفات التغليف المتخصصة في الخلفية بدلاً من نسخ منطقها في مسارات التكامل المستمر؛ فتبقى `debian/` وملف RPM و`PKGBUILD` وmanifest Flatpak وملفا Windows/macOS مسؤولة عن صيغة الحزمة الخاصة بها، بينما يصبح اختيار الهدف والتحقق والإخراج موحداً.

> **المبدأ:** أمر واحد للمطور وCI، ووصفة خلفية واحدة لكل مدير حزم أو نظام تشغيل. لا تُدمج وصفات Debian أو RPM أو Arch أو Flatpak داخل ملف واحد لأنها عقود أصلية لتلك الأنظمة؛ بل تُستدعى من واجهة واحدة قابلة للتوسع.

## البدء السريع

نفّذ الأوامر من جذر المستودع. تستخدم كل الأوامر Python المضمّن مع بيئة المشروع ولا تتطلب مكتبات Python إضافية خارج المكتبة القياسية.

| الهدف | الأمر الموحد | المخرج أو الغرض |
| --- | --- | --- |
| تشخيص البيئة | `python3 tools/build.py doctor` | يعرض النظام والمعمارية والإصدار والأدوات المتاحة. |
| فحص وصفات الحزم | `python3 tools/build.py validate-recipes` | يتحقق من PKGBUILD وFlatpak والملفات المقفلة المطلوبة. |
| بناء Linux المحمول | `python3 tools/build.py portable --prepare` | يبني wheel وsdist ويشغل اختبارات Python/Rust/RTL العربية. |
| مرشح Linux العام | `python3 tools/build.py candidate linux --arch x64` | `release-out/linux-x64/` |
| حزمة Debian/Ubuntu | `python3 tools/build.py candidate debian --arch arm64` | `release-out/debian-arm64/` |
| حزمة Fedora/RHEL | `python3 tools/build.py candidate rpm --arch x64` | `release-out/rpm-x64/` |
| حزمة Arch | `python3 tools/build.py candidate arch --arch arm64` | `release-out/arch-arm64/` |
| Flatpak bundle | `python3 tools/build.py candidate flatpak --arch x64` | `release-out/flatpak-x64/` |
| جسر Rust الأصلي | `python3 tools/build.py native` | اختبارات وبناء release للـcrate `native/onboard-native`. |
| معاينة Windows | `python tools/build.py preview windows --arch x64` | ZIP وبيان provenance في `release-out/windows/`. |
| معاينة macOS | `python3 tools/build.py preview macos --arch arm64` | `.app` وZIP وDMG في `release-out/macos/`. |

يمكن تمرير `--version <version>` مع أمر `candidate` كحارس اتساق. ترفض الأداة المتابعة إذا لم تتطابق القيمة مع الإصدار المعلن في `pyproject.toml`.

## حدود المنصة المتعمدة

البناء أصلي للمضيف. لا تحاول الواجهة بناء RPM داخل Ubuntu أو معاينة macOS من Linux، بل تتحقق من النظام الحالي وتعيد رسالة واضحة. هذا يمنع إنتاج artifacts مضللة أو ثنائية غير أصلية، ويحافظ على تشغيل بنّاءات GitHub Actions لكل من x64 وARM64 في البيئة المطابقة.

| عائلة المخرج | النظام المضيف المطلوب | الوصفة الخلفية |
| --- | --- | --- |
| wheel وsdist واختبارات GTK | Linux | setuptools + Cargo + اختبارات مركزة |
| Debian | Debian/Ubuntu | تنفيذ مدمج في `tools/build.py` باستخدام `debian/` كبيانات وصفة. |
| RPM | Fedora/RHEL | تنفيذ مدمج في `tools/build.py` باستخدام `packaging/fedora/onboard.spec`. |
| Arch | Arch Linux | تنفيذ مدمج في `tools/build.py` باستخدام `packaging/arch/PKGBUILD`. |
| Flatpak | Linux مع Flatpak SDK | تنفيذ مدمج في `tools/build.py` باستخدام manifest Flatpak. |
| Preview Windows | Windows | تنفيذ مدمج في `tools/build.py`؛ لا wrapper PowerShell. |
| Preview macOS | macOS | تنفيذ مدمج في `tools/build.py`؛ لا wrapper shell. |

## عقد التكامل المستمر

ملف `.github/workflows/ci.yml` هو **نقطة الدخول الوحيدة** لـGitHub Actions: يستقبل كل Pull Request، وكل دفع إلى `main`، والتشغيل اليدوي. يضبط هذا الملف الصلاحية الدنيا `contents: read` ومجموعة الإلغاء المشتركة، ثم يشغّل بوابة الجودة أولاً. لا تبدأ أي مصفوفة بناء أو معاينة قبل نجاح تلك البوابة.

يحتوي المسار `.github/workflows/` على الملف `ci.yml` فقط. يضم هذا الملف بوابة الجودة ومصفوفات Linux المحمولة وجسور Rust وحزم Debian وRPM وArch وFlatpak ومرشحات Linux ومعاينات Windows وmacOS. بذلك لا توجد ملفات workflow وسيطة أو استدعاءات `workflow_call` أو تعريفات منفصلة قد تنحرف عن سياسة التوازي والصلاحيات والحارس الأولي للجودة.

| المرحلة داخل `ci.yml` | المسؤولية |
| --- | --- |
| `quality` | فحوصات الصياغة والأنواع والتنسيق والاختبارات وYAML والوصفات. |
| `portable-*` | حزم Linux المحمولة على Ubuntu وFedora، x64 وARM64. |
| `*-bridge` | جاهزية جسور Rust على Windows وmacOS، x64 وARM64. |
| `debian` و`rpm` و`arch-*` و`flatpak` | مرشحو جميع صيغ حزم Linux والمعماريات المدعومة. |
| `resolve-version` و`linux-release-candidate` | حارس الإصدار ومرشحات Linux وchecksums. |
| `windows-preview` و`macos-preview` | معاينات التطبيق الأصلية غير الموقعة، بما فيها مُثبّت Windows. |

تستدعي مراحل البناء `tools/build.py` بدلاً من تكرار منطق Python وCargo والتغليف. لا توجد نصوص بناء أو workflows وسيطة؛ تبقى فقط وصفات الحزم الأصلية التي تقرؤها الأداة مباشرةً. لا تنشئ هذه الطبقة إصداراً مستقراً أو توقيعاً أو نشرًا عاماً؛ تظل تلك العمليات محمية في workflow إصدار مستقر مستقل بعد تجهيز أسرار Apple وWindows وبيئة الموافقة المحمية.

## بوابة الجودة الصارمة

تعمل بوابة الجودة `Unified build quality gate` تلقائياً مع **كل Pull Request** ومع كل دفع إلى `main` بواسطة `ci.yml`. وهي المرحلة الإلزامية الأولى قبل المصفوفات الأصلية الثقيلة، ولا ترفع artifacts ولا تحتاج إلى أسرار أو صلاحيات كتابة.

| الفحص | ما الذي يضمنه |
| --- | --- |
| `py_compile` | سلامة صياغة واجهة البناء واختبارات العقد المعزولة. |
| Ruff lint وformat | غياب الاستيرادات غير المستخدمة وأنماط Python غير القياسية وانحراف التنسيق. |
| Mypy strict | صحة الأنواع الكاملة لواجهة `tools/build.py` واختبارات عقدها. |
| اختبارات العقد | ثبات أوامر CLI، تطابق الإصدار، وجود كل backends، وحظر تجاوز workflows للواجهة الموحدة. |
| Yamllint | سلامة YAML وحد 120 حرفاً مع دعم صيغ GitHub Actions الصحيحة. |
| فحص recipe | استمرار صلاحية PKGBUILD وmanifest Flatpak والملفات المقفلة. |

تعتمد البوابة الإصدارات المقفلة في `ci/requirements-quality.txt`. وعند فشلها يجب تصحيح السبب في المصدر؛ لا تُستخدم استثناءات lint أو تجاهلات type checking لإخفاء العيوب الجديدة.
