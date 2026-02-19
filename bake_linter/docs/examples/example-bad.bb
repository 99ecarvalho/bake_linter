# Example: Poor Inline Suppression Usage (Anti-patterns)
#
# This file demonstrates BAD practices - what NOT to do with suppressions.
# Use this as a guide for what to avoid in your own recipes.

SUMMARY = "Example showing suppression anti-patterns"

# ❌ BAD: No explanation why LICENSE is suppressed
# nolint: LICENSE001

# ❌ BAD: Blanket suppression hides real issues
# nolint: *
DESCRIPTION = "This suppresses ALL rules, hiding real problems"

# ❌ BAD: Suppressing security issues without review
# nolint: SECURITY004
PASSWORD = "hardcoded_secret_123"

# ❌ BAD: Using suppression instead of fixing the issue
# nolint: DEPRECATED001
SRC_URI_append = " file://patch.patch"
# Should be: SRC_URI:append = " file://patch.patch"

# ❌ BAD: Suppressing style without reason
# nolint: STYLE001
DEPENDS = "foo bar baz"

# ❌ BAD: No tracking or timeline for removal
# nolint: BESTPRACTICE003
# TODO: add homepage someday maybe

# ❌ BAD: Suppressing multiple unrelated rules
# nolint: LICENSE001, MANDATORY001, STYLE001, DEPRECATED001, SECURITY001
CUSTOM_VAR = "something"

# ❌ BAD: Using suppression for laziness
do_install() {
    # nolint: INSTALL001
    cp -r ${S}/* ${D}/
}
# Should use: install -D -m 0644 file ${D}/path/to/file

# ❌ BAD: Suppressing without understanding why it's flagged
# nolint: SYNTAX001
BROKEN_VAR = "unmatched quote

# ❌ BAD: Suppressing entire task instead of fixing
# nolint: TASK001, TASK002, TASK003
python do_custom() {
    os.system("sudo rm -rf /important/data")  # DANGEROUS!
}

# ❌ BAD: Repeated suppressions suggest configuration needed
# nolint: STYLE002
REALLY_LONG_LINE = "This is a really long line that exceeds the maximum length but I'm suppressing instead of configuring"
# nolint: STYLE002
ANOTHER_LONG_LINE = "Another long line, should just disable STYLE002 globally if you don't want it"
# nolint: STYLE002
YET_ANOTHER = "If you're suppressing the same rule many times, disable it in config"

# ❌ BAD: Suppressing legitimate errors
# nolint: PKG001
RDEPENDS:${PN} = "library-dev kernel-dev"
# Dev packages shouldn't be in runtime dependencies!

# ❌ BAD: No alternative considered
# nolint: INSTALL004
do_install:append() {
    mkdir -p ${D}/usr/local/bin
    cp ${WORKDIR}/tool ${D}/usr/local/bin/
}
# Could use /usr/bin or /opt instead

---

## Why These Are Bad

1. **No explanation** - Future maintainers don't know why
2. **Blanket suppressions** - Hide real issues
3. **Security risks** - Ignored without review
4. **Technical debt** - Should fix, not suppress
5. **Repeated patterns** - Suggests config change needed
6. **Missing context** - No tracking or timeline
7. **Lazy coding** - Easier to suppress than fix

## What To Do Instead

1. **Fix the issue** - Most suppressions are avoidable
2. **Configure globally** - If rule doesn't apply to project
3. **Document thoroughly** - Explain why suppression is needed
4. **Track removal** - Link to issue tracker
5. **Get review** - Especially for security
6. **Consider alternatives** - Is there a better way?
