# A recipe with multiple issues for testing the linter

# Issue: LICENSEX is a typo (LICENSE002)
LICENSEX = "MIT"

# Issue: Missing SUMMARY/DESCRIPTION (MANDATORY001)
# Issue: Missing LICENSE (LICENSE001)
# Issue: Missing LIC_FILES_CHKSUM (LICENSE003)

# Issue: Deprecated _append syntax (DEPRECATED001)
RDEPENDS_${PN} += "foo"

# Issue: Deprecated _prepend syntax (DEPRECATED001)
SRC_URI_prepend = "file://patch1.patch "

# Issue: HTTP instead of HTTPS (SECURITY001)
SRC_URI = "http://insecure-site.com/bad-recipe-1.0.tar.gz"

# Issue: No checksum for remote file (SECURITY002)

# Issue: Hardcoded path (STYLE003)
do_install() {
    install -d /usr/lib/myapp
    install -m 0755 myapp /usr/bin/myapp
}

# Issue: Overly permissive chmod (SECURITY003)
do_configure:append() {
    chmod 777 ${S}/scripts/*
}

# Issue: Duplicate inherit (STYLE006)
inherit autotools
inherit pkgconfig
inherit autotools

# Issue: Empty variable assignment (STYLE005)
EXTRA_OECONF = ""

# TODO: Fix this later (STYLE004 if enabled)
# FIXME: This is broken
