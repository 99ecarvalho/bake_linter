# Rule Documentation

This directory contains detailed documentation for each lint rule in bake-linter.

## Organization

Rules are organized by category:
- **LICENSE** - License-related checks
- **MANDATORY** - Mandatory variable checks
- **DEPRECATED** - Deprecated syntax detection
- **NAMING** - Naming convention checks
- **STYLE** - Code style checks
- **SECURITY** - Security-related checks
- And more...

## Format

Each rule documentation includes:
- **Severity level** (error, warning, info)
- **Description** of what the rule checks
- **Examples** of bad and good code
- **Explanation** of why it matters
- **How to fix** the issue
- **Inline suppression** syntax
- **Configuration** options

## Using Rule Documentation

When the linter reports an issue, you can find detailed information about the rule:

1. **From the error message** - Look for the rule ID (e.g., `LICENSE001`)
2. **Find the documentation** - Open `docs/rules/{RULE_ID}.md`
3. **Read the explanation** - Understand why it's flagged
4. **Apply the fix** - Follow the "How to Fix It" section
5. **Or suppress it** - Use inline suppression if it's a false positive

## Generating Documentation

Documentation can be generated or updated using the documentation generator:

```bash
python -m bake_linter.utils.gen_docs
```

This will:
- Create/update documentation for all rules
- Use the template in `template.md`
- Extract information from rule class definitions
- Generate examples where available

## Contributing

When adding a new rule, please:
1. Add documentation using the template
2. Include clear examples of bad and good code
3. Explain why the rule matters
4. Document any configuration options
5. Test the inline suppression syntax

---

*Last updated: January 19, 2026*
