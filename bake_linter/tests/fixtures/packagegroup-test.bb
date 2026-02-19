# A packagegroup recipe - special type that doesn't need SRC_URI
SUMMARY = "Test packagegroup"
LICENSE = "CLOSED"

inherit packagegroup

RDEPENDS:${PN} = "\
    bash \
    coreutils \
    util-linux \
"
