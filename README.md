# CoreELEC Fire TV Cube Dolby Vision raised-black fix

A community fix for **Dolby Vision playback that looks correct after a reboot, then develops raised blacks on later plays** on the **Fire TV Cube 3rd generation**.

The fix corrects a mismatch in the Amlogic host video driver's VADJ1 brightness stage. Dolby Vision processing remains active, including the tested **DV-to-HDR10 output for TVs without Dolby Vision**. It works with the existing Dolby module; replacing `dovi.ko` or reloading it on every play is unnecessary.

**Confirmed working on two Cubes.** This is an independent community package, not an official CoreELEC or SamuriHL release.

## The problem and why this fixes it

The driver could report that its brightness stage was bypassed while that stage remained enabled in hardware. On the same paused frame, enabling the correction changed the captured dark background from **Y21 back to the known-good Y17**, with Dolby Vision processing and HDR10 output still active.

**[Read the illustrated investigation and maintainer guide](TECHNICAL.md)** for our actual before/after captures, raw readings, the kernel code paths responsible, the exact fix, and how to integrate and validate it in another build. The numbers are internal capture codes, not nits.

## Download and install

**[Download Cube-DV-Fix-v1.1.zip](https://github.com/Radmeister/coreelec-cube-dv-fix/releases/download/v1.1/Cube-DV-Fix-v1.1.zip)** from the [release page](https://github.com/Radmeister/coreelec-cube-dv-fix/releases/tag/v1.1). Extract it, then follow your computer's guide:

| Computer | Guide |
|---|---|
| Windows 10 / 11 | **[Windows tutorial](WINDOWS.md)** — PowerShell helper, automatic checks and backups |
| Mac | **[Mac tutorial](MACOS.md)** — Terminal helper, automatic checks and backups |
| Linux / manual SSH | [Manual method](MANUAL.md) |

Choose the named **Cube-DV-Fix-v1.1.zip** asset. GitHub's automatic **Source code (zip)** download contains the repository source, without the kernel image, and cannot install the fix on its own.

## Supported build

| Item | Required |
|---|---|
| Device | Amazon Fire TV Cube **3rd generation**, T7 / gazelle |
| CoreELEC | **22.0-Piers-samurihl_20260928164552** |
| Linux | **5.15.196** |
| Original kernel | Exact SHA256 checked automatically; see [compatibility](COMPATIBILITY.md) |

**Other builds need their own matching kernel.** The helper saves a compatibility report and refuses an unmatched device or image. Do not edit version files or bypass the checks. This binary is not for an AM6B Plus or an older-generation Cube. The source patch is available for maintainers to adapt to other builds.

## What changes

- Installs one compatible, patched kernel image and verifies it.
- Saves the original kernel on **both the Cube and your computer** before installing.
- Preserves the existing Dolby module, device tree, library, Plex setup, and display/audio settings.
- Provides a checked rollback command.

No capture configuration, luminance adjustment, new Dolby module, bootloader change, or playback script is required. Keep the settings appropriate to your own TV; our 2,150-nit test setting is not a requirement.

## Reboots and updates

**The fix survives reboots.** A CoreELEC update normally replaces the kernel and may remove the fix. After an update, use a package built for that release or a maintainer build containing the source patch. Never copy this older kernel into a newer CoreELEC release. Boot order is preserved.

## Details and source

- [Technical findings and validation](TECHNICAL.md)
- [Compatibility, recovery and troubleshooting](COMPATIBILITY.md)
- [Source and build instructions](BUILDING.md)
- [The tested common_drivers patch](0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch)
- [Release history](CHANGELOG.md)
- [Credits and licensing](NOTICE.md)

For an unsupported build, open an issue with its exact CoreELEC version, Cube generation, and the saved `check-report.json`. Review it before posting: it contains build/hardware details and a timestamp. Do not post SSH passwords, Plex tokens, media URLs, personal backups, or full unsanitized logs. An issue is a request for investigation, not a promise of a new binary.
