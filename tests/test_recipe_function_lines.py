# -*- coding: utf-8 -*-
"""
Tests for the logical lines of function bodies.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext

RECIPE = '''\
SRC_URI = "file://a \\
           file://b"

do_install() {
    install -d ${D}${bindir}
    sed -i -e 's,@BINDIR@,${bindir},' \\
        ${D}${sysconfdir}/foo.conf
}
do_install() {
    true
}

do_install:append() {
    rm -f ${D}${libdir}/*.la
}
'''


def _lines():
    context = FileContext(path=Path("foo_1.0.bb"), content=RECIPE,
                          lines=RECIPE.splitlines(keepends=True))
    return context.function_lines


def test_continuations_joined():
    sed = [f for f in _lines() if f.text.startswith("sed")][0]
    assert sed.function == "do_install"
    assert sed.text == "sed -i -e 's,@BINDIR@,${bindir},' ${D}${sysconfdir}/foo.conf"
    assert (sed.line, sed.end_line) == (6, 7)


def test_headers_left_out_and_functions_named():
    lines = _lines()
    texts = [f.text for f in lines]
    assert not any(t.startswith("do_install") for t in texts)
    assert ("do_install", "true") in [(f.function, f.text) for f in lines]
    assert ("do_install:append", "rm -f ${D}${libdir}/*.la") in [
        (f.function, f.text) for f in lines
    ]


def test_assignments_are_not_function_lines():
    assert not any("file://" in f.text for f in _lines())
