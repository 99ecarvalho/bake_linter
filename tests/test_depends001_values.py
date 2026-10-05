# -*- coding: utf-8 -*-
"""
DEPENDS001 checks the values of dependency variables only.

Python code that reads RDEPENDS (rdeps = d.getVar('RDEPENDS:' + pkg)) has
an "=" next to a word but is no dependency list.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.uri import VersionConstraintSyntaxRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return VersionConstraintSyntaxRule().check(context)


@pytest.mark.parametrize("content", [
    "python populate_packages:prepend() {\n"
    "    rdeps = d.getVar('RDEPENDS:' + pkg)\n"
    "}\n",
    "python split_modules() {\n"
    "    for line in lines:\n"
    "        module = line[0].replace(\"RDEPENDS:foo\", \"RDEPENDS:${PN}\")\n"
    "}\n",
    'RDEPENDS:${PN} = "bar (>= 1.2) baz"\n',
    'RPROVIDES:${PN} = "foo-plugin (= 2.0)"\n',
])
def test_not_reported(content):
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    'RDEPENDS:${PN} = "bar >= 1.2"\n',
    'RRECOMMENDS:${PN} = "baz \\\n    bar >= 1.2 \\\n"\n',
    'RCONFLICTS:${PN} = "bar (== 1.0)"\n',
])
def test_reported(content):
    results = _check(content)
    assert len(results) == 1
    assert results[0].rule_id == "DEPENDS001"
