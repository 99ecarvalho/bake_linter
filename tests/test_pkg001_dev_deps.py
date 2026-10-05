# -*- coding: utf-8 -*-
"""
PKG001 follows the dev-deps QA test of insane.bbclass.

Only runtime dependencies ending in -dev count, and only for packages
that are not development, debug, packagegroup or image packages, in
recipes that are not kernels or kernel modules, without INSANE_SKIP.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.package import RdependsOnDevPackageRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return RdependsOnDevPackageRule().check(context)


@pytest.mark.parametrize("content", [
    'RDEPENDS:${PN}-dev += "libbar-dev"\n',
    'RDEPENDS:${PN}-dev:append:class-native = " libbar-dev"\n',
    'RDEPENDS:libfoo-staticdev = "libfoo-dev"\n',
    'RDEPENDS:packagegroup-foo-sdk = "libbar-dev"\n',
    'RDEPENDS:${PN}-image = "libbar-dev"\n',
    'inherit module\nRDEPENDS:${PN} = "libbar-dev"\n',
    'inherit kernel\nRDEPENDS:${PN} = "libbar-dev"\n',
    'RDEPENDS:${PN}-ptest = "libbar-dev"\nINSANE_SKIP:${PN}-ptest = "dev-deps"\n',
    'RDEPENDS:foo = "libbar-dev"\nINSANE_SKIP:${PN} += "dev-deps"\n',
    # Not a -dev package: the name only contains -dev
    'RDEPENDS:${PN} = "libfoo-devtools udev-dev-helper"\n',
    # The package name, not the value, holds -dev
    'RDEPENDS:${PN}-dev = "${PN}"\n',
])
def test_not_flagged(content):
    assert _check(content) == []


def test_continuation_lines_and_versions():
    results = _check(
        'RDEPENDS:${PN} = " \\\n    bash \\\n    libbar-dev (>= 1.0) \\\n"\n'
    )
    assert len(results) == 1
    assert "libbar-dev" in results[0].message
    assert results[0].line == 1


def test_other_package_skip_does_not_apply():
    results = _check(
        'RDEPENDS:${PN} = "libbar-dev"\nINSANE_SKIP:${PN}-ptest = "dev-deps"\n'
    )
    assert len(results) == 1
