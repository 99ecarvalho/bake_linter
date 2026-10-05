# -*- coding: utf-8 -*-
"""
STYLE003 reports a hardcoded path only where it names a target directory.

Sed search patterns, python code (it reads build host paths), paths inside
other paths (${PV}/etc/, file://etc/...), /usr/bin/env and documentation
variables spread over continuation lines are not install destinations.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.style import HardcodedPathsRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(),
    )
    return HardcodedPathsRule().check(context)


def _in_install(line):
    return f"do_install() {{\n    {line}\n}}\n"


@pytest.mark.parametrize("line", [
    "install -d ${D}/etc/foo",
    "install -m 0644 foo $D/usr/share/foo/",
    "rm -rf ${D}/usr/lib/",
    "sed -i 's|^PATH=.*|PATH=/usr/bin|' ${D}${sysconfdir}/foo.conf",
])
def test_destinations_are_reported(line):
    assert len(_check(_in_install(line))) == 1


@pytest.mark.parametrize("line", [
    "sed -i -e 's:/usr/bin/perl:${bindir}/perl:g' ${S}/foo",
    "sed -i 's#/etc/foo#${sysconfdir}/foo#' ${D}${sysconfdir}/foo",
    "install -m 0644 foo ${D}${datadir}/${BPN}/${PV}/etc/",
    "cp etc.conf ${D}${sysconfdir}/",
    "oe_runmake PERL='/usr/bin/env perl'",
])
def test_non_destinations_are_not_reported(line):
    assert _check(_in_install(line)) == []


def test_python_function_is_skipped():
    content = (
        "python do_foo() {\n"
        "    if os.path.exists('/usr/include/linux/kvm.h'):\n"
        "        pass\n"
        "}\n"
    )
    assert _check(content) == []


def test_def_and_inline_python_are_skipped():
    content = (
        "def has_kvm(d):\n"
        "    return os.path.exists('/usr/include/linux/kvm.h')\n"
        "PACKAGECONFIG:remove = \"${@'kvm' if not os.path.exists('/usr/include/linux/kvm.h') else ''}\"\n"
    )
    assert _check(content) == []


def test_file_uri_is_not_a_path():
    content = 'SOMETHING = "file://etc/default/foo"\n'
    assert _check(content) == []


def test_documentation_continuation_lines_are_skipped():
    content = (
        'DESCRIPTION = "Reads its settings from \\\n'
        '    /etc/foo.conf"\n'
    )
    assert _check(content) == []
