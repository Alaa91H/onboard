# -*- coding: utf-8 -*-

import unittest

from Onboard import I18n


class FakeGtk(object):
    class TextDirection(object):
        LTR = "ltr-value"
        RTL = "rtl-value"

    class Widget(object):
        selected = None

        @classmethod
        def set_default_direction(cls, direction):
            cls.selected = direction


class TestTextDirection(unittest.TestCase):

    def test_normalizes_posix_and_bcp47_locales(self):
        self.assertEqual("ar", I18n.normalize_language_tag("ar_SA.UTF-8"))
        self.assertEqual("ar", I18n.normalize_language_tag("ar-SA"))
        self.assertEqual("", I18n.normalize_language_tag("C"))
        self.assertEqual("", I18n.normalize_language_tag(""))

    def test_arabic_gets_rtl_direction(self):
        environment = {"LANGUAGE": "ar:en_US", "LANG": "en_US.UTF-8"}
        self.assertEqual("rtl", I18n.get_text_direction(environment))
        self.assertTrue(I18n.is_rtl_locale(environment))

    def test_language_precedence_matches_gettext(self):
        environment = {
            "LANGUAGE": "en_US:ar",
            "LC_ALL": "ar_SA.UTF-8",
            "LC_MESSAGES": "ar_SA.UTF-8",
            "LANG": "ar_SA.UTF-8",
        }
        self.assertEqual("ltr", I18n.get_text_direction(environment))

    def test_empty_or_ltr_environment_stays_ltr(self):
        self.assertEqual("ltr", I18n.get_text_direction({}))
        self.assertEqual("ltr", I18n.get_text_direction({"LANG": "en_US.UTF-8"}))

    def test_apply_gtk_direction(self):
        FakeGtk.Widget.selected = None
        self.assertEqual("rtl", I18n.apply_gtk_text_direction(
            FakeGtk, {"LANG": "ar_SA.UTF-8"}))
        self.assertEqual(FakeGtk.TextDirection.RTL, FakeGtk.Widget.selected)
        self.assertEqual("ltr", I18n.apply_gtk_text_direction(
            FakeGtk, {"LANG": "en_US.UTF-8"}))
        self.assertEqual(FakeGtk.TextDirection.LTR, FakeGtk.Widget.selected)
