"""Extract MISR radiances, geometry, cloud-top heights and cloud motion over the RF17 scene.

Source: notebooks/preprocessing/MISR_preprocessA.ipynb (HEAD), cells idx 1-3.
Conda env: misr (MisrToolkit)
Inputs: data/raw/MISR/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{DF..DA}_F03_0024.hdf,
        data/raw/MISR/MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf,
        data/raw/MISR/MISR_AM1_TC_CLOUD_P117_O105254_F01_0001.hdf
Outputs: data/interim/MISR_{RAD,GEO,CTH,CMV}_O105254_<regionID>.nc
Changes: data paths are OUT_ROOT-relative.
"""
import MisrToolkit as mtk
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT))

from src.MISR import hdf2xr, grp2xr

## Set data path
misr_data_dir = OUT_ROOT / 'data' / 'raw' / 'MISR'

## Specify MISR parameters
path = 117
orbit = 105254
cameras = ['DF', 'CF', 'BF', 'AF', 'AN', 'AA', 'BA', 'CA', 'DA']

## Define geographic region
center_lat = 19.266267063099104
center_lon = 119.72428415176724
region = mtk.MtkRegion(center_lat, center_lon, 8.8*3, 8.8*3, "km")

## Load MISR red band images
imagery = grp2xr(misr_data_dir, path, orbit, cameras, region)
imagery.to_netcdf(OUT_ROOT / 'data' / 'interim' / f'MISR_RAD_O{orbit:06}_{imagery.regionID}.nc')

## Load geometric parameters
gmp_file = misr_data_dir / f'MISR_AM1_GP_GMP_P{path}_O{orbit}_F03_0013.hdf'
field_list_solar = ['SolarZenith', 'SolarAzimuth']
field_list_vza = [f'{c.lower().capitalize()}Zenith' for c in cameras]
field_list_vaa = [f'{c.lower().capitalize()}Azimuth' for c in cameras]
field_list = field_list_solar + field_list_vza + field_list_vaa
gmp = hdf2xr(gmp_file, 'GeometricParameters', field_list, region)
gmp.to_netcdf(OUT_ROOT / 'data' / 'interim' / f'MISR_GEO_O{orbit:06}_{gmp.regionID}.nc')

## Load CTH
tc_cloud_file = misr_data_dir / f'MISR_AM1_TC_CLOUD_P{path:03d}_O{orbit:06d}_F01_0001.hdf'
cth = hdf2xr(tc_cloud_file, 'Stereo_1.1_km', ['CloudTopHeight', 'StereoDerivedCloudMask'], region)
cth.to_netcdf(OUT_ROOT / 'data' / 'interim' / f'MISR_CTH_O{orbit:06}_{cth.regionID}.nc')

## Load CMV
cmv = hdf2xr(tc_cloud_file, 'Motion_17.6_km', ['CloudTopHeightOfMotion', 'CloudMotionNorthward', 'CloudMotionEastward'], region)
cmv.to_netcdf(OUT_ROOT / 'data' / 'interim' / f'MISR_CMV_O{orbit:06}_{cmv.regionID}.nc')
