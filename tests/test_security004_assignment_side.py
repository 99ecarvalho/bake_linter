# -*- coding: utf-8 -*-
"""
SECURITY004 looks for credentials in the name being assigned.

A credential keyword inside another word (pn-libsecret) or inside the
value of a BitBake assignment is not a hardcoded secret; DB_PASSWORD = "x"
and a shell line password="x" are.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.security import HardcodedCredentialsRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return HardcodedCredentialsRule().check(context)


@pytest.mark.parametrize("content", [
    'RECIPE_MAINTAINER:pn-libsecret = "Jane Doe <jane@example.org>"\n',
    'FOO:pn-libsecret = "bar"\n',
    'RDEPENDS:${PN}-mytoken = "abcdefghijklmnopqrstuvwxyz"\n',
    'FOO = "a \\\n    password = \'x\' \\\n"\n',
    'EXTRA_OECONF = "--with-default-secret=\'abc\'"\n',
])
def test_not_flagged(content):
    assert _check(content) == []


@pytest.mark.parametrize("content", [
    'DB_PASSWORD = "hunter2"\n',
    'export API_KEY = "abc"\n',
    'secret = "abc"\n',
    'do_install() {\n    password="hunter2"\n}\n',
])
def test_flagged(content):
    assert len(_check(content)) == 1
