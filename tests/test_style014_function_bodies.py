# -*- coding: utf-8 -*-
"""
STYLE014 looks only at BitBake variable definitions.

Tabs in shell or python function bodies are fine, whatever the function
header looks like; tabs in any variable definition, ${PN} overrides
included, are reported.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.style import TabInVariableDefinitionRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(),
    )
    return TabInVariableDefinitionRule().check(context)


@pytest.mark.parametrize("header", [
    "do_install:append:class-native() {",
    "pkg_postinst:${PN} () {",
    "fakeroot do_install() {",
    "do_install:class-target () {",
    "python do_foo () {",
])
def test_function_bodies_are_skipped(header):
    content = f"{header}\n\tOPTS=\"--root=$D\"\n\tFOO=bar \\\n\t\tbaz\n}}\n"
    assert _check(content) == []


def test_tabs_in_overridden_variable_are_reported():
    content = 'RDEPENDS:${PN} = "\\\n\tdbus \\\n"\n'
    results = _check(content)
    assert [r.line for r in results] == [2]
