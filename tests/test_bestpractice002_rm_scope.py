# -*- coding: utf-8 -*-
"""
BESTPRACTICE002 only reports rm in do_configure outside the recipe's own
work directory.

Clearing stale generated files from ${S}, ${B} or ${WORKDIR} before
configuring is routine; sysroots, deploy directories and host paths belong
to other tasks and recipes.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.best_practices import CleanupInConfigureRule


def _check(body, function="do_configure:prepend"):
    content = f'{function}() {{\n{body}\n}}\n'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return CleanupInConfigureRule().check(context)


@pytest.mark.parametrize("body", [
    "    rm -rf ${S}/m4/*",
    "    rm -f ${B}/config.h",
    "    rm -rf ${WORKDIR}/build-extra",
    "    rm -rf aclocal-copy/",
    "    rm -rf ${S}/a \\\n        ${S}/b",
    # Shell variables: where they point is unknown
    "    rm -rf $d",
    "    rm -f ${dir}/aclocal.m4",
])
def test_work_tree_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body", [
    "    rm -rf ${STAGING_INCDIR}/foo",
    "    rm -f ${DEPLOY_DIR_IMAGE}/foo.bin",
    "    rm -rf /tmp/foo",
    "    rm -rf ${S}/a \\\n        ${TMPDIR}/b",
])
def test_outside_work_tree_reported(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].rule_id == "BESTPRACTICE002"
    assert results[0].line == 2


def test_other_tasks_ignored():
    assert _check("    rm -rf ${STAGING_INCDIR}/foo", "do_install") == []
