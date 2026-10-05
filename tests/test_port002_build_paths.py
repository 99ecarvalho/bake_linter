# -*- coding: utf-8 -*-
"""
PORT002 looks for host paths only where they affect the build.

Compiler and linker search paths, configure/CMake/Meson directory options
and do_install writes outside ${D} are reported; absolute paths that name
a location on the target (scripts, ALTERNATIVE_*, documentation, sed
expressions) are not.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.portability import AbsoluteHostPathRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return AbsoluteHostPathRule().check(context)


@pytest.mark.parametrize("content", [
    'CFLAGS += "-I/usr/include/foo"\n',
    'LDFLAGS:append = " -L/usr/lib"\n',
    'TARGET_LDFLAGS += "-Wl,-rpath-link=/opt/foo/lib"\n',
    'EXTRA_OECONF = "--disable-x \\\n    --with-foo-include=/usr/include/foo \\\n"\n',
    'EXTRA_OECONF += "--prefix=/usr/local"\n',
    'EXTRA_OECMAKE += "-DFOO_INCLUDE_DIR=/usr/include"\n',
    'PACKAGECONFIG[foo] = "--with-foo-prefix=/opt/foo,--without-foo,foo"\n',
    'do_configure:prepend() {\n    export PKG_CONFIG_PATH=/usr/lib/pkgconfig\n}\n',
    'do_compile() {\n    oe_runmake CFLAGS="-isystem /usr/include"\n}\n',
    'do_install() {\n    install -m 0644 foo.conf /etc/foo.conf\n}\n',
])
def test_build_host_path_flagged(content):
    results = _check(content)
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING


@pytest.mark.parametrize("content", [
    # Sysroot relative
    'CFLAGS += "-I=/usr/include/foo"\n',
    'EXTRA_OECONF += "--with-foo-include=${STAGING_INCDIR}/foo"\n',
    # Target locations outside build-affecting places
    'ALTERNATIVE_LINK_NAME[sendmail] = "/usr/lib/sendmail"\n',
    'SUMMARY:${PN}-foo = "Saves the state in /etc/foo.state"\n',
    'DESCRIPTION = "Reads /etc/foo \\\n    and /etc/bar"\n',
    'FOO_HOME = "/home/foo"\n',
    'pkg_postinst:${PN}() {\n    touch /etc/aliases\n}\n',
    'python do_foo() {\n    libpaths = [sysroot + "/usr/lib"]\n}\n',
    # sed rewriting host paths out of generated files
    'do_configure:append() {\n'
    '    sed -i -e "s:-I/usr/include:-I${STAGING_INCDIR}:" Makefile\n}\n',
    'do_compile:prepend() {\n    sed -i \\\n        -e "s:-L/usr/lib:-L=/usr/lib:" Makefile\n}\n',
    # Writes into ${D}
    'do_install() {\n    install -m 0644 foo.conf ${D}/etc/foo.conf\n}\n',
])
def test_not_flagged(content):
    assert _check(content) == []


def test_native_recipe_skipped():
    assert _check('CFLAGS += "-I/usr/include"\n', Path("foo-native_1.0.bb")) == []
