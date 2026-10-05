# -*- coding: utf-8 -*-
"""
URI001 looks at the URIs in SRC_URI only, one URI at a time.

URLs in HOMEPAGE, BUGTRACKER or MIRRORS are not fetched as sources, so they
cannot make the protocols in SRC_URI inconsistent.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.uri import SrcUriProtocolConsistencyRule


def _check(content):
    context = FileContext(
        path=Path("foo_1.0.bb"),
        content=content,
        lines=content.splitlines(keepends=True),
        variables={},
    )
    return SrcUriProtocolConsistencyRule().check(context)


def test_homepage_does_not_count():
    content = (
        'HOMEPAGE = "http://www.example.org/"\n'
        'SRC_URI = "https://example.org/foo-${PV}.tar.gz"\n'
    )
    assert _check(content) == []


def test_git_protocol_https_is_not_http():
    content = (
        'SRC_URI = "git://example.org/foo.git;protocol=https;branch=main \\\n'
        '           https://example.org/data.tar.gz"\n'
    )
    assert _check(content) == []


def test_mixed_http_and_https_across_appends():
    content = (
        'SRC_URI = "https://example.org/foo-${PV}.tar.gz \\\n'
        '           file://fix.patch"\n'
        'SRC_URI:append:class-target = " http://example.org/extra.tar.gz"\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 3
    assert "HTTP and HTTPS" in results[0].message


def test_mixed_git_protocols():
    content = (
        'SRC_URI = "git://example.org/a.git;protocol=https;branch=main;name=a \\\n'
        '           git://example.org/b.git;protocol=ssh;branch=main;name=b"\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert "https, ssh" in results[0].message


def test_checksum_flag_is_not_a_uri_list():
    content = (
        'SRC_URI = "https://example.org/foo.tar.gz"\n'
        'SRC_URI[sha256sum] = "0123"\n'
    )
    assert _check(content) == []
