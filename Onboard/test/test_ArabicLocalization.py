#!/usr/bin/python3

import gettext
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCALE_CATALOG = ROOT / "build" / "locale" / "ar" / "LC_MESSAGES" / "onboard.mo"
DESKTOP_ENTRY = ROOT / "build" / "desktop" / "onboard.desktop"


class TestArabicLocalization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(LOCALE_CATALOG.is_file(),
                       "The Arabic message catalog must be built before tests run")
        with LOCALE_CATALOG.open("rb") as catalog_file:
            cls.translation = gettext.GNUTranslations(catalog_file)

    def test_core_menu_labels_are_localized(self):
        expected = {
            "Onboard": "لوحة مفاتيح الشاشة",
            "_Preferences": "_تفضيلات",
            "_Help": "_مساعدة",
            "_Show Onboard": "أ_ظهر لوحة مفاتيح الشاشة",
            "_Hide Onboard": "_أخفِ لوحة مفاتيح الشاشة",
            "Show or hide Onboard": "إظهار لوحة مفاتيح الشاشة أو إخفاؤها",
        }
        for source, translated in expected.items():
            with self.subTest(source=source):
                self.assertEqual(translated, self.translation.gettext(source))

    def test_preferences_and_keyboard_labels_are_localized(self):
        expected = {
            "Key-repeat": "تكرار المفتاح",
            "Clipboard is empty": "الحافظة فارغة",
            "(empty line)": "(سطر فارغ)",
            "Input-source controller is unavailable": "متحكّم مصادر الإدخال غير متاح",
            "No input sources are configured": "لم يتم تكوين أي مصادر إدخال",
            "This Wayland compositor has no supported input-source API": "مُركِّب Wayland هذا لا يدعم واجهة برمجة تطبيقات لمصادر الإدخال",
            "Main keyboard": "لوحة المفاتيح الأساسية",
            "Other _Languages": "_لغات أخرى",
        }
        for source, translated in expected.items():
            with self.subTest(source=source):
                self.assertEqual(translated, self.translation.gettext(source))

    def test_desktop_entry_contains_arabic_application_metadata(self):
        self.assertTrue(DESKTOP_ENTRY.is_file(),
                        "The localized desktop entry must be built before tests run")
        content = DESKTOP_ENTRY.read_text(encoding="utf-8")
        self.assertIn("Name[ar]=لوحة مفاتيح الشاشة", content)
        self.assertIn("Name[ar]=إظهار لوحة مفاتيح الشاشة أو إخفاؤها", content)


if __name__ == "__main__":
    unittest.main()
