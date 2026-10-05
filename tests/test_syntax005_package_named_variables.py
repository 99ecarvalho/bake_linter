# -*- coding: utf-8 -*-
"""
SYNTAX005 knows variables whose name carries a package.

update-alternatives.bbclass reads ALTERNATIVE_PRIORITY_<pkg> and
ALTERNATIVE_TARGET_<pkg>: the underscore there is part of the variable
name, not an old-style override.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.syntax import MixedOverrideSyntaxRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return MixedOverrideSyntaxRule().check(context)


@pytest.mark.parametrize("line", [
    'ALTERNATIVE_PRIORITY_${PN} = "100"\n',
    'ALTERNATIVE_PRIORITY_${PN}-tools = "60"\n',
    'ALTERNATIVE_TARGET_${PN} = "${bindir}/foo"\n',
])
def test_package_named_variable_not_old_syntax(line):
    assert _check(line + 'RDEPENDS:${PN} += "bash"\n') == []


@pytest.mark.parametrize("line", [
    'RDEPENDS_${PN} = "bash"\n',
    'ALTERNATIVE_PRIORITY_${PN}_append = " 1"\n',
    'SRC_URI_append = " file://a.patch"\n',
])
def test_old_syntax_still_flagged(line):
    assert len(_check(line + 'FILES:${PN} += "${datadir}"\n')) == 1
