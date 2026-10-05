# -*- coding: utf-8 -*-
"""
DEPENDENCY003 reads the packages in an RRECOMMENDS value, as whole names.

An override in the variable name (RRECOMMENDS:${PN}:libc-glibc) is not a
package, and a package whose name starts with a library name
(glibc-thread-db) is not that library.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext
from bake_linter.rules.dependency import RrecommendsEssentialRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return RrecommendsEssentialRule().check(context)


@pytest.mark.parametrize("line", [
    'RRECOMMENDS:${PN}:append:libc-glibc = " glibc-gconv-utf-16"',
    'RRECOMMENDS:${PN} = "glibc-thread-db"',
    'RRECOMMENDS:${PN}-dev = "zlib-dev libssl-staticdev"',
    'RRECOMMENDS:${PN}:remove = "zlib"',
])
def test_not_reported(line):
    assert _check(line + "\n") == []


def test_essential_package_is_reported_on_its_line():
    content = 'RRECOMMENDS:${PN} = "foo-extra \\\n    zlib \\\n"\n'
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 2
    assert "'zlib'" in results[0].message
