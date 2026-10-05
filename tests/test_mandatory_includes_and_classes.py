# -*- coding: utf-8 -*-
"""
MANDATORY001-004 follow includes and inherited classes.

A recipe's SUMMARY, SRC_URI or HOMEPAGE often lives in a required .inc, and
classes such as pypi set SRC_URI and HOMEPAGE themselves. When an include
cannot be found, what it sets is unknown and nothing is reported missing.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, Severity
from bake_linter.rules.mandatory import (
    HomepageRule, InheritCheck, SrcUriRule, SummaryDescriptionRule,
)


def _context(content, path=Path("foo_1.0.bb")):
    return FileContext(
        path=path,
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )


def _layer(tmp_path, recipe, content, inc=None):
    """A layer with recipes-foo/foo/<recipe> and optionally foo.inc."""
    (tmp_path / "conf").mkdir()
    (tmp_path / "conf" / "layer.conf").write_text("")
    recipe_dir = tmp_path / "recipes-foo" / "foo"
    recipe_dir.mkdir(parents=True)
    if inc is not None:
        (recipe_dir / "foo.inc").write_text(inc)
    path = recipe_dir / recipe
    path.write_text(content)
    return _context(content, path)


# MANDATORY001

def test_summary_in_include(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb", 'require foo.inc\n',
                     inc='SUMMARY = "Foo"\n')
    assert SummaryDescriptionRule().check(context) == []


def test_description_here_summary_in_include(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb",
                     'require foo.inc\nDESCRIPTION = "Foo does things"\n',
                     inc='SUMMARY = "Foo"\n')
    assert SummaryDescriptionRule().check(context) == []


def test_unresolved_include_reports_nothing_missing():
    context = _context('require recipes-bar/bar/bar.inc\n')
    assert SummaryDescriptionRule().check(context) == []


def test_prefer_summary_still_reported():
    results = SummaryDescriptionRule().check(_context('DESCRIPTION = "Foo"\n'))
    assert len(results) == 1
    assert results[0].severity == Severity.INFO


def test_missing_both_still_reported(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb", 'require foo.inc\n',
                     inc='LICENSE = "MIT"\n')
    results = SummaryDescriptionRule().check(context)
    assert len(results) == 1
    assert results[0].severity == Severity.WARNING


# MANDATORY002

@pytest.mark.parametrize("cls", [
    "pypi", "gnomebase", "xfce", "nopackages", "packagegroup", "image",
    "core-image", "kernelsrc", "populate_sdk",
])
def test_class_sets_or_needs_no_src_uri(cls):
    assert SrcUriRule().check(_context(f'inherit {cls}\n')) == []


@pytest.mark.parametrize("line", [
    'SRC_URI:append = " file://a.patch"',
    'SRC_URI[sha256sum] = "0123"',
    'SRC_URI += "file://a.patch"',
])
def test_any_src_uri_assignment_counts(line):
    assert SrcUriRule().check(_context(line + "\n")) == []


def test_src_uri_in_include(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb", 'require foo.inc\n',
                     inc='SRC_URI = "https://example.com/foo.tar.gz"\n')
    assert SrcUriRule().check(context) == []


def test_unresolved_include_src_uri_unknown():
    assert SrcUriRule().check(_context('require ${BPN}.inc\n')) == []


def test_class_named_like_image_is_not_an_image():
    """inherit image-buildinfo is not inherit image."""
    results = SrcUriRule().check(_context('inherit image-buildinfo\n'))
    assert len(results) == 1


def test_missing_src_uri_reported():
    results = SrcUriRule().check(_context('inherit autotools\nLICENSE = "MIT"\n'))
    assert len(results) == 1
    assert results[0].rule_id == "MANDATORY002"


# MANDATORY003

@pytest.mark.parametrize("cls", [
    "pypi", "xfce", "xfce-panel-plugin", "packagegroup", "image", "core-image",
])
def test_homepage_from_class_or_not_applicable(cls):
    assert HomepageRule().check(_context(f'inherit {cls}\nLICENSE = "MIT"\n')) == []


def test_homepage_in_include(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb", 'require foo.inc\nLICENSE = "MIT"\n',
                     inc='HOMEPAGE = "https://example.com"\n')
    assert HomepageRule().check(context) == []


def test_closed_license_in_include(tmp_path):
    context = _layer(tmp_path, "foo_1.0.bb", 'require foo.inc\n',
                     inc='LICENSE = "CLOSED"\n')
    assert HomepageRule().check(context) == []


def test_missing_homepage_reported():
    results = HomepageRule().check(_context('LICENSE = "MIT"\ninherit autotools\n'))
    assert len(results) == 1
    assert results[0].rule_id == "MANDATORY003"


# MANDATORY004

def test_image_built_on_another_image():
    context = _context('require recipes-core/images/core-image-minimal.bb\n',
                       Path("foo-image-dev.bb"))
    assert InheritCheck().check(context) == []


def test_image_class_inherited_in_include(tmp_path):
    context = _layer(tmp_path, "foo-image.bb", 'require foo.inc\n',
                     inc='inherit core-image\n')
    assert InheritCheck().check(context) == []


def test_nopackages_recipe_named_image():
    context = _context('inherit nopackages\n', Path("foo-image-tools.bb"))
    assert InheritCheck().check(context) == []


def test_image_without_class_reported():
    context = _context('IMAGE_INSTALL = "foo"\n', Path("foo-image.bb"))
    results = InheritCheck().check(context)
    assert len(results) == 1
    assert results[0].rule_id == "MANDATORY004"
