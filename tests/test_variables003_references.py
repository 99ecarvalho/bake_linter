# -*- coding: utf-8 -*-
"""
VARIABLES003 sees references from python and ignores shell assignments.

d.getVar('X') and names passed to helpers inside ${@...} read a
variable as surely as ${X}; FOO=bar in a function body or on a
continuation line is not a BitBake assignment.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.variables import UnusedVariableAssignmentRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return UnusedVariableAssignmentRule().check(context)


@pytest.mark.parametrize("reference", [
    "python do_foo() {\n    bb.note(d.getVar('FOO_MODE'))\n}\n",
    'python do_foo() {\n    bb.note(d.getVar("FOO_MODE"))\n}\n',
    "DEPENDS = \"${@bb.utils.contains('FOO_MODE', 'x', 'y', '', d)}\"\n",
    "DEPENDS = \"${@oe.utils.conditional('FOO_MODE', '1', 'y', '', d)}\"\n",
])
def test_python_references(reference):
    assert _check('FOO_MODE = "x"\n' + reference) == []


def test_shell_and_continuation_assignments_are_ignored():
    content = (
        "do_install:append:class-native() {\n"
        "LOCALVAR=1\n"
        "}\n"
        'EXTRA_OEMAKE = "\\\n'
        'OTHERVAR=1 \\\n'
        '"\n'
    )
    assert _check(content) == []


def test_unreferenced_variable_is_reported():
    assert len(_check('FOO_MODE = "x"\n')) == 1
