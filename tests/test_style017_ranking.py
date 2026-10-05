# -*- coding: utf-8 -*-
"""
STYLE017 ranks only the main definition of each variable.

Additions (+=, :append, :prepend, :remove) and per-package or
conditional variants sit next to what they refine, not in the
recipe-level order.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.style import RecipeVariableOrderRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return RecipeVariableOrderRule().check(context)


@pytest.mark.parametrize("line", [
    'RDEPENDS:${PN}-tools += "bash"',
    'RDEPENDS:${PN}:append = " bash"',
    'SRC_URI += "file://fix.patch"',
    'DEPENDS:remove = "bar"',
    'EXTRA_OECONF:class-native = "--disable-x"',
    'RRECOMMENDS:${PN}-dev = "bar-dev"',
])
def test_additions_and_variants_are_not_ranked(line):
    content = f'{line}\nSUMMARY = "Foo"\nLICENSE = "MIT"\n'
    assert _check(content) == []


def test_main_definition_out_of_order_is_reported():
    content = 'RDEPENDS:${PN} = "bash"\nSUMMARY = "Foo"\n'
    assert len(_check(content)) == 1
