# -*- coding: UTF-8 -*-
#
# Copyright © 2026 Onboard contributors
#
# This file is part of Onboard.
#
# Onboard is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""
System input-source backends.

This module deliberately separates the system input source (the XKB group
that determines the characters actually typed) from Onboard's prediction
language.  A backend only reports a source change after the desktop session
has confirmed it; callers must never update a language label optimistically.
"""

from __future__ import division, print_function, unicode_literals

import logging

_logger = logging.getLogger(__name__)


class InputSourceError(Exception):
    """Raised when a desktop backend cannot complete an input-source action."""


class InputSourceAvailability(object):
    """Explicit support state returned to the user interface."""

    SUPPORTED = "supported"
    READ_ONLY = "read-only"
    UNAVAILABLE = "unavailable"

    def __init__(self, state, message=""):
        self.state = state
        self.message = message

    @property
    def can_activate(self):
        return self.state == self.SUPPORTED


class InputSource(object):
    """A desktop input source known to a backend."""

    def __init__(self, source_id, name, short_name=None, index=None):
        self.id = str(source_id)
        self.name = name
        self.short_name = short_name or name
        self.index = index

    def __eq__(self, other):
        return isinstance(other, InputSource) and self.id == other.id

    def __repr__(self):
        return "InputSource({!r}, {!r})".format(self.id, self.name)


class InputSourceBackend(object):
    """Common contract for desktop-specific input-source integrations."""

    def __init__(self):
        self._changed_callback = None
        self._error_callback = None

    def set_callbacks(self, changed_callback=None, error_callback=None):
        self._changed_callback = changed_callback
        self._error_callback = error_callback

    def start(self):
        """Start backend-specific watches. Safe to call more than once."""

    def stop(self):
        """Release backend-specific watches. Safe to call more than once."""

    def availability(self):
        return InputSourceAvailability(InputSourceAvailability.UNAVAILABLE)

    def list_sources(self):
        return []

    def get_active(self):
        return None

    def activate(self, source_id):
        raise InputSourceError(_("Input-source activation is unavailable"))

    def switch_next(self):
        sources = self.list_sources()
        active = self.get_active()
        if not sources or active is None:
            raise InputSourceError(_("No input sources are available"))
        try:
            index = sources.index(active)
        except ValueError:
            index = -1
        self.activate(sources[(index + 1) % len(sources)].id)

    def _notify_changed(self):
        if self._changed_callback:
            self._changed_callback(self.get_active())

    def _notify_error(self, message):
        _logger.warning(message)
        if self._error_callback:
            self._error_callback(message)


class ReadOnlyInputSourceBackend(InputSourceBackend):
    """Safe backend for compositors without an input-source control API."""

    def __init__(self, message):
        InputSourceBackend.__init__(self)
        self._message = message

    def availability(self):
        return InputSourceAvailability(InputSourceAvailability.READ_ONLY,
                                       self._message)

    def activate(self, source_id):
        raise InputSourceError(self._message)

    def switch_next(self):
        raise InputSourceError(self._message)


class X11InputSourceBackend(InputSourceBackend):
    """Control XKB groups through the existing Virtkey X11 implementation."""

    def __init__(self, virtkey):
        InputSourceBackend.__init__(self)
        self._virtkey = virtkey

    def availability(self):
        if self._virtkey is None:
            return InputSourceAvailability(
                InputSourceAvailability.UNAVAILABLE,
                _("X11 keyboard information is not available"))
        return InputSourceAvailability(InputSourceAvailability.SUPPORTED)

    def _layout_names(self):
        if self._virtkey is None:
            return []
        try:
            value = self._virtkey.get_layout_as_string() or ""
        except Exception as ex:
            self._notify_error(_("Could not read X11 keyboard layouts: {}")
                               .format(ex))
            return []
        return [name for name in value.split("+") if name]

    def list_sources(self):
        sources = []
        for index, name in enumerate(self._layout_names()):
            short_name = name.split("(", 1)[0].upper()
            sources.append(InputSource(index, name, short_name, index))
        return sources

    def get_active(self):
        if self._virtkey is None:
            return None
        try:
            group = int(self._virtkey.get_current_group())
        except Exception as ex:
            self._notify_error(_("Could not read the active X11 layout: {}")
                               .format(ex))
            return None
        sources = self.list_sources()
        if 0 <= group < len(sources):
            return sources[group]
        return None

    def activate(self, source_id):
        availability = self.availability()
        if not availability.can_activate:
            raise InputSourceError(availability.message)
        try:
            group = int(source_id)
        except (TypeError, ValueError):
            raise InputSourceError(_("Invalid X11 input-source identifier"))
        sources = self.list_sources()
        if group < 0 or group >= len(sources):
            raise InputSourceError(_("Requested X11 input source is unavailable"))
        try:
            self._virtkey.lock_group(group)
        except Exception as ex:
            raise InputSourceError(_("Could not activate X11 input source: {}")
                                   .format(ex))
        self._notify_changed()


class KdeInputSourceBackend(InputSourceBackend):
    """KDE Plasma input-source controller using org.kde.KeyboardLayouts."""

    BUS_NAME = "org.kde.keyboard"
    OBJECT_PATH = "/Layouts"
    INTERFACE = "org.kde.KeyboardLayouts"

    def __init__(self, proxy=None, gio=None):
        InputSourceBackend.__init__(self)
        self._proxy = proxy
        self._gio = gio
        self._bus = None
        self._signal_handler_id = 0

    def start(self):
        if self._proxy is None:
            self._connect_proxy()
        if self._proxy is None:
            return
        if self._signal_handler_id:
            return
        try:
            self._signal_handler_id = self._proxy.connect(
                "g-signal", self._on_g_signal)
        except Exception as ex:
            self._notify_error(_("Could not watch KDE layout changes: {}")
                               .format(ex))

    def stop(self):
        if self._proxy is not None and self._signal_handler_id:
            try:
                self._proxy.disconnect(self._signal_handler_id)
            except Exception:
                pass
        self._signal_handler_id = 0
        self._proxy = None
        self._bus = None

    def _connect_proxy(self):
        try:
            if self._gio is None:
                from gi.repository import Gio
                self._gio = Gio
            self._bus = self._gio.bus_get_sync(self._gio.BusType.SESSION,
                                                None)
            proxy = self._gio.DBusProxy.new_sync(
                self._bus,
                self._gio.DBusProxyFlags.DO_NOT_AUTO_START,
                None,
                self.BUS_NAME,
                self.OBJECT_PATH,
                self.INTERFACE,
                None)
            if proxy.get_name_owner() is not None:
                self._proxy = proxy
        except Exception as ex:
            self._notify_error(_("Could not connect to KDE keyboard layouts: {}")
                               .format(ex))

    def availability(self):
        if self._proxy is None:
            return InputSourceAvailability(
                InputSourceAvailability.UNAVAILABLE,
                _("KDE keyboard-layout service is not available"))
        return InputSourceAvailability(InputSourceAvailability.SUPPORTED)

    def _call(self, method_name, parameters=None):
        availability = self.availability()
        if not availability.can_activate:
            raise InputSourceError(availability.message)
        try:
            result = self._proxy.call_sync(
                method_name,
                parameters,
                self._gio.DBusCallFlags.NO_AUTO_START if self._gio else 0,
                750,
                None)
        except Exception as ex:
            raise InputSourceError(_("KDE input-source request failed: {}")
                                   .format(ex))
        if hasattr(result, "unpack"):
            return result.unpack()
        return result

    @staticmethod
    def _unwrap_single(value):
        if isinstance(value, tuple) and len(value) == 1:
            return value[0]
        return value

    def _get_layout_index(self):
        value = self._unwrap_single(self._call("getLayout"))
        try:
            return int(value)
        except (TypeError, ValueError):
            raise InputSourceError(_("KDE returned an invalid active layout"))

    def _get_layouts(self):
        value = self._unwrap_single(self._call("getLayoutsList"))
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise InputSourceError(_("KDE returned an invalid layout list"))
        return list(value)

    @staticmethod
    def _layout_name(value, index):
        if isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str) and item:
                    return item
        if isinstance(value, str) and value:
            return value
        return _("Layout {}").format(index + 1)

    def list_sources(self):
        try:
            layouts = self._get_layouts()
        except InputSourceError as ex:
            self._notify_error(str(ex))
            return []
        sources = []
        for index, value in enumerate(layouts):
            name = self._layout_name(value, index)
            short_name = name.split("(", 1)[0].upper()
            sources.append(InputSource(index, name, short_name, index))
        return sources

    def get_active(self):
        try:
            index = self._get_layout_index()
        except InputSourceError as ex:
            self._notify_error(str(ex))
            return None
        sources = self.list_sources()
        if 0 <= index < len(sources):
            return sources[index]
        return None

    def _int_parameters(self, value):
        if self._gio is not None:
            return self._gio.Variant("(i)", (int(value),))
        return (int(value),)

    def activate(self, source_id):
        try:
            index = int(source_id)
        except (TypeError, ValueError):
            raise InputSourceError(_("Invalid KDE input-source identifier"))
        if index < 0 or index >= len(self.list_sources()):
            raise InputSourceError(_("Requested KDE input source is unavailable"))
        self._call("setLayout", self._int_parameters(index))

    def switch_next(self):
        self._call("switchToNextLayout")

    def _on_g_signal(self, _proxy, _sender, signal_name, _parameters):
        if signal_name in ("layoutChanged", "layoutListChanged"):
            self._notify_changed()


class GnomeInputSourceBackend(InputSourceBackend):
    """GNOME Shell backend exposed only by Onboard's bundled extension."""

    BUS_NAME = "org.gnome.Shell"
    OBJECT_PATH = "/org/onboard/InputSources"
    INTERFACE = "org.onboard.InputSources1"

    def __init__(self, proxy=None, gio=None):
        InputSourceBackend.__init__(self)
        self._proxy = proxy
        self._gio = gio
        self._bus = None
        self._signal_handler_id = 0

    def start(self):
        if self._proxy is None:
            self._connect_proxy()
        if self._proxy is None or self._signal_handler_id:
            return
        try:
            self._signal_handler_id = self._proxy.connect(
                "g-signal", self._on_g_signal)
        except Exception as ex:
            self._notify_error(_("Could not watch GNOME input sources: {}")
                               .format(ex))

    def stop(self):
        if self._proxy is not None and self._signal_handler_id:
            try:
                self._proxy.disconnect(self._signal_handler_id)
            except Exception:
                pass
        self._signal_handler_id = 0
        self._proxy = None
        self._bus = None

    def _connect_proxy(self):
        try:
            if self._gio is None:
                from gi.repository import Gio
                self._gio = Gio
            self._bus = self._gio.bus_get_sync(self._gio.BusType.SESSION,
                                                None)
            proxy = self._gio.DBusProxy.new_sync(
                self._bus,
                self._gio.DBusProxyFlags.DO_NOT_AUTO_START,
                None,
                self.BUS_NAME,
                self.OBJECT_PATH,
                self.INTERFACE,
                None)
            if proxy.get_name_owner() is not None:
                self._proxy = proxy
        except Exception as ex:
            self._notify_error(_("Could not connect to the Onboard GNOME "
                               "input-source bridge: {}").format(ex))

    def availability(self):
        if self._proxy is None:
            return InputSourceAvailability(
                InputSourceAvailability.UNAVAILABLE,
                _("Onboard's GNOME input-source extension is not available"))
        return InputSourceAvailability(InputSourceAvailability.SUPPORTED)

    def _call(self, method_name, parameters=None):
        availability = self.availability()
        if not availability.can_activate:
            raise InputSourceError(availability.message)
        try:
            result = self._proxy.call_sync(
                method_name,
                parameters,
                self._gio.DBusCallFlags.NO_AUTO_START if self._gio else 0,
                750,
                None)
        except Exception as ex:
            raise InputSourceError(_("GNOME input-source request failed: {}")
                                   .format(ex))
        if hasattr(result, "unpack"):
            return result.unpack()
        return result

    @staticmethod
    def _unwrap_single(value):
        if isinstance(value, tuple) and len(value) == 1:
            return value[0]
        return value

    def _string_parameters(self, value):
        if self._gio is not None:
            return self._gio.Variant("(s)", (str(value),))
        return (str(value),)

    def list_sources(self):
        try:
            values = self._unwrap_single(self._call("ListSources"))
        except InputSourceError as ex:
            self._notify_error(str(ex))
            return []
        if not isinstance(values, (list, tuple)):
            self._notify_error(_("GNOME returned an invalid input-source list"))
            return []
        sources = []
        for index, value in enumerate(values):
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                continue
            source_id, name, short_name = value
            sources.append(InputSource(source_id, name, short_name, index))
        return sources

    def get_active(self):
        try:
            source_id = self._unwrap_single(self._call("GetActiveSource"))
        except InputSourceError as ex:
            self._notify_error(str(ex))
            return None
        for source in self.list_sources():
            if source.id == str(source_id):
                return source
        return None

    def activate(self, source_id):
        result = self._unwrap_single(
            self._call("ActivateSource", self._string_parameters(source_id)))
        if not bool(result):
            raise InputSourceError(_("GNOME rejected the requested input source"))

    def switch_next(self):
        result = self._unwrap_single(self._call("SwitchToNext"))
        if not bool(result):
            raise InputSourceError(_("GNOME could not switch to the next input source"))

    def _on_g_signal(self, _proxy, _sender, signal_name, _parameters):
        if signal_name in ("SourceChanged", "SourcesChanged"):
            self._notify_changed()


class InputSourceController(object):
    """Coordinate a backend and publish only confirmed source changes."""

    def __init__(self, backend, changed_callback=None, error_callback=None):
        self._backend = backend
        self._changed_callback = changed_callback
        self._error_callback = error_callback
        self._request_id = 0
        self._last_source = None
        self._backend.set_callbacks(self._on_backend_changed,
                                    self._on_backend_error)

    @property
    def backend(self):
        return self._backend

    @property
    def request_id(self):
        return self._request_id

    def start(self):
        self._backend.start()
        self.refresh()

    def stop(self):
        self._backend.stop()

    def availability(self):
        return self._backend.availability()

    def list_sources(self):
        return self._backend.list_sources()

    def get_active(self):
        # UI refreshes are frequent. KDE D-Bus and XKB must be queried only
        # on startup, an explicit refresh, or an authoritative backend event.
        if self._last_source is None:
            self.refresh()
        return self._last_source

    def refresh(self):
        self._publish_if_changed(self._backend.get_active())

    def activate(self, source_id):
        self._request_id += 1
        try:
            self._backend.activate(source_id)
        except InputSourceError as ex:
            self._on_backend_error(str(ex))
            return False
        return True

    def switch_next(self):
        self._request_id += 1
        try:
            self._backend.switch_next()
        except InputSourceError as ex:
            self._on_backend_error(str(ex))
            return False
        return True

    def _on_backend_changed(self, source):
        self._publish_if_changed(source)

    def _publish_if_changed(self, source):
        if source != self._last_source:
            self._last_source = source
            if self._changed_callback:
                self._changed_callback(source)

    def _on_backend_error(self, message):
        if self._error_callback:
            self._error_callback(message)


def create_backend(virtkey, is_wayland, is_kde_plasma, is_gnome_shell=False):
    """Select an explicit backend without guessing unsupported Wayland APIs."""

    if not is_wayland:
        return X11InputSourceBackend(virtkey)
    if is_kde_plasma:
        return KdeInputSourceBackend()
    if is_gnome_shell:
        return GnomeInputSourceBackend()
    return ReadOnlyInputSourceBackend(
        _("This Wayland compositor has no supported input-source API"))
