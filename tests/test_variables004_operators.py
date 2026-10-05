# -*- coding: utf-8 -*-
"""
VARIABLES004 counts only plain "=" BitBake assignments.

=+ and =. prepend, .= and += append, and an assignment in a shell
function body or on a continuation line is not a BitBake assignment.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.variables import VariableRedefinitionRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(),
    )
    return VariableRedefinitionRule().check(context)


@pytest.mark.parametrize("op", ["=+", "=.", ".=", "+=", "?="])
def test_adding_to_a_value_is_not_a_redefinition(op):
    assert _check(f'FOO = "a"\nFOO {op} "b"\n') == []


def test_shell_assignments_in_functions_are_ignored():
    content = (
        'B = "${WORKDIR}/build"\n'
        'do_configure:prepend:class-native() {\n'
        'B=foo\n'
        '}\n'
    )
    assert _check(content) == []


def test_continuation_lines_are_ignored():
    content = (
        'S = "${WORKDIR}/foo"\n'
        'EXTRA_OEMAKE = "\\\n'
        'S = bar \\\n'
        '"\n'
    )
    assert _check(content) == []


def test_plain_redefinition_is_reported():
    results = _check('FOO = "a"\nFOO = "b"\n')
    assert len(results) == 1
    assert results[0].line == 2
