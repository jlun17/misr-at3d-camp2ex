"""Unconstrained cloud volume mask with the top two levels cleared.

Source: data/V11/gen_CVM_unc_mod.ipynb (untracked; copied here as gen_CVM_unc_mod.ipynb), cells idx 0-2.
Conda env: at3d_pure_k9
Input: data/V11/CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc (s08)
Output: data/V11/CVM_unconstrained_mod.nc
Changes: './' paths replaced with OUT_ROOT/data/V11.
"""
import xarray as xr
import numpy as np
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
V11_DATA = OUT_ROOT / 'data' / 'V11'

cvm_ds = xr.load_dataset(V11_DATA / 'CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc')

cvm = cvm_ds.cloud_volume_mask.data
cvm[:,:,-2:] = 0
cvm_ds['cloud_volume_mask'] = (['x', 'y', 'z'], cvm)
cvm_ds.to_netcdf(V11_DATA / 'CVM_unconstrained_mod.nc')
