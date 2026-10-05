# -*- coding: utf-8 -*-
"""
STYLE006 does not split a conditional ${@...} inherit into classes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import DuplicateInheritRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return DuplicateInheritRule().check(context)


def test_conditional_inherit_is_not_a_duplicate():
    content = "inherit ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'systemd', '', d)}\n"
    assert _check(content) == []


def test_classes_around_the_expression_are_still_checked():
    content = (
        "inherit pkgconfig ${@bb.utils.contains('PACKAGECONFIG', 'vala', 'vala', '', d)}\n"
        "inherit pkgconfig\n"
    )
    results = _check(content)
    assert len(results) == 1
    assert "'pkgconfig'" in results[0].message
