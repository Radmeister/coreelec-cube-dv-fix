# Package verification

The v1.1 release keeps the exact kernel image confirmed working on two real Cubes. No new picture-processing change was made for public distribution.

Before publication:

- 14 Cube-installer tests passed against temporary files: compatibility refusal, backup verification, installation, rollback, damaged payload/backup, staging, mount restoration, and concurrent-change cases.
- 14 Mac-helper tests passed with local SSH/SCP substitutes.
- 14 Windows-helper tests passed under PowerShell 7.6.9 on macOS with local SSH/SCP substitutes: successful install with computer backup before activation, wrong-build refusal/report, install failure without reboot, corrupt backup refusal, idempotence, check/status, rollback, failed rollback, legacy SCP fallback, transfer failure, invalid input, and local payload corruption.
- Bash and PowerShell syntax checks passed.
- The published source-preparation script recreated byte-identical tested `amve.c` from the bundled pinned archives and release patches.
- The public boot-packing script recreated the published kernel image exactly from the original supported image and the tested LZO kernel.
- The export checker matched all 15,886 reference kernel exports.

These helper tests perform no real network operations. A physical Windows end-to-end installation is **not yet verified**. Windows PowerShell 5.1 compatibility is based on the script's syntax and supported commands; the automated execution above used PowerShell 7. See [TECHNICAL.md](TECHNICAL.md) for the separate hardware and picture validation.
