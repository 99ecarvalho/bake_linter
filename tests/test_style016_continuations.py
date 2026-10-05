# -*- coding: utf-8 -*-
"""
STYLE016 checks block indentation, not continuation alignment.

A line inside open brackets, a triple-quoted string or after a backslash
continues a statement and is aligned freely. Dict braces in the code do
not end the BitBake function.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import PythonFunctionIndentationRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return PythonFunctionIndentationRule().check(context)


def test_aligned_continuations_are_accepted():
    content = (
        "python populate_packages:prepend () {\n"
        "    do_split_packages(d, root, r'^lib(.*)\\.so$',\n"
        "                      output_pattern='lib%s',\n"
        "                      description='%s library')\n"
        "    for name in (\"a\",\n"
        "                 \"b\"):\n"
        "        x = '(' + \\\n"
        "              name\n"
        "    text = '''\n"
        "   free text\n"
        "'''\n"
        "}\n"
    )
    assert _check(content) == []


def test_dict_braces_do_not_end_the_function():
    content = (
        "python __anonymous () {\n"
        "    m = {'a': 1}\n"
        "    if m:\n"
        "      pass\n"
        "}\n"
    )
    results = _check(content)
    assert [r.line for r in results] == [4]


def test_tabs_are_reported():
    content = "python do_foo () {\n\tbb.note('x')\n}\n"
    assert any("Tab" in r.message for r in _check(content))
