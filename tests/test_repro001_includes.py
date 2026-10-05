# -*- coding: utf-8 -*-
"""
REPRO001 finds the SRCREV that pins a git URI where bitbake would.

The SRCREV may be single-quoted, or set in a file the recipe requires. An
.inc file is itself required by recipes that may pin its URIs, and an
include that cannot be found may pin them too, so neither is reported
unless the SRCREV is explicitly AUTOREV.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.supply_chain import UnpinnedBranchRule

URI = 'SRC_URI = "git://example.org/foo.git;protocol=https;branch=master;name=foo"\n'


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return UnpinnedBranchRule().check(context)


def test_single_quoted_srcrev_pins():
    content = URI + "SRCREV_foo = '0123456789abcdef0123456789abcdef01234567'\n"
    assert _check(content) == []


def test_single_quoted_autorev_is_reported():
    content = URI + "SRCREV_foo ?= '${@d.getVar(\"X\") and \"${AUTOREV}\" or \"x\"}'\n"
    assert len(_check(content)) == 1


def test_srcrev_from_included_file(tmp_path):
    (tmp_path / "foo-version.inc").write_text(
        'SRCREV_foo ?= "0123456789abcdef0123456789abcdef01234567"\n')
    content = "require foo-version.inc\n" + URI
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(content)
    assert _check(content, recipe) == []


def test_resolved_include_without_srcrev_is_reported(tmp_path):
    (tmp_path / "foo.inc").write_text('SUMMARY = "foo"\n')
    content = "require foo.inc\n" + URI
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(content)
    assert len(_check(content, recipe)) == 1


def test_unresolvable_include_is_unknown(tmp_path):
    content = "require recipes-foo/foo/foo-srcrev.inc\n" + URI
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(content)
    assert _check(content, recipe) == []


def test_inc_file_is_pinned_by_its_recipe():
    assert _check(URI, Path("foo.inc")) == []


def test_inc_file_with_autorev_is_reported():
    content = URI + 'SRCREV_foo = "${AUTOREV}"\n'
    assert len(_check(content, Path("foo.inc"))) == 1


def test_recipe_without_srcrev_is_reported():
    assert len(_check(URI)) == 1
