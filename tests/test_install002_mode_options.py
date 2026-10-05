# -*- coding: utf-8 -*-
"""
INSTALL002 reads install's options the way install does.

-d creates directories (also in a cluster such as -dm or with
--directory), and the mode can be given as -m MODE, -mMODE, -Dm MODE,
--mode=MODE or --mode MODE, in octal, symbolic or as a variable. Commands
split over several lines are judged as a whole.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.install import InstallWithoutModeRule


def _check(body, function="do_install"):
    content = f'{function}() {{\n{body}\n}}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return InstallWithoutModeRule().check(context)


@pytest.mark.parametrize("body", [
    "    install -d ${D}${bindir} ${D}${sysconfdir}/foo ${D}${datadir}/foo",
    "    install -Dd ${D}${bindir}",
    "    install --directory ${D}${bindir}",
    "    install -o root -g root -d ${D}${bindir}",
    "    install -m 0644 foo ${D}${sysconfdir}",
    "    install -m0644 foo ${D}${sysconfdir}",
    "    install -Dm 0644 foo ${D}${sysconfdir}/foo",
    "    install -m u=rw,go=r foo ${D}${sysconfdir}",
    "    install -m ${FOO_MODE} foo ${D}${sysconfdir}",
    "    install --mode=0644 foo ${D}${sysconfdir}",
    "    install --mode 0644 foo ${D}${sysconfdir}",
    "    install -o root -m 0644 foo ${D}${sysconfdir}",
    "    install \\\n        -m 0644 foo ${D}${sysconfdir}",
    # Not the install command
    "    oe_runmake install DESTDIR=${D}",
])
def test_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body", [
    "    install foo ${D}${bindir}",
    "    install -D foo ${D}${bindir}/foo",
    "    install -o root -g root foo ${D}${bindir}",
    "    install -t ${D}${bindir} foo",
    "    install -v \\\n        foo ${D}${bindir}",
])
def test_reported(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].rule_id == "INSTALL002"
    assert results[0].line == 2


def test_install_ptest_judged():
    assert len(_check("    install foo ${D}${PTEST_PATH}", "do_install_ptest")) == 1
