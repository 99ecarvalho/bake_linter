# Quick start

## Lint a layer

```bash
bake-linter meta-mylayer/
bake-linter meta-mylayer/recipes-core/foo/foo_1.0.bb
```

bake_linter checks `.bb`, `.bbappend` and `.inc` files. Each finding names
the rule, its severity, the line, a hint, and the rule's page:

```text
━━━ recipes-core/foo/foo_1.0.bb ━━━
  Line 4
  ⚠ WARNING [SECURITY001]
    Insecure HTTP URI detected; use HTTPS instead
    💡 Change http:// to https://
    📚 docs/rules/SECURITY001.md
```

For one line per finding, use `--format compact`:

```text
recipes-core/foo/foo_1.0.bb:4: warning: [SECURITY001] Insecure HTTP URI detected; use HTTPS instead: docs/rules/SECURITY001.md
```

## Reports

```bash
bake-linter --output html,report.html meta-mylayer/
bake-linter --output json,report.json --output html,report.html meta-mylayer/
```

`--output FORMAT,FILE` can be repeated; formats are `text`, `compact`,
`json`, `jsonl` and `html`. Add `--quiet` to write the files without
printing every finding.

## Choosing rules

```bash
bake-linter --list-rules                 # every rule, severity, default state
bake-linter --list-groups                # rule groups
bake-linter --enable LICENSE001,MANDATORY001 meta-mylayer/
bake-linter --disable STYLE001,STYLE002 meta-mylayer/
bake-linter --disable-group formatting meta-mylayer/
bake-linter --exclude 'build/*' --exclude '*.bak' .
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No findings, or only info |
| 1 | Warnings, no errors |
| 2 | Errors |
| 3 | Configuration or runtime error, including an oelint-adv run that failed |

In CI, `--ci` turns colours off, and `--warnings-as-errors` makes warnings
exit with 2.

## Configuration file

Put `.bake-linter.yaml` in the directory you run bake-linter from, or pass
`--config FILE`:

```yaml
rules:
  LICENSE001:
    severity: error
  STYLE001:
    enabled: false

settings:
  oelint_release: scarthgap   # the release your layers build for

exclude:
  - "build/*"
  - "tmp/*"
```

`bake-linter --show-config` prints the configuration in effect. The
[README](https://github.com/99ecarvalho/bake_linter#configuration) lists all
settings, and `config/.bake-linter.yaml` in the repository lists every rule.

## Suppressing a finding

```bitbake
# Meta package: nothing to license
# nolint: LICENSE001
SUMMARY = "Meta package"

SRC_URI = "http://example.com/foo.tar.gz"  # nolint: SECURITY001
```

See [Inline suppression](../INLINE_SUPPRESSION.md).

## Next steps

- [Rules](../rules/README.md): what each rule checks and how to fix it
- [Examples](../examples/README.md)
