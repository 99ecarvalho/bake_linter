# -*- coding: utf-8 -*-
"""
VARIABLES002 follows the configured Yocto release.

S = "${WORKDIR}" works up to scarthgap and is a fatal error from styhead
on, so it is info on old releases and a warning on new or unknown ones.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.engine import LintEngine
from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.variables import UnconventionalSAssignmentRule

CONTENT = 'SRC_URI = "file://helper.sh"\nS = "${WORKDIR}"\n'


def _check(release):
    context = FileContext(path=Path("foo_1.0.bb"), content=CONTENT,
                          lines=CONTENT.splitlines(), release=release)
    return UnconventionalSAssignmentRule().check(context)


@pytest.mark.parametrize("release,severity", [
    ("kirkstone", Severity.INFO),
    ("scarthgap", Severity.INFO),
    ("Scarthgap", Severity.INFO),
    ("styhead", Severity.WARNING),
    ("whinlatter", Severity.WARNING),
    (None, Severity.WARNING),
    ("unknown-release", Severity.WARNING),
])
def test_severity_follows_release(release, severity):
    results = _check(release)
    assert [r.severity for r in results] == [severity]


def test_engine_passes_release(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(CONTENT)
    engine = LintEngine()
    engine.configure(release="scarthgap")
    assert engine._parse_file(recipe).release == "scarthgap"
