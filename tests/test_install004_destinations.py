# -*- coding: utf-8 -*-
"""
INSTALL004 reports /usr/local only where files are installed there.

That is below ${D}, in a FILES value, or as the install prefix handed to
the build system. A sed expression rewriting /usr/local out of a script
is the fix, not an install.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.install import UsrLocalInstallRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return UsrLocalInstallRule().check(context)


@pytest.mark.parametrize("content", [
    'do_install() {\n    install -d ${D}/usr/local/bin\n}\n',
    'FILES:${PN} += "/usr/local/bin/foo"\n',
    'FILES:${PN} = " \\\n    ${bindir} \\\n    /usr/local/share/foo \\\n"\n',
    'EXTRA_OECONF += "--prefix=/usr/local"\n',
    'EXTRA_OEMAKE = "PREFIX=/usr/local"\n',
    'EXTRA_OECMAKE += "-DCMAKE_INSTALL_PREFIX=/usr/local"\n',
    'prefix = "/usr/local"\n',
])
def test_install_to_usr_local_flagged(content):
    results = _check(content)
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING


@pytest.mark.parametrize("content", [
    'do_install() {\n    sed -i -e "s:/usr/local/bin/perl:/usr/bin/perl:g" ${D}${bindir}/foo\n}\n',
    'do_install() {\n    sed -i \\\n        -e "s:/usr/local/share:/usr/share:g" \\\n'
    '        ${D}${bindir}/foo\n}\n',
    'do_configure:prepend() {\n    sed -i "s# /usr/local/bin##g" ${S}/cmake/FindPerl.cmake\n}\n',
    'DESCRIPTION = "Does not use /usr/local/bin"\n',
])
def test_not_flagged(content):
    assert _check(content) == []
