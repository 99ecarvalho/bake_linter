# Examples

Two example recipes show inline suppression in practice. They are not real
recipes and are not meant to be built.

- [example-good.bb](example-good.bb): suppressions used well. Each one names
  the rule and says why, and covers only the line it is about.
- [example-bad.bb](example-bad.bb): habits to avoid, such as suppressions
  with no reason, blanket `# nolint: *`, and hiding security findings.

Lint them to see what is reported and what is suppressed:

```bash
bake-linter docs/examples/example-good.bb
bake-linter docs/examples/example-bad.bb
```

The good example still gets a few warnings and info findings: suppressions
are for specific, explained cases, not for silencing a file. Remove a
suppression to see the finding it hides, and look the rule up in
[the rules](../rules/README.md).
