# Source and building

The downloadable installer image is for one exact release. Maintainers can use the [small driver patch](0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch) independently; newer branches may need rebasing and validation.

Read the [illustrated investigation and integration checklist](TECHNICAL.md) for the hardware/cache mismatch, raw evidence, exact gates, and validation steps before adapting the patch.

## Pinned source inputs

| Component | Repository and revision |
|---|---|
| Linux | [CoreELEC/linux-amlogic `69e87fa40cc3a04bf91d92e388d2787a2efcb50c`](https://github.com/CoreELEC/linux-amlogic/tree/69e87fa40cc3a04bf91d92e388d2787a2efcb50c) |
| Common drivers | [CoreELEC/common_drivers `f9af0b41d6da6cd501b75c33bf44338693195d96`](https://github.com/CoreELEC/common_drivers/tree/f9af0b41d6da6cd501b75c33bf44338693195d96), plus all 17 release patches |
| CoreELEC recipes | [SamuriHL/CoreELEC `7848ac1ca3fb05da7791037aa281bb00acd71ca1`](https://github.com/SamuriHL/CoreELEC/tree/7848ac1ca3fb05da7791037aa281bb00acd71ca1), tag `v22.0-samurihl-20260928164552` |
| GPIO source input | [CoreELEC/bl30 `e08015a6b17fda21260c7a9c8bfd3c98ee2a61c1`](https://github.com/CoreELEC/bl30/tree/e08015a6b17fda21260c7a9c8bfd3c98ee2a61c1) |

Observed runtime userspace `BUILD_ID` was `f91de323452d3bac428dbb677719be78a7404437`. It is recorded separately from the recipe commit. The installer additionally requires the exact original image hash.

Download **Cube-DV-Fix-source-v1.1.tar.gz** from [Releases](https://github.com/Radmeister/coreelec-cube-dv-fix/releases/tag/v1.1). It contains the complete pinned upstream archives, all release/device patches, the tested configuration, build/packaging scripts, export reference, and license/provenance files. It excludes private media, credentials, settings, the proprietary Dolby module, and computer/Cube backups. The CoreELEC recipe archive retains its upstream source declarations for the unchanged original initramfs.

## Apply the patch in an existing common_drivers checkout

After applying that release's own patches:

```bash
git apply --check /path/to/0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch
git apply /path/to/0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch
```

This changes the host media driver compiled into the kernel. It is not a patch to the Dolby module binary.

## Recreate the kernel source and compile

The tested environment was **ARM64 Ubuntu 24.04**, **clang/lld 17.0.6**, `ARCH=arm64 LLVM=1 LLVM_IAS=1`, with the matching installed kernel configuration. A Linux VM can be used. Install normal kernel-build dependencies (make, a C compiler, clang/lld/LLVM, flex, bison, libssl development headers, libelf development headers, bc, GNU awk, patch, Python 3, and lzop). LLVM 17.0.6 must be first in `PATH`; the source bundle does not redistribute the compiler. A cross build on x86 Linux needs its own verified ARM64 toolchain setup.

From the extracted source bundle:

```bash
python3 prepare-source.py ./build
bash build-kernel.sh ./build/kernel
python3 verify-exports.py SOURCE/Cube.Module.symvers ./build/kernel/Module.symvers
```

Preparation verifies the archive checksums, extracts Linux/common_drivers/BL30/recipes, applies the release's 17 driver patches and xpadneo device patch, applies this correction, copies the tested `.config`, and checks that the resulting `amve.c` is byte-identical to the tested source. The build script regenerates the GPIO header using the release's GNU-awk function, then builds `Image.lzo`. No BL30 firmware or bootloader is installed.

Review all configuration changes and compiler warnings. The original validation matched all 15,886 exported CRCs; four codec_mm section-mismatch warnings were also present in the unchanged baseline. Matching CRCs alone is not a complete behavioral compatibility proof.

## Pack a test image

Obtain the exact supported original `/flash/kernel.img` from your own Cube, preserving a separate backup. The original boot image is not distributed as a recovery backup. Then:

```bash
python3 pack-boot.py /path/to/original-kernel.img ./build/kernel/arch/arm64/boot/Image.lzo ./kernel.test.img
```

The packer verifies the original checksum and Android boot-v0 layout/ID, roundtrips the original container exactly, preserves its initramfs and load addresses, and replaces the LZO kernel and required header fields only. The initramfs is about 7 MiB and is unchanged by the correction. Build timestamps/tool paths can change the rebuilt kernel's checksum; this is source reproducibility guidance, not a claim of deterministic byte-for-byte builds.

The public installer accepts **only the published, tested image hash**. A locally rebuilt image will need separate compatibility review and controlled testing; do not change the public installer's hashes to bypass that review. Never install a kernel compiled for this old release into a different release.

## Helper tests

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 test_installer.py
PYTHONDONTWRITEBYTECODE=1 python3 test_helpers.py
```

The helper suite uses local SSH/SCP stubs and synthetic kernel fixtures. It never connects to a Cube. Set `CUBE_TEST_PWSH` to a PowerShell 7 executable to include Windows-helper tests. Windows PowerShell 5.1 syntax is retained, but physical Windows deployment remains pending.
