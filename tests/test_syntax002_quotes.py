# -*- coding: utf-8 -*-
"""
SYNTAX002 follows the quote a value opens with and skips function bodies.

A single-quoted value closes on a single quote (it may contain double
quotes), and lines in shell functions, heredocs included, are not
BitBake assignments.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.syntax import MissingLineContinuationRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return MissingLineContinuationRule().check(context)


def test_single_quoted_value_with_double_quotes():
    content = (
        "EXTRA_OEMAKE='KERNEL_DIR=\"${STAGING_KERNEL_DIR}\" PREFIX=\"${D}\"'\n"
        "\n"
        "do_compile() {\n"
        "    oe_runmake\n"
        "}\n"
    )
    assert _check(content) == []


def test_heredoc_in_function_body():
    content = (
        "do_install:append() {\n"
        "    cat > ${D}${sysconfdir}/foo.conf <<EOF\n"
        'Name = "${FOO_NAME}" , "${FOO_KEY}";\n'
        'Path = "/srv/foo";\n'
        "EOF\n"
        "}\n"
    )
    assert _check(content) == []


def test_prepend_operator_and_missing_continuation():
    content = (
        'FOO =+ "a\n'
        'b\n'
        'c"\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 2
