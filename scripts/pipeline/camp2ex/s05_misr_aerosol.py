"""Aerosol optical properties on the RTE grid from MISR mixture 21 at a given AOD.

Usage: python s05_misr_aerosol.py <aod>       (the pipeline runs 0.150, 0.200 and 0.250)

Source: notebooks/preprocessing/MISR_aerosol.ipynb (HEAD), cells idx 0, 1, 3-5 (Default section),
        with src/preprocess/MISR_aerosol_mixture.py.
Conda env: at3d_pure_k9
Inputs: data/interim/RTG_default.nc (s03), data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc (s01)
Output: data/interim/AEROSOL_MISR_21_<aod>.nc
Changes: data paths are OUT_ROOT-relative; aod is a command-line argument.
         leg_ord = 20 instead of the notebook's 166 [FLAGGED]. No committed notebook state records
         the value used on 2025-07-16; 20 is read from the V11 input files, which hold 21 Legendre
         terms. See PIPELINE.md.
"""
from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
INTERIM_DATA = OUT_ROOT / 'data' / 'interim'
RAW_DATA = OUT_ROOT / 'data' / 'raw'

import sys
sys.path.append(str(PROJECT_ROOT))

import src.preprocess.MISR_aerosol_mixture as asol
import xarray as xr
import numpy as np
import at3d

## INPUT
wavelength = 0.67
aod = float(sys.argv[1])
mixture = 21
leg_ord = 20

rte_grid_file = INTERIM_DATA / 'RTG_default.nc'

## OUTPUT
aod_str = '{:.3f}'.format(aod).replace('.', 'p')
out_file = INTERIM_DATA / 'AEROSOL_MISR_{}_{}.nc'.format(mixture, aod_str)

rte_grid = xr.load_dataset(rte_grid_file)

aerosol_optical_properties = asol.get_MISR_mixture_optical_properties(
    band=wavelength,
    mixture=mixture,
    aod=aod,
    rte_grid=rte_grid,
    acp_file=RAW_DATA / 'MISR' / 'MISR_AM1_ACP_MIXTURE_F06_0022.nc',
    legendre_order=leg_ord,
    g_tol=1e-2,
    res_tol=1
)
aerosol_optical_properties.to_netcdf(out_file)
