# Example: Proper Inline Suppression Usage
#
# This file demonstrates good practices for using inline suppressions.
# Each suppression includes a clear comment explaining why it's needed.

SUMMARY = "Example meta-package for bundling dependencies"
DESCRIPTION = "This meta-package provides a convenient way to install \
a collection of related tools. It doesn't have its own source code."

# Meta-packages don't have traditional source or license because they
# just bundle other packages. All dependencies have their own licenses.
# nolint: LICENSE001, MANDATORY002
RDEPENDS:${PN} = " \
    tool-one \
    tool-two \
    tool-three \
"

# HOMEPAGE not applicable for internal meta-packages
# Tracked in JIRA-5678 to add proper project page
# nolint: BESTPRACTICE003
AUTHOR = "Platform Team <platform@example.com>"

# Temporary during migration from old syntax to new syntax
# Will be fixed in sprint 2024-Q2 as part of JIRA-1234
# nolint: DEPRECATED001
PACKAGECONFIG_append = " extra-features"

# This is a valid use of /usr/local for optional add-on tools
# that are not part of the core system. Discussed with architect.
# nolint: INSTALL004
do_install:append() {
    install -d ${D}/usr/local/example-addons
    install -m 0755 ${WORKDIR}/addon.sh ${D}/usr/local/example-addons/
}

# Git repository uses 'trunk' instead of 'master' - can't change upstream
# Verified with security team - repository is internal and trusted
# nolint: REPRO001
SRC_URI = "git://internal-git.example.com/legacy-tool.git;branch=trunk;protocol=https"
SRCREV = "1234567890abcdef1234567890abcdef12345678"

# Using eval here is safe - the variable is fully controlled and validated
# Alternative approaches were considered but this is the cleanest solution
# Code reviewed by senior developer (see PR #456)
# nolint: SECURITY006
python do_custom_task() {
    import subprocess
    # Validated input - only alphanumeric characters allowed
    safe_var = d.getVar('VALIDATED_INPUT').strip()
    if safe_var.isalnum():
        subprocess.run(['tool', safe_var], check=True)
}

# Package architecture is MACHINE specific because we include
# kernel modules that are compiled for specific hardware
# Documented in architecture decision record ADR-0042
# nolint: COMPAT002
PACKAGE_ARCH = "${MACHINE_ARCH}"

# This recipe intentionally provides -dev files in the main package
# because it's a development SDK bundle, not a runtime component
# nolint: PKG001
FILES:${PN} = " \
    ${libdir}/*.so \
    ${includedir}/* \
    ${datadir}/pkgconfig \
"
