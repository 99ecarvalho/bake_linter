# -*- coding: utf-8 -*-
"""
Tests for the functions and per-line assignment lookups of a BitBake file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.core.recipe import parse_structure

RECIPE = '''\
FOO = "a \\
    b"
do_install:append:class-native() {
    install -d ${D}${bindir}
}
python do_bar() {
    d.setVar('X', 'y')
}
fakeroot python do_baz () {
    pass
}

def helper(d):
    x = 1

    return x
BAR = "1"
pkg_postinst:${PN} () {
    true
}
'''


def _context():
    return FileContext(path=Path("foo_1.0.bb"), content=RECIPE,
                       lines=RECIPE.splitlines())


def test_functions_and_python_flag():
    functions = {f.name: f for f in parse_structure(RECIPE.splitlines()).functions}
    assert (functions["do_install:append:class-native"].line,
            functions["do_install:append:class-native"].end_line) == (3, 5)
    assert functions["do_install:append:class-native"].python is False
    assert functions["do_bar"].python is True
    assert functions["do_baz"].python is True
    assert (functions["helper"].line, functions["helper"].end_line) == (13, 16)
    assert functions["helper"].python is True
    assert functions["pkg_postinst:${PN}"].python is False


def test_function_at():
    context = _context()
    assert context.function_at(4).name == "do_install:append:class-native"
    assert context.function_at(5).name == "do_install:append:class-native"
    assert context.function_at(15).name == "helper"
    assert context.function_at(1) is None
    assert context.function_at(17) is None


def test_assignment_at_and_top_level():
    context = _context()
    assert context.assignment_at(2).name == "FOO"
    assert context.is_top_level_assignment(1) is True
    assert context.is_top_level_assignment(2) is False
    assert context.is_top_level_assignment(4) is False
    assert context.is_top_level_assignment(17) is True
