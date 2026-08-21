# Maintainer release template for Fedora, RHEL-derived distributions and openSUSE.
# Copy the released source archive beside this file, then replace Version and
# Source0 with the signed release URL/checksum policy of the target project.

Name:           onboard
Version:        1.4.4
Release:        6%{?dist}
Summary:        On-screen keyboard for Linux desktops
License:        GPL-3.0-or-later
URL:            https://github.com/Alaa91H/onboard
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  gettext
BuildRequires:  intltool
BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  pkgconfig(dconf)
BuildRequires:  pkgconfig(gdk-3.0)
BuildRequires:  pkgconfig(hunspell)
BuildRequires:  pkgconfig(libcanberra)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(x11)
BuildRequires:  pkgconfig(xi)
BuildRequires:  pkgconfig(xkbfile)
BuildRequires:  pkgconfig(xtst)
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros
BuildRequires:  xorg-x11-server-Xvfb

Requires:       dconf
Requires:       gettext
Requires:       gtk3
Requires:       hunspell
Requires:       iso-codes
Requires:       librsvg2
Requires:       python3-cairo
Requires:       python3-dbus
Requires:       python3-gobject

# gtk-layer-shell improves native floating windows on compatible Wayland
# compositors. It is optional: the runtime detects its presence safely.
Recommends:     gtk-layer-shell
Recommends:     at-spi2-core

%description
Onboard is an on-screen keyboard for Linux desktops. This package supports
X11 and uses runtime capability detection for supported KDE Plasma and GNOME
Wayland integration. Other Wayland compositors use the safest available
fallback rather than an optimistic input-injection path.

%prep
%autosetup -n %{name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
install -Dpm 0644 build/desktop/onboard-autostart.desktop \
  %{buildroot}%{_sysconfdir}/xdg/autostart/onboard-autostart.desktop

# The application owns only its own udev rule. Packaging policy decides whether
# to install/enable it in a separate subpackage.
install -Dpm 0644 data/72-onboard-uinput.rules \
  %{buildroot}%{_datadir}/onboard/72-onboard-uinput.rules

%check
# The focused tests import source modules, so build the native extensions into
# the source tree before running them in addition to validating the wheel.
%{python3} setup.py build
xvfb-run -a %{python3} -m unittest \
  Onboard.test.test_ClipboardHistory \
  Onboard.test.test_InputSources \
  Onboard.test.test_NativeInput \
  Onboard.test.test_ArabicLocalization \
  Onboard.test.test_RTL

%files
%doc %{_docdir}/%{name}/
%{_bindir}/onboard
%{_bindir}/onboard-settings
%{_bindir}/onboard-toggle
%{python3_sitearch}/Onboard/
%{python3_sitearch}/onboard-%{version}.dist-info/
%{_datadir}/applications/onboard.desktop
%{_datadir}/applications/onboard-settings.desktop
%{_datadir}/dbus-1/services/org.onboard.Onboard.service
%{_datadir}/glib-2.0/schemas/
%{_datadir}/gnome-shell/extensions/Onboard_Indicator@onboard.org/
%{_datadir}/icons/
%{_datadir}/locale/*/LC_MESSAGES/onboard.mo
%{_datadir}/man/man1/onboard*
%{_datadir}/onboard/
%{_datadir}/sounds/freedesktop/stereo/
%config(noreplace) %{_sysconfdir}/xdg/autostart/onboard-autostart.desktop

%changelog
* Thu Aug 20 2026 Onboard contributors <noreply@example.invalid> - 1.4.4-6
- Add portable PEP 517 build path and desktop capability support.
