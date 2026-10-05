# -*- coding: utf-8 -*-
"""
STYLE005 reports only a value the recipe set itself and then blanks.

Clearing a bitbake.conf or class default (PARALLEL_MAKE = "") or
declaring a variable empty before appending to it is deliberate.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from bake_linter.core.engine import LintEngine
from bake_linter.rules.style import EmptyVariableRule


def _layer(tmp_path):
    (tmp_path / "conf").mkdir()
    (tmp_path / "conf" / "layer.conf").write_text("")
    recipes = tmp_path / "recipes-x" / "foo"
    recipes.mkdir(parents=True)
    return recipes


def _check(path):
    return EmptyVariableRule().check(LintEngine()._parse_file(path))


def test_clearing_a_default_is_not_reported(tmp_path):
    recipe = _layer(tmp_path) / "foo_1.0.bb"
    recipe.write_text('PARALLEL_MAKE = ""\nTOOLS_DEPS = ""\nTOOLS_DEPS:append = " bar"\n')
    assert _check(recipe) == []


def test_blanking_a_value_set_in_an_include_is_reported(tmp_path):
    recipes = _layer(tmp_path)
    (recipes / "foo.inc").write_text('EXTRA_FOO = "--with-bar"\n')
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nEXTRA_FOO = ""\n')
    results = _check(recipe)
    assert [r.line for r in results] == [2]


def test_blanking_a_value_set_earlier_is_reported(tmp_path):
    recipe = _layer(tmp_path) / "foo_1.0.bb"
    recipe.write_text('EXTRA_FOO = "--with-bar"\nEXTRA_FOO = ""\n')
    assert [r.line for r in _check(recipe)] == [2]
