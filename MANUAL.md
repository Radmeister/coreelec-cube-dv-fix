# Manual SSH method

The [Mac](MACOS.md) and [Windows](WINDOWS.md) helpers automate the checked computer backup and are recommended. These commands are for users comfortable with SSH. Use only the [supported build](COMPATIBILITY.md).

Extract the named release ZIP on your computer. In a terminal in the `Cube-DV-Fix` folder, replace `192.168.1.50` with your Cube's actual IP:

```text
ssh root@192.168.1.50 "mkdir -p /storage/Cube-DV-Fix"
scp cube-dv-fix.py kernel.pq-guard.img root@192.168.1.50:/storage/Cube-DV-Fix/
ssh root@192.168.1.50 "python3 /storage/Cube-DV-Fix/cube-dv-fix.py check"
```

If SCP reports SFTP is unavailable, retry with `scp -O ...`. Use the Cube's own password, not a password copied from a guide.

If the result is **READY TO INSTALL**, copy the original kernel to a new computer backup folder that you will keep:

```text
scp root@192.168.1.50:/flash/kernel.img kernel.before-install.img
```

Verify its SHA256 equals:

```
cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16
```

Use `Get-FileHash .\kernel.before-install.img -Algorithm SHA256` on Windows, `shasum -a 256 kernel.before-install.img` on Mac, or `sha256sum kernel.before-install.img` on Linux. Stop if it differs. Then:

```text
ssh root@192.168.1.50 "python3 /storage/Cube-DV-Fix/cube-dv-fix.py install"
```

Only if installation succeeds, save the Cube manifest and request the reboot:

```text
scp root@192.168.1.50:/storage/cube-dv-fix-backup/manifest.json manifest.json
ssh root@192.168.1.50 "sync; systemctl reboot"
```

Return to CoreELEC and check:

```text
ssh root@192.168.1.50 "python3 /storage/Cube-DV-Fix/cube-dv-fix.py status"
```

Expect **ALREADY INSTALLED**, **Running fix: Y**. Validate repeated DV playback visually.

To undo an install made by this package:

```text
ssh root@192.168.1.50 "python3 /storage/Cube-DV-Fix/cube-dv-fix.py rollback"
```

Only after rollback succeeds, send the reboot command again. Review [recovery](COMPATIBILITY.md#recovery) if SSH is unavailable.
