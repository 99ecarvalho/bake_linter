# -*- coding: utf-8 -*-
"""
PKG005 reads the package list the way BitBake builds it.

PACKAGES and PACKAGE_BEFORE_PN span continuation lines, name packages
through ${PN} or local variables, and are extended by classes, includes and
PACKAGES_DYNAMIC. A .bbappend or .inc only holds part of the list.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.package import RdependsPackageExistenceRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return RdependsPackageExistenceRule().check(context)


@pytest.mark.parametrize("content", [
    # Continuation lines
    'PACKAGES =+ "${PN}-a \\\n    ${PN}-tools \\\n"\nRDEPENDS:${PN}-tools = "bash"\n',
    'PACKAGE_BEFORE_PN = " \\\n    ${PN}-a \\\n    ${PN}-tools \\\n"\n'
    'RDEPENDS:${PN}-tools = "bash"\n',
    # Local variable indirection
    'FOO_PACKAGES = "${PN}-tools"\nPACKAGE_BEFORE_PN = "${FOO_PACKAGES}"\n'
    'RDEPENDS:${PN}-tools = "bash"\n',
    # Literal PN on one side, ${PN} on the other
    'PACKAGES =+ "foo-tools"\nRDEPENDS:${PN}-tools = "bash"\n',
    'PACKAGES =+ "${PN}-tools"\nRDEPENDS:foo-tools = "bash"\n',
    # Names with '.' and '+'
    'PACKAGES =+ "${PN}-gtk+3 ${PN}-1.2"\nRDEPENDS:${PN}-gtk+3 = "a"\n'
    'RDEPENDS:${PN}-1.2 = "b"\n',
    # Inline expression
    'PACKAGES =+ "${@bb.utils.contains(\'PACKAGECONFIG\', \'x\', \'${PN}-x\', \'\', d)}"\n'
    'RDEPENDS:${PN}-x = "bash"\n',
    # PACKAGES_DYNAMIC
    'PACKAGES_DYNAMIC = "^${PN}-plugin-.*"\nRDEPENDS:${PN}-plugin-foo = "bash"\n',
    # Standard and class-created packages
    'RDEPENDS:${PN}-src = "bash"\nRDEPENDS:${PN}-lic = "bash"\n',
    'inherit lib_package\nRDEPENDS:${PN}-bin = "bash"\n',
    'inherit ptest-perl\nRDEPENDS:${PN}-ptest = "bash"\n',
    'inherit ptest-gnome\nRDEPENDS:${PN}-ptest = "bash"\n',
    # BBCLASSEXTEND variants
    'BBCLASSEXTEND = "native nativesdk"\nRDEPENDS:nativesdk-${PN} = "a"\n'
    'RDEPENDS:${PN}-native-dev = "b"\n',
    # PACKAGES built from Python
    'python () {\n    d.appendVar(\'PACKAGES\', \' ${PN}-tools\')\n}\n'
    'RDEPENDS:${PN}-tools = "bash"\n',
    # "+=" written without a space before it
    'RDEPENDS:${PN}+= "bash"\n',
    # A package named through a variable this file does not set
    'RDEPENDS:${KERNEL_PACKAGE_NAME}-base = "bash"\n',
])
def test_existing_package_not_flagged(content):
    assert _check(content) == []


def test_missing_package_flagged_as_warning():
    results = _check(
        'PACKAGES =+ "${PN}-a \\\n    ${PN}-b \\\n"\n'
        'RDEPENDS:${PN}-tools = "bash"\n'
    )
    assert len(results) == 1
    assert results[0].line == 4
    assert results[0].severity == Severity.WARNING


def test_exact_name_match_only():
    """A defined package whose name contains the missing one does not count."""
    results = _check('PACKAGES =+ "${PN}-tools-extra"\nRDEPENDS:${PN}-tools = "bash"\n')
    assert len(results) == 1


@pytest.mark.parametrize("name", ["foo_%.bbappend", "foo.inc"])
def test_fragment_without_hard_packages_skipped(name):
    assert _check('RDEPENDS:${PN}-tools = "bash"\n', Path(name)) == []


def test_bbappend_replacing_packages_checked():
    results = _check('PACKAGES = "${PN}"\nRDEPENDS:${PN}-tools = "bash"\n',
                     Path("foo_%.bbappend"))
    assert len(results) == 1


def test_package_from_include(tmp_path):
    (tmp_path / "foo.inc").write_text('inherit ptest\nPACKAGES =+ "${PN}-tools"\n')
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nRDEPENDS:${PN}-tools = "a"\n'
                      'RDEPENDS:${PN}-ptest = "b"\n')
    assert _check(recipe.read_text(), recipe) == []


def test_unresolved_include_skipped(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require missing.inc\nRDEPENDS:${PN}-tools = "a"\n')
    assert _check(recipe.read_text(), recipe) == []
