# مصادر واجهات Windows وmacOS لجسور Onboard-next

تسجل هذه الوثيقة المصادر الرسمية التي تحدد الحدود التنفيذية للجسرين الأصليين. لا تعني الإشارة إلى API أن حزمة مستقرة أصبحت متاحة؛ النشر يظل مشروطاً ببناء أصلي واختبارات تشغيل وتوقيع كل منصة.

| المنصة | الواجهة | قرار التنفيذ في Onboard-next | المصدر الرسمي |
|---|---|---|---|
| Windows | `SendInput` | يستخدم الجسر عملية إدخال افتراضية ضيقة للضغط والإفلات فقط. يجب إبلاغ الفشل بوضوح لأن Windows قد يمنع الإدخال عبر UIPI عندما يكون الهدف عند مستوى تكامل أعلى. | [Microsoft: SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput) |
| Windows | `ActivateKeyboardLayout` | لا يستخدم كحل نهائي لتبديل لغة التطبيق المستهدف لأنه يغير تخطيط thread/process المستدعي. يبقى تبديل المصدر `read-only` إلى أن يكتمل محول TSF للهدف ذي التركيز. | [Microsoft: ActivateKeyboardLayout](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-activatekeyboardlayout) |
| macOS | Quartz `CGEvent` | ينشئ الجسر حدث لوحة مفاتيح فقط بعد التحقق من وصول Accessibility. يعيد حالة إذن مطلوبة بدل ادعاء نجاح عملية محظورة. | [Apple: CGEvent](https://developer.apple.com/documentation/coregraphics/cgevent) |
| macOS | Text Input Services | لا يحاكي الجسر اختصار تبديل المصدر؛ تظل القدرة `read-only` إلى أن يكتمل اختيار مصدر الإدخال عبر TIS مع اختبارات جلسة حقيقية. | [Apple: Keyboard input sources](https://developer.apple.com/documentation/appkit/nstextinputcontext/keyboardinputsources) |
| الواجهة المشتركة | GTK4 Rust | تعتمد واجهة `onboard-next` المخططة على gtk-rs وGTK4 بعد اجتياز عقد الجسر والحزم الأصلية. | [GTK: Rust bindings](https://www.gtk.org/docs/language-bindings/rust/) |

## أثر أمني

> يجب ألا يتجاوز أي جسر صلاحيات المنصة أو يتحول إلى حقن مفاتيح صامت. تعاد رموز قدرة وخطأ ثابتة، بينما تترجم الواجهة الرسالة المناسبة للمستخدم.

## المراجع

[1]: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput "SendInput"
[2]: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-activatekeyboardlayout "ActivateKeyboardLayout"
[3]: https://developer.apple.com/documentation/coregraphics/cgevent "CGEvent"
[4]: https://developer.apple.com/documentation/appkit/nstextinputcontext/keyboardinputsources "Keyboard input sources"
[5]: https://www.gtk.org/docs/language-bindings/rust/ "GTK and Rust"
