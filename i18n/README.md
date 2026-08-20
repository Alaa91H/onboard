# Onboard internationalization and RTL

This directory contains the maintainable internationalization policy for the
standalone Onboard application. Runtime gettext catalogs remain in `po/` so the
existing build and translation ecosystem stays compatible.

## Project layout

```text
i18n/
├── README.md                 # Workflow, ownership, and RTL policy
├── glossary/
│   └── ar.md                 # Approved Arabic user-interface terminology
└── scripts/
    └── check_catalog.py      # CI quality gate for a gettext PO catalog

po/
├── POTFILES.in               # Extractable Python, UI, and desktop sources
├── onboard.pot               # Generated message template
└── ar.po                     # Arabic translations, reviewed in version control

Onboard/
├── I18n.py                   # Locale detection and centralized GTK direction
├── NativeInput.py            # Error-code boundary; user messages remain in gettext
└── ...
```

## Workflow for a user-visible string

Every user-visible Python string must use `_()` and every ambiguous short label
must use `pgettext()` when a translator needs context. New source files are
added to `po/POTFILES.in`. Desktop actions use the `_Name` and `_Comment`
markers understood by `intltool`; GtkBuilder files keep the corresponding
translatable attributes.

```bash
python3 setup.py build_i18n
msgmerge --update --backup=none po/ar.po po/onboard.pot
python3 i18n/scripts/check_catalog.py po/ar.po
msgfmt --check --statistics po/ar.po
```

The build compiles catalogs to `share/locale/<language>/LC_MESSAGES/onboard.mo`.
The `.mo` output is generated, not committed. Translation code must never be
implemented separately in Rust: native code returns a stable error code and
Python maps that code to a gettext message so each language has a single
catalog.

## RTL policy

`Onboard.I18n.apply_gtk_text_direction()` runs before keyboard or settings
widgets are created. It detects the gettext locale precedence (`LANGUAGE`,
`LC_ALL`, `LC_MESSAGES`, then `LANG`) and sets GTK's default text direction to
RTL for Arabic and other supported right-to-left languages. LTR remains the
safe default for every other locale.

A release containing an Arabic catalog must be smoke-tested with a real Arabic
session as well as automated checks:

```bash
LANG=ar_SA.UTF-8 LANGUAGE=ar GTK_TEXT_DIR=rtl onboard
LANG=ar_SA.UTF-8 LANGUAGE=ar GTK_TEXT_DIR=rtl onboard-settings
```

Review the indicator and popup menus, preferences, file-selection dialogs,
clipboard history, input-source menu, emoji palette, and keyboard labels. A
review is complete only when text is readable, mnemonic markers remain unique,
Pango markup is preserved, and no layout element is clipped or rendered in the
wrong direction.

## Rust boundary

The Rust crate is deliberately locale-neutral. It returns machine-readable
codes such as `invalid-keymap` and `engine-not-open`; `Onboard.NativeInput`
turns those codes into UI messages in Python. This prevents duplicated PO files
and keeps all Arabic, plural, mnemonic, and RTL review in one workflow.
