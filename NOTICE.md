# Credits and licensing

This community package builds on **CoreELEC**, its Linux/Amlogic driver contributors, **SamuriHL's release and patches**, and Kodi. Their existing copyright notices and licenses remain in effect.

The kernel correction targets `CoreELEC/common_drivers`, not the proprietary Dolby module. [thatfunkymunki's open-source Dolby reconstruction](https://github.com/thatfunkymunki/common_drivers) helped make deeper investigation possible, but no Dolby module is distributed or required by this package.

The new installer/helpers and original documentation in this repository are provided under **GPL-2.0-only**; see [LICENSE](LICENSE). The driver patch modifies existing GPL-licensed kernel code under that code's existing license. Upstream source archives include their own licensing notices. No license to proprietary Dolby software is granted.

This is an independent community project. It is not an official release or endorsement by SamuriHL, Team CoreELEC, Amazon, Samsung, or Dolby. The current binary is limited to the exact build documented in [COMPATIBILITY.md](COMPATIBILITY.md).

Complete pinned kernel/driver source inputs, release patches, configuration, and preparation/build scripts are supplied as the separate **Cube-DV-Fix-source-v1.1.tar.gz** release asset. Maintainers can also use the small source patch directly. See [BUILDING.md](BUILDING.md).
