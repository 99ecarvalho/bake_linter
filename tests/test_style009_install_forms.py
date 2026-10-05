# -*- coding: utf-8 -*-
"""
STYLE009 looks only at install commands that copy files to a directory.

install -d creates directories, install -t names the destination
directory, and oe_libinstall is a different command.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.style import InstallDirectoryTrailingSlashRule


def _check(line):
    content = f"do_install() {{\n    {line}\n}}\n"
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return InstallDirectoryTrailingSlashRule().check(context)


@pytest.mark.parametrize("line", [
    "install -d ${D}${bindir}",
    "install -m 0755 -d ${D}${sysconfdir}",
    "install -dm 0755 ${D}${datadir}",
    "install --directory ${D}${libdir}",
    "install -m 0644 -t ${D}${datadir} foo bar",
    "oe_libinstall -C src libfoo ${D}${libdir}",
])
def test_not_a_file_destination(line):
    assert _check(line) == []


def test_file_to_directory_without_slash_is_reported():
    assert len(_check("install -m 0644 foo.conf ${D}${sysconfdir}")) == 1
