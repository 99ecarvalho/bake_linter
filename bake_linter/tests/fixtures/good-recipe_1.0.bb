# A well-formed Yocto recipe with all required elements
SUMMARY = "Example good recipe demonstrating best practices"
DESCRIPTION = "This recipe demonstrates proper BitBake recipe structure \
with all required variables and proper syntax."
HOMEPAGE = "https://example.com/good-recipe"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=abc123def456"

SRC_URI = "https://example.com/good-recipe-${PV}.tar.gz"
SRC_URI[sha256sum] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

S = "${WORKDIR}/good-recipe-${PV}"

inherit autotools pkgconfig

DEPENDS = "zlib openssl"
RDEPENDS:${PN} = "bash"

do_install:append() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/myapp ${D}${bindir}/myapp
}

FILES:${PN} += "${bindir}/myapp"
