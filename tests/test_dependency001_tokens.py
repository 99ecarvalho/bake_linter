# -*- coding: utf-8 -*-
"""
DEPENDENCY001 reads the packages in an RDEPENDS value, as whole names.

The variable name (RDEPENDS:${PN}:class-native) is not a package, a
package name that merely contains a tool name (gcc-symlinks) is not that
tool, and :remove takes packages away. Test suites and -dev packages need
build tools on the target, and native recipes and packagegroups are not
target packages that pull build tools by accident.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.dependency import WrongDependencyTypeRule


def _check(content, name="foo_1.0.bb"):
    context = FileContext(
        path=Path(name),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return WrongDependencyTypeRule().check(context)


@pytest.mark.parametrize("line", [
    'RDEPENDS:${PN}:class-native = ""',
    'RDEPENDS:${PN}:class-native = "m4-native perl-native"',
    'RDEPENDS:${PN}:append:class-nativesdk = " openssl-native"',
    'RDEPENDS:${PN}-ptest += "make cmake bash"',
    'RDEPENDS:${PN}-ptest:append = " make"',
    'RDEPENDS:${PN}-dev += "libtool"',
    'RDEPENDS:${PN} = "gcc-symlinks g++-symlinks cpp"',
    'RDEPENDS:${PN} = "gettext-dev libxml-parser-perl"',
    'RDEPENDS:${PN}:remove = "make"',
    'RDEPENDS:foo-native:remove = "bar-native"',
])
def test_not_reported(line):
    assert _check(line + "\n") == []


def test_native_recipe_is_skipped():
    assert _check('RDEPENDS:${PN} = "m4-native"\n', name="foo-native_1.0.bb") == []


def test_inherit_native_is_skipped():
    assert _check('inherit native\nRDEPENDS:${PN} = "m4-native"\n') == []


def test_packagegroup_is_skipped():
    content = 'inherit packagegroup\nRDEPENDS:${PN} = "make gcc"\n'
    assert _check(content, name="packagegroup-foo.bb") == []


@pytest.mark.parametrize("line,token", [
    ('RDEPENDS:${PN} = "qemu-system-native"', "qemu-system-native"),
    ('RDEPENDS:${PN} = "bash ninja python3-core"', "ninja"),
    ('RDEPENDS:${PN}:append:class-target = " gcc g++ binutils"', "gcc"),
])
def test_reported(line, token):
    results = _check(line + "\n")
    assert len(results) == 1
    assert f"'{token}'" in results[0].message


def test_continuation_line_is_reported_where_the_package_is():
    content = 'RDEPENDS:${PN} = "bash \\\n    cmake \\\n"\n'
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 2
