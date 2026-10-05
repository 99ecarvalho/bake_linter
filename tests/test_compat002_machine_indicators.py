# -*- coding: utf-8 -*-
"""
COMPAT002 recognises recipes whose content depends on the machine.

A recipe that uses ${MACHINE}, the machine's serial consoles, its kernel,
its tune or its U-Boot configuration, or that inherits a class tied to the
machine's kernel or deploy output, has a reason for MACHINE_ARCH. The
indicator may also be in an included file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.compatibility import UnjustifiedMachineArchRule

ARCH = 'PACKAGE_ARCH = "${MACHINE_ARCH}"\n'


def _context(content, path=Path("foo_1.0.bb")):
    return FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )


@pytest.mark.parametrize("line", [
    'SRC_URI = "file://${MACHINE}/foo.conf"',
    'do_install() {\n    echo "${SERIAL_CONSOLES}" > ${D}/x\n}',
    'do_compile[depends] += "virtual/kernel:do_shared_workdir"',
    'EXTRA_OEMAKE = "KERNEL_SRC=${STAGING_KERNEL_DIR}"',
    'echo ${KERNEL_IMAGETYPE}',
    'ARCHS = "${PACKAGE_ARCHS}"',
    'RDEPENDS:${PN} = "${@bb.utils.contains("COMBINED_FEATURES", "alsa", "a", "", d)}"',
    'X = "${@bb.utils.contains("TUNE_FEATURES", "neon", "1", "0", d)}"',
    'B = "${WORKDIR}/${UBOOT_MACHINE}"',
    'MACHINEOVERRIDES:prepend = "foo:"',
    'inherit kernelsrc',
    'inherit nopackages',
    'inherit deploy',
    'inherit toolchain-scripts',
])
def test_machine_specific(line):
    assert UnjustifiedMachineArchRule().check(_context(ARCH + line + "\n")) == []


def test_indicator_in_include(tmp_path):
    (tmp_path / "conf").mkdir()
    (tmp_path / "conf" / "layer.conf").write_text("")
    recipes = tmp_path / "recipes-foo" / "foo"
    recipes.mkdir(parents=True)
    (recipes / "foo.inc").write_text('SRC_URI = "file://${MACHINE}.conf"\n')
    content = "require foo.inc\n" + ARCH
    path = recipes / "foo_1.0.bb"
    path.write_text(content)
    assert UnjustifiedMachineArchRule().check(_context(content, path)) == []


def test_unresolved_include_may_justify():
    content = "require recipes-other/bar/bar.inc\n" + ARCH
    assert UnjustifiedMachineArchRule().check(_context(content)) == []


@pytest.mark.parametrize("line", [
    'inherit autotools',
    'X = "${@bb.utils.contains("DISTRO_FEATURES", "x11", "1", "0", d)}"',
    'FILESEXTRAPATHS:prepend := "${THISDIR}/files:"',
])
def test_no_indicator_still_warns(line):
    results = UnjustifiedMachineArchRule().check(_context(ARCH + line + "\n"))
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING
