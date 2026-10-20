"""MISR radiances and geometry in the older MISR_OBS format (input to the Fig B1 observation file).

Source: notebooks/preprocessing/MISR_preprocess1.ipynb at git 8277215^ (deleted in 8277215), cells idx 0-6.
Conda env: misr (MisrToolkit)
Inputs: data/raw/MISR/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{DF..DA}_F03_0024.hdf,
        data/raw/MISR/MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf
Output: data/interim/MISR_OBS_CAMP2Ex_RF17_default.nc
Changes: data paths are OUT_ROOT-relative.
"""
import MisrToolkit as mtk
import numpy as np
import xarray as xr

from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
RAW_DATA = OUT_ROOT / 'data' / 'raw'
INTERIM_DATA = OUT_ROOT / 'data' / 'interim'


def nearest_sample(lat, lon, path, resolution):
    region = mtk.MtkRegion(lat,lon, 1, 1, "km")
    lats, lons = region.snap_to_grid(path, resolution).create_latlon()
    lats = lats.ravel()
    lons = lons.ravel()
    lat_diff = lats - lat
    lon_diff = lons - lon
    D = (lat_diff**2 + lon_diff**2)**0.5
    return lats[np.argmin(D)], lons[np.argmin(D)]

## INPUT
path = 117
orbit = 105254
database = RAW_DATA / 'MISR'
cameras = ['DF', 'CF', 'BF', 'AF', 'AN', 'AA', 'BA', 'CA', 'DA']
lat, lon = nearest_sample(19.266, 119.724, path, 17600)

## OUTPUT
out_file = INTERIM_DATA / 'MISR_OBS_CAMP2Ex_RF17_default.nc'

grp_general = 'MISR_AM1_GRP_ELLIPSOID_GM_P{:d}_O{:d}_{}_F03_0024.hdf'
gmp_general = 'MISR_AM1_GP_GMP_P{}_O{}_F03_0013.hdf'
region = mtk.MtkRegion(lat, lon, 8.8*3, 8.8*3, "km")
lat275, lon275 = region.snap_to_grid(path, 275).create_latlon()
lat17600, lon17600 = region.snap_to_grid(path, 17600).create_latlon()
assert lat17600.shape[0] % 2 == 1
assert lon17600.shape[0] % 2 == 1
i_center_lat = int((lat17600.shape[0] - 1) / 2)
j_center_lon = int((lon17600.shape[1] - 1) / 2)

"""
At each MISR sample coordinate, angles are reported in Local North (LN)
coordinates. That is, +x points North, +y points East, and +z points into the
Earth and is normal to the ellipsoid. Azimuthal angles are measured in the
usuial way: from +x in the direction of +y first. Solar zenith angle is
measured from the +z axis while viewing zenith angles are measured from the -z
axis. Solar and viewing angles are reported in the direction of photon travel.
Solar - away from the sun. View - into the sensor.

References:
https://asdc.larc.nasa.gov/documents/misr/DPS_v33_RevM.pdf
https://eospso.gsfc.nasa.gov/sites/default/files/atbd/atbd-misr-03.pdf
"""
gmp_file = database / gmp_general.format(path, orbit)
gmp_grid = mtk.MtkFile(str(gmp_file)).grid('GeometricParameters')
SZA = gmp_grid.field('SolarZenith').read(region).data()
SAA = gmp_grid.field('SolarAzimuth').read(region).data()
VZA = np.zeros(shape=(len(cameras), lat17600.shape[0], lat17600.shape[1]))
VAA = np.zeros(shape=(len(cameras), lat17600.shape[0], lat17600.shape[1]))
for i, c in enumerate(cameras):
    VZA[i,:,:] = gmp_grid.field('{}Zenith'.format(c.lower().capitalize())).read(region).data()
    VAA[i,:,:] = gmp_grid.field('{}Azimuth'.format(c.lower().capitalize())).read(region).data()
SZA_center = SZA[i_center_lat, j_center_lon]
SAA_center = SAA[i_center_lat, j_center_lon]
VZA_center = VZA[:, i_center_lat, j_center_lon]
VAA_center = VAA[:, i_center_lat, j_center_lon]

grp_file = [database / grp_general.format(path, orbit, c.upper()) for c in cameras]
brf = np.zeros(shape=(len(cameras), lat275.shape[0], lat275.shape[1]))
for i, f in enumerate(grp_file):
    brf[i,:,:] = mtk.MtkFile(str(f)).grid('RedBand').field('Red Brf').read(region).data()

misr_obs = xr.Dataset(
                data_vars = {
                    'brf': (['camera', 'y275', 'x275'], brf),
                    'lat275': (['y275', 'x275'], lat275),
                    'lon275': (['y275', 'x275'], lon275),
                    'lat17600': (['y17600', 'x17600'], lat17600),
                    'lon17600': (['y17600', 'x17600'], lon17600),
                    'SZA': (['y17600', 'x17600'], SZA),
                    'SAA': (['y17600', 'x17600'], SAA),
                    'VZA': (['camera', 'y17600', 'x17600'], VZA),
                    'VAA': (['camera', 'y17600', 'x17600'], VAA),
                    'VZA_center': (['camera'], VZA_center),
                    'VAA_center': (['camera'], VAA_center),
                    'SZA_center': SZA_center,
                    'SAA_center': SAA_center,
                    'center_lat': region.center[0],
                    'center_lon': region.center[1],
                },
                coords = {
                    'camera': cameras
                },
                attrs = {
                    'orbit': orbit,
                    'path': path,
                    'blocks': region.block_range(path),
                }
)
misr_obs.to_netcdf(out_file)
