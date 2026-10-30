# Release history

## Documentation and evidence update — 30 October 2026

- Expanded the technical report with the original same-frame guard-off/on captures, raw NV12 buffers, ROI readings, source-code explanation and maintainer integration checklist.
- Added a standard-library script that verifies evidence hashes and recalculates the published Y21/Y17 measurements offline.
- Added a prominent problem/evidence link to the repository front page. The v1.1 kernel, patch and installer downloads are unchanged.

## v1.1 — 30 October 2026

- First public GitHub package, with Windows PowerShell helper and Windows/Mac/manual guides.
- Same tested kernel image and driver correction as the private v1.0 package.
- Helpers check the local image before connecting. Mac helper uploads only the two required files.
- Compatibility checks, verified backups on both computer and Cube, installation, status, and rollback.
- Source patch, corresponding kernel-source bundle, build inputs, and technical findings.
- Kernel confirmed working on two home Cubes. Windows helper tested with mocked transfers under PowerShell 7; physical Windows end-to-end testing remains pending.

## v1.0 — private distribution

Initial checked installer and Mac helper. First Cube passed controlled driver and visual tests; second Cube subsequently installed and visually confirmed working.
