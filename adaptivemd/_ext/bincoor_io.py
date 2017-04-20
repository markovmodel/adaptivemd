# IO for ACEMD
# write and read for bincoor format
from __future__ import print_function, absolute_import

import numpy as np

# this is taken from HTMD code so MAKE SURE we are allowed to use this!


# htmd/htmd/molecule/writers.py

def BINCOORwrite(coords, filename):
    import struct
    natoms = np.array([coords.shape[0]])
    with open(filename, 'wb') as f:
        dat = coords[:, :, 0]
        dat = dat.reshape(dat.shape[0] * 3).astype(np.float64)

        fmt1 = 'i' * natoms.shape[0]
        bin1 = struct.pack(fmt1, *natoms)
        fmt2 = 'd' * dat.shape[0]
        bin2 = struct.pack(fmt2, *dat)
        f.write(bin1)
        f.write(bin2)


# htmd/htmd/molecule/writers.py

def BINCOORread(filename):
    import struct
    with open(filename, 'rb') as f:
        dat = f.read(4)
        fmt = 'i'
        natoms = struct.unpack(fmt, dat)[0]
        dat = f.read(natoms * 3 * 8)
    fmt = 'd' * (natoms * 3)
    coords = struct.unpack(fmt, dat)
    coords = np.array(coords, dtype=np.float32).reshape((natoms, 3, 1))
    return coords

