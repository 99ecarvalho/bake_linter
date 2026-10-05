# -*- coding: utf-8 -*-
"""
STYLE020 looks at the recipe-level SUMMARY/DESCRIPTION/... and LICENSE.

SUMMARY:libfoo and DESCRIPTION:${PN}-vpn describe one package and sit
with its other per-package variables; LICENSE_FLAGS is not LICENSE.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import MetadataBeforeLicenseRule


def _check(content):
    context = FileContext(path=Path("foo_1.0.bb"), content=content,
                          lines=content.splitlines())
    return MetadataBeforeLicenseRule().check(context)


def test_per_package_metadata_is_skipped():
    content = (
        'SUMMARY = "Foo"\n'
        'LICENSE = "MIT"\n'
        'SUMMARY:libfoo = "Foo library"\n'
        'DESCRIPTION:${PN}-tools = "Foo tools \\\n'
        '    and helpers"\n'
    )
    assert _check(content) == []


def test_license_flags_is_not_license():
    content = 'LICENSE_FLAGS = "commercial"\nSUMMARY = "Foo"\nLICENSE = "MIT"\n'
    assert _check(content) == []


def test_recipe_summary_after_license_is_reported():
    assert len(_check('LICENSE = "MIT"\nSUMMARY = "Foo"\n')) == 1
