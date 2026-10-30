#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
from pathlib import Path
import sys


def load(path):
    return {fields[1]: fields[0].lower() for line in Path(path).read_text().splitlines()
            if len(fields := line.split()) >= 2}


if len(sys.argv) != 3:
    sys.exit('Use: python3 verify-exports.py REFERENCE.Module.symvers BUILT.Module.symvers')
reference, built = (load(path) for path in sys.argv[1:])
differences = {name: (crc, built.get(name)) for name, crc in reference.items()
               if built.get(name) != crc}
if not reference or differences:
    sys.exit('STOP: export CRC differences: ' + str(differences))
print('All ' + str(len(reference)) + ' reference export CRCs match.')
