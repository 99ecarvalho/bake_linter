# -*- coding: utf-8 -*-
"""
DEPRECATED001 accepts the per-package update-alternatives variables.

update-alternatives.bbclass reads ALTERNATIVE_PRIORITY_<pkg> and
ALTERNATIVE_TARGET_<pkg> by name, so the underscore is part of the
variable name and the colon form would not be read.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.deprecated import DeprecatedOverrideSyntaxRule


def _check(line):
    content = line + "\n"
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return DeprecatedOverrideSyntaxRule().check(context)


@pytest.mark.parametrize("line", [
    'ALTERNATIVE_PRIORITY_${PN} = "100"',
    'ALTERNATIVE_TARGET_${PN} = "${bindir}/foo"',
])
def test_update_alternatives_variables(line):
    assert _check(line) == []


def test_old_override_is_still_reported():
    assert len(_check('RDEPENDS_${PN} = "bar"')) == 1
