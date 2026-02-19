# Inline Suppression Examples

This directory contains example BitBake recipes demonstrating various inline suppression scenarios.

## Files

- `example-good.bb` - Proper usage of inline suppressions
- `example-bad.bb` - Anti-patterns to avoid
- `example-migration.bb` - Using suppressions during migration

## Usage

These examples are for documentation purposes. You can lint them to see how suppressions work:

```bash
# Lint the good example
bake-linter docs/examples/example-good.bb

# Lint the bad example (should show warnings about suppressions)
bake-linter docs/examples/example-bad.bb
```

## Learning

1. Read through each example file
2. Note the comments explaining each suppression
3. Try removing suppressions to see what errors appear
4. Compare with the rule documentation in `docs/rules/`

---

*These examples are part of the bake-linter documentation*
