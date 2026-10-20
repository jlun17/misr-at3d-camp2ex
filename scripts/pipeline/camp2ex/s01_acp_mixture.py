"""Convert the MISR aerosol climatology product (ACP) mixture table from HDF to netCDF.

Source: tmp/src_old/MISR_ACP_preprocess.ipynb (identical to git b3cf83e^:src_old/MISR_ACP_preprocess.ipynb),
        cells idx 0, 1, 3, 4.
Conda env: pyhdf (the notebook kernel was misr, which no longer has pyhdf)
Input:  data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.hdf
Output: data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc
Changes: '../data/MISR/' paths replaced with OUT_ROOT/data/raw/MISR.
"""
from pathlib import Path
import os
import numpy as np
from pyhdf.SD import SD, SDC
import xarray as xr

from pyhdf.HDF import HDF, HC
from pyhdf.VS import VS

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
MISR_DIR = OUT_ROOT / 'data' / 'raw' / 'MISR'

acp_file = str(MISR_DIR / 'MISR_AM1_ACP_MIXTURE_F06_0022.hdf')
sd = SD(acp_file, SDC.READ)
hdf = HDF(acp_file, HC.READ)
vs = VS(hdf)

mixture_data = vs.attach('Mixture Data')[:]
ssalb = np.zeros((4, len(mixture_data)))
angstrom = np.zeros(len(mixture_data))
for i in range(len(mixture_data)):
    ssalb[:, i] = mixture_data[i][5]
    angstrom[i] = mixture_data[i][9]

scatter_angle = sd.select('Scattering angle')[:]
phase = sd.select('Mixture Spectral Phase Functions')[:]
band = sd.select('Band')[:]
acp = xr.Dataset(
    data_vars=dict(
        phase=(['band', 'angle', 'mixture'], phase),
        ssalb=(['band', 'mixture'], ssalb),
        angstrom=(['mixture'], angstrom)
    ),
    coords=dict(
        band=band,
        angle=scatter_angle,
        mixture=np.arange(1,75)
    )
)
acp = acp.assign_coords(theta = np.radians(acp.angle))
acp['g_integrand'] = acp.phase * np.cos(acp.theta) * np.sin(acp.theta)
acp['g'] = 0.5 * acp.g_integrand.integrate('theta')
acp = acp.drop_vars('g_integrand')

acp['angle'] = acp.angle.assign_attrs(long_name='Scattering angle', units='degrees')
acp['band'] = acp.band.assign_attrs(long_name='Wavelength', units='um')
acp['theta'] = acp.theta.assign_attrs(long_name='Scattering angle', units='radians')

acp.to_netcdf(MISR_DIR / 'MISR_AM1_ACP_MIXTURE_F06_0022.nc')
