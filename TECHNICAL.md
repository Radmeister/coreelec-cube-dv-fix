# Findings and validation

## Cause reproduced on the Cube

The affected stage is **VADJ1 in the Amlogic host media driver**, outside `dovi.ko`.

`video_adj1_brightness_store()` and `video_adj1_contrast_store()` can enable VADJ1 independently of `pq_cfg_cur.vadj1_en`. Kodi's Amlogic codec setup writes these controls. In the affected state, the software cache still says VADJ1 is disabled for DV bypass, but the hardware enable bit is set. `vpp_pq_ctrl_config()` can skip disabling the stage because its cached value already equals the request.

On the same paused frame:

| State / action | VPP_VADJ1_MISC | Cached vadj1_en | Internal captured background |
|---|---|---|---|
| Good, bypassed | `0x2` | `0` | Y17 |
| Write brightness zero, already zero | `0x3` | `0` | Y21 |
| Native bypass refresh | `0x2` | `0` | Y17 |
| Repeat zero write | `0x3` | `0` | Y21 |
| Repeat native refresh | `0x2` | `0` | Y17 |

`VPP_VADJ1_MISC` is register `0x3280`; bit 0 enables the stage. Other bits were preserved. The values above are **internal 8-bit capture codes, not nits or calibrated measurements of the HDMI wire**. The visual symptom and controlled on/off reversal support the causal mechanism. The precise ordering of every earlier playback startup was not traced.

The native refresh used existing `debug_bypass_vpp_pq` states 2, 1, then 0, restoring automatic mode. It was an investigative control, not the installed workaround.

## Source correction

The [patch](0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch) updates `drivers/media/enhancement/amvecm/amve.c`. In both applicable VADJ1 write branches it reconciles hardware with the requested disabled state when all of these hold:

- T7 CPU, VPP instance 0;
- STB Dolby Vision bypass: `dv_pq_bypass == 2`;
- requested VADJ1 enable is zero;
- the actual hardware enable bit is still set;
- the new `pq_vadj1_sync` control is enabled, which is the default.

It reuses the driver's existing register-write path. It does not change Dolby-generated lookup tables, HDR metadata, brightness offsets, or luminance targets. No module reload or per-play service is installed.

Runtime diagnostics:

```
/sys/module/aml_media/parameters/pq_vadj1_sync
/sys/module/aml_media/parameters/pq_vadj1_resyncs
```

The first should be `Y`; the second counts reconciliation requests, not independently measured unique transitions. Users do not need to change either value.

## Validation on the first Cube

| Boot | Dolby module / test | Result |
|---|---|---|
| 1 | Source-built module; 6 measured starts, 6 deliberate zero-brightness challenges | All corrected captures Y17; guard off Y21, back on Y17 |
| 2 | Source-built module; 4 starts without capture, then one measured start | Fifth start Y17; first four were not individually measured |
| 3 | Original proprietary module; 3 measured starts, 3 zero-brightness challenges | All corrected captures Y17; off Y21, on Y17 |
| 4 | Source-built module restored; 2 measured starts | Both Y17 |

Total: 16 starts, **12 measured starts**, and 9 measured deliberate challenges across four boots. Driver/library tracing was off during these runs. Afterwards, the user visually confirmed two episodes played twice each through Plex, with normal blacks on all four plays.

All **15,886** freshly generated exported kernel CRCs matched the original Cube. There were no new compiler/modpost warnings against the unchanged baseline. Android boot-v0 header/load addresses and the exact initramfs were preserved; only kernel size and standard boot ID changed in the header. Original roundtrip and LZO decompression checks passed.

## Second Cube

The distribution installer was applied to another Cube on the same exact release with the **original proprietary Dolby module preserved**. Backup, installation, reboot, image checksum, and running guard were verified. The user then confirmed normal playback: “perfect. working great.” No exact playback count was recorded for that confirmation.

## Earlier tests that did not fix it

- Original versus reconstructed Dolby module alone.
- Genuine normal Dolby-module unload/reload, native control-path reinitialization, host unregister/register, and Kodi restart.
- Engine toggles, LUT-refresh request, refresh-rate changes, and 1,000-nit peak target.
- Bypassing the soundbar and connecting directly to the TV.
- Native Kodi versus Plex playback; both could develop the fault.
- Continuous capture. It did not prevent the fault.

Generated Dolby settings, matrices, LUTs, metadata, and input fingerprints matched between good and raised samples. Frame matching later showed the lift concentrated near black, with midtones and brighter details unchanged in those internal comparisons. These findings redirected the investigation to host-side picture processing.

## Limits

The tested output was DV processing with HDR10 HDMI output to a non-DV Samsung TV. Native DV output, other SoCs/VPPs, and a broad SDR/HDR regression suite remain unvalidated. Normal menu/non-DV recovery was checked: the original VADJ1 enable state returned outside the gated DV bypass condition. Capture comparisons do not independently measure the HDMI signal or the TV's light output.

The working AM6B Plus reference was kept unchanged throughout the experiments.
