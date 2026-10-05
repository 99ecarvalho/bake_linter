# -*- coding: utf-8 -*-
"""
SRCREV001 accepts the pinned revisions of every fetcher that uses SRCREV.

An svn revision is a number and an hg changeset id may be abbreviated;
both pin the source as firmly as a git commit id does.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.patch import SrcrevUnpinnedRule

SVN = 'SRC_URI = "svn://svn.example.org/foo;module=trunk;protocol=https"\n'
HG = 'SRC_URI = "hg://hg.example.org/foo;module=foo;protocol=https"\n'
GIT = 'SRC_URI = "git://example.org/foo.git;protocol=https;branch=main"\n'


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return SrcrevUnpinnedRule().check(context)


@pytest.mark.parametrize("content", [
    SVN + 'SRCREV = "11718"\n',
    HG + 'SRCREV = "a1b2c3d4e5f6"\n',
    HG + 'SRCREV = "0123456789abcdef0123456789abcdef01234567"\n',
])
def test_pinned_revision(content):
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    GIT + 'SRCREV = "11718"\n',
    SVN + 'SRCREV = "trunk"\n',
    HG + 'SRCREV = "a1b2c3"\n',
    SVN + 'SRCREV = "${AUTOREV}"\n',
])
def test_unpinned_revision(content):
    assert len(_check(content)) == 1
