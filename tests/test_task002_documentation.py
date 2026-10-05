# -*- coding: utf-8 -*-
"""
TASK002 leaves documentation variables alone.

A DESCRIPTION that mentions "su and sudo" is prose, not a command run
by the build.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.task import SudoUsageRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return SudoUsageRule().check(context)


@pytest.mark.parametrize("content", [
    'DESCRIPTION = "A tool that replaces su and sudo for containers"\n',
    'SUMMARY:${PN}-tools = "Helpers to run sudo -u in scripts"\n',
    'DESCRIPTION = "A simple tool. \\\n    Unlike su and sudo = it does not fork"\n',
])
def test_documentation_not_flagged(content):
    assert _check(content) == []


def test_sudo_in_variable_still_flagged():
    assert len(_check('FOO_CMD = "cd src && sudo make install"\n')) == 1
