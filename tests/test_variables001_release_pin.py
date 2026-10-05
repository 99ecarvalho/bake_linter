# -*- coding: utf-8 -*-
"""
VARIABLES001 is a suggestion: a release-tag SRCREV keeps a plain PV.

Whether SRCREV is the commit of a release tag cannot be checked offline,
so the finding is informational, and *_git.inc files are skipped like
*_git.bb recipes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.variables import GitRecipeWithoutSRCPVRule

CONTENT = (
    'SRC_URI = "git://example.org/foo.git;protocol=https;branch=main"\n'
    'SRCREV = "0123456789abcdef0123456789abcdef01234567"\n'
    'PV = "1.0"\n'
)


def _check(name):
    context = FileContext(path=Path(name), content=CONTENT,
                          lines=CONTENT.splitlines())
    return GitRecipeWithoutSRCPVRule().check(context)


def test_finding_is_informational():
    results = _check("foo_1.0.bb")
    assert len(results) == 1
    assert results[0].severity == Severity.INFO
    assert "release tag" in results[0].hint


def test_git_inc_is_skipped():
    assert _check("foo_git.inc") == []
