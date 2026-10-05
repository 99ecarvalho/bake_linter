# -*- coding: utf-8 -*-
"""
Best practices rules for Yocto recipes.

These rules check for adherence to Yocto best practices.

Copyright (c) 2024-2026 Eduardo Correia <ecorreia@apliant.com.br>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""

from __future__ import annotations

import re
from typing import List

from bake_linter.core.models import LintResult, Severity, FileContext
from bake_linter.core.recipe import command_words
from bake_linter.rules.base import BaseRule


class DoFetchModificationRule(BaseRule):
    """
    Check for modifications to do_fetch task.
    
    Modifying do_fetch is an anti-pattern; sources should be added
    to SRC_URI instead for proper checksumming and caching.
    """
    
    rule_id = "BESTPRACTICE001"
    name = "do_fetch Modification"
    description = "Detects modifications to do_fetch which should use SRC_URI"
    default_severity = Severity.WARNING
    groups = ["best_practices"]
    hint = "Add sources to SRC_URI instead of modifying do_fetch"

    DO_FETCH_PATTERN = re.compile(r'^do_fetch(?::append|:prepend|_append|_prepend)?\s*\(')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line_num, line in enumerate(context.lines, start=1):
            stripped = line.strip()
            
            if stripped.startswith("#"):
                continue
            
            if self.DO_FETCH_PATTERN.match(stripped):
                results.append(self.create_result(
                    file=context,
                    line=line_num,
                    message="Modifying do_fetch is an anti-pattern",
                    context=stripped[:60],
                    hint="Add sources to SRC_URI for proper checksumming and caching",
                ))
        
        return results


class CleanupInConfigureRule(BaseRule):
    """
    Check for rm commands in do_configure that reach outside the recipe's
    own work directory.
    
    Clearing stale files from ${S}, ${B} or ${WORKDIR} before configuring
    is routine. Removing files elsewhere (sysroots, deploy directories,
    TMPDIR, host paths) touches what other tasks and recipes own.
    """
    
    rule_id = "BESTPRACTICE002"
    name = "Cleanup in do_configure"
    description = "Detects rm commands in do_configure outside the recipe's work directory"
    default_severity = Severity.INFO
    groups = ["best_practices"]
    hint = "Only remove files in ${S}, ${B} or ${WORKDIR}; other paths belong to other tasks or recipes"

    WORK_TREE = re.compile(r'^\$\{(?:S|B|WORKDIR|UNPACKDIR)\}')
    BITBAKE_VAR = re.compile(r'^\$\{[A-Z][A-Z0-9_]*\}')

    def _outside_work_tree(self, target: str) -> bool:
        if target.startswith("/"):
            return True
        # ${STAGING_DIR_HOST}, ${DEPLOY_DIR}, ${TMPDIR}, ...; a shell
        # variable ($d, ${dir}) could be anywhere and a relative path is in
        # ${B}
        return bool(self.BITBAKE_VAR.match(target)) and not self.WORK_TREE.match(target)

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line in context.function_lines:
            if line.function.split(":", 1)[0] != "do_configure":
                continue
            words = command_words(line.text)
            if words[:1] != ["rm"]:
                continue
            targets = [w for w in words[1:] if not w.startswith("-")]
            if any(self._outside_work_tree(t) for t in targets):
                results.append(self.create_result(
                    file=context,
                    line=line.line,
                    message="rm in do_configure removes files outside the recipe's work directory",
                    context=line.text[:60],
                ))
        
        return results


class MissingHomepageRule(BaseRule):
    """
    Check for recipes without HOMEPAGE when upstream project exists.
    
    HOMEPAGE is important documentation for package maintainers.
    """
    
    rule_id = "BESTPRACTICE003"
    name = "Missing HOMEPAGE"
    description = "Detects recipes without HOMEPAGE"
    default_severity = Severity.INFO
    groups = ["best_practices", "documentation"]
    hint = "Add HOMEPAGE = \"URL\" pointing to project website"
    
    enabled_by_default = False

    # Known hosting services to suggest HOMEPAGE from
    GITHUB_PATTERN = re.compile(r'github\.com/([^/]+/[^/;]+)')
    GITLAB_PATTERN = re.compile(r'gitlab\.com/([^/]+/[^/;]+)')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        # Skip certain recipe types
        filename = context.path.name.lower()
        if any(skip in filename for skip in ['packagegroup', '-image']):
            return results
        
        has_homepage = False
        suggested_url = None
        
        for line in context.lines:
            stripped = line.strip()
            if stripped.startswith("HOMEPAGE"):
                has_homepage = True
                break
            
            # Try to extract URL from SRC_URI
            if not suggested_url:
                gh_match = self.GITHUB_PATTERN.search(stripped)
                if gh_match:
                    suggested_url = f"https://github.com/{gh_match.group(1)}"
                gl_match = self.GITLAB_PATTERN.search(stripped)
                if gl_match:
                    suggested_url = f"https://gitlab.com/{gl_match.group(1)}"
        
        if not has_homepage and suggested_url:
            results.append(self.create_result(
                file=context,
                line=1,
                message="Recipe missing HOMEPAGE",
                hint=f'Consider adding: HOMEPAGE = "{suggested_url}"',
            ))
        
        return results


class SedInDoInstallRule(BaseRule):
    """
    Check for sed usage in do_install on the source or build tree.
    
    Editing files under ${D} after installing them is the usual way to
    substitute paths in installed files: they only exist once installed.
    Editing the source or build tree in do_install changes what earlier
    tasks used; that belongs in a patch or do_configure.
    """
    
    rule_id = "BESTPRACTICE004"
    name = "sed in do_install"
    description = "Detects sed -i in do_install on the source or build tree"
    default_severity = Severity.WARNING
    groups = ["best_practices"]
    hint = "sed on the source/build tree in do_install; prefer a patch or do_configure"

    # -i, -i.bak, -ri, --in-place
    IN_PLACE = re.compile(r'^(?:-[A-Za-z]*i|--in-place)')
    # Options that take the next word as their argument
    OPTIONS_WITH_ARGUMENT = {"-e", "-f", "-l", "--expression", "--file", "--line-length"}
    DESTDIR = re.compile(r'\$\{D\}|\$D(?![A-Za-z0-9_])')
    BUILD_TREE = re.compile(r'^\$\{(?:S|B|WORKDIR|UNPACKDIR)\}')
    # do_install, do_install_ptest, ...
    INSTALL_TASK = re.compile(r'^do_install(?:_\w+)?$')

    @classmethod
    def _targets(cls, words: List[str]) -> List[str]:
        """The files a sed command edits."""
        targets: List[str] = []
        has_script = False
        skip_next = False
        for word in words[1:]:
            if skip_next:
                skip_next = False
                continue
            if word in cls.OPTIONS_WITH_ARGUMENT:
                has_script = has_script or word in {"-e", "-f", "--expression", "--file"}
                skip_next = True
            elif word.startswith("--"):
                has_script = has_script or word.startswith(("--expression=", "--file="))
            elif word.startswith("-") and len(word) > 1:
                # A cluster: -ne takes the script as its argument, -e's/a/b/'
                # carries it, and in -ie the e is the suffix of -i
                match = re.match(r'^-[A-Za-z]*?([efi])', word)
                if match and match.group(1) in "ef":
                    has_script = True
                    skip_next = match.end() == len(word)
            elif not has_script:
                has_script = True  # without -e/-f the first operand is the script
            else:
                targets.append(word)
        return targets

    def _on_build_tree(self, target: str) -> bool:
        if self.BUILD_TREE.match(target):
            return True
        # Relative paths are in the task's working directory, ${B}
        return not target.startswith(("$", "/", "`"))

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        
        for line in context.function_lines:
            if not self.INSTALL_TASK.match(line.function.split(":", 1)[0]):
                continue
            words = command_words(line.text)
            if words[:1] != ["sed"] or not any(self.IN_PLACE.match(w) for w in words[1:]):
                continue
            targets = self._targets(words)
            # Installed files can only be edited after do_install put them there
            if not targets or any(self.DESTDIR.search(t) for t in targets):
                continue
            if any(self._on_build_tree(t) for t in targets):
                results.append(self.create_result(
                    file=context,
                    line=line.line,
                    message="sed -i in do_install modifies the source/build tree",
                    context=line.text[:60],
                ))
        
        return results
