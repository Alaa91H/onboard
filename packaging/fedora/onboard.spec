%global srcname onboard

Name:           onboard
Version:        1.4.4
Release:        5%{?dist}
Summary:        On-screen keyboard for everyone
License:        GPLv3+
URL:            https://github.com/Alaa91H/onboard
Source0:        %{url}/archive/v%{version}/%{srcname}-%{version}.tar.gz

BuildRequires:  gcc-c++
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-packaging
BuildRequires:  python3-distutils-extra
BuildRequires:  pkgconfig(gdk-3.0)
BuildRequires:  pkgconfig(xtst)
BuildRequires:  pkgconfig(xkbfile)
BuildRequires:  pkgconfig(dconf)
BuildRequires:  pkgconfig(libcanberra)
BuildRequires:  pkgconfig(hunspell)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  desktop-file-utils
BuildRequires:  intltool
BuildRequires:  glib2-devel
BuildRequires:  gtk3-devel

Requires:       python3-gobject
Requires:       python3-cairo
Requires:       python3-dbus
Requires:       iso-codes
Requires:       librsvg2
Requires:       gnome-shell

%description
Onboard is an on-screen keyboard useful for everybody that cannot use a
hardware keyboard; for example TabletPC users, mobility impaired users, etc.
It works out of the box without requiring manual configuration, automatically
reading the keyboard layout from the X server.

%package -n gnome-shell-extension-onboard
Summary:        GNOME Shell extension for Onboard
Requires:       gnome-shell >= 3.16
Requires:       %{name} >= %{version}
BuildArch:      noarch

%description -n gnome-shell-extension-onboard
This package hides the official GNOME3 keyboard and provides an icon to
show/hide Onboard. It is only an initial extension that does not show
Onboard for activities and passwords, yet.

%prep
%autosetup -n %{srcname}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --root=%{buildroot}

# Remove unnecessary files
rm -f %{buildroot}%{_datadir}/onboard/COPYING*
rm -f %{buildroot}%{_datadir}/onboard/HACKING

# Validate desktop files
desktop-file-validate %{buildroot}%{_datadir}/applications/onboard.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/onboard-settings.desktop

%files
%license COPYING COPYING.GPL3 COPYING.BSD3
%doc AUTHORS CHANGELOG HACKING DBUS.md README.md
%doc onboard-defaults.conf.example onboard-default-settings.gschema.override.example
%{_bindir}/onboard
%{_bindir}/onboard-settings
%{_libdir}/python3*/site-packages/Onboard/
%{_datadir}/glib-2.0/schemas/org.onboard.gschema.xml
%{_datadir}/glib-2.0/schemas/99_onboard-default-settings.gschema.override
%{_datadir}/applications/onboard.desktop
%{_datadir}/applications/onboard-settings.desktop
%{_datadir}/icons/hicolor/*/apps/*
%{_datadir}/icons/HighContrast/symbolic/apps/*
%{_datadir}/icons/ubuntu-mono-dark/status/22/*
%{_datadir}/icons/ubuntu-mono-light/status/22/*
%{_datadir}/man/man1/onboard.1.gz
%{_datadir}/man/man1/onboard-settings.1.gz
%{_datadir}/dbus-1/services/org.onboard.Onboard.service
%{_datadir}/onboard/*.ui
%{_datadir}/onboard/layouts/
%{_datadir}/onboard/scripts/
%{_datadir}/onboard/themes/
%{_datadir}/onboard/tools/
%{_datadir}/onboard/layoutstrings.py
%{_datadir}/onboard/72-onboard-uinput.rules
%{_datadir}/onboard/gnome-extension/onboard@onboard.local/
%{_datadir}/sounds/freedesktop/stereo/
%{_datadir}/help/C/onboard/

%files -n gnome-shell-extension-onboard
%{_datadir}/gnome-shell/extensions/Onboard_Indicator@onboard.org/

%changelog
* Mon Jul 06 2026 Alaa91H <alaa91h@example.com> - 1.4.4-5
- Add Tibetan translation
- Fix bo.po escape literal newlines in msgid strings
- Fix bo.po remove duplicate msgstr lines with literal newlines
- Fix remove non-existent files from POTFILES.in
- Fix xsync-badwindow-on-unrealize
- Improve robustness

* Sat Jun 06 2026 Alaa91H <alaa91h@example.com> - 1.4.4-3
- Fix prevent crash on shutdown caused by BadWindow X error
- Fix suppress Gdk-CRITICAL on exit, cancel pending idle handler
- Fix use malloc/free instead of PyMem in PoolAllocator to prevent SIGSEGV on exit

* Mon May 26 2026 Alaa91H <alaa91h@example.com> - 1.4.4-2
- Fix prevent window from being dragged off-screen
- Fix replace invalid UTF-8 chars in ACPI events
- Add native Wayland key injection and documentation

* Sat Apr 11 2026 Alaa91H <alaa91h@example.com> - 1.4.4-1
- Add ANSI key geometry variants to Compact and Full Keyboard layouts
- Detect XKB keyboard model and remap keys for ANSI layout
- Add new layout without emoji
- Added openSUSE and Fedora build support

* Thu Jul 03 2025 Alaa91H <alaa91h@example.com> - 1.4.3-7
- Remove env GDK_BACKEND=x11 in case of wayland
- Add dist_choice/revision to setup.py

* Thu Jun 12 2025 Alaa91H <alaa91h@example.com> - 1.4.3-1
- Merge useful changes from theofficialgman
- Ensure .deb packages can be built without root privileges
