# -*- coding: utf-8 -*-
"""
PKG006 reads the package list the way BitBake builds it.

It shares PKG005's reading of PACKAGES. The package an RRECOMMENDS is for
comes before any flag or operation override, and a distro or machine
configuration sets RRECOMMENDS of packages other recipes create.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.package import RrecommendsPackageValidityRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return RrecommendsPackageValidityRule().check(context)


@pytest.mark.parametrize("content", [
    # Continuation lines and local variables
    'PACKAGES =+ "${PN}-a \\\n    ${PN}-tools \\\n"\nRRECOMMENDS:${PN}-tools = "bash"\n',
    'FOO_PACKAGES = "${PN}-tools"\nPACKAGE_BEFORE_PN = "${FOO_PACKAGES}"\n'
    'RRECOMMENDS:${PN}-tools = "bash"\n',
    # Literal PN and ${PN}
    'PACKAGES =+ "${PN}-tools"\nRRECOMMENDS:foo-tools = "bash"\n',
    # Flags and operation overrides name the same package
    'RRECOMMENDS:foo-dev[nodeprrecs] = "1"\n',
    'PACKAGES =+ "${PN}-tools"\nRRECOMMENDS:${PN}-tools:append = " bash"\n',
    'RRECOMMENDS:${PN}:remove = "bash"\n',
    # Standard packages
    'RRECOMMENDS:${PN}-staticdev = "a"\nRRECOMMENDS:${PN}-src = "b"\n'
    'RRECOMMENDS:${PN}-locale = "c"\nRRECOMMENDS:${PN}-lic = "d"\n',
    # Class-created packages
    'inherit ptest\nRRECOMMENDS:${PN}-ptest = "bash"\n',
    'inherit packagegroup\nPACKAGES = "${PN} ${PN}-x"\nRRECOMMENDS:${PN}-x = "a"\n',
    # PACKAGES_DYNAMIC
    'PACKAGES_DYNAMIC = "^${PN}-plugin-.*"\nRRECOMMENDS:${PN}-plugin-x = "a"\n',
    # Packages split off at packaging time
    'python populate_packages:prepend () {\n'
    '    do_split_packages(d, "${libdir}", r"^(.*)\\.so$", "${PN}-%s", "%s")\n'
    '}\nRRECOMMENDS:${PN}-mod = "a"\n',
])
def test_existing_package_not_flagged(content):
    assert _check(content) == []


def test_missing_package_flagged_as_info():
    results = _check('PACKAGES = "${PN}"\nRRECOMMENDS:${PN}-utils += "a"\n')
    assert len(results) == 1
    assert results[0].line == 2
    assert results[0].severity == Severity.INFO


def test_ptest_package_needs_ptest_class():
    assert len(_check('RRECOMMENDS:${PN}-ptest = "bash"\n')) == 1


def test_configuration_not_judged():
    path = Path("meta-foo/conf/machine/include/foo.conf")
    assert _check('RRECOMMENDS:${PN}-extra = "a"\n', path) == []


def test_unresolved_include_not_judged(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    content = 'require missing.inc\nRRECOMMENDS:${PN}-tools = "a"\n'
    recipe.write_text(content)
    assert _check(content, recipe) == []


def test_include_fragment_not_judged():
    assert _check('RRECOMMENDS:${PN}-tools = "a"\n', Path("foo.inc")) == []
