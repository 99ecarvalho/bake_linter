# -*- coding: utf-8 -*-
"""
STYLE019 reads only BitBake assignments, not shell code.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import SourceVariablesOrderRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return SourceVariablesOrderRule().check(context)


def test_shell_assignment_is_not_s():
    content = (
        "do_configure:prepend:class-native() {\n"
        "S=${B}\n"
        "}\n"
        'SRC_URI = "https://example.org/foo-${PV}.tar.gz"\n'
        'S = "${WORKDIR}/foo-${PV}"\n'
    )
    assert _check(content) == []


def test_s_before_src_uri_is_reported():
    content = 'S = "${WORKDIR}/foo"\nSRC_URI = "https://example.org/foo.tar.gz"\n'
    assert len(_check(content)) == 1
