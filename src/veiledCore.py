from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

import numpy as np
from tqdm.auto import tqdm
from scipy.interpolate import RegularGridInterpolator
from multiprocessing import Pool, cpu_count
import math
from ExperimentSet import ExperimentSet

exset = ExperimentSet(Path(sys.argv[1]))
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])

for r in exset.retrievals.values():
    # Parallelized optical-path computation using a RegularGridInterpolator
    cloud = r.solvers_retrieval[0.67].medium['cloud'].copy(deep=True)
    nx, ny, nz = cloud.dims['x'], cloud.dims['y'], cloud.dims['z']
    min_optical_path = np.zeros((nx, ny, nz))

    # Prepare interpolator (3D) and grid vectors
    x_vals = cloud.x.data
    y_vals = cloud.y.data
    z_vals = cloud.z.data
    ext_vals = cloud.extinction.data
    ext_interp = RegularGridInterpolator((x_vals, y_vals, z_vals), ext_vals, bounds_error=False, fill_value=0.0)

    # Build list of points (i,j,k,x,y,z) where there is non-zero extinction
    idxs = np.array(np.where(ext_vals > 0.0)).T
    points = [(int(i), int(j), int(k), float(x_vals[i]), float(y_vals[j]), float(z_vals[k])) for i, j, k in idxs]

    # Worker initializer to set global interpolator and parameters in each worker process
    def _worker_init(interp, n_directions, ext_threshold, step_size):
        global EXT_INTERP, N_DIRECTIONS, EXT_THRESHOLD, STEP_SIZE
        EXT_INTERP = interp
        N_DIRECTIONS = n_directions
        EXT_THRESHOLD = ext_threshold
        STEP_SIZE = step_size

    # Directional optical-path march using the global EXT_INTERP (3D interpolator)
    def _optical_path_directional(point_xyz, phi, max_steps=10000):
        x0, y0, z0 = point_xyz
        phi_rad = math.radians(phi)
        dx_dir = math.cos(phi_rad)
        dy_dir = math.sin(phi_rad)
        step = STEP_SIZE
        optical_path = 0.0
        x, y = x0, y0
        for _ in range(max_steps):
            # Interpolate extinction at current 3D location; outside grid returns 0.0
            ext = float(EXT_INTERP([x, y, z0]))
            if ext < EXT_THRESHOLD:
                break
            optical_path += ext * step
            x += dx_dir * step
            y += dy_dir * step
        return optical_path

    def _optical_path_all_directions(point_xyz):
        phis = np.linspace(0, 360, N_DIRECTIONS, endpoint=False)
        paths = [_optical_path_directional(point_xyz, phi) for phi in phis]
        return float(np.min(paths))

    def _compute_point(item):
        i, j, k, x, y, z = item
        minp = _optical_path_all_directions((x, y, z))
        return (i, j, k, minp)

    # Choose step size based on grid spacing
    step_size = min(abs(x_vals[1] - x_vals[0]), abs(y_vals[1] - y_vals[0])) * 0.5
    n_directions = 8
    ext_threshold = 0.3
    nprocs = max(1, cpu_count() - 1)

    if nprocs > 1 and len(points) > 0:
        with Pool(processes=nprocs, initializer=_worker_init, initargs=(ext_interp, n_directions, ext_threshold, step_size)) as pool:
            results = list(tqdm(pool.imap_unordered(_compute_point, points), total=len(points)))
    else:
        # Fallback single-process loop
        _worker_init(ext_interp, n_directions, ext_threshold, step_size)
        results = [ _compute_point(p) for p in tqdm(points) ]

    # Fill results into array
    for i, j, k, minp in results:
        min_optical_path[i, j, k] = minp

    cloud['min_optical_path'] = (['x','y','z'], min_optical_path)

    cloud.to_netcdf(r.root_dir / 'min_optical_path.nc')
