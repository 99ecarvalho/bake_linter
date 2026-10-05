# -*- coding: utf-8 -*-
"""
DEPENDENCY002 reports a run of pkg-config, not a mention of "pkgconfig".

${libdir}/pkgconfig is where every library installs its .pc files, patch
and crate URLs may contain "pkg-config", and documentation or package
lists name the pkgconfig recipe. None of these run the tool. The inherit
may also come from a required .inc file.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.dependency import MissingPkgconfigInheritRule


def _context(content, path=Path("foo_1.0.bb")):
    return FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )


def _check(content):
    return MissingPkgconfigInheritRule().check(_context(content))


@pytest.mark.parametrize("content", [
    'do_install() {\n    install -d ${D}${libdir}/pkgconfig\n}\n',
    'do_install() {\n    rm -f ${D}${libdir}/pkgconfig/foo.pc\n}\n',
    'FILES:${PN}-dev += "${libdir}/foo/pkgconfig"\n',
    'SRC_URI = "file://0001-use-pkg-config-for-detection.patch"\n',
    'SRC_URI += "crate://crates.io/pkg-config/0.3.29"\n',
    'SUMMARY = "Python interface to the pkg-config command line tool"\n',
    'DESCRIPTION = "pkg-config is a helper tool \\\n    used when compiling."\n',
    'RDEPENDS:${PN} = "bash \\\n    pkgconfig \\\n"\n',
    'PREFERRED_PROVIDER_pkgconfig ?= "pkgconfig"\n',
    'RECIPE_MAINTAINER:pn-pkgconfig = "Jane Doe <jane@example.org>"\n',
    'DISTRO_PN_ALIAS:pn-pkgconfig = "Debian=pkg-config"\n',
    'EXTRA_OECMAKE = "-DPKGCONFIG_INSTALL_DIR=${libdir}/pkgconfig"\n',
    'do_configure:prepend() {\n    # we used to call pkg-config here\n    :\n}\n',
    'do_install() {\n    tar --exclude=./.pc -cf - . | tar -xf - -C ${D}\n}\n',
    'do_install() {\n    install -m 0644 foo-config.h ${D}${includedir}\n}\n',
])
def test_not_a_pkg_config_run(content):
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    'do_configure() {\n    CFLAGS="$(pkg-config --cflags foo)" oe_runconf\n}\n',
    'do_compile() {\n    oe_runmake PKG_CONFIG=${PKG_CONFIG}\n}\n',
    'EXTRA_OEMAKE = "PKG_CONFIG=pkg-config"\n',
    'do_configure() {\n    export PKG_CONFIG_PATH="${STAGING_LIBDIR}/pkgconfig"\n}\n',
])
def test_pkg_config_run_is_reported(content):
    results = _check(content)
    assert len(results) == 1
    assert results[0].rule_id == "DEPENDENCY002"


def test_heredoc_body_is_not_run():
    content = (
        'do_install() {\n'
        '    cat > ${D}${datadir}/foo/native.ini <<EOF\n'
        '[binaries]\n'
        "pkg-config = 'pkg-config-native'\n"
        'EOF\n'
        '}\n'
    )
    assert _check(content) == []


def test_command_after_heredoc_is_checked():
    content = (
        'do_install() {\n'
        "    cat > ${D}/x <<'EOF'\n"
        'text\n'
        'EOF\n'
        '    pkg-config --modversion foo > ${D}/version\n'
        '}\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 5


@pytest.mark.parametrize("name,content", [
    ("pkgconfig_git.bb", 'do_install:append() {\n    sed -i -e "s|^pkg-config|pkg-config.real|" x\n}\n'),
    ("pkgconf_2.1.bb", 'PROVIDES += "pkgconfig"\ndo_install() {\n    pkg-config --version\n}\n'),
])
def test_recipe_providing_pkg_config(name, content):
    rule = MissingPkgconfigInheritRule()
    assert rule.check(_context(content, Path(name))) == []


def test_inherit_from_included_file(tmp_path):
    (tmp_path / "foo.inc").write_text("inherit autotools pkgconfig\n")
    content = 'require foo.inc\ndo_configure() {\n    pkg-config --cflags bar\n}\n'
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(content)
    assert MissingPkgconfigInheritRule().check(_context(content, recipe)) == []


def test_unresolvable_include_is_unknown(tmp_path):
    content = 'require recipes-foo/foo/foo.inc\ndo_configure() {\n    pkg-config --cflags bar\n}\n'
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text(content)
    assert MissingPkgconfigInheritRule().check(_context(content, recipe)) == []


def test_pkgconfig_native_in_continued_depends():
    content = (
        'DEPENDS = "zlib \\\n    pkgconfig-native \\\n"\n'
        'do_configure() {\n    pkg-config --cflags zlib\n}\n'
    )
    assert _check(content) == []
