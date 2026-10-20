"""Radiative transfer grid, plus the older-format observation file used by Fig B1.

Source: notebooks/preprocessing/MISR_preprocess2.ipynb at git 8277215^ (deleted in 8277215), cells idx 0-2.
Conda env: at3d_k9 (the notebook kernel)
Inputs: data/interim/MISR_OBS_CAMP2Ex_RF17_default.nc (s02b)
Outputs: data/interim/RTG_default.nc (all V11 retrievals),
         data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc (Fig B1 only)
Changes: data paths are OUT_ROOT-relative.
         s = 1.5 instead of 0.67 [FLAGGED]. The existing AT3D_OBS_CAMP2Ex_RF17_default.nc (2025-07-16) holds
         u=0.856, v=1.232 = 1.5 m/s at 34.8 deg, the value in this notebook at git cd4a47d (2025-07-15);
         by 7b45453 (2025-07-18) it had moved on to 3.35. The wind does not affect RTG_default.nc.
"""
from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
INTERIM_DATA = OUT_ROOT / 'data' / 'interim'

import sys
sys.path.append(str(PROJECT_ROOT))

import xarray as xr
import numpy as np
import at3d
import src.preprocess.MISR_preprocess2 as pp
import src.utils.util as util

# INPUT
# MISR NetCDF File (from MISR_preprocess1)
misr_data_file = INTERIM_DATA / 'MISR_OBS_CAMP2Ex_RF17_default.nc'

# Observation wavelength
wavelength = 0.67

# Cloud motion wind vector
s = 1.5 # m/s
theta = 34.8 # degrees
u = s * np.sin(np.radians(theta)) # m/s
v = s * np.cos(np.radians(theta)) # m/s

# OUTPUT
rte_grid_outfile = INTERIM_DATA / 'RTG_default.nc'
obs_outfile = INTERIM_DATA / 'AT3D_OBS_CAMP2Ex_RF17_default.nc'

# Create radiative transfer grid (for the bounding box)
if(os.path.exists(rte_grid_outfile)):
    print('Grid exists already. Loaded from {}'.format(rte_grid_outfile))
    rte_grid = xr.load_dataset(rte_grid_outfile)
else:
    z = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4])
    rte_grid = at3d.grid.make_grid(0.275, 65, 0.275, 65, z)
    rte_grid.to_netcdf(rte_grid_outfile)
    print('Saved RTE grid to: {}'.format(rte_grid_outfile))

# Read in MISR data in Local North coordinates
misr_data_LN = xr.load_dataset(misr_data_file)

# Convert MISR data to ENU coordinates
misr_data_ENU = pp.LN2ENU(misr_data_LN)

# Horizontal shift to place origin at the corner of the rte grid (maintain centering)
misr_data_ENU['E'] = misr_data_ENU.E + np.max(rte_grid.x.data)/2
misr_data_ENU['E'] = misr_data_ENU.E.assign_attrs(units='km')
misr_data_ENU['N'] = misr_data_ENU.N + np.max(rte_grid.y.data)/2
misr_data_ENU['N'] = misr_data_ENU.N.assign_attrs(units='km')

# Project rays to the top of the domain
U2 = np.ones(misr_data_ENU.mu.data.shape)*np.max(rte_grid.z.data)
misr_data_ENU = pp.project_to_U2(misr_data_ENU, U2)

# Perform wind correction
misr_data_ENU = misr_data_ENU.assign_attrs(u=u, v=v)
misr_data_ENU['dt'] = (['camera'], -1*(np.array([0, 60, 113, 159, 204, 249, 295, 348, 408])-204))
misr_data_ENU['dt'] = misr_data_ENU.dt.assign_attrs(units='s')
misr_data_ENU['dt'] = misr_data_ENU.dt.assign_attrs(description='Time shift needed to register at AN camera')
misr_data_ENU['dE'] = misr_data_ENU.dt * u * 1e-3
misr_data_ENU['dE'] = misr_data_ENU.dE.assign_attrs(units='km')
misr_data_ENU['dN'] = misr_data_ENU.dt * v * 1e-3
misr_data_ENU['dN'] = misr_data_ENU.dN.assign_attrs(units='km')
misr_data_ENU['E2'] = misr_data_ENU.E2 + misr_data_ENU.dE
misr_data_ENU['N2'] = misr_data_ENU.N2 + misr_data_ENU.dN

# Calculate the maximum extent at oblique angles and pad
pad = 2 # km
min_extent, max_extent = pp.TOA_extent(rte_grid, misr_data_ENU)
min_extent = min_extent - pad
max_extent = max_extent + pad

# Store observations in a sensor dict
measurements = at3d.containers.SensorsDict()
for cam in misr_data_ENU.camera.data:
    measurements.add_sensor('MISR', pp.make_sensor(misr_data_ENU, cam, min_extent, max_extent, wavelength))

# Save measurements
util.save_sensor_dict(obs_outfile, measurements)
