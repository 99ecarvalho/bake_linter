# -*- coding: utf-8 -*-
"""
SECURITY003 recognises a recursive chmod 777 with -R on either side of
the mode, and reports each line once.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.security import InsecurePermissionsRule


def _check(command):
    content = f"do_install() {{\n    {command}\n}}\n"
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return InsecurePermissionsRule().check(context)


@pytest.mark.parametrize("command", [
    "chmod -R 777 ${D}${PTEST_PATH}",
    "chmod 777 -R ${D}${PTEST_PATH}/tests",
])
def test_recursive(command):
    results = _check(command)
    assert len(results) == 1
    assert results[0].message == "Recursive chmod 777 is dangerous"


def test_non_recursive():
    results = _check("chmod 777 ${D}${bindir}/foo")
    assert len(results) == 1
    assert results[0].message == "chmod 777 is overly permissive"
