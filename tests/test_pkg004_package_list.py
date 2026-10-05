# -*- coding: utf-8 -*-
"""
PKG004 reads the package list the way BitBake builds it.

PACKAGES and PACKAGE_BEFORE_PN span continuation lines, name packages
through ${PN}, the literal recipe name or local variables, and are extended
by classes, includes, PACKAGES_DYNAMIC and do_split_packages(). FILES_<NAME>
variables such as FILES_SOLIBSDEV are not FILES of a package.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.package import FilesPackagesConsistencyRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return FilesPackagesConsistencyRule().check(context)


@pytest.mark.parametrize("content", [
    # Continuation lines
    'PACKAGES =+ "${PN}-a \\\n    ${PN}-tools \\\n"\nFILES:${PN}-tools = "${bindir}/t"\n',
    'PACKAGE_BEFORE_PN = " \\\n    ${PN}-a \\\n    ${PN}-tools \\\n"\n'
    'FILES:${PN}-tools = "${bindir}/t"\n',
    # Local variable indirection
    'FOO_PACKAGES = "${PN}-tools"\nPACKAGE_BEFORE_PN = "${FOO_PACKAGES}"\n'
    'FILES:${PN}-tools = "${bindir}/t"\n',
    # Literal PN on one side, ${PN} or ${BPN} on the other
    'PACKAGES =+ "foo-tools"\nFILES:${PN}-tools = "${bindir}/t"\n',
    'PACKAGES =+ "${BPN}-tools"\nFILES:foo-tools = "${bindir}/t"\n',
    # Names with '+' and '.'
    'PACKAGES =+ "libfoo++ foo1.0-bar"\nFILES:libfoo++ = "${libdir}/a"\n'
    'FILES:foo1.0-bar = "${libdir}/b"\n',
    # FILES_SOLIBSDEV is a variable, not FILES of a package
    'FILES_SOLIBSDEV = ""\n',
    # FILES:append is the variable itself
    'FILES:append = " ${bindir}/t"\n',
    # PACKAGES_DYNAMIC regular expressions
    'PACKAGES_DYNAMIC = "^${PN}-plugin-.*"\nFILES:${PN}-plugin-x = "${libdir}/x"\n',
    'PACKAGES_DYNAMIC += "^${PN}-locale-.*"\nFILES:${PN}-locale-de = "${datadir}/de"\n',
    # Standard and class-created packages
    'FILES:${PN}-src = "a"\nFILES:${PN}-lic = "b"\nFILES:${PN}-locale = "c"\n',
    'inherit ptest-perl\nFILES:${PN}-ptest = "${PTEST_PATH}"\n',
    'inherit lib_package\nFILES:${PN}-bin = "${bindir}"\n',
    'inherit bash-completion\nFILES:${PN}-bash-completion += "a"\n',
    'inherit gnome-help\nFILES:${PN}-help += "a"\n',
    'inherit breakpad\nFILES:${PN}-breakpad = "a"\n',
    'inherit packagegroup\nPACKAGES = "${PN} ${PN}-x"\nFILES:${PN}-x-dev = "a"\n',
    # Packages split off at packaging time
    'python populate_packages:prepend () {\n'
    '    do_split_packages(d, "${libdir}", r"^(.*)\\.so$", "${PN}-%s", "%s")\n'
    '}\nFILES:${PN}-mod = "a"\n',
    'PACKAGESPLITFUNCS:prepend = "split_foo "\nFILES:${PN}-mod = "a"\n',
    # A package list named through a variable set elsewhere
    'PACKAGES =+ "${KERNEL_PACKAGE_NAME}-x"\nFILES:${PN}-x = "a"\n',
    # A package named through a variable this file does not set
    'FILES:${KERNEL_PACKAGE_NAME}-base = "a"\n',
])
def test_existing_package_not_flagged(content):
    assert _check(content) == []


def test_missing_package_flagged_as_warning():
    results = _check(
        'PACKAGES =+ "${PN}-a \\\n    ${PN}-b \\\n"\n'
        'FILES:${PN}-tools = "${bindir}/t"\n'
    )
    assert len(results) == 1
    assert results[0].line == 4
    assert results[0].severity == Severity.WARNING
    assert "${PN}-tools" in results[0].message


def test_append_to_missing_package_flagged():
    results = _check('FILES:${PN}-tools:append = " ${bindir}/t"\n')
    assert len(results) == 1


def test_ptest_package_needs_ptest_class():
    assert len(_check('FILES:${PN}-ptest = "a"\n')) == 1


@pytest.mark.parametrize("path", [Path("foo.inc"), Path("foo_%.bbappend")])
def test_fragment_without_package_list_not_judged(path):
    assert _check('FILES:${PN}-tools = "${bindir}/t"\n', path) == []


def test_fragment_replacing_package_list_judged():
    results = _check(
        'PACKAGES = "${PN} ${PN}-a"\nFILES:${PN}-tools = "${bindir}/t"\n',
        Path("foo.inc"),
    )
    assert len(results) == 1


def test_packages_from_include(tmp_path):
    (tmp_path / "foo.inc").write_text('PACKAGES =+ "${PN}-tools"\n')
    recipe = tmp_path / "foo_1.0.bb"
    content = 'require foo.inc\nFILES:${PN}-tools = "${bindir}/t"\n'
    recipe.write_text(content)
    assert _check(content, recipe) == []


def test_unresolved_include_not_judged(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    content = 'require missing.inc\nFILES:${PN}-tools = "${bindir}/t"\n'
    recipe.write_text(content)
    assert _check(content, recipe) == []
