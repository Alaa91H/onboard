# مراجع تقييم إعادة كتابة Onboard

## النتيجة الأولية

اللغة المناسبة للنواة الجديدة هي **Rust**. فهي تتيح بناء نواة آمنة وإدارة ملكية الذاكرة وحالة لوحة المفاتيح وجسور المنصات ضمن مشروع واحد، مع استدعاءات FFI ضيقة ومدققة للواجهات الخاصة بكل نظام.

## الإطار الرسومي

`eframe`/`egui` يوفّر تطبيقات أصلية عبر `run_native`، وخيارات حفظ الحالة، وضبط الخطوط من `CreationContext`، وخيارات النافذة. يصلح للوحة مفاتيح مصغرة ذات رسم مخصص وسلوك نافذة دقيق عبر Windows وmacOS وLinux. لا يزيل هذا الحاجة إلى جسر منصة؛ فهو واجهة فقط.

توفّر `gtk4-rs` واجهات Rust موثقة لـGTK4 وGio وGLib وPango. هي خيار مناسب لتكامل GNOME/Linux العميق، لكنها ليست السطح الرسومي الموحد المقترح لإصدار Windows وmacOS. يمكن استخدام GTK4 لاحقاً كواجهة Linux أصلية اختيارية من دون تغيير النواة.

## جسور الإدخال

توضح Microsoft أن `SendInput` يدرج أحداثاً في تدفق الإدخال، لكن يتأثر بعزل امتيازات UIPI؛ لذلك يجب أن يعرض الجسر قدرة مفهومة ورسالة واضحة عند عدم السماح بالكتابة في برنامج أعلى امتيازاً.

توثق Apple أن `CGEvent` يدعم إنشاء أحداث لوحة مفاتيح، وضع سلسلة Unicode، ونشر الحدث. لذلك يناسب جسر macOS مع ضرورة معالجة أذونات Accessibility في التطبيق.

## المصادر

- https://docs.rs/eframe/latest/eframe/
- https://www.gtk.org/docs/language-bindings/rust/
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
- https://developer.apple.com/documentation/coregraphics/cgevent
