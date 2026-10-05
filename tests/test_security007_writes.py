# -*- coding: utf-8 -*-
"""
SECURITY007 reports a build path written into a file in ${D}, not a build
path that is merely mentioned.

The most common sed in do_install removes a build path from an installed
file (sed -i -e 's|${B}/||g' ${D}...): the path is in the pattern, which is
the fix for a leak. Only a build path in the replacement, or one echoed
into a file in ${D}, ends up in the installed file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.security import BuildPathLeakageRule


def _check(body, task="do_install"):
    content = f"{task}() {{\n{body}\n}}\n"
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return BuildPathLeakageRule().check(context)


@pytest.mark.parametrize("body", [
    "    sed -i -e 's|${B}/||g' ${D}${libdir}/cmake/foo/fooTargets.cmake",
    "    sed -i -e 's#${RECIPE_SYSROOT}##g' ${D}${libdir}/pkgconfig/foo.pc",
    "    sed -i 's:${S}:${PTEST_PATH}:g' ${D}${PTEST_PATH}/CTestTestfile.cmake",
    "    sed -i s#${WORKDIR}#/usr/src/debug#g ${D}${bindir}/foo-config",
    # Build path as input file, not in the replacement
    "    sed 's/@VERSION@/${PV}/' ${WORKDIR}/foo.pc.in > ${D}${libdir}/pkgconfig/foo.pc",
    # Writes into the build tree, not ${D}
    "    sed -i 's:@SRC@:${S}:' ${B}/foo.sh",
    "    install -m 0644 ${WORKDIR}/foo.conf ${D}${sysconfdir}/foo.conf",
    "    install -m 0644 ${S}/concat.h ${D}${includedir}",
    "    for f in $(find ${B}/tests -name '*.sh' -printf '%P '); do :; done",
    "    echo ${S} > ${B}/where",
])
def test_not_a_leak(body):
    assert _check(body) == []


@pytest.mark.parametrize("body", [
    "    sed -i -e 's:@BUILDDIR@:${B}:g' ${D}${bindir}/foo-config",
    "    sed -i 's|@SYSROOT@|${STAGING_DIR_HOST}|' ${D}${libdir}/foo.la",
    "    echo \"DATA_DIR=${S}/data\" > ${D}${sysconfdir}/foo.conf",
    "    printf '%s\\n' ${WORKDIR}/data >> ${D}${sysconfdir}/foo.conf",
])
def test_leak(body):
    results = _check(body)
    assert len(results) == 1
    assert results[0].rule_id == "SECURITY007"


def test_continued_sed_target_on_next_line():
    body = (
        "    sed -i -e 's:@TOP@:${S}:g' \\\n"
        "        ${D}${bindir}/foo-config"
    )
    results = _check(body)
    assert len(results) == 1
    assert results[0].line == 2


def test_install_variant_is_checked():
    body = "    sed -i -e 's:@TOP@:${B}:g' ${D}${PTEST_PATH}/run-ptest"
    assert len(_check(body, task="do_install_ptest")) == 1


def test_other_task_is_not_checked():
    body = "    echo ${S} > ${D}/foo"
    assert _check(body, task="do_compile") == []
