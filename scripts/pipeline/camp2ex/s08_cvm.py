"""Cloud volume mask from the LCL, MISR cloud-top heights and space carving.

Usage: python s08_cvm.py <region> [<region> ...]
  7                  -> CVM_LCL_CTH_SC_R7.nc                (LCL & CTH & SC; default, aerosol, periodic, surf4p0)
  0 1 2 3 4 5 6 7    -> CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc  (unconstrained; input to s09)

Source: notebooks/preprocessing/CVM_LCL_CTH_SC.ipynb at git a29d0eb, cells idx 1, 2, 4, 6, 8, 11, 15.
        cloud_regions was toggled by hand in cell idx 15 (the commented alternatives there).
Conda env: at3d_pure_k9
Inputs: data/V11/AT3D_OBS_bbox_..._H1400_U1p3_V2p4.nc (s07), data/interim/RTG_default.nc (s03),
        data/interim/MISR_CTH_O105254_P117_R01100_X17950900_18002600_Y0193600_0245300.nc (s02)
Output: data/V11/CVM_LCL_CTH_SC_R<regions>.nc
Changes: data paths are OUT_ROOT-relative; cloud_regions is a command-line argument; plotting and the
         summary table are dropped.
"""
import xarray as xr
import numpy as np
from scipy.interpolate import griddata
import sys
import os
import at3d
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT))

from src.utils.util import load_sensor_dict
import src.CoordinateTransform as ct

obs_file = OUT_ROOT / 'data' / 'V11' / 'AT3D_OBS_bbox_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712_H1400_U1p3_V2p4.nc'
obs = load_sensor_dict(obs_file)

rte_grid = xr.load_dataset(OUT_ROOT / 'data' / 'interim' / 'RTG_default.nc')

## Lifting Condensation Level
lcl = 0.4 # km
lcl_cvm = np.zeros((rte_grid.sizes['x'], rte_grid.sizes['y'], rte_grid.sizes['z']))
lcl_cvm[:,:,rte_grid.z.data >= lcl] = 1
lcl_cvm = lcl_cvm.astype(int)

## Cloud Top Height
opacity_bias = 120 # m
# Transform SOM to AT3D coordinates
cth = xr.load_dataset(OUT_ROOT / 'data' / 'interim' / 'MISR_CTH_O105254_P117_R01100_X17950900_18002600_Y0193600_0245300.nc')
transform = ct.CoordinateTransform(
    17976750.0,
    219450.0,
    1.655084388740932,
    17600,
    17600
)
X, Y = np.meshgrid(cth.som_x, cth.som_y, indexing='ij')
Xp, Yp = transform.SOM2AT3D(X, Y)
cth['x'] = (['som_x', 'som_y'], Xp/1000)
cth['y'] = (['som_x', 'som_y'], Yp/1000)
cth['CloudTopHeight'] = (cth.CloudTopHeight + opacity_bias) / 1000

# Create the new grid
at3d_x, at3d_y = np.meshgrid(rte_grid.x.data, rte_grid.y.data, indexing='ij')

# Flatten the original grid and data
coarse_points = np.array([cth.x.data.flatten(), cth.y.data.flatten()]).T
coarse_cth = cth.CloudTopHeight.data.flatten()

# Mask out NaN values
mask = coarse_cth > -5
coarse_points = coarse_points[mask]
coarse_cth = coarse_cth[mask]

# Interpolate the data onto the new grid
cth_interp = griddata(coarse_points, coarse_cth, (at3d_x, at3d_y), method='linear')

cth_on_rte_grid = rte_grid.z.data[np.searchsorted(rte_grid.z.data, cth_interp, side='right')]

cth_on_rte_grid = np.expand_dims(cth_on_rte_grid, axis=-1)
cth_cvm = (rte_grid.z.data <= cth_on_rte_grid).astype(int)

## Space Carving
brf_thresholds = [0.120, 0.076, 0.054, 0.044, 0.040, 0.045, 0.052, 0.068, 0.092]
agreement = (0, 2/9)

masked_sensors = at3d.containers.SensorsDict()
for i, sensor in enumerate(obs['MISR']['sensor_list']):
    sensor_copy = sensor.copy(deep=True)
    mask = np.zeros(sensor.dims['nrays'])
    mask[sensor_copy.brf.data > brf_thresholds[i]] = 1
    sensor_copy['cloud_mask'] = (['nrays'], mask)
    masked_sensors.add_sensor('MISR', sensor_copy)

space_carver = at3d.space_carve.SpaceCarver(rte_grid, bcflag=3)
sc_cvm = space_carver.carve(masked_sensors, agreement=agreement, linear_mode=False)

## Cloud volume mask
cvm = rte_grid.copy(deep=True)
cvm['lcl'] = (['x','y','z'], lcl_cvm)
cvm['cth'] = (['x','y','z'], cth_cvm)
cvm['sc'] = sc_cvm.mask
cvm['encoded'] = (cvm.lcl * 1) + (cvm.cth * 2) + (cvm.sc * 4)
# Swap the 3's and 4's...
tmp = cvm.encoded.copy(deep=True).data
new_encoded = cvm.encoded.copy(deep=True).data
new_encoded[tmp == 3] = 4
new_encoded[tmp == 4] = 3
cvm['encoded'] = (['x','y','z'], new_encoded)
cvm['encoded'].attrs['description'] = '(LCL * 1) + (CTH * 2) + (SC * 4); then swap the 3s and 4s.'

cvm_final = np.zeros_like(lcl_cvm)
cloud_regions = [int(r) for r in sys.argv[1:]]

cloud_regions.sort()
for r in cloud_regions:
    cvm_final[cvm.encoded.data == r] = 1
cvm['cloud_volume_mask'] = (['x','y','z'], cvm_final.astype(int))
filename = 'CVM_LCL_CTH_SC_R' + '_'.join([str(num) for num in cloud_regions]) + '.nc'
outfile = OUT_ROOT / 'data' / 'V11' / filename
cvm.to_netcdf(outfile)
