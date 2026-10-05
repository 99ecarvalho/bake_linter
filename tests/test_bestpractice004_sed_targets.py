# -*- coding: utf-8 -*-
"""
BESTPRACTICE004 only reports sed -i in do_install on the source or build
tree.

Files under ${D} only exist once do_install has installed them, so editing
them there (substituting @VARS@, stripping build paths) is the normal way to
fix up installed files.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.best_practices import SedInDoInstallRule


def _check(body, function="do_install"):
    content = f'{function}() {{\n{body}\n}}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return SedInDoInstallRule().check(context)


@pytest.mark.parametrize("body", [
    "    sed -i -e 's,@BINDIR@,${bindir},g' ${D}${sysconfdir}/foo.conf",
    "    sed -i 's,${WORKDIR},,g' $D${libdir}/pkgconfig/foo.pc",
    # The installed target is on a continuation line
    "    sed -i -e 's,@A@,a,' \\\n        -e 's,@B@,b,' \\\n        ${D}${bindir}/foo-config",
    '    sed -i "s|${RECIPE_SYSROOT}||g" "${D}${datadir}/foo/foo.cmake"',
    # A loop variable: where it points is unknown
    "    sed -i 's/a/b/' $f",
    # Not an in-place edit
    "    sed 's/a/b/' ${S}/foo.in > ${D}${sysconfdir}/foo",
])
def test_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body", [
    "    sed -i 's/a/b/' ${S}/Makefile",
    "    sed -i -e 's/a/b/' ${B}/config.h",
    "    sed -i 's/a/b/' foo.pc",
    "    sed -e 's/a/b/' -i ${WORKDIR}/foo.service",
    "    sed -ie 's/a/b/' ${S}/foo.conf",
    "    sed -i \\\n        -e 's/a/b/' \\\n        ${S}/foo.conf",
])
def test_reported(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].rule_id == "BESTPRACTICE004"
    assert results[0].line == 2


@pytest.mark.parametrize("function", ["do_install:append", "do_install_ptest"])
def test_other_install_functions_reported(function):
    assert len(_check("    sed -i 's/a/b/' ${S}/foo", function)) == 1


def test_other_tasks_ignored():
    assert _check("    sed -i 's/a/b/' ${S}/foo", "do_configure") == []
