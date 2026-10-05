# -*- coding: utf-8 -*-
"""
INSTALL005 judges literal destinations under ${D} against the FHS roots.

A destination under a variable (${D}${bindir}, ${D}/${PTEST_PATH}) cannot
be judged from the text. Initramfs and image recipes lay out a root
filesystem of their own.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.install import NonFHSPathRule


def _check(body, path=Path("foo_1.0.bb"), extra=""):
    content = f'{extra}do_install() {{\n{body}\n}}\n'
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return NonFHSPathRule().check(context)


@pytest.mark.parametrize("body", [
    "    install -d ${D}/${PTEST_PATH}/tests",
    '    install -d "${D}/${SDKPATH}"',
    "    install -m 0755 foo ${D}${bindir}",
    "    install -d ${D}/dev ${D}/proc ${D}/sys ${D}/mnt ${D}/tmp",
    "    install -d ${D}/sbin ${D}/bin ${D}/media ${D}/root ${D}/srv ${D}/boot",
    '    install -m 0644 foo "${D}/etc/foo.conf"',
])
def test_not_reported(body):
    assert _check(body) == []


@pytest.mark.parametrize("body,dest", [
    ("    install -d ${D}/www/pages", "/www/pages"),
    ('    install -m 0644 index.html "${D}/www/pages/index.html"', "/www/pages/index.html"),
    ("    install -m 0755 foo \\\n        ${D}/foo/bin", "/foo/bin"),
    ("    install -m 0755 foo $D/init", "/init"),
])
def test_reported(body, dest):
    results = _check(body)
    assert len(results) == 1
    assert results[0].message.endswith(dest)


def test_initramfs_recipe_not_judged():
    assert _check("    install -m 0755 init ${D}/init",
                  path=Path("initramfs-foo_1.0.bb")) == []


@pytest.mark.parametrize("cls", ["image", "nopackages"])
def test_image_and_nopackages_not_judged(cls):
    assert _check("    install -m 0755 init ${D}/init", extra=f"inherit {cls}\n") == []
