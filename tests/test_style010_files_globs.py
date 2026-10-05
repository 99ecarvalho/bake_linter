# -*- coding: utf-8 -*-
"""
STYLE010 reads FILES as globs and ${D}/${datadir} as ${D}${datadir}.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import SystemdRedundantFilesRule


def _check(install, files):
    content = (
        "do_install() {\n"
        f"    install -m 644 ${{S}}/dbus/*.service {install}\n"
        "}\n"
        f'FILES:${{PN}} += "{files}"\n'
    )
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return SystemdRedundantFilesRule().check(context)


def test_redundant_slash_and_glob():
    assert _check("${D}/${datadir}/dbus-1/system-services",
                  "${datadir}/dbus-1/system-services/*") == []


def test_directory_entry_covers_contents():
    assert _check("${D}/${datadir}/dbus-1/system-services/",
                  "${datadir}/dbus-1") == []


def test_uncovered_location_is_reported():
    assert len(_check("${D}/${datadir}/dbus-1/system-services",
                      "${datadir}/other/*")) == 1
