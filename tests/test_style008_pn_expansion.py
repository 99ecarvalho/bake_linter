# -*- coding: utf-8 -*-
"""
STYLE008 counts ${PN} and the recipe name as one package.

SYSTEMD_PACKAGES = "foo" and SYSTEMD_SERVICE:${PN} in foo_1.0.bb name the
same package, so a bare SYSTEMD_AUTO_ENABLE is not ambiguous.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import SystemdAutoEnableRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return SystemdAutoEnableRule().check(context)


def test_pn_and_recipe_name_are_one_package():
    content = (
        'inherit systemd\n'
        'SYSTEMD_PACKAGES = "foo"\n'
        'SYSTEMD_SERVICE:${PN} = "foo.service"\n'
        'SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    assert _check(content) == []


def test_two_packages_are_still_ambiguous():
    content = (
        'inherit systemd\n'
        'SYSTEMD_PACKAGES = "foo ${PN}-extra"\n'
        'SYSTEMD_SERVICE:${PN} = "foo.service"\n'
        'SYSTEMD_SERVICE:${PN}-extra = "bar.service"\n'
        'SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    assert len(_check(content)) == 1
