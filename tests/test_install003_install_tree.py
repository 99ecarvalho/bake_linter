# -*- coding: utf-8 -*-
"""
INSTALL003 only judges directories created in the install tree.

mkdir of a scratch directory in ${B} or ${WORKDIR} creates nothing that is
packaged, so install -d has nothing to add there.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.install import MkdirInsteadOfInstallDRule


def _check(body):
    content = f'do_install() {{\n{body}\n}}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return MkdirInsteadOfInstallDRule().check(context)


@pytest.mark.parametrize("body", [
    "    mkdir -p ${B}/stage",
    "    mkdir -p ${WORKDIR}/tmp",
    "    mkdir build",
])
def test_outside_install_tree_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body", [
    "    mkdir -p ${D}${datadir}/foo",
    "    mkdir $D/opt",
    "    mkdir -p \\\n        ${D}${sysconfdir}/foo",
])
def test_install_tree_reported(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].line == 2
