# -*- coding: utf-8 -*-
"""
PKG002 reads FILES and the default packaging the way BitBake does.

FILES of any package counts, literal package names included, and so does
FILES set in a required file. The base_* and nonarch_* directories are
packaged by the default FILES, ${systemd_unitdir}/system by systemd.bbclass
and ${PTEST_PATH} by ptest.bbclass.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.package import FilesNotMatchingInstallRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return FilesNotMatchingInstallRule().check(context)


def _install(dest, extra=""):
    return (
        extra
        + 'do_install() {\n'
        + f'    install -d {dest}\n'
        + '}\n'
    )


@pytest.mark.parametrize("dest", [
    '${D}/${base_bindir}',
    '${D}/${base_sbindir}/',
    '${D}/${base_libdir}/foo',
    '${D}/${nonarch_base_libdir}/firmware',
    '${D}/${nonarch_libdir}/foo',
    '${D}/sbin',
    '${D}/bin',
])
def test_default_files_paths_not_flagged(dest):
    assert _check(_install(dest)) == []


@pytest.mark.parametrize("dest,inherit", [
    ('${D}/${systemd_unitdir}/system', 'inherit systemd\n'),
    ('${D}/${PTEST_PATH}/tests', 'inherit ptest\n'),
    ('"${D}/${PTEST_PATH}"', 'inherit ptest-perl\n'),
])
def test_class_packaged_paths_not_flagged(dest, inherit):
    assert _check(_install(dest, inherit)) == []


@pytest.mark.parametrize("dest", [
    '${D}/${systemd_unitdir}/system',
    '${D}/${PTEST_PATH}/tests',
])
def test_class_paths_need_the_class(dest):
    assert len(_check(_install(dest))) == 1


def test_quote_not_part_of_path():
    results = _check(_install('"${D}/opt/foo"'))
    assert len(results) == 1
    assert "'/opt/foo'" in results[0].message


def test_literal_package_name_covers():
    content = _install('${D}/init.d', 'FILES:initramfs-module-foo = "/init.d/01-foo"\n')
    assert _check(content) == []


def test_multiline_files_of_other_package_covers():
    content = _install(
        '${D}/efi/boot',
        'PACKAGES =+ "foo-efi"\nFILES:foo-efi = " \\\n    /efi/boot/* \\\n"\n',
    )
    assert _check(content) == []


def test_continuation_marker_does_not_cover_everything():
    content = _install('${D}/opt/foo', 'FILES:${PN} += "\\\n    ${libdir}/foo \\\n"\n')
    assert len(_check(content)) == 1


def test_files_variable_is_not_files():
    content = _install('${D}/opt/foo', 'FILES_SOLIBSDEV = "/opt/foo"\n')
    assert len(_check(content)) == 1


def test_files_from_include_cover(tmp_path):
    (tmp_path / "foo.inc").write_text('FOODIR = "/opt/foo"\nFILES:${PN} += "${FOODIR}"\n')
    recipe = tmp_path / "foo_1.0.bb"
    content = _install('${D}/${FOODIR}', 'require foo.inc\n')
    recipe.write_text(content)
    assert _check(content, recipe) == []


def test_unresolved_include_not_judged(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    content = _install('${D}/opt/foo', 'require missing.inc\n')
    recipe.write_text(content)
    assert _check(content, recipe) == []
