#!/usr/bin/python3

# Copyright © 2026 Onboard contributors
#
# This file is part of Onboard.

from __future__ import division, print_function, unicode_literals

import unittest

from Onboard.InputSources import (GnomeInputSourceBackend,
                                  InputSourceAvailability,
                                  InputSourceController,
                                  KdeInputSourceBackend,
                                  ReadOnlyInputSourceBackend,
                                  X11InputSourceBackend,
                                  create_backend)


class FakeVirtkey(object):

    def __init__(self, layouts="us+ara", group=0):
        self.layouts = layouts
        self.group = group
        self.locked_groups = []

    def get_layout_as_string(self):
        return self.layouts

    def get_current_group(self):
        return self.group

    def lock_group(self, group):
        self.locked_groups.append(group)
        self.group = group


class FakeKdeProxy(object):

    def __init__(self, layouts=None, active=0):
        self.layouts = layouts or ["us", "ara"]
        self.active = active
        self.calls = []
        self._callbacks = {}
        self._next_handler_id = 1

    def get_name_owner(self):
        return ":1.42"

    def connect(self, _name, callback):
        handler_id = self._next_handler_id
        self._next_handler_id += 1
        self._callbacks[handler_id] = callback
        return handler_id

    def disconnect(self, handler_id):
        del self._callbacks[handler_id]

    def call_sync(self, method, parameters, _flags, _timeout, _cancellable):
        self.calls.append((method, parameters))
        if method == "getLayout":
            return (self.active,)
        if method == "getLayoutsList":
            return (self.layouts,)
        if method == "setLayout":
            self.active = int(parameters[0])
            return ()
        if method == "switchToNextLayout":
            self.active = (self.active + 1) % len(self.layouts)
            return ()
        raise AssertionError("Unexpected D-Bus method: {}".format(method))

    def emit_layout_changed(self, signal_name="layoutChanged"):
        for callback in list(self._callbacks.values()):
            callback(self, self, signal_name, None)


class FakeGnomeProxy(FakeKdeProxy):

    def __init__(self, active="us"):
        FakeKdeProxy.__init__(self, active=0)
        self.sources = [("us", "English (US)", "EN"),
                        ("ara", "Arabic", "AR")]
        self.active_id = active

    def call_sync(self, method, parameters, _flags, _timeout, _cancellable):
        self.calls.append((method, parameters))
        if method == "ListSources":
            return (self.sources,)
        if method == "GetActiveSource":
            return (self.active_id,)
        if method == "ActivateSource":
            self.active_id = str(parameters[0])
            return (True,)
        if method == "SwitchToNext":
            source_ids = [source[0] for source in self.sources]
            index = source_ids.index(self.active_id)
            self.active_id = source_ids[(index + 1) % len(source_ids)]
            return (True,)
        raise AssertionError("Unexpected D-Bus method: {}".format(method))

    def emit_source_changed(self, signal_name="SourceChanged"):
        self.emit_layout_changed(signal_name)


class TestInputSources(unittest.TestCase):

    def test_x11_switches_group_and_confirms_active_source(self):
        virtkey = FakeVirtkey()
        backend = X11InputSourceBackend(virtkey)
        changed = []
        controller = InputSourceController(backend, changed.append)

        controller.start()
        self.assertEqual("0", changed[-1].id)
        self.assertTrue(controller.activate("1"))

        self.assertEqual([1], virtkey.locked_groups)
        self.assertEqual("1", changed[-1].id)
        self.assertEqual("ARA", changed[-1].short_name)

    def test_external_x11_group_change_refreshes_confirmed_source(self):
        virtkey = FakeVirtkey()
        changed = []
        controller = InputSourceController(X11InputSourceBackend(virtkey),
                                           changed.append)
        controller.start()
        self.assertEqual("0", changed[-1].id)

        virtkey.group = 1
        controller.refresh()
        self.assertEqual("1", changed[-1].id)

    def test_backend_selection_is_explicit_per_session(self):
        self.assertIsInstance(create_backend(FakeVirtkey(), False, False),
                              X11InputSourceBackend)
        self.assertIsInstance(create_backend(None, True, True),
                              KdeInputSourceBackend)
        self.assertIsInstance(create_backend(None, True, False, True),
                              GnomeInputSourceBackend)
        self.assertIsInstance(create_backend(None, True, False),
                              ReadOnlyInputSourceBackend)

    def test_kde_does_not_publish_before_desktop_confirmation(self):
        proxy = FakeKdeProxy()
        backend = KdeInputSourceBackend(proxy=proxy)
        changed = []
        controller = InputSourceController(backend, changed.append)

        controller.start()
        self.assertEqual(["0"], [source.id for source in changed])

        self.assertTrue(controller.switch_next())
        self.assertEqual(["0"], [source.id for source in changed])
        self.assertEqual("switchToNextLayout", proxy.calls[-1][0])

        proxy.emit_layout_changed()
        self.assertEqual(["0", "1"], [source.id for source in changed])
        self.assertEqual("ARA", changed[-1].short_name)

    def test_kde_set_layout_uses_requested_index_then_signal_confirms(self):
        proxy = FakeKdeProxy()
        backend = KdeInputSourceBackend(proxy=proxy)
        changed = []
        controller = InputSourceController(backend, changed.append)
        controller.start()

        self.assertTrue(controller.activate("1"))
        self.assertEqual("setLayout", proxy.calls[-1][0])
        self.assertEqual((1,), proxy.calls[-1][1])
        self.assertEqual("0", changed[-1].id)

        proxy.emit_layout_changed()
        self.assertEqual("1", changed[-1].id)

    def test_kde_layout_list_change_refreshes_current_source(self):
        proxy = FakeKdeProxy(layouts=["us", "ara"], active=1)
        backend = KdeInputSourceBackend(proxy=proxy)
        changed = []
        controller = InputSourceController(backend, changed.append)
        controller.start()
        self.assertEqual("1", changed[-1].id)

        proxy.layouts = ["us", "ara", "de"]
        proxy.emit_layout_changed("layoutListChanged")
        self.assertEqual("1", changed[-1].id)
        self.assertEqual(3, len(controller.list_sources()))

    def test_gnome_does_not_publish_before_shell_confirmation(self):
        proxy = FakeGnomeProxy()
        backend = GnomeInputSourceBackend(proxy=proxy)
        changed = []
        controller = InputSourceController(backend, changed.append)
        controller.start()
        self.assertEqual("us", changed[-1].id)

        self.assertTrue(controller.switch_next())
        self.assertEqual("us", changed[-1].id)
        self.assertEqual("SwitchToNext", proxy.calls[-1][0])

        proxy.emit_source_changed()
        self.assertEqual("ara", changed[-1].id)
        self.assertEqual("AR", changed[-1].short_name)

    def test_read_only_backend_never_claims_activation_success(self):
        errors = []
        backend = ReadOnlyInputSourceBackend("No compositor API")
        controller = InputSourceController(backend, error_callback=errors.append)

        availability = controller.availability()
        self.assertEqual(InputSourceAvailability.READ_ONLY,
                         availability.state)
        self.assertFalse(controller.switch_next())
        self.assertEqual(["No compositor API"], errors)


if __name__ == "__main__":
    unittest.main()
