# -*- coding: utf-8 -*-
"""
STYLE013 accepts single quotes around a value that holds double quotes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import SingleQuoteUsageRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return SingleQuoteUsageRule().check(context)


def test_value_with_double_quotes():
    assert _check("EXTRA_OEMAKE = 'CC=\"${CC}\" PREFIX=\"${prefix}\"'\n") == []


def test_prepend_operator_and_function_body():
    content = (
        "do_configure:prepend:class-target() {\n"
        "FOO='bar'\n"
        "}\n"
    )
    assert _check(content) == []
    assert len(_check("FOO =+ 'bar'\n")) == 1


def test_plain_single_quotes_are_reported():
    assert len(_check("FOO = 'bar'\n")) == 1
