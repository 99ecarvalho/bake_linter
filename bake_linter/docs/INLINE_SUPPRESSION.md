# Inline Suppression Quick Reference

## Syntax

```bitbake
# nolint: RULE_ID
```

## Examples

### Suppress Single Rule
```bitbake
# nolint: LICENSE001
SUMMARY = "Meta-package without traditional license"
```

### Suppress Multiple Rules
```bitbake
# nolint: LICENSE001, MANDATORY001, STYLE001
RDEPENDS:${PN} = "packages"
```

### Inline Suppression
```bitbake
LICENSE = "CLOSED"  # nolint: LICENSE001
```

### Suppress All Rules (Use Sparingly!)
```bitbake
# nolint: *
LEGACY_CODE = "needs-refactoring"
```

## Variations (All Valid)

```bitbake
# nolint: RULE_ID     ← Standard
# NOLINT: RULE_ID     ← Case insensitive
# NoLint: RULE_ID     ← Works too
#nolint: RULE_ID      ← No space after #
# nolint:RULE_ID      ← No space after :
```

## Scope

- **Standalone comment**: Applies to next non-comment line
- **Inline comment**: Applies to current line only
- **Not file-wide**: Each suppression is line-specific

## Best Practices

### ✅ DO

```bitbake
# This is a meta-package that bundles other packages
# It doesn't have its own source, so LICENSE isn't applicable
# nolint: LICENSE001
RDEPENDS:${PN} = "pkg1 pkg2 pkg3"

# TODO: Fix this deprecated syntax in next sprint (JIRA-1234)
# nolint: DEPRECATED001
SRC_URI_append = " file://patch.patch"

# False positive - this IS using HTTPS but linter misdetects
# nolint: SECURITY001
CUSTOM_URL = "https://example.com/download"
```

### ❌ DON'T

```bitbake
# Just hiding the issue without fixing it
# nolint: LICENSE001
SUMMARY = "Something"

# Suppressing security warnings without review
# nolint: SECURITY004
PASSWORD = "admin123"

# Blanket suppression across entire file
# nolint: *
# ... entire file ...

# No explanation why it's suppressed
# nolint: STYLE001
```

## Common Use Cases

| Scenario | Example |
|----------|---------|
| **False Positive** | Linter incorrectly flags valid code |
| **Migration** | Temporary during transition period |
| **Legacy Code** | Scheduled for refactor, tracked in backlog |
| **Special Case** | Valid exception to general rule |
| **External Code** | Third-party code you can't modify |

## Finding Rule IDs

```bash
# List all available rules
bake-linter --list-rules

# See which rule flagged an issue
bake-linter recipe.bb
# Output: recipe.bb:5:error:LICENSE001:Variable 'LICENSE' should be set
#                               ^^^^^^^^^^
#                               This is the Rule ID
```

## Documentation

Each rule has detailed documentation:

```bash
# In your editor or browser, open:
docs/rules/{RULE_ID}.md

# Examples:
docs/rules/LICENSE001.md
docs/rules/DEPRECATED001.md
docs/rules/MANDATORY001.md
```

## Checking Suppressions

Currently, the linter doesn't warn about unused suppressions. To review:

```bash
# Search for all suppressions in your codebase
grep -r "nolint:" .

# Count suppressions
grep -r "nolint:" . | wc -l

# Find suppressions of specific rule
grep -r "nolint:.*LICENSE001" .
```

## Tips

1. **Always add a comment** explaining WHY you're suppressing
2. **Link to issue tracker** if it's temporary
3. **Be specific** - suppress individual rules, not `*`
4. **Review periodically** - suppressions may become obsolete
5. **Get code review** for security suppressions
6. **Consider fixing** instead of suppressing when possible

## Alternatives to Suppression

Before suppressing, consider:

1. **Fix the code** - Is the linter right? Fix the issue
2. **Configure the rule** - Disable globally in `.bake-linter.yaml`
3. **Adjust severity** - Change from error to warning
4. **Report false positive** - File an issue if the rule is buggy

## Configuration Alternative

Instead of inline suppression, you can disable rules globally:

```yaml
# .bake-linter.yaml
rules:
  LICENSE001:
    enabled: false  # Disable for entire project

  STYLE001:
    severity: info  # Reduce severity
```

## Help

- **Documentation**: See `docs/rules/README.md`
- **Examples**: See rule-specific documentation
- **Issues**: Report false positives on issue tracker
- **Questions**: Ask in team chat or documentation

---

*Last updated: January 19, 2026*
