# -*- coding: utf-8 -*-
"""
LICENSE001 follows required files and the classes that default LICENSE.

image, core-image and packagegroup set LICENSE ?= "MIT", devicetree sets
LICENSE ?= "GPL-2.0-only", and a recipe often takes LICENSE from the .inc
it requires.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.license import LicenseRequiredRule


def _check(content, path=Path("foo_1.0.bb")):
    context = FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return LicenseRequiredRule().check(context)


@pytest.mark.parametrize("cls", ["packagegroup", "image", "core-image", "devicetree"])
def test_class_default_not_flagged(cls):
    assert _check(f'SUMMARY = "x"\ninherit {cls}\n') == []


def test_other_class_still_flagged():
    assert len(_check('SUMMARY = "x"\ninherit autotools\n')) == 1


def test_license_from_include(tmp_path):
    (tmp_path / "foo.inc").write_text('LICENSE = "MIT"\n')
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\n')
    assert _check(recipe.read_text(), recipe) == []


def test_include_without_license_flagged(tmp_path):
    (tmp_path / "foo.inc").write_text('SUMMARY = "x"\n')
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require foo.inc\n')
    assert len(_check(recipe.read_text(), recipe)) == 1


def test_unresolved_include_not_flagged(tmp_path):
    recipe = tmp_path / "foo_1.0.bb"
    recipe.write_text('require missing.inc\n')
    assert _check(recipe.read_text(), recipe) == []
