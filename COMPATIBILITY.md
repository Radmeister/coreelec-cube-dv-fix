# Compatibility and troubleshooting

The release image supports **Amazon Fire TV Cube 3rd generation (T7/gazelle)** running **22.0-Piers-samurihl_20260928164552**, Linux **5.15.196**, with this exact original kernel:

```
cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16
```

Patched image SHA256:

```
071498095ae2362caaea3ff052b3262fadd904fd37bd607128fc307b517e4b10
```

The installer checks hardware, release, running Linux version, payload checksum, and the complete existing kernel image. Matching a version label alone is insufficient. There is no force option.

## Other CoreELEC releases

Run **check**, keep its report, and stop if unmatched. The source patch may be adapted by a maintainer, but this repository currently supplies one compatible binary. Do not downgrade an otherwise working system solely on the assumption that every installation with a similar version string matches.

## Already installed, but Running fix is not Y

The file on disk may have been installed while the old kernel is still running. Reboot into CoreELEC and rerun status. `Running fix: Y` confirms the compiled correction is enabled; the correction counter may be zero at the menu and does not need to reach a specific value.

## SCP / SFTP errors

The helpers automatically retry with the legacy SCP protocol. If transfers still fail, confirm the Cube is booted into CoreELEC, SSH is enabled, the IP is correct, and your computer is on the same network. A wrong SSH password cannot be fixed by repeating installation.

## Host key changed after replacing/reinstalling a Cube

Verify that the address really belongs to the intended Cube. Follow SSH's host-key update instructions only after checking the device; the helpers do not disable host-key validation.

## Checksums or existing staging/backup errors

Stop and preserve the printed files/error. A damaged download needs a fresh release package. An incomplete or unexpected backup/staging file needs review; do not delete the only original backup just to make installation proceed. The helper refuses an unrelated kernel instead of overwriting it.

## Future updates

Reboots keep the fix. A CoreELEC update normally replaces the kernel. After updating, obtain a matching patched kernel or a build with the source correction included. This package intentionally refuses to install its older kernel on the new release.

## Recovery

Normal rollback requires a reachable CoreELEC SSH session and the backup created by this installer. Both computer guides include a rollback command.

If CoreELEC cannot boot, remote rollback cannot run. Use the verified `kernel.before-install.img` saved on your computer with the recovery procedure appropriate to that Cube's CoreELEC storage layout. The original image belongs at `/flash/kernel.img` on the CoreELEC boot volume, but how that volume is mounted from another system depends on the installation. Keep the backup and ask for help with that layout rather than erasing the installation. This installer does not alter Fire OS, the bootloader, or boot priority.

## Scope of validation

The kernel correction has been tested on two Cubes with repeated normal Plex playback confirmed on the TV, plus controlled driver tests described in [TECHNICAL.md](TECHNICAL.md). Native Dolby Vision output, other SoCs, and a broad SDR/HDR regression suite have not been validated. This is a kernel replacement: keep the verified backup until normal use is confirmed.
