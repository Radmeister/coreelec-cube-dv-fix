#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Prepare the exact tested source from the separate release source bundle."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

INPUTS = {
    'kernel.tar.gz': '9f46105d6ceb1047cb9ca28b55b0ad8dea42a783d59e33fac200b784fe138580',
    'common-drivers.tar.gz': '1859998ce9e1bd2369a76211fe85a51f284dc7b164d3296054b5d68fe6acbeb2',
    'bl30.tar.gz': 'cc79de0b7e0829648ce950579236b26ee4e129a01d9e75cd55efc828126fa3a6',
    'CoreELEC-recipes.tar.gz': 'b881334cc7da9cbf6338360311c290325a3b270bf22ee6935ee9c5514fb68252',
}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def main():
    if len(sys.argv) != 2:
        raise RuntimeError('Use: python3 prepare-source.py NEW_BUILD_DIRECTORY')
    root = Path(__file__).resolve().parent
    destination = Path(sys.argv[1]).resolve()
    if destination.exists():
        raise RuntimeError('Build directory already exists; choose a new directory.')
    for name, expected in INPUTS.items():
        if digest(root / 'archives' / name) != expected:
            raise RuntimeError('Source archive checksum differs: ' + name)
    destination.mkdir(parents=True)
    kernel = destination / 'kernel'
    for name, target in [('kernel.tar.gz', kernel),
                         ('common-drivers.tar.gz', kernel / 'common_drivers'),
                         ('bl30.tar.gz', destination / 'bl30'),
                         ('CoreELEC-recipes.tar.gz', destination / 'CoreELEC')]:
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(['tar', '-xf', str(root / 'archives' / name),
                        '--strip-components=1', '-C', str(target)], check=True)
    patches = sorted((root / 'SOURCE/release-patches').glob('*.patch'))
    if len(patches) != 17:
        raise RuntimeError('Expected all 17 release media-driver patches.')
    for patch in patches:
        subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)],
                       cwd=kernel / 'common_drivers', check=True)
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i',
                    str(root / 'SOURCE/linux-04-xpadneo.patch')], cwd=kernel, check=True)
    subprocess.run(['patch', '--batch', '--forward', '-p1', '-i',
                    str(root / '0001-amvecm-t7-reconcile-vadj1-dv-bypass.patch')],
                   cwd=kernel / 'common_drivers', check=True)
    amve = kernel / 'common_drivers/drivers/media/enhancement/amvecm/amve.c'
    if digest(amve) != 'f896c6dbc29f53c1b58fd17a85bc48202e59b5fa61ec0136a89cbec547571db4':
        raise RuntimeError('Prepared driver differs from the tested source.')
    shutil.copyfile(root / 'SOURCE/kernel.config', kernel / '.config')
    print('Prepared exact tested driver source: ' + str(kernel))
    print('Next: bash build-kernel.sh ' + str(kernel))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit('STOP: ' + str(error))
