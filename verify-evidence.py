#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Recalculate the published near-black readings. No hardware or network access."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parent
    report = json.loads((root / 'evidence-readings.json').read_text())
    roi = report['roi']
    fmt = report['format']
    for sample in report['samples']:
        for asset in sample['files'].values():
            content = (root / asset['path']).read_bytes()
            if len(content) != asset['bytes'] or hashlib.sha256(content).hexdigest() != asset['sha256']:
                raise RuntimeError('Evidence checksum/length mismatch: ' + asset['path'])
        raw = (root / sample['files']['nv12']['path']).read_bytes()
        if len(raw) < fmt['luma_offset_bytes'] + fmt['luma_plane_bytes']:
            raise RuntimeError('Incomplete luma plane')
        values = sorted(raw[fmt['luma_offset_bytes'] + y * fmt['luma_stride_bytes'] + x]
                        for y in range(roi['y_start_inclusive'], roi['y_end_exclusive'])
                        for x in range(roi['x_start_inclusive'], roi['x_end_exclusive']))
        actual = {'minimum': values[0], 'median': values[len(values) // 2], 'maximum': values[-1]}
        if len(values) != roi['samples'] or actual != sample['luma']:
            raise RuntimeError('Published readings differ: ' + sample['label'])
        print(sample['label'] + ': ' + str(len(values)) + ' samples, ' + str(actual) +
              ', VADJ1=' + sample['hardware_register']['value'])
    print('Both image/buffer checksums and all published ROI readings match.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyError, ValueError, RuntimeError) as error:
        sys.exit('STOP: ' + str(error))
