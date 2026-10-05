# -*- coding: utf-8 -*-
"""
SUPPLY002 checks the sources a recipe fetches, and knows that a file on
raw.githubusercontent.com at a fixed ref does not change.

Only SRC_URI is fetched as source; a HOMEPAGE or a comment on such a host
is not a download. A raw file at a commit id, or at the release tag of the
version being built, is fixed content; one at a branch is not.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.supply_chain import UnreliableHostingRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return UnreliableHostingRule().check(context)


@pytest.mark.parametrize("content", [
    'HOMEPAGE = "https://gist.github.com/someone/0123"\n',
    'SRC_URI += "https://raw.githubusercontent.com/org/foo/v${PV}/LICENSE;name=lic"\n',
    'SRC_URI = "https://example.org/foo.tar.gz \\\n'
    '    https://raw.githubusercontent.com/org/foo/0123456789abcdef0123456789abcdef01234567/test.py \\\n'
    '"\n',
])
def test_not_reported(content):
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    'SRC_URI += "https://raw.githubusercontent.com/org/foo/master/foo.h"\n',
    'SRC_URI = "https://example.org/foo.tar.gz \\\n'
    '    https://raw.githubusercontent.com/org/foo/release-4.9/foo.h \\\n"\n',
    'SRC_URI = "https://www.dropbox.com/s/abc/foo.tar.gz"\n',
])
def test_reported(content):
    assert len(_check(content)) == 1
