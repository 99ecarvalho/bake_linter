# Contributing to bake_linter

Thank you for helping. This guide covers reporting problems, setting up a
development checkout, how the code is organised, how to write or fix a
rule, and the conventions for commits and pull requests.

- [Reporting false positives and bugs](#reporting-false-positives-and-bugs)
- [Development setup](#development-setup)
- [How the code is organised](#how-the-code-is-organised)
- [Writing a rule](#writing-a-rule)
- [Fixing a false positive](#fixing-a-false-positive)
- [Tests](#tests)
- [Documentation](#documentation)
- [Coding style and file headers](#coding-style-and-file-headers)
- [Commit messages](#commit-messages)
- [Pull requests](#pull-requests)
- [Licensing of contributions](#licensing-of-contributions)

## Reporting false positives and bugs

The most useful report is a minimal recipe that shows the problem:

- the rule ID and the message you got;
- the smallest `.bb` / `.bbappend` / `.inc` content that reproduces it,
  with names made generic (`foo`, `example.com`, `qemux86-64`);
- the Yocto release you build for;
- why you think the finding is wrong, ideally with a pointer to the
  BitBake, OE-Core class or manual behaviour involved.

Please don't paste recipes you are not allowed to publish.

## Development setup

```bash
git clone --recurse-submodules https://github.com/99ecarvalho/bake_linter.git
cd bake_linter
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e ./vendor/oelint-adv   # optional, Python 3.10+
pytest
```

To see a rule's effect on real layers, run it over a checkout of poky and
meta-openembedded and compare the counts before and after your change:

```bash
bake-linter --quiet --output json,/tmp/after.json poky/meta meta-openembedded
```

Keep such reports out of the repository; `output/` is ignored for that
reason.

## How the code is organised

```text
bake_linter/
  cli.py                 command line, output files, oelint-adv pass
  config.py              .bake-linter.yaml / .json loading
  core/
    engine.py            finds files, parses them, runs the enabled rules
    models.py            FileContext, LintResult, Severity, ExitCode
    recipe.py            structure of a file beyond single lines
    registry.py          rule discovery
    oelint_integration.py  finding and running oelint-adv
  rules/                 one module per rule family
  output/                text, compact, JSON, JSON Lines, HTML formatters
  utils/gen_docs.py      rule pages and the rule index
docs/rules/              one page per rule, plus the generated index
hooks/                   pre-commit hook and its installer
tests/                   pytest suite
```

The engine reads each file once into a `FileContext` and hands it to every
enabled rule that applies to that kind of file (`recipe`, `bbappend` or
`include`). Results are filtered for inline suppressions in one place, after
the rule returns.

`FileContext` gives rules the structure of the file, computed on first use
(see `core/recipe.py`):

| Attribute | What it gives |
| --- | --- |
| `lines`, `content` | The raw file |
| `structure.assignments` | Logical assignments: name, flag, operator, value with continuation lines joined, first and last line; `.base` and `.overrides` split the name |
| `owner(line)`, `owner_base(line)` | What a line belongs to: a variable (also on its continuation lines), `FUNC:<name>` inside a function, `#` for a comment |
| `assignment_at(line)`, `function_at(line)`, `is_top_level_assignment(line)` | The same, as objects |
| `function_lines` | Function body lines with continuations joined |
| `inherits` | Classes inherited here or in a resolved include, including those named in inline Python |
| `included_files` | `require`/`include` resolved next to the file and from the layer root; `None` when one cannot be found |
| `sets_variable(name)` | `True` / `False`, or `None` when an unresolved include might set it |
| `pn` | PN as BitBake derives it from the file name |
| `release`, `release_before(name)` | The configured target release, when there is one |

Use these instead of matching raw lines: most false positives come from a
rule that reads a continuation line, a shell variable in a function body, or
a variable set in an included file as something else.

## Writing a rule

A rule is a subclass of `BaseRule` in a module under `bake_linter/rules/`.
Subclasses register themselves; there is nothing else to wire up.

```python
import re
from typing import List

from bake_linter.core.models import FileContext, LintResult, Severity
from bake_linter.rules.base import BaseRule


class PlaintextMirrorRule(BaseRule):
    """
    One paragraph on what the rule checks and the BitBake reason it matters.
    """

    rule_id = "SECURITY009"            # FAMILY + number, unique
    name = "Plaintext Mirror"
    description = "Detects MIRRORS entries that download over http://"
    default_severity = Severity.WARNING  # ERROR when BitBake or QA rejects it
    groups = ["security", "network"]
    hint = "Use an https:// mirror"
    applicable_file_types = {"recipe", "bbappend", "include"}

    HTTP = re.compile(r'\bhttp://')

    def check(self, context: FileContext) -> List[LintResult]:
        results = []
        for assignment in context.structure.assignments:
            if assignment.base != "MIRRORS":
                continue
            if self.HTTP.search(assignment.value):
                results.append(self.create_result(
                    file=context,
                    line=assignment.line,
                    message="MIRRORS downloads over plaintext http://",
                ))
        return results
```

- Pass `file=context` to `create_result`, so suppression and the rule's
  documentation link work.
- Report on the line the user has to change. A finding about the file as a
  whole (a missing variable) may have no line.
- Rule options come from the configuration file through
  `self.get_option("name", default)`.

### When a rule should stay silent

A linter that is wrong teaches people to ignore it. When a rule cannot know
the answer it should say nothing rather than guess:

- a variable that may be set by an include that cannot be found
  (`sets_variable()` returns `None`), or by an inherited class;
- a `.inc` or `.bbappend` fragment whose base recipe holds the rest;
- values built in Python (`d.setVar(...)`) or by functions such as
  `do_split_packages`.

## Fixing a false positive

Only change a rule when it misreads BitBake: the wrong variable or owner,
continuation lines, function bodies, an operator, override syntax, a class
or include it does not follow, fetcher or class semantics, or a pattern that
matches inside a longer word. Explain the BitBake behaviour in the commit,
ideally with the class or fetcher code involved.

A practice is not correct just because it is common. Poky, meta-openembedded
and vendor layers all contain recipes that do things the style guide or good
practice advise against, and a rule that reports those is doing its job.
Don't lower a severity or narrow a rule only because it fires often on a
popular layer.

## Tests

Every behaviour change comes with tests:

- one positive case (the rule fires) and the negative cases you fixed;
- in a new file named after the rule, such as
  `tests/test_security009_mirrors.py`;
- with generic content: no company, product, recipe or machine names from
  private layers. Use QEMU machines (`qemux86-64`, `qemuarm64`) and
  `example.com`;
- with `tmp_path` and a `conf/layer.conf` when the rule follows includes.

```bash
pytest                              # everything
pytest tests/test_security009_mirrors.py -v
pytest -k SECURITY009
```

## Documentation

Each rule has a page `docs/rules/<RULE_ID>.md`. Create it from the template
and fill in the example, the reason and the fix:

```bash
python -m bake_linter.utils.gen_docs --rule SECURITY009
```

The rule index in `docs/rules/README.md` is generated. Regenerate it after
adding a rule or changing a rule's name, description, severity or default
state:

```bash
python -m bake_linter.utils.gen_docs --index
```

A test fails when the index, or a page's title, severity or default state,
no longer matches the code. When you change a severity, also update the
rule's entry in `config/.bake-linter.yaml`.

## Coding style and file headers

Follow the style of the surrounding code: type hints, docstrings that say
why, compiled regular expressions as class attributes, and comments for the
BitBake behaviour a check relies on.

New source files start with this header (in a module docstring for Python,
in `#` comments for shell and YAML):

```python
"""
One-line description.

Copyright (c) 2026 Your Name <you@example.com>

This file is part of bake_linter. It is free software, licensed under the
GNU Lesser General Public License v3.0 or later. See COPYING.LESSER and
COPYING for details.

SPDX-License-Identifier: LGPL-3.0-or-later
"""
```

When you make a substantial change to an existing file, you may add your own
copyright line below the existing one.

## Commit messages

The project uses [Conventional Commits](https://www.conventionalcommits.org/).
For a rule, the scope is the rule ID:

```text
fix(SECURITY001): ignore informational URL variables

HOMEPAGE, BUGTRACKER and UPSTREAM_CHECK_URI only document a URL; BitBake
never fetches from them, so an http:// there is no plaintext download.
```

Common types are `feat`, `fix`, `docs`, `refactor`, `test`, `build` and
`chore`. Keep the summary under about 72 characters, explain the reason in
the body, and keep each commit working and tested.

## Pull requests

Before opening one, check that:

- [ ] `pytest` passes;
- [ ] new and changed rules have tests and an up-to-date page in
      `docs/rules/`, and the index is regenerated;
- [ ] the change does not add findings on a stock poky / meta-openembedded
      checkout that are misreadings;
- [ ] new files carry the copyright and SPDX header;
- [ ] commits follow the convention above.

## Licensing of contributions

bake_linter is licensed under the GNU Lesser General Public License v3.0 or
later (see [COPYING.LESSER](COPYING.LESSER) and [COPYING](COPYING)). By
submitting a contribution you agree that it is licensed under the same terms,
and you confirm that you have the right to submit it.
