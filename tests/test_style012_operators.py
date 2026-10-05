# -*- coding: utf-8 -*-
"""
STYLE012 knows every BitBake operator and checks only assignments.

=+ was read as = followed by "+", and shell assignments in function
bodies or values on continuation lines were taken for BitBake ones.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.style import VariableAssignmentSpacingRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return VariableAssignmentSpacingRule().check(context)


@pytest.mark.parametrize("op", ["=+", "=.", ".=", "+=", "?=", "??=", ":="])
def test_spaced_operators_are_accepted(op):
    assert _check(f'FOO {op} "x"\n') == []


def test_function_body_and_continuation_lines_are_skipped():
    content = (
        "do_install:append:class-native() {\n"
        "FOO=bar\n"
        "}\n"
        'EXTRA_OEMAKE = "\\\n'
        'CC="${CC}" \\\n'
        '"\n'
    )
    assert _check(content) == []


def test_missing_space_is_reported():
    results = _check('FOO="x"\n')
    assert len(results) == 1
