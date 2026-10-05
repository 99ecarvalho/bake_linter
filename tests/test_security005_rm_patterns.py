# -*- coding: utf-8 -*-
"""
SECURITY005 tells emptying a directory from deleting files by name.

rm -rf ${D}${dir}/* empties the directory and is dangerous when the
variable is empty; rm -rf ${D}${dir}/*.egg removes matching files only.
rm -rf / and rm -rf /* stay errors.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.security import DangerousRmRfRule


def _check(command):
    content = 'do_install:append() {\n    ' + command + '\n}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return DangerousRmRfRule().check(context)


@pytest.mark.parametrize("command", [
    'rm -rf ${D}${PYTHON_SITEPACKAGES_DIR}/*.egg',
    'rm -rf ${D}${datadir}/*-tests',
    'rm -rf ${D}/*.la',
    'rm -rf ${B}/*',
])
def test_by_name_not_flagged(command):
    assert _check(command) == []


@pytest.mark.parametrize("command", [
    'rm -rf ${D}/*',
    'rm -rf ${D}${datadir}/*',
    'rm -rf ${D}${datadir}/* ${D}${bindir}/foo',
])
def test_destdir_contents_warning(command):
    results = _check(command)
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING


@pytest.mark.parametrize("command", ['rm -rf /', 'rm -rf /*', 'rm -rf / ${D}'])
def test_root_error(command):
    results = _check(command)
    assert len(results) == 1
    assert results[0].severity == Severity.ERROR
