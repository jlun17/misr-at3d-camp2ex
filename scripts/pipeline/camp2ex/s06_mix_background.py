"""Background scatterers: ERA5 Rayleigh atmosphere mixed with MISR aerosol.

Usage: python s06_mix_background.py <aerosol_suffix> <out_suffix>
       e.g. 0p200 ''      -> MIXTURE_default_ERA5.nc
            0p150 _0p150  -> MIXTURE_default_ERA5_0p150.nc

Source: notebooks/preprocessing/mix_background.ipynb (HEAD), cells idx 0, 2-4 (Default section).
Conda env: at3d_pure_k9
Inputs: data/interim/ATMOS_ERA5_CAMP2Ex_RF17_default.nc (s04), data/interim/AEROSOL_MISR_21_<aod>.nc (s05)
Output: data/interim/MIXTURE_default_ERA5<out_suffix>.nc
Changes: data paths are OUT_ROOT-relative. Input and output names are set to atmos_file =
         ATMOS_ERA5_CAMP2Ex_RF17_default.nc and MIXTURE_default_ERA5*.nc [FLAGGED]. No committed notebook
         state uses these names. The recipe was confirmed numerically: the V11 MIXTURE_default_ERA5*
         extinction equals ATMOS_ERA5 + AEROSOL_MISR_21_* to within 7e-18. See PIPELINE.md.
"""
from collections import OrderedDict
import at3d
import xarray as xr
import numpy as np
import sys

from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
INTERIM_DATA = OUT_ROOT / 'data' / 'interim'

## INPUT
aerosol_file = INTERIM_DATA / f'AEROSOL_MISR_21_{sys.argv[1]}.nc'
atmos_file = INTERIM_DATA / 'ATMOS_ERA5_CAMP2Ex_RF17_default.nc'

## OUTPUT
out_file = INTERIM_DATA / f'MIXTURE_default_ERA5{sys.argv[2]}.nc'

aerosol = xr.load_dataset(aerosol_file)
atmos = xr.load_dataset(atmos_file)

assert np.array_equal(aerosol.x.data, atmos.x.data)
assert np.array_equal(aerosol.y.data, atmos.y.data)
assert np.array_equal(aerosol.z.data, atmos.z.data)

background_optical_scatterers = OrderedDict()
merged_properties = at3d.medium.mix_optical_properties(
    atmos,
    aerosol,
    asymmetry_tol=0.02,
    maxnphase=40
)

ones = np.ones((atmos.dims['x'], atmos.dims['y'], atmos.dims['z']))
if((np.array_equal(atmos.ssalb.data, ones)) & (np.array_equal(aerosol.ssalb.data, ones))):
    merged_properties['ssalb'] = (['x', 'y', 'z'], ones)

merged_properties.to_netcdf(out_file)
