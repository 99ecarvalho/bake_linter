# -*- coding: utf-8 -*-
"""
NAMING003 accepts the PN forms BitBake recipes use on purpose.

PN under an override (PN:class-devupstream) names a variant for that
override only, and a PN suffixed with expansions
(foo-cross-canadian-${TRANSLATED_TARGET_ARCH}) is the cross-canadian/SDK
idiom of one recipe per target.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.engine import LintEngine
from bake_linter.rules.naming import InconsistentPNRule


def _check(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    context = LintEngine()._parse_file(path)
    return InconsistentPNRule().check(context)


@pytest.mark.parametrize("line", [
    'PN:class-devupstream = "foo-upstream"',
    'PN = "foo-${MACHINE}"',
    'PN = "foo-${SDK_SYS}-${MACHINE}"',
])
def test_accepted_forms(tmp_path, line):
    assert _check(tmp_path, "foo_1.0.bb", line + "\n") == []


@pytest.mark.parametrize("line", ['PN = "bar"', 'PN = "foo-extra"', 'PN = "bar-${MACHINE}"'])
def test_other_names_are_reported(tmp_path, line):
    assert len(_check(tmp_path, "foo_1.0.bb", line + "\n")) == 1
