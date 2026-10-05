# -*- coding: utf-8 -*-
"""
PYTHON003 accepts raising SkipRecipe/SkipPackage in anonymous python.

That is how a recipe skips itself at parse time; bb.fatal() would fail
the whole parse instead.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.python_code import AnonymousPythonIssuesRule


def _check(statement):
    content = (
        "python __anonymous () {\n"
        "    if not d.getVar('FOO'):\n"
        f"        {statement}\n"
        "}\n"
    )
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return AnonymousPythonIssuesRule().check(context)


@pytest.mark.parametrize("statement", [
    'raise bb.parse.SkipRecipe("FOO is not set")',
    "raise SkipRecipe('FOO is not set')",
    'raise bb.parse.SkipPackage("FOO is not set")',
])
def test_skip_exceptions_are_accepted(statement):
    assert _check(statement) == []


def test_other_exceptions_are_reported():
    assert len(_check('raise ValueError("FOO is not set")')) == 1
