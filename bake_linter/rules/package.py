# -*- coding: utf-8 -*-
"""
Package rules for Yocto recipes.

These rules check for proper package configuration and dependencies.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.rules.base import BaseRule


class RdependsOnDevPackageRule(BaseRule):
    """
    Check for -dev packages in RDEPENDS.
    
    -dev packages contain headers and static libraries for development
    and must never be runtime dependencies.
    """
    
    rule_id = "PKG001"
    name = "RDEPENDS on Development Package"
    description = "Detects -dev packages incorrectly in RDEPENDS"
    default_severity = Severity.ERROR
    groups = ["packaging", "dependency"]
    hint = "Move -dev packages to DEPENDS, use runtime library in RDEPENDS"

    # Version constraints: foo (>= 1.0)
    VERSION_CONSTRAINT_PATTERN = re.compile(r'\([^)]*\)')
    # Recipes insane.bbclass does not check: kernel module packages such as
    # kernel-module-lirc-dev are not development packages. module inherits
    # module-base.
    SKIP_CLASSES = {"kernel", "module-base", "module"}

    @staticmethod
    def _rdepends_package(name: str) -> str:
        """The package an RDEPENDS assignment is for: ${PN}-foo for
        RDEPENDS:${PN}-foo:append, "" for a bare RDEPENDS."""
        if name.startswith("RDEPENDS_"):
            return name[len("RDEPENDS_"):]
        parts = name.split(":")
        return parts[1] if len(parts) > 1 else ""

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # The same check insane.bbclass runs as the dev-deps QA test
        if context.inherits & self.SKIP_CLASSES:
            return results

        def expand(name: str) -> str:
            return name.replace("${PN}", context.pn).replace("${BPN}", context.pn)

        # INSANE_SKIP applies to every package, INSANE_SKIP:pkg to one
        skips: dict = {}
        structures = [context.structure] + [
            i.structure for i in context.included_files or []
        ]
        for structure in structures:
            for a in structure.assignments:
                if a.base != "INSANE_SKIP" or a.flag:
                    continue
                key = expand(a.overrides[0]) if a.overrides else ""
                skips.setdefault(key, set()).update(a.value.split())

        for a in context.structure.assignments:
            if a.flag or not (a.base == "RDEPENDS" or a.base.startswith("RDEPENDS_")):
                continue
            package = self._rdepends_package(a.name)
            expanded = expand(package) or context.pn

            if "-dev" in expanded or "-staticdev" in expanded or "-dbg" in expanded:
                continue
            if "packagegroup-" in expanded or "-image" in expanded:
                continue
            skip = skips.get("", set()) | skips.get(expanded, set())
            if "dev-deps" in skip or "build-deps" in skip:
                continue

            value = self.VERSION_CONSTRAINT_PATTERN.sub(" ", a.value)
            for dev_pkg in value.split():
                if not dev_pkg.endswith("-dev"):
                    continue
                results.append(self.create_result(
                    file=context,
                    line=a.line,
                    message=f"Development package '{dev_pkg}' in RDEPENDS (should be build-time only)",
                    context=context.lines[a.line - 1].strip()[:60],
                    hint=f"Move '{dev_pkg}' to DEPENDS; use runtime library in RDEPENDS",
                ))
        
        return results


class FilesNotMatchingInstallRule(BaseRule):
    """
    Check for files installed to non-standard paths not covered by FILES.
    
    Files installed to custom paths need explicit FILES entries to be packaged.
    """
    
    rule_id = "PKG002"
    name = "FILES Not Matching Installed Paths"
    description = "Detects installed files that may not be covered by FILES"
    default_severity = Severity.WARNING
    groups = ["packaging"]
    hint = "Add matching FILES entry for installed paths"

    # Standard paths that are auto-covered by default FILES
    STANDARD_PATHS = [
        '${bindir}', '${sbindir}', '${libdir}', '${libexecdir}',
        '${datadir}', '${sysconfdir}', '${localstatedir}',
        '${includedir}', '${docdir}', '${mandir}', '${infodir}',
        '${systemd_system_unitdir}', '${systemd_user_unitdir}',
        '/usr/', '/etc/', '/var/', '/lib/', '/run/',
    ]
    
    INSTALL_TASK_PATTERN = re.compile(r'^do_install(?:[_:]|$|\s*\(\))')
    INSTALL_CMD_PATTERN = re.compile(r'install\s+.*\$\{D\}(/\S+)')
    # Any per-package FILES assignment, including FILES:${PN}-dev,
    # FILES:${PN}:append and the ptest variants
    FILES_PATTERN = re.compile(r'^FILES[_:]\$\{PN\}')
    # A hard assignment to FILES:${PN}. In a .bbappend this replaces the base
    # recipe's value, so the complete set is visible in the file being read.
    # ':append', ':prepend', '+=' and the conditional operators only add to a
    # value the base recipe owns, and that half is never in this file.
    FILES_HARD_ASSIGN_PATTERN = re.compile(r'^FILES[_:]\$\{PN\}\s*:?=')

    @staticmethod
    def _normalise_path(token: str) -> str:
        """Normalise a FILES entry or install path to a comparable form.

        An install path captured from ``${D}/foo`` keeps a leading slash, while
        a FILES entry is normally written as ``${dir}/foo`` without one, so
        both sides are anchored the same way before comparing.
        """
        return '/' + token.strip().strip('"\'').strip('\\').lstrip('/')

    GLOB_CHARS = re.compile(r'[*?\[]')

    @staticmethod
    def _glob_regex(pattern: str) -> "re.Pattern":
        """Translate a FILES glob into a regex. As in glob.glob, which
        package.bbclass uses to expand FILES, '*' and '?' do not cross '/'."""
        out, i = [], 0
        while i < len(pattern):
            char = pattern[i]
            if char == '*':
                out.append('[^/]*')
            elif char == '?':
                out.append('[^/]')
            elif char == '[' and ']' in pattern[i + 1:]:
                end = pattern.index(']', i + 1)
                out.append('[' + pattern[i + 1:end].replace('\\', '\\\\') + ']')
                i = end
            else:
                out.append(re.escape(char))
            i += 1
        return re.compile(''.join(out) + r'\Z')

    @classmethod
    def _covers(cls, entry: str, installed: str) -> bool:
        """Whether the FILES *entry* packages the *installed* path."""
        installed = installed.rstrip('/') or '/'
        if not cls.GLOB_CHARS.search(entry):
            entry = entry.rstrip('/') or '/'
            # The entry names the path, or a directory above it (a packaged
            # directory brings its contents)
            if installed == entry or installed.startswith(entry.rstrip('/') + '/'):
                return True
            # The entry names something INSIDE the installed directory.
            # Listing a directory's contents rather than the bare directory
            # is the correct packaging pattern (packaging the directory
            # itself would swallow the -dbg/-dev split), so an `install -d`
            # whose contents are packaged is covered.
            return entry.startswith(installed + '/')

        # A glob covers the path when it matches the path or a directory
        # above it.
        regex = cls._glob_regex(entry.rstrip('/'))
        parts = installed.split('/')
        for depth in range(2, len(parts) + 1):
            if regex.match('/'.join(parts[:depth])):
                return True
        # Or when it selects contents of the installed directory: its literal
        # directory prefix lies inside the path (/opt/foo/*.so for an
        # `install -d ${D}/opt/foo`).
        literal = entry[:cls.GLOB_CHARS.search(entry).start()]
        literal_dir = literal.rsplit('/', 1)[0]
        return literal_dir == installed or literal_dir.startswith(installed + '/')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # A .bbappend holds a fragment of a recipe. The FILES that covers its
        # installs lives in the base recipe, which is not in this file and is
        # not resolved here, so coverage cannot be judged from an append that
        # only adds to FILES. Judging anyway reports every install to a
        # non-standard path in every such bbappend, and the hint it prints
        # ("add FILES:${PN} += ...") is actively wrong advice when the base
        # recipe already covers the path - base-files, for one, sets
        # FILES:${PN} = "/".
        #
        # A hard assignment is different: it replaces the base value, so the
        # whole set is here and an uncovered install is a real finding.
        if context.file_type == "bbappend" and not any(
            self.FILES_HARD_ASSIGN_PATTERN.match(line.strip())
            for line in context.lines
        ):
            return results

        in_do_install = False
        brace_depth = 0

        # Collect non-standard install paths
        custom_installs = []
        files_entries = []
        in_files = False

        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            # Collect FILES entries. A FILES assignment is usually written
            # across several continuation lines, so the value has to be
            # accumulated - reading only the first line saw an empty list and
            # flagged every installed path in the recipe.
            if self.FILES_PATTERN.match(stripped):
                in_files = True
            if in_files:
                files_entries.extend(
                    self._normalise_path(tok)
                    for tok in stripped.split('=', 1)[-1].split()
                    if tok not in ('\\', '"', '')
                )
                if not stripped.endswith('\\'):
                    in_files = False

            # Track do_install
            if self.INSTALL_TASK_PATTERN.match(stripped):
                in_do_install = True
                if '{' in stripped:
                    brace_depth = 1
                continue
            
            if in_do_install:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0:
                    in_do_install = False
                    brace_depth = 0
                    continue
                
                # Find install commands
                match = self.INSTALL_CMD_PATTERN.search(line)
                if match:
                    install_path = match.group(1)

                    # `find ... -exec install -d ${D}/dir/{} \;` expands {} per
                    # match at build time, so the captured "path" is a shell
                    # placeholder, not something FILES can name.
                    if '{}' in install_path:
                        continue


                    # Standard locations are packaged by the default FILES.
                    # Compare the path's prefix: a standard directory name
                    # deeper in the path (/opt/foo/lib/x) does not count.
                    location = install_path.strip('"\'').strip('/') + '/'
                    is_standard = any(
                        location.startswith(std_path.strip('/') + '/')
                        for std_path in self.STANDARD_PATHS
                    )

                    if not is_standard:
                        custom_installs.append((line_num, install_path))
        
        # Check custom installs against FILES
        for line_num, install_path in custom_installs:
            installed = self._normalise_path(install_path)
            path_covered = any(self._covers(entry, installed) for entry in files_entries)

            if not path_covered:
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message=f"Installed path '{install_path}' may not be covered by FILES",
                    hint=f'Add: FILES:${{PN}} += "{install_path}"',
                ))
        
        return results


class WildcardBbappendOverreachRule(BaseRule):
    """
    Check for version-wildcard bbappend files with version-specific modifications.
    
    Using recipe_%.bbappend with version-specific patches may cause issues
    when applied to incompatible recipe versions.
    """
    
    rule_id = "PKG003"
    name = "Wildcard bbappend Overreach"
    description = "Detects wildcard .bbappend with version-specific changes"
    default_severity = Severity.WARNING
    groups = ["packaging", "bbappend"]
    hint = "Use more specific version pattern or conditional logic"
    
    applicable_file_types = {"bbappend"}

    # Version-specific indicators
    VERSION_SPECIFIC_PATTERNS = [
        re.compile(r'fix.*v?\d+\.\d+', re.IGNORECASE),  # Patches mentioning versions
        re.compile(r'patch.*v?\d+\.\d+', re.IGNORECASE),
        re.compile(r'SRCREV\s*='),  # SRCREV changes
        re.compile(r'PV\s*='),  # PV overrides
    ]

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Only check wildcard bbappends
        filename = context.path.name
        if not filename.endswith('.bbappend'):
            return results
        
        if '%' not in filename:
            return results  # Not a wildcard append
        
        # Check for version-specific content
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            for pattern in self.VERSION_SPECIFIC_PATTERNS:
                if pattern.search(stripped):
                    results.append(self.create_result(
                        file=context,
                        line=line_num,
                        message="Wildcard bbappend with potentially version-specific content",
                        context=stripped[:60],
                        hint="Consider using recipe_X.%.bbappend for version-specific changes",
                    ))
                    return results  # One warning per file
        
        return results


# Packages bitbake.conf and the always-inherited classes create
_STANDARD_SUFFIXES = ['', '-dev', '-dbg', '-doc', '-staticdev', '-locale',
                      '-src', '-lic']

# Classes that auto-create packages: class name -> package suffix
_CLASS_PACKAGES = {
    'lib_package': '-bin',
    'bash-completion': '-bash-completion',
    'gnome-help': '-help',
    'breakpad': '-breakpad',
}

# PACKAGES built from Python: the list is not knowable statically.
# do_split_packages() adds every package it splits off to PACKAGES, and
# the functions PACKAGESPLITFUNCS names run to do the same. A
# populate_packages:prepend that only sets RRECOMMENDS leaves it alone.
_PYTHON_PACKAGES_PATTERN = re.compile(
    r"""d\.(?:setVar|appendVar|prependVar)\(\s*['"]PACKAGES['"]"""
    r'|do_split_packages|PACKAGESPLITFUNCS')
_VARIABLE_REF_PATTERN = re.compile(r'\$\{([\w-]+)\}')
# A reference left after expansion, other than an inline ${@...} expression
_UNEXPANDED_PATTERN = re.compile(r'\$\{(?!@)')
_NAME_PATTERN = re.compile(r'[\w${}.+-]+')
# Overrides that operate on a variable rather than name a package
_OPERATION_OVERRIDES = {'append', 'prepend', 'remove'}


def _base_pn(pn: str) -> str:
    """BPN: PN without the native/nativesdk/cross variant markers."""
    bpn = re.sub(r'-(native|cross|crosssdk|cross-canadian-.*)$', '', pn)
    return re.sub(r'^nativesdk-', '', bpn)


class _PackageList:
    """The packages a recipe creates, read the way BitBake builds PACKAGES."""

    def __init__(self, variables: Dict[str, str]):
        self.packages: Set[str] = set()
        self.dynamic: List[str] = []
        self.variables = variables

    def expand(self, value: str, depth: int = 0) -> str:
        """Expand ${VAR} from the variables the recipe (and its includes)
        assigns. Unknown references are left in place."""
        if depth > 5 or '${' not in value:
            return value
        expanded = _VARIABLE_REF_PATTERN.sub(
            lambda m: self.variables.get(m.group(1), m.group(0)), value)
        if expanded == value:
            return value
        return self.expand(expanded, depth + 1)

    def declares(self, name: str) -> bool:
        """Whether the package *name* (already expanded) is created."""
        if name in self.packages:
            return True
        return any(self._dynamic_match(p, name) for p in self.dynamic)

    @staticmethod
    def _dynamic_match(pattern: str, name: str) -> bool:
        """PACKAGES_DYNAMIC entries are regular expressions matched against
        the start of a package name (^${PN}-plugin-.*)."""
        try:
            return re.match(pattern, name) is not None
        except re.error:
            return False


def _declared_packages(context: FileContext) -> Optional[_PackageList]:
    """The packages *context* creates, or None when the files at hand do
    not tell."""
    included = context.included_files
    if included is None:
        # A file this one includes was not found: what it adds to
        # PACKAGES is unknown
        return None
    structures = [context.structure] + [i.structure for i in included]
    assignments = [a for s in structures for a in s.assignments]

    # A .bbappend or .inc holds a fragment of a recipe: the rest of
    # PACKAGES lives elsewhere, unless the fragment replaces it outright
    if context.file_type in ("bbappend", "include") and not any(
        a.name == 'PACKAGES' and a.op in ('=', ':=') and not a.flag
        for a in context.structure.assignments
    ):
        return None

    texts = [context.content] + [
        i.path.read_text(encoding="utf-8", errors="replace") for i in included
    ]
    if any(_PYTHON_PACKAGES_PATTERN.search(t) for t in texts):
        return None

    pn = context.pn
    variables = {'PN': pn, 'BPN': _base_pn(pn), 'MLPREFIX': ''}
    for a in assignments:
        if a.flag or a.overrides or a.name in ('PN', 'BPN'):
            continue
        if a.op in ('=', ':=') or a.name not in variables:
            variables[a.name] = a.value
        else:
            variables[a.name] += ' ' + a.value
    package_list = _PackageList(variables)
    packages = package_list.packages

    packages.update(pn + suffix for suffix in _STANDARD_SUFFIXES)
    for class_name, suffix in _CLASS_PACKAGES.items():
        if class_name in context.inherits:
            packages.add(pn + suffix)
    # ptest and its variants (ptest-perl, ptest-gnome, ptest-cargo, ...)
    if any(c == 'ptest' or c.startswith('ptest-') for c in context.inherits):
        packages.add(pn + '-ptest')

    for a in assignments:
        if a.flag:
            continue
        if a.base in ('PACKAGES', 'PACKAGE_BEFORE_PN'):
            value = package_list.expand(a.value)
            if _UNEXPANDED_PATTERN.search(value):
                # Names a package through a variable set elsewhere (a
                # class, the distro): the list is not knowable here
                return None
            # Names inside an inline expression count too:
            # ${@bb.utils.contains('PACKAGECONFIG', 'x', '${PN}-x', '', d)}
            packages.update(_NAME_PATTERN.findall(value))
        elif a.base == 'PACKAGES_DYNAMIC':
            package_list.dynamic.extend(package_list.expand(a.value).split())

    # packagegroup.bbclass adds -dbg, -dev and (with the ptest distro
    # feature) -ptest flavours of every package in PACKAGES
    if ('packagegroup' in context.inherits
            and variables.get('PACKAGEGROUP_DISABLE_COMPLEMENTARY') != '1'):
        for package in list(packages):
            packages.update(package + s for s in ('-dbg', '-dev', '-ptest'))

    # BBCLASSEXTEND variants rename every package: foo-dev becomes
    # foo-native-dev or nativesdk-foo-dev
    variants = set()
    for a in assignments:
        if a.base == 'BBCLASSEXTEND':
            variants.update(package_list.expand(a.value).split())
    for package in list(packages):
        if 'native' in variants:
            packages.add(package.replace(pn, pn + '-native', 1))
        if 'nativesdk' in variants:
            packages.add('nativesdk-' + package)

    return package_list


class FilesPackagesConsistencyRule(BaseRule):
    """
    Check that FILES entries correspond to packages in PACKAGES.

    Each FILES:${PN}-foo must have corresponding ${PN}-foo in PACKAGES.
    BitBake ignores FILES of a package that is never created, so the files
    it names end up in another package or are not shipped at all.

    The package list is read the way BitBake builds it (see PKG005):
    - PACKAGES = "..." or PACKAGES += "..." or PACKAGES =+ "..."
    - PACKAGE_BEFORE_PN += "..." (auto-adds to PACKAGES before ${PN})
    - PACKAGES_DYNAMIC = "..." (regular expressions)
    - Inherited classes that auto-create packages (ptest, lib_package, ...)
    - Values held in local variables, ${PN} or the literal recipe name
    - Required or included files
    """

    rule_id = "PKG004"
    name = "FILES and PACKAGES Consistency"
    description = "Verifies FILES entries match packages defined in PACKAGES"
    default_severity = Severity.WARNING
    groups = ["packaging", "consistency"]
    hint = "Add missing package to PACKAGES or remove orphaned FILES"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        package_list = _declared_packages(context)
        if package_list is None:
            return results

        # FILES:<package>. FILES_SOLIBSDEV and the like are variables of
        # their own, not FILES of a package.
        for a in context.structure.assignments:
            if a.base != 'FILES' or not a.overrides:
                continue
            package = a.overrides[0]
            if package in _OPERATION_OVERRIDES:
                continue  # FILES:append, the variable itself
            name = package_list.expand(package)
            if '${' in name:
                continue  # Names a variable this file does not set
            if package_list.declares(name):
                continue

            results.append(self.create_result(
                file=context,
                line=a.line,
                message=f"FILES:{package} defined but '{package}' not in PACKAGES",
                hint=f'Add: PACKAGES += "{package}" or PACKAGE_BEFORE_PN += "{package}"',
            ))

        return results


class RdependsPackageExistenceRule(BaseRule):
    """
    Check that packages in RDEPENDS:pkg are defined in PACKAGES.
    
    RDEPENDS:${PN}-foo requires ${PN}-foo to exist in PACKAGES. BitBake
    silently ignores RDEPENDS of a package that is never created, so the
    assignment is dead metadata rather than a build failure.
    
    Recognizes packages added via:
    - PACKAGES = "..." or PACKAGES += "..." or PACKAGES =+ "..."
    - PACKAGE_BEFORE_PN += "..."
    - PACKAGES_DYNAMIC patterns
    - Inherited classes that auto-create packages (ptest, lib_package, etc.)
    - Values held in local variables (PACKAGE_BEFORE_PN = "${FOO_PACKAGES}")
    - Required or included files
    """
    
    rule_id = "PKG005"
    name = "RDEPENDS Package Existence"
    description = "Ensures packages referenced in RDEPENDS:pkg are in PACKAGES"
    default_severity = Severity.WARNING
    groups = ["packaging", "dependency"]
    hint = "Add package to PACKAGES or fix package name"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        package_list = _declared_packages(context)
        if package_list is None:
            return results

        for a in context.structure.assignments:
            if a.flag:
                continue
            if a.base == 'RDEPENDS' and a.overrides:
                package = a.overrides[0]
            elif a.base.startswith('RDEPENDS_'):
                package = a.base[len('RDEPENDS_'):]
            else:
                continue

            # "RDEPENDS:${PN}+= ..." is an append to RDEPENDS:${PN}: BitBake
            # takes the shortest name before the operator
            if a.op == '=' and package[-1:] in ('+', '.'):
                package = package[:-1]
            name = package_list.expand(package)
            if '${' in name:
                continue  # Names a variable this file does not set
            if package_list.declares(name):
                continue

            results.append(self.create_result(
                file=context,
                line=a.line,
                message=f"RDEPENDS:{package} but '{package}' not defined in PACKAGES",
                hint=f'Add: PACKAGES += "{package}" or PACKAGE_BEFORE_PN += "{package}"',
            ))
        
        return results

class RrecommendsPackageValidityRule(BaseRule):
    """
    Check that packages in RRECOMMENDS:pkg are defined in PACKAGES.

    Similar to PKG005 but for RRECOMMENDS (lower severity), reading the
    package list the same way: PACKAGES, PACKAGE_BEFORE_PN, PACKAGES_DYNAMIC,
    local variables, includes and the packages classes create.
    """

    rule_id = "PKG006"
    name = "RRECOMMENDS Package Validity"
    description = "Checks packages in RRECOMMENDS:pkg are defined in PACKAGES"
    default_severity = Severity.INFO
    groups = ["packaging", "dependency"]
    hint = "Add package to PACKAGES or fix package name"

    def check(self, context: FileContext) -> List[LintResult]:
        results = []

        # A distro or machine configuration sets RRECOMMENDS of packages
        # other recipes create
        if 'conf' in context.path.parts[:-1]:
            return results

        package_list = _declared_packages(context)
        if package_list is None:
            return results

        for a in context.structure.assignments:
            # RRECOMMENDS:${PN}-dev[nodeprrecs] is a flag of the same
            # package's variable, so flags are judged too
            if a.base == 'RRECOMMENDS' and a.overrides:
                package = a.overrides[0]
            elif a.base.startswith('RRECOMMENDS_'):
                package = a.base[len('RRECOMMENDS_'):]
            else:
                continue
            if package in _OPERATION_OVERRIDES:
                continue  # RRECOMMENDS:append, the variable itself
            name = package_list.expand(package)
            if '${' in name:
                continue  # Names a variable this file does not set
            if package_list.declares(name):
                continue

            results.append(self.create_result(
                file=context,
                line=a.line,
                message=f"RRECOMMENDS:{package} but '{package}' not in PACKAGES",
                hint=f'Verify package name or add: PACKAGES += "{package}" or PACKAGE_BEFORE_PN += "{package}"',
            ))

        return results
