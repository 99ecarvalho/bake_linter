# -*- coding: utf-8 -*-
"""
INSTALL001 warns about cp into ${D} that preserves ownership.

do_install runs under pseudo, which records the ownership cp gives the
copied files; -a, -p and --preserve=ownership keep the build user's uid and
gid, and package QA then reports host-user-contaminated files. Other copies
into ${D} are info, and copies elsewhere are not judged.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.install import CpInsteadOfInstallRule


def _check(body, function="do_install"):
    content = f'{function}() {{\n{body}\n}}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return CpInsteadOfInstallRule().check(context)


@pytest.mark.parametrize("body", [
    "    cp -a ${S}/data ${D}${datadir}/foo",
    "    cp -rp ${S}/data ${D}${datadir}/foo",
    "    cp --preserve ${S}/a $D${bindir}",
    "    cp -R --preserve=mode,ownership ${S}/data ${D}${datadir}",
    "    cp --archive ${S}/data ${D}${datadir}",
    # The destination is on a continuation line
    "    cp -a ${S}/data \\\n        ${D}${datadir}/foo",
])
def test_ownership_preserved_warns(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING
    assert results[0].line == 2
    assert "ownership" in results[0].message


@pytest.mark.parametrize("body", [
    "    cp -R --no-dereference --preserve=mode,links ${S}/data ${D}${datadir}",
    "    cp -a --no-preserve=ownership ${S}/data ${D}${datadir}",
    # Not into the install tree
    "    cp ${S}/foo.conf.in ${B}/foo.conf",
    "    cp -a ${S}/data ${B}/data",
])
def test_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body,hint", [
    ("    cp ${S}/foo ${D}${bindir}", "install -m MODE"),
    ("    cp -R ${S}/data ${D}${datadir}", "find"),
])
def test_other_copies_into_destdir_are_info(body, hint):
    results = _check(body)
    assert len(results) == 1
    assert results[0].severity == Severity.INFO
    assert hint in results[0].hint
