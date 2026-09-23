"""STYLE008 only reports SYSTEMD_AUTO_ENABLE when it is genuinely ambiguous.

An unsuffixed SYSTEMD_AUTO_ENABLE works: systemd.bbclass reads it through
get_package_var, which falls back to the unsuffixed variable. It is also the
dominant idiom, used in seven poky recipes against one that suffixes it. The
rule used to flag every bare assignment as a WARNING, which gates commits on a
non-issue and contradicts upstream.

It is ambiguous only when a recipe ships services in more than one package,
where one bare value silently covers all of them.
"""

from pathlib import Path

from bake_linter.core.models import FileContext
from bake_linter.rules.style import SystemdAutoEnableRule


def _check(content, path="recipe_1.0.bb"):
    context = FileContext(
        path=Path(path),
        content=content,
        lines=content.splitlines(),
        variables={},
    )
    return SystemdAutoEnableRule().check(context)


def test_single_package_bare_form_is_not_reported():
    content = (
        'inherit systemd\n'
        'SYSTEMD_SERVICE:${PN} = "thing.service"\n'
        'SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    assert _check(content) == []


def test_no_service_declared_is_not_reported():
    # A bbappend that only flips the value has nothing to disambiguate here.
    content = 'SYSTEMD_AUTO_ENABLE = "disable"\n'
    assert _check(content, "recipe_%.bbappend") == []


def test_overrides_on_one_package_still_count_as_one():
    # SYSTEMD_SERVICE:${PN}:append:qemuarm targets the same package as
    # SYSTEMD_SERVICE:${PN}, so the bare form remains unambiguous.
    content = (
        'SYSTEMD_SERVICE:${PN} = "a.service"\n'
        'SYSTEMD_SERVICE:${PN}:append:qemuarm = " b.service"\n'
        'SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    assert _check(content) == []


def test_two_packages_with_bare_form_is_reported():
    content = (
        'SYSTEMD_SERVICE:${PN} = "a.service"\n'
        'SYSTEMD_SERVICE:${PN}-extra = "b.service"\n'
        'SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    results = _check(content)
    assert len(results) == 1
    assert results[0].line == 3
    assert "every systemd package" in results[0].message


def test_two_packages_each_qualified_is_not_reported():
    content = (
        'SYSTEMD_SERVICE:${PN} = "a.service"\n'
        'SYSTEMD_SERVICE:${PN}-extra = "b.service"\n'
        'SYSTEMD_AUTO_ENABLE:${PN} = "enable"\n'
        'SYSTEMD_AUTO_ENABLE:${PN}-extra = "disable"\n'
    )
    assert _check(content) == []


def test_two_packages_bare_form_in_a_comment_is_ignored():
    content = (
        'SYSTEMD_SERVICE:${PN} = "a.service"\n'
        'SYSTEMD_SERVICE:${PN}-extra = "b.service"\n'
        '# SYSTEMD_AUTO_ENABLE = "enable"\n'
    )
    assert _check(content) == []
