# -*- coding: utf-8 -*-
"""
Tests for the multi-line structure of a BitBake file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.core.recipe import parse_structure, recipe_name

RECIPE = '''\
# A comment
SUMMARY = "Example"
DESCRIPTION = "Spans \\
    two lines"
SRC_URI = "https://example.org/foo-${PV}.tar.gz \\
           file://fix.patch \\
          "
SRC_URI[sha256sum] = "abc"
RDEPENDS:${PN}-dev:append = " bar"
export FOO = "1"
inherit autotools ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'systemd', '', d)}
require foo.inc

do_install() {
    install -d ${D}${bindir}
}

python do_bar() {
    d.setVar('X', 'y')
}

def helper(d):
    return "x"

AFTER = "1"
'''


def _structure():
    return parse_structure(RECIPE.splitlines())


def test_owners():
    s = _structure()
    assert s.owner(1) == "#"
    assert s.owner(2) == "SUMMARY"
    assert s.owner(4) == "DESCRIPTION"
    assert [s.owner(n) for n in (5, 6, 7)] == ["SRC_URI"] * 3
    assert s.owner(8) == "SRC_URI"
    assert s.owner(9) == "RDEPENDS:${PN}-dev:append"
    assert s.owner(10) == "FOO"
    assert [s.owner(n) for n in (14, 15, 16)] == ["FUNC:do_install"] * 3
    assert [s.owner(n) for n in (18, 19, 20)] == ["FUNC:do_bar"] * 3
    assert [s.owner(n) for n in (22, 23)] == ["FUNC:def"] * 2
    assert s.owner(25) == "AFTER"


def test_logical_assignments():
    by_line = {a.line: a for a in _structure().assignments}
    assert by_line[3].value == "Spans two lines"
    assert by_line[3].end_line == 4
    assert by_line[5].value.split() == [
        "https://example.org/foo-${PV}.tar.gz", "file://fix.patch",
    ]
    assert by_line[8].flag == "sha256sum"
    assert by_line[9].base == "RDEPENDS"
    assert by_line[9].overrides == ["${PN}-dev", "append"]
    assert by_line[9].op == "="


def test_inherits_and_includes():
    s = _structure()
    assert {"autotools", "systemd"} <= s.inherits
    assert s.includes == ["foo.inc"]


def test_recipe_name():
    assert recipe_name(Path("foo-bar_1.0.bb")) == "foo-bar"
    assert recipe_name(Path("foo_%.bbappend")) == "foo"
    assert recipe_name(Path("foo.inc")) == "foo"
    assert recipe_name(Path("foo_git.bb")) == "foo"


def _layer(tmp_path):
    (tmp_path / "conf").mkdir()
    (tmp_path / "conf" / "layer.conf").write_text("")
    recipes = tmp_path / "recipes-x" / "foo"
    recipes.mkdir(parents=True)
    return recipes


def _context(path):
    content = path.read_text()
    return FileContext(path=path, content=content, lines=content.splitlines())


def test_sets_variable_through_includes(tmp_path):
    recipes = _layer(tmp_path)
    (tmp_path / "recipes-x" / "common.inc").write_text('LICENSE = "MIT"\ninherit systemd\n')
    (recipes / "foo.inc").write_text("require recipes-x/common.inc\n")
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nSUMMARY = "x"\n')

    context = _context(recipe)

    assert context.sets_variable("SUMMARY") is True
    assert context.sets_variable("LICENSE") is True
    assert context.sets_variable("HOMEPAGE") is False
    assert "systemd" in context.inherits


def test_unresolved_include_makes_absence_unknown(tmp_path):
    recipes = _layer(tmp_path)
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text('require recipes-other/elsewhere.inc\nSUMMARY = "x"\n')

    context = _context(recipe)

    assert context.included_files is None
    assert context.sets_variable("SUMMARY") is True
    assert context.sets_variable("LICENSE") is None


def test_include_cycle_terminates(tmp_path):
    recipes = _layer(tmp_path)
    (recipes / "a.inc").write_text("require b.inc\n")
    (recipes / "b.inc").write_text("require a.inc\nLICENSE = \"MIT\"\n")
    recipe = recipes / "foo_1.0.bb"
    recipe.write_text("require a.inc\n")

    assert _context(recipe).sets_variable("LICENSE") is True
