"""MISR observations as AT3D sensors, wind-corrected and registered to 1.4 km.

Usage: python s07_obs.py <u> <v> [suffix]
  1.3 2.4         -> ..._H1400_U1p3_V2p4.nc  (default; git a29d0eb)
  1.9 5.1 ATM     -> ..._H1400_ATM.nc        (cloud-motion tracks; git 993661c)
  0.7 -0.3 ATP    -> ..._H1400_ATP.nc
  -0.3 2.7 CTM    -> ..._H1400_CTM.nc
  2.9 2.1 CTP     -> ..._H1400_CTP.nc
The track winds are the saved output of notebooks/investigation/pre_retrieval/MISR_CloudMotionVectors.ipynb
(cell idx 5). That notebook needs a TC_CLOUD v2026 file that is not in data/raw, so the values are given
here directly.

Source: notebooks/preprocessing/MISR2AT3D_OBS.ipynb at git a29d0eb (default) and 993661c (tracks),
        cells idx 1, 2, 4, 6, 9, 11, 13, 15, 16, 17. The two commits differ only in u and v.
Conda env: at3d_pure_k9
Inputs: data/interim/MISR_RAD_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712.nc,
        data/interim/MISR_GEO_O105254_P117_R17600_X17959150_17994350_Y0201850_0237050.nc (s02)
Output: data/V11/AT3D_OBS_bbox_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712_H1400_<U.._V..|suffix>.nc
Changes: data paths are OUT_ROOT-relative; u, v and an optional output suffix are command-line arguments
         (the suffix replaces the manual rename of the track files); the self-test block under
         `if __name__ == "__main__"` in cell idx 16, prints and plotting are dropped. save_sensor_dict
         never overwrites (it appends _1, _2, ...), so an existing output is an error here.
"""
import numpy as np
import xarray as xr
from pathlib import Path
import os
import sys
import at3d

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT))

from src.utils.util import save_sensor_dict
import src.CoordinateTransform as ct

orbit = 105254
path = 117
imagery = xr.load_dataset(OUT_ROOT / 'data' / 'interim' / f'MISR_RAD_O{orbit:06d}_P{path:03d}_R00275_X17950487_18003012_Y0193187_0245712.nc')
gmp = xr.load_dataset(OUT_ROOT / 'data' / 'interim' / f'MISR_GEO_O{orbit:06d}_P{path:03d}_R17600_X17959150_17994350_Y0201850_0237050.nc')

## 1. Azimuth angle coordiante transform
for var in gmp.data_vars:
    if('Azimuth' in var):
        gmp[var] = (90 - gmp[var]) % 360
        gmp[var].attrs['description'] = 'Azimuth relative to local East going counter-clockwise'

## 2. SOM x and y coordinate transform
origin = gmp.isel(som_x=1, som_y=1)
transform = ct.CoordinateTransform(
    origin.som_x.data,
    origin.som_y.data,
    origin.gamma.data,
    17600,
    17600
)
print(transform)

X, Y = np.meshgrid(imagery.som_x, imagery.som_y, indexing='ij')
Xp, Yp = transform.SOM2AT3D(X, Y)

imagery['x'] = (['som_x', 'som_y'], Xp)
imagery['y'] = (['som_x', 'som_y'], Yp)
imagery['z'] = (['som_x', 'som_y'], np.zeros_like(X))

## 3. Merge position (x, y, z) and viewing geometry
phi = np.array([origin[f'{c.lower().capitalize()}Azimuth'].data for c in imagery.camera.data])
mu = np.array([origin[f'{c.lower().capitalize()}Zenith'].data for c in imagery.camera.data])

tmp_shape = (imagery.sizes['camera'], imagery.sizes['som_x'], imagery.sizes['som_y'])
imagery['x'] = (['camera', 'som_x', 'som_y'], np.broadcast_to(imagery.x.data, tmp_shape))
imagery['y'] = (['camera', 'som_x', 'som_y'], np.broadcast_to(imagery.y.data, tmp_shape))
imagery['z'] = (['camera', 'som_x', 'som_y'], np.broadcast_to(imagery.z.data, tmp_shape))

phi = np.array([origin[f'{c.lower().capitalize()}Azimuth'].data for c in imagery.camera.data])
phi = np.radians(phi)
imagery['phi'] = (['camera', 'som_x', 'som_y'], np.broadcast_to(phi[:, None, None], tmp_shape))

mu = np.array([origin[f'{c.lower().capitalize()}Zenith'].data for c in imagery.camera.data])
mu = np.cos(np.radians(mu))
imagery['mu'] = (['camera', 'som_x', 'som_y'], np.broadcast_to(mu[:, None, None], tmp_shape))

## 4. Wind correction
u = float(sys.argv[1]) # m/s
v = float(sys.argv[2]) # m/s

imagery['deltat'] = (['camera'], np.array([-204, -144, -91, -45, 0, 45, 91, 144, 204]))

imagery['x'] = imagery.x - u*imagery.deltat
imagery['y'] = imagery.y - v*imagery.deltat

## 6. Create AT3D sensor objects
def register_to_height(x, y, z, mu, phi, h):
    """
    Transform x, y coordinates to be registered at height h.

    Parameters:
    -----------
    x, y, z : array-like
        Original coordinates
    mu : array-like
        Cosine of zenith angle
    phi : array-like
        Azimuthal angle in radians
    h : float
        Target height for registration

    Returns:
    --------
    x_new, y_new : arrays
        Transformed coordinates at height h
    """
    # Calculate the distance to travel along the viewing direction
    # to reach height h
    dz = h - z

    # sin(zenith) = sqrt(1 - mu^2)
    sin_zenith = np.sqrt(1 - mu**2)

    # Displacement in x and y directions
    dx = (dz / mu) * sin_zenith * np.cos(phi)
    dy = (dz / mu) * sin_zenith * np.sin(phi)

    # New coordinates
    x_new = x + dx
    y_new = y + dy
    z_new = h * np.ones_like(z)

    return x_new, y_new, z_new


def filter_rays_bbox(
    x, y, z, mu, phi,
    xmin, xmax,
    ymin, ymax,
    zmin, zmax,
):
    """
    Return a boolean mask selecting rays that intersect an axis-aligned
    bounding box (AABB).

    Ray parametric form:
        P(t) = origin + t * direction
    where direction is derived from the physics convention:
        mu  – cosine of the polar angle θ  (mu = cos θ)
        phi – azimuthal angle φ  (radians)

    So the unit-direction components are:
        dx = sqrt(1 - mu²) * cos(phi)
        dy = sqrt(1 - mu²) * sin(phi)
        dz = mu

    The slab method computes, for each axis, the interval [t_near, t_far]
    at which the ray is inside that axis's slab.  A ray hits the box when
    the intersection of all three intervals is non-empty:
        max(t_near_x, t_near_y, t_near_z) <= min(t_far_x, t_far_y, t_far_z)
    and that overlap has t_far >= 0  (box is not entirely behind the origin).

    Parameters
    ----------
    x, y, z : array-like, shape (N,)
        Ray origin coordinates.
    mu : array-like, shape (N,)
        Cosine of the polar angle (−1 ≤ mu ≤ 1).
    phi : array-like, shape (N,)
        Azimuthal angle in radians.
    xmin, xmax : float   – bounding box x extents
    ymin, ymax : float   – bounding box y extents
    zmin, zmax : float   – bounding box z extents

    Returns
    -------
    mask : np.ndarray, dtype=bool, shape (N,)
        True where the ray intersects the AABB.
    """
    x   = np.asarray(x,   dtype=float)
    y   = np.asarray(y,   dtype=float)
    z   = np.asarray(z,   dtype=float)
    mu  = np.asarray(mu,  dtype=float)
    phi = np.asarray(phi, dtype=float)

    # ------------------------------------------------------------------ #
    # Direction vectors from (mu, phi)                                     #
    # ------------------------------------------------------------------ #
    sin_theta = np.sqrt(np.clip(1.0 - mu**2, 0.0, 1.0))
    dx = sin_theta * np.cos(phi)
    dy = sin_theta * np.sin(phi)
    dz = mu.copy()

    # ------------------------------------------------------------------ #
    # Slab intersections for each axis                                     #
    # ------------------------------------------------------------------ #
    t_near = np.full(x.shape, -np.inf)
    t_far  = np.full(x.shape,  np.inf)

    for origin, direction, lo, hi in (
        (x, dx, xmin, xmax),
        (y, dy, ymin, ymax),
        (z, dz, zmin, zmax),
    ):
        # Parallel rays (direction ≈ 0)
        parallel = direction == 0.0
        inside   = parallel & (origin >= lo) & (origin <= hi)
        outside  = parallel & ~inside

        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = np.where(~parallel, (lo - origin) / direction, np.nan)
            t2 = np.where(~parallel, (hi - origin) / direction, np.nan)

        # Ensure t1 is always the near hit and t2 is the far hit
        t_axis_near = np.minimum(t1, t2)
        t_axis_far  = np.maximum(t1, t2)

        # Parallel & outside: no intersection possible – push interval
        # to ±inf so the final test will fail for those rays.
        t_axis_near = np.where(outside,  np.inf, t_axis_near)
        t_axis_far  = np.where(outside, -np.inf, t_axis_far)

        # Parallel & inside: no constraint on t from this axis
        t_axis_near = np.where(inside, -np.inf, t_axis_near)
        t_axis_far  = np.where(inside,  np.inf, t_axis_far)

        t_near = np.maximum(t_near, t_axis_near)
        t_far  = np.minimum(t_far,  t_axis_far)

    # ------------------------------------------------------------------ #
    # A ray hits the box when the overlap is valid and not entirely        #
    # behind the ray origin (t_far >= 0).                                  #
    # ------------------------------------------------------------------ #
    mask = (t_near <= t_far) & (t_far >= 0.0)
    return mask


h = 1400
wavelength = 0.67

bbox = dict(xmin=0, xmax=17600, ymin=0, ymax=17600, zmin=0, zmax=h)

obs = at3d.containers.SensorsDict()
for c in imagery.camera.data:
    img_tmp = imagery.sel(camera=c)
    x = np.ravel(img_tmp.x.data)
    y = np.ravel(img_tmp.y.data)
    z = np.ravel(img_tmp.z.data)
    mu = np.ravel(img_tmp.mu.data)
    phi = np.ravel(img_tmp.phi.data)
    cond = filter_rays_bbox(x, y, z, mu, phi, **bbox)
    x, y, z = register_to_height(x, y, z, mu, phi, h)
    mu0 = np.cos(np.radians(origin.SolarZenith.data))
    I = np.ravel(img_tmp.brf.data) / np.pi
    sensor = at3d.sensor.make_sensor_dataset(
        x[cond]/1000,
        y[cond]/1000,
        z[cond]/1000,
        mu[cond],
        phi[cond],
        'I',
        wavelength,
        fill_ray_variables = True
    )
    sensor['I'] = (['nrays'], I[cond])
    sensor['I'].attrs['description'] = 'I = BRF_MISR / pi = I /  (mu0 * F_0)'
    sensor['brf'] = (['nrays'], np.ravel(img_tmp.brf.data)[cond])
    sensor['brf'].attrs['description'] = 'MISR BRF'
    sensor['mu0'] = mu0
    sensor['mu0'].attrs['long_name'] = 'cosine of the solar zenith angle'
    sensor['SAA'] = origin.SolarAzimuth.data
    sensor['SAA'].attrs['description'] = origin.SolarAzimuth.description
    sensor['SAA'].attrs['units'] = 'degrees'
    sensor.attrs['name'] = c
    sensor.attrs['wind_correction_u'] = u
    sensor.attrs['wind_correction_v'] = v
    obs.add_sensor('MISR', sensor)

outfilename = f'AT3D_OBS_bbox_O{orbit:06d}_{imagery.regionID}_H{int(h):d}_U{str(u).replace(".","p")}_V{str(v).replace(".","p")}.nc'
if len(sys.argv) > 3:
    outfilename = f'AT3D_OBS_bbox_O{orbit:06d}_{imagery.regionID}_H{int(h):d}_{sys.argv[3]}.nc'
outfile = OUT_ROOT / 'data' / 'V11' / outfilename
assert not outfile.exists(), f'{outfile} exists; save_sensor_dict would write a renamed copy instead'
outfile.parent.mkdir(parents=True, exist_ok=True)
save_sensor_dict(outfile, obs)
