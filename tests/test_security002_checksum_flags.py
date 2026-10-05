# -*- coding: utf-8 -*-
"""
SECURITY002 accepts every checksum flag the fetcher verifies.

fetch2 checks md5sum, sha1sum, sha256sum, sha384sum and sha512sum, with or
without a ;name= prefix (SRC_URI[foo.sha256sum]).

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

import pytest

from bake_linter.core.models import FileContext, VariableAssignment
from bake_linter.rules.security import NoChecksumRule

SRC_URI = "https://example.org/foo-${PV}.tar.gz"


def _check(checksum_line):
    content = f'SRC_URI = "{SRC_URI}"\n{checksum_line}'
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={"SRC_URI": [VariableAssignment("SRC_URI", SRC_URI, 1)]},
    )
    return NoChecksumRule().check(context)


@pytest.mark.parametrize("flag", [
    "md5sum", "sha1sum", "sha256sum", "sha384sum", "sha512sum", "foo.sha512sum",
])
def test_checksum_flag_is_accepted(flag):
    assert _check(f'SRC_URI[{flag}] = "0123"\n') == []


def test_no_checksum_is_reported():
    assert len(_check("")) == 1
