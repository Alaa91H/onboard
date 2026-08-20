#!/usr/bin/python3

import unittest

from Onboard.ClipboardHistory import ClipboardHistory


class FakeClipboard(object):

    def __init__(self, text=None):
        self.text = text
        self._handler = None
        self.stored = False

    def connect(self, _signal, handler):
        self._handler = handler
        return 1

    def disconnect(self, _handler_id):
        self._handler = None

    def wait_for_text(self):
        return self.text

    def set_text(self, text, _length):
        self.text = text

    def store(self):
        self.stored = True


class TestClipboardHistory(unittest.TestCase):

    def test_remember_keeps_newest_unique_text_with_limit(self):
        history = ClipboardHistory(FakeClipboard(), max_entries=3)
        history.remember("one")
        history.remember("two")
        history.remember("three")
        history.remember("two")
        history.remember("four")

        self.assertEqual(["four", "two", "three"], history.entries())

    def test_refresh_ignores_empty_and_remembers_system_text(self):
        clipboard = FakeClipboard("")
        history = ClipboardHistory(clipboard)
        history.refresh()
        self.assertEqual([], history.entries())

        clipboard.text = "مرحبا"
        history.refresh()
        self.assertEqual(["مرحبا"], history.entries())

    def test_select_promotes_entry_and_updates_system_clipboard(self):
        clipboard = FakeClipboard()
        history = ClipboardHistory(clipboard)
        history.remember("first")
        history.remember("second")

        self.assertTrue(history.select("first"))
        self.assertEqual("first", clipboard.text)
        self.assertTrue(clipboard.stored)
        self.assertEqual(["first", "second"], history.entries())
