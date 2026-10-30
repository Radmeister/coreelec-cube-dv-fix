# Windows 10 / 11 tutorial

You need a Windows computer and supported Cube on the same network, the Cube running CoreELEC, and its SSH password. This helper runs on Windows; Python is used on the Cube and does not need to be installed on Windows.

## 1. Download and extract

Download **[Cube-DV-Fix-v1.1.zip](https://github.com/Radmeister/coreelec-cube-dv-fix/releases/download/v1.1/Cube-DV-Fix-v1.1.zip)**. In File Explorer, right-click the ZIP, choose **Extract All**, and extract into Downloads. Open the resulting `Cube-DV-Fix` folder. It should directly contain:

```
run-on-windows.ps1
cube-dv-fix.py
kernel.pq-guard.img
```

Keep all files together. If the kernel is missing, you downloaded GitHub's repository source ZIP instead of the named release package.

## 2. Check that Windows has OpenSSH Client

Open **PowerShell** or **Windows Terminal → Windows PowerShell** as your normal user and run:

```powershell
ssh -V
Get-Command scp.exe
```

If either is missing, use Windows **Settings → Optional features → Add/View features → OpenSSH Client → Install**. Windows versions differ in where Optional features appears; Settings search can find it. You only need **OpenSSH Client**.

Alternatively, in an **Administrator PowerShell** window:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

Close that window and reopen normal PowerShell after installation. See [Microsoft's OpenSSH installation instructions](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) if Windows requests installation files or a restart. No Windows SSH server or inbound firewall rule is needed.

## 3. Prepare the Cube

Boot into CoreELEC. Enable **SSH** in the CoreELEC Services settings if needed. Find the Cube's IP under **Settings → System information → Network**. Use this Cube's own SSH password.

Stop playback before installing. Confirm the [supported build](COMPATIBILITY.md); the helper will also check it automatically.

## 4. Run the compatibility check

In PowerShell, change to the extracted folder. For the usual Downloads location:

```powershell
Set-Location "$HOME\Downloads\Cube-DV-Fix"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-on-windows.ps1 check
```

If you extracted elsewhere, open that folder in File Explorer, click the address bar, type `powershell`, and press Enter. Then run the second command above.

`-ExecutionPolicy Bypass` applies only to this new PowerShell process; it does not permanently change the computer's policy. Review the included script first. A managed work computer may prohibit unsigned scripts; use an approved computer or the manual SSH method instead of changing organizational policy.

Enter the Cube's IP and a label such as `living-room`. A first SSH connection may ask you to confirm the Cube's host key. Check that the address is your Cube. Password characters do not appear as you type.

**Windows may ask for the password several times.** The script uses separate SSH/SCP commands and does not store a password or create an authentication key.

| Result | Next step |
|---|---|
| `READY TO INSTALL` | Continue below. |
| `ALREADY INSTALLED` | Skip installation; check status. |
| `DIFFERENT BUILD OR HARDWARE — NO INSTALL` | Stop. Save the printed report folder for a matching package. |
| Transfer or checksum error | Nothing should be installed; resolve the error before retrying. |

The check uploads the installer and kernel to `/storage/Cube-DV-Fix` and saves a report. It does not change boot files/settings or reboot.

## 5. Install

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-on-windows.ps1 install
```

Enter the same Cube address and label. The helper repeats the compatibility check, saves and verifies the original kernel on the computer, makes a second verified backup on the Cube, installs the fix, and requests a reboot. The TV may go blank when Kodi stops.

If the Cube boots into Fire OS, return to CoreELEC in your usual way. The installer does not change boot priority.

## 6. Verify after reboot

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-on-windows.ps1 status
```

Look for **`ALREADY INSTALLED`** and **`Running fix: Y`**. Then play an affected Dolby Vision video, stop it, and play it again. Compare the same dark scene; repeat with another episode.

Computer backups/reports are saved in:

```
Downloads\Cube-DV-Fix-Backups\<label-IP-date-id>\
```

Keep `kernel.before-install.img`, `manifest.json`, and the reports. The Cube backup is `/storage/cube-dv-fix-backup/kernel.original.img`.

## Rollback

For an installation made with this distribution package, while the Cube is reachable in CoreELEC:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-on-windows.ps1 rollback
```

This verifies and restores the original Cube backup, then requests a reboot. It refuses to overwrite an unrelated/newer kernel or a different OS release. If CoreELEC cannot boot, see [recovery](COMPATIBILITY.md#recovery).

## Optional command parameters

Avoid retyping the address and label, while keeping normal password prompts:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\run-on-windows.ps1 check -CubeAddress 192.168.1.50 -CubeLabel living-room
```

`-ReportsDirectory "D:\Cube-Backups"` changes the computer backup location. Each run gets a new subfolder.

The Windows helper has automated mock-transfer tests run under PowerShell 7, including paths containing spaces. It has not yet been tested end to end on a physical Windows computer. The underlying Cube installer and identical kernel have been deployed successfully to two real Cubes; report Windows-specific problems through Issues.
