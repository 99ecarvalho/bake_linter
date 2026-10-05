# -*- coding: utf-8 -*-
"""
SYSTEMD001 and SYSTEMD002 see the systemd class wherever it is inherited.

The class may be inherited in a required file or through an inline
expression, and SYSTEMD_SERVICE may be declared in a required file. An
empty SYSTEMD_SERVICE does not use the class.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.systemd import (
    SystemdMissingServiceDeclarationRule,
    SystemdWithoutInheritRule,
)


def _context(content, path=Path("foo_1.0.bb")):
    return FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )


@pytest.mark.parametrize("content", [
    "inherit ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'systemd', '', d)}\n"
    'SYSTEMD_SERVICE:${PN} = "foo.service"\n',
    'SYSTEMD_SERVICE:${PN} = ""\n',
])
def test_systemd001_not_flagged(content):
    assert SystemdWithoutInheritRule().check(_context(content)) == []


def test_systemd001_flagged_without_inherit():
    results = SystemdWithoutInheritRule().check(
        _context('SYSTEMD_SERVICE:${PN} = "foo.service"\n'))
    assert len(results) == 1


def test_systemd001_inherit_in_include(tmp_path):
    (tmp_path / "foo.inc").write_text("inherit autotools systemd\n")
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\nSYSTEMD_SERVICE:${PN} = "foo.service"\n')
    context = _context(recipe.read_text(), recipe)
    assert SystemdWithoutInheritRule().check(context) == []


def test_systemd001_unresolved_include(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require missing.inc\nSYSTEMD_SERVICE:${PN} = "foo.service"\n')
    context = _context(recipe.read_text(), recipe)
    assert SystemdWithoutInheritRule().check(context) == []


INSTALL = (
    'do_install() {\n'
    '    install -m 0644 ${WORKDIR}/foo.service ${D}${systemd_system_unitdir}\n'
    '}\n'
)


def test_systemd002_declaration_in_include(tmp_path):
    (tmp_path / "foo.inc").write_text('inherit systemd\nSYSTEMD_SERVICE:${PN} = "foo.service"\n')
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\n' + INSTALL)
    context = _context(recipe.read_text(), recipe)
    assert SystemdMissingServiceDeclarationRule().check(context) == []


def test_systemd002_inherit_in_include_without_declaration(tmp_path):
    (tmp_path / "foo.inc").write_text('inherit systemd\n')
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\n' + INSTALL)
    context = _context(recipe.read_text(), recipe)
    assert len(SystemdMissingServiceDeclarationRule().check(context)) == 1
