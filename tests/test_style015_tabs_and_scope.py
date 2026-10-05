# -*- coding: utf-8 -*-
"""
STYLE015 measures tabs as 8 columns and checks only assignments.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import MultilineContinuationAlignmentRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return MultilineContinuationAlignmentRule().check(context)


def test_tab_indented_continuation_is_deep_enough():
    content = 'DEPENDS = "\\\n\tfoo \\\n\tbar \\\n"\n'
    assert _check(content) == []


def test_tab_and_eight_spaces_are_the_same_column():
    content = 'DEPENDS = "\\\n\tfoo \\\n        bar \\\n"\n'
    assert _check(content) == []


def test_function_body_is_skipped():
    content = (
        "do_install:append:class-native() {\n"
        'FOO="a \\\n'
        '  b"\n'
        "}\n"
    )
    assert _check(content) == []


def test_inconsistent_indentation_is_reported():
    content = 'DEPENDS = "\\\n    foo \\\n  bar \\\n"\n'
    assert len(_check(content)) == 1
