# bake_linter and oelint-adv

[oelint-adv](https://github.com/priv-kweihmann/oelint-adv) is the established
linter for BitBake recipes. bake_linter does not replace it: it ships
oelint-adv as a git submodule under `vendor/oelint-adv` and runs it as a
second pass after its own rules, so one command gives both sets of findings.
This page explains what each tool covers and where they differ, so you can
decide how to use them together.

The figures below are for bake_linter at the current `main` and the vendored
oelint-adv 9.7.0.

## At a glance

| | bake_linter | oelint-adv 9.7.0 |
| --- | --- | --- |
| Rules | 110 (`bake-linter --list-rules`), in 52 groups | 114 rule IDs |
| Rule IDs | Short codes (`LICENSE001`, `SECURITY001`) | Dotted names (`oelint.var.mandatoryvar.LICENSE`) |
| Parsing | Its own lightweight parser; follows `require`/`include` inside the layer | [oelint-parser](https://github.com/priv-kweihmann/oelint-parser), with variable expansion and file grouping |
| Inline suppression | `# nolint: RULE_ID` | `# nooelint: rule.id` |
| Release-specific rules | Not yet; the release is passed to oelint-adv | `--release` |
| Auto-fix | No | `--fix` (18 rules) |
| Parallel runs and caching | No | `--jobs`, `--cached` |
| Custom rules | Add a module under `bake_linter/rules/` | `--customrules`, `--addrules`, rule files |
| Output | text, compact, JSON, JSON Lines, HTML report | Text with a configurable message format |
| Exit codes | 0 clean, 1 warnings, 2 errors, 3 runtime error | Non-zero when issues are found, 0 with `--exit-zero` |
| License | LGPL-3.0-or-later | BSD-2-Clause |

## What bake_linter adds

**Rule areas oelint-adv does not cover in depth.** Besides syntax and style,
bake_linter has rule families for:

- security: plaintext fetches, world-writable or setuid installs, credentials
  in recipes, build paths leaking into installed files;
- supply chain and reproducibility: unpinned branches, unreliable hosting,
  bbappends that fetch new sources without updating `LIC_FILES_CHKSUM`;
- packaging: `FILES` coverage of installed paths, `RDEPENDS` on packages the
  recipe does not create, `-dev` dependencies;
- install hygiene: `cp` that preserves the build user's ownership, missing
  modes, `/usr/local`, non-FHS destinations;
- systemd, bbappend, layer and lifecycle checks.

Every rule has a documentation page under [docs/rules/](docs/rules/) with an
example, the reason, and the fix.

**Reports for CI and review.** JSON and JSON Lines for tooling, a compact
`file:line: severity: [RULE] message` format for editors, and a
self-contained HTML report with filters and statistics. When oelint-adv runs,
its findings are written alongside (`report_oelintadv.html` next to an HTML
report).

**Configuration in one file.** `.bake-linter.yaml` enables, disables and
re-grades rules and groups, sets exclusions, and passes settings through to
oelint-adv (`oelint_release`, `oelint_extra_machines`, which becomes its
`--constantmods`).

**A pre-commit hook.** [hooks/install-hooks.sh](hooks/install-hooks.sh)
installs a hook that lints only the staged recipes, from the staged content.

## What oelint-adv does that bake_linter does not

- **A full BitBake parser.** oelint-parser expands variables and groups a
  recipe with its bbappends, so its rules see the recipe the way BitBake
  does. bake_linter reads each file with its own parser and follows
  `require`/`include` within the layer. It does not expand variables beyond
  `${PN}` or merge bbappends into their recipe, so a rule that needs the
  merged view stays silent rather than guess.
- **Release awareness.** oelint-adv knows which variables and features exist
  in each Yocto release and gates rules on `--release`. bake_linter passes
  the configured release through to oelint-adv but its own rules are not
  release-gated yet.
- **Auto-fix**, **parallel runs**, **caching**, and **custom rule loading**.
- **Patch file checks** (`Upstream-Status`, `Signed-off-by`), which bake_linter
  does not have.

## Using them together

By default `bake-linter` runs its own rules, then oelint-adv if it can be
imported together with its dependencies (`oelint_parser`). The summary of
each tool is printed separately; the exit code reflects bake_linter's own
findings. If oelint-adv is found but fails, bake-linter exits with code 3
instead of reporting a clean result.

To install oelint-adv next to bake_linter, run `./install.sh`, which uses
pipx and injects the vendored copy, or install it into the same environment:

```bash
git submodule update --init
pip install ./vendor/oelint-adv
```

Use `--debug` (or `BAKE_LINTER_DEBUG=1`) to see how oelint-adv is detected
and invoked.

Some checks exist in both tools, for example mandatory variables, override
syntax and tabs. When both report the same problem, fix it once and use
`# nolint:` or `# nooelint:` for the tool whose finding you disagree with.

## Ideas taken from oelint-adv

bake_linter adopted these ideas from oelint-adv:

- one documentation page per rule, with an example and a fix;
- inline suppression comments;
- passing a target release, and extra machine names, to the release-gated
  checks.

Still open, and good candidates for contributions:

- release-gated rules in bake_linter itself, for example `S = "${WORKDIR}"`,
  which is fatal from styhead on;
- auto-fix for the mechanical style rules;
- parallel linting of large layers;
- loading custom rules from outside the package.
