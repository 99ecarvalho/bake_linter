"""
PKG002 scope on .bbappend files.

A .bbappend holds a fragment of a recipe. The FILES that covers its installs
lives in the base recipe, which PKG002 does not read and does not resolve, so
coverage cannot be judged from an append that only adds to FILES: ':append',
':prepend' and '+=' say what the append contributes and nothing about what the
base already covers. A hard assignment is different, because in a .bbappend it
replaces the base value and the whole set is therefore visible.

These tests pin that split: silent where the rule cannot be right, still strict
everywhere it can.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.package import FilesNotMatchingInstallRule

APPEND_INSTALL = 'do_install:append() {\n\tinstall -d ${D}/data\n}\n'
RECIPE_INSTALL = 'do_install() {\n\tinstall -d ${D}/data\n}\n'


def _check(name: str, content: str):
    context = FileContext(
        path=Path(name),
        content=content,
        lines=content.splitlines(),
        variables={},
    )
    return FilesNotMatchingInstallRule().check(context)


# --- .bbappend: additive or absent FILES means the rule cannot judge ---

def test_bbappend_without_files_is_not_judged():
    assert _check("thing_%.bbappend", APPEND_INSTALL) == []


def test_bbappend_with_files_append_is_not_judged():
    """The real shape in base-files: append two entries, rely on the base for the rest."""
    content = APPEND_INSTALL + '\nFILES:${PN}:append:qemuriscv64= " /lib64"\n'
    assert _check("base-files_%.bbappend", content) == []


def test_bbappend_with_files_plus_equals_is_not_judged():
    content = APPEND_INSTALL + '\nFILES:${PN} += "/lib64"\n'
    assert _check("thing_%.bbappend", content) == []


def test_bbappend_with_conditional_files_is_not_judged():
    """'?=' does nothing when the base recipe already set FILES."""
    content = APPEND_INSTALL + '\nFILES:${PN} ?= "/lib64"\n'
    assert _check("thing_%.bbappend", content) == []


# --- .bbappend: a hard assignment replaces the base value, so judge it ---

def test_bbappend_with_hard_assignment_missing_the_path_is_reported():
    content = APPEND_INSTALL + '\nFILES:${PN} = "/lib64"\n'
    results = _check("thing_%.bbappend", content)
    assert len(results) == 1
    assert "/data" in results[0].message


def test_bbappend_with_hard_assignment_covering_the_path_is_clean():
    content = APPEND_INSTALL + '\nFILES:${PN} = "/data"\n'
    assert _check("thing_%.bbappend", content) == []


def test_bbappend_with_immediate_hard_assignment_is_judged():
    content = APPEND_INSTALL + '\nFILES:${PN} := "/lib64"\n'
    assert len(_check("thing_%.bbappend", content)) == 1


# --- .bb recipes: behaviour must be exactly as before ---

def test_recipe_missing_the_path_is_reported():
    content = RECIPE_INSTALL + '\nFILES:${PN} = "${bindir}/*"\n'
    assert len(_check("thing_1.0.bb", content)) == 1


def test_recipe_with_root_files_is_covered():
    """FILES:${PN} = "/" covers everything, which is how base-files is written."""
    content = RECIPE_INSTALL + '\nFILES:${PN} = "/"\n'
    assert _check("base-files_3.0.14.bb", content) == []


def test_recipe_without_any_files_is_still_reported():
    assert len(_check("thing_1.0.bb", RECIPE_INSTALL)) == 1
