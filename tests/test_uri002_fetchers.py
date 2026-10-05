# -*- coding: utf-8 -*-
"""
URI002 knows that SRCREV is not only for git.

The svn, hg, bzr and repo fetchers use SRCREV with revisions of their own
format, the git URI may be in a required file, and a git repository in the
sha256 object format has 64-hex commit ids.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.uri import GitSrcrevValidityRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return GitSrcrevValidityRule().check(context)


@pytest.mark.parametrize("content", [
    'SRC_URI = "svn://svn.example.org/foo;module=trunk;protocol=https"\nSRCREV = "11718"\n',
    'SRC_URI = "hg://hg.example.org/foo;module=foo;protocol=https"\nSRCREV = "a1b2c3d4e5f6"\n',
    'SRC_URI = "bzr://bzr.example.org/foo"\nSRCREV = "42"\n',
    'require foo.inc\nSRCREV = "0123456789abcdef0123456789abcdef01234567"\n',
    'SRC_URI = "git://example.org/foo.git;protocol=https;branch=main"\n'
    'SRCREV = "' + "ab" * 32 + '"\n',
])
def test_not_reported(content):
    assert _check(content) == []


def test_srcrev_without_any_scm_uri_is_reported():
    content = 'SRC_URI = "https://example.org/foo.tar.gz"\nSRCREV = "0123456789abcdef0123456789abcdef01234567"\n'
    results = _check(content)
    assert len(results) == 1
    assert "no git" in results[0].message


def test_short_git_srcrev_is_reported():
    content = 'SRC_URI = "gitsm://example.org/foo.git;protocol=https;branch=main"\nSRCREV = "abc123"\n'
    results = _check(content)
    assert len(results) == 1
    assert "Invalid SRCREV" in results[0].message
