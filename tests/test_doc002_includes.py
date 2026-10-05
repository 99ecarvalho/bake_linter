# -*- coding: utf-8 -*-
"""
DOC002 counts a SUMMARY set in a required .inc file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from bake_linter.core.models import FileContext
from bake_linter.rules.documentation import MissingSummaryRule


def _layer(tmp_path):
    (tmp_path / "conf").mkdir()
    (tmp_path / "conf" / "layer.conf").write_text("")
    recipes = tmp_path / "recipes-x" / "foo"
    recipes.mkdir(parents=True)
    return recipes


def _check(path):
    content = path.read_text()
    context = FileContext(path=path, content=content, lines=content.splitlines())
    return MissingSummaryRule().check(context)


def test_summary_in_required_inc(tmp_path):
    recipes = _layer(tmp_path)
    (recipes / "foo.inc").write_text('SUMMARY = "Foo"\n')
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nLICENSE = "MIT"\n')
    assert _check(recipe) == []


def test_unresolved_include_is_unknown(tmp_path):
    recipe = _layer(tmp_path) / "foo_1.0.bb"
    recipe.write_text('require recipes-other/bar.inc\nLICENSE = "MIT"\n')
    assert _check(recipe) == []


def test_missing_summary_is_reported(tmp_path):
    recipes = _layer(tmp_path)
    (recipes / "foo.inc").write_text('LICENSE = "MIT"\n')
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nDESCRIPTION = "Foo"\n')
    assert len(_check(recipe)) == 1
