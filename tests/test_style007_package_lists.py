# -*- coding: utf-8 -*-
"""
STYLE007 reads package lists the way BitBake does.

Quotes inside ${@...} do not close the value, expansions have no name to
sort by, PACKAGES is ordered on purpose (the first package whose FILES
match a file gets it), and only the listed variables themselves are
package lists (not PACKAGECONFIG_GL or PACKAGES_DYNAMIC).

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import PackageListFormatRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(),
    )
    return PackageListFormatRule().check(context)


def test_quotes_inside_inline_python_do_not_close():
    content = (
        'RDEPENDS:${PN} = " \\\n'
        '    alpha \\\n'
        '    ${@bb.utils.contains("DISTRO_FEATURES", "pam", "beta", "", d)} \\\n'
        '    gamma \\\n'
        '"\n'
        '\n'
    )
    assert _check(content) == []


def test_expansions_are_left_out_of_sorting():
    content = (
        'RDEPENDS:${PN} = " \\\n'
        '    alpha \\\n'
        '    ${VIRTUAL-RUNTIME_init_manager} \\\n'
        '    beta \\\n'
        '"\n'
        '\n'
    )
    assert _check(content) == []


def test_packages_order_is_not_checked():
    content = (
        'PACKAGES = " \\\n'
        '    ${PN}-tools \\\n'
        '    libfoo-dev \\\n'
        '    libfoo \\\n'
        '"\n'
        '\n'
    )
    assert _check(content) == []


def test_similar_names_are_not_package_lists():
    content = (
        'PACKAGECONFIG_GL = " \\\n'
        '    zeta \\\n'
        '    alpha \\\n'
        '"\n'
        'PACKAGES_DYNAMIC = "^${PN}-plugin-.* \\\n'
        '    ^${PN}-locale-.*"\n'
    )
    assert _check(content) == []


def test_unsorted_dependencies_are_still_reported():
    content = (
        'DEPENDS = " \\\n'
        '    zeta \\\n'
        '    alpha \\\n'
        '"\n'
        '\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert "alphabetical" in results[0].message
