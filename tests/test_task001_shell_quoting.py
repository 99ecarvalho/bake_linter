# -*- coding: utf-8 -*-
"""
TASK001 knows where the shell does not split an expansion.

Inside single quotes $D is not expanded at all, and the value of a shell
variable assignment (name=$D at the start of a command) is not split.
An argument that merely looks like an assignment (make DESTDIR=$D) is.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.task import UnquotedVariableRule


def _check(line):
    content = f"do_install() {{\n    {line}\n}}\n"
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return UnquotedVariableRule().check(context)


@pytest.mark.parametrize("line", [
    "opts='-E LD_LIBRARY_PATH=$D${libdir}'",
    "dest=$D${bindir}",
    "FOO=1 dest=$D${bindir}",
    "if true; then dest=$D${bindir}; fi",
    'cp foo "$D${bindir}"',
])
def test_safe_expansions(line):
    assert _check(line) == []


@pytest.mark.parametrize("line", [
    "cp foo $D${bindir}",
    "make DESTDIR=$D install",
])
def test_split_expansions_are_reported(line):
    assert len(_check(line)) == 1
