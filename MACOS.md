# Mac tutorial

Use a Mac on the same network as the supported Cube. Boot the Cube into CoreELEC, stop playback, enable SSH in CoreELEC Services if necessary, and find its address in **Settings → System information → Network**. Have that Cube's SSH password ready.

## Download

Extract **[Cube-DV-Fix-v1.1.zip](https://github.com/Radmeister/coreelec-cube-dv-fix/releases/download/v1.1/Cube-DV-Fix-v1.1.zip)** into Downloads. The folder `Cube-DV-Fix` should directly contain `run-on-mac.sh`, `cube-dv-fix.py`, and `kernel.pq-guard.img`.

Use the named release asset, not GitHub's automatic Source code ZIP.

## Check

Open Terminal:

```bash
bash "$HOME/Downloads/Cube-DV-Fix/run-on-mac.sh" check
```

Enter the IP and a label such as `living-room`. The first connection may ask you to confirm the Cube's SSH host key. Confirm the address belongs to your Cube. Password characters are not displayed as you type.

The helper uploads two files, saves a compatibility report, and leaves boot files/settings unchanged. It does not reboot.

- **READY TO INSTALL:** continue.
- **ALREADY INSTALLED:** skip install and check status.
- **DIFFERENT BUILD OR HARDWARE — NO INSTALL:** stop. Keep `check-report.json` from the computer folder printed by the helper. A matching kernel is needed.

## Install and reboot

```bash
bash "$HOME/Downloads/Cube-DV-Fix/run-on-mac.sh" install
```

The helper checks compatibility again, verifies an original-kernel backup on both Mac and Cube, installs, and requests a reboot. The TV may briefly go blank as Kodi stops.

If it boots into Fire OS, return to CoreELEC normally. The helper preserves boot order.

## Verify

After CoreELEC is back:

```bash
bash "$HOME/Downloads/Cube-DV-Fix/run-on-mac.sh" status
```

Look for **ALREADY INSTALLED** and **Running fix: Y**. Play an affected Dolby Vision episode twice, comparing the same dark scene after stopping/restarting. Repeat with another episode.

Backups/reports are in `~/Downloads/Cube-DV-Fix-Backups/<label-IP-date>/`. Keep `kernel.before-install.img`, `manifest.json`, and the reports. The Cube backup is `/storage/cube-dv-fix-backup/kernel.original.img`.

The helper reuses one SSH connection during a run and saves no password. It closes that connection when it exits. A new run normally asks again.

## Rollback

```bash
bash "$HOME/Downloads/Cube-DV-Fix/run-on-mac.sh" rollback
```

This restores the verified original from a backup made by this distribution installer and requests a reboot. It refuses an unrelated/newer kernel or different OS release. See [recovery and compatibility](COMPATIBILITY.md) if the Cube cannot be reached.

For a custom computer backup location, set `CUBE_DV_REPORTS_DIR` when running the helper. Keep your original backup through future updates; a new OS release needs its own matching patched kernel.
