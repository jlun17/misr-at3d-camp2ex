# conda vis2
"""Cache everything the iteration animation needs from the default V11 retrieval.

Loads iter000..iter{N-1} of the cold-start V11 default run (in parallel), and for each iteration stores the AT3D
forward-simulated MISR BRF images, the (thresholded) cloud extinction field, and
chi^2 (4% MISR uncertainty, as in notebooks/figures/chi2.ipynb). The MISR
observations, ray positions, and cloud volume mask are stored once.

Writes iteration_animation_frames/cache.pkl, which iteration_animation_render.py
reads, so restyling the animation never requires reloading the retrieval.

Usage:
    python iteration_animation_extract.py --niter 16 --workers 8
"""
import argparse
import pickle
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
sys.path.append(str(PROJECT_ROOT))

# V11/default is a restart from default_obsolete/iter030 (identical config otherwise),
# so the cold start from the uniform first guess lives in default_obsolete
EXPERIMENT = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11' / 'default_obsolete'
CACHE = HERE / 'iteration_animation_frames' / 'cache.pkl'
EXTINCTION_TH = [0.3, np.inf]  # same threshold as the publication figures


def misr_S_1(y):
    return np.diag(1 / (0.04 * y)**2)


def load_iteration(i):
    from src.Retrieval import Retrieval
    r = Retrieval(EXPERIMENT)
    r.load_retrieval(i, extinction_th=EXTINCTION_TH)
    cloud = r.solvers_retrieval[0.67].medium['cloud']
    out = {
        'iteration': r.iteration,
        'sim_brf': [cam.brf.data.copy() for cam in r.sensors_retrieval['MISR']['sensor_list']],
        'extinction': cloud.extinction.data.copy(),
        'chi2': float(r.get_chi2(misr_S_1, 'I')),
    }
    if i == 0:
        obs = r.obs['MISR']['sensor_list']
        out['static'] = {
            'cam_names': [str(cam.name) if 'name' in cam.attrs or hasattr(cam, 'name') else f'cam{k}'
                          for k, cam in enumerate(obs)],
            'ray_x': [cam.ray_x.data.copy() for cam in obs],
            'ray_y': [cam.ray_y.data.copy() for cam in obs],
            'obs_brf': [cam.brf.data.copy() for cam in obs],
            'x': cloud.x.data.copy(),
            'y': cloud.y.data.copy(),
            'z': cloud.z.data.copy(),
            'cvm': r.cvm.cloud_volume_mask.transpose('x', 'y', 'z').data.copy(),
            'cvm_x': r.cvm.x.data.copy(),
            'cvm_y': r.cvm.y.data.copy(),
            'cvm_z': r.cvm.z.data.copy(),
        }
        # sanity info for choosing image extents
        for k, cam in enumerate(obs):
            sim = r.sensors_retrieval['MISR']['sensor_list'][k]
            print(f'{out["static"]["cam_names"][k]}: nrays={cam.ray_x.size} '
                  f'x=[{cam.ray_x.min().item():.2f}, {cam.ray_x.max().item():.2f}] '
                  f'y=[{cam.ray_y.min().item():.2f}, {cam.ray_y.max().item():.2f}] '
                  f'sim rays match obs: {np.allclose(sim.ray_x.data, cam.ray_x.data)}',
                  flush=True)
        print('extinction dims:', cloud.extinction.dims, cloud.extinction.shape, flush=True)
    print(f'{r.iteration}: chi2={out["chi2"]:.2f} max ext={np.nanmax(out["extinction"]):.1f}', flush=True)
    return i, out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--niter', type=int, default=16)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    with Pool(args.workers) as pool:
        results = dict(pool.imap_unordered(load_iteration, range(args.niter)))

    cache = results[0].pop('static')
    cache['iterations'] = [results[i]['iteration'] for i in range(args.niter)]
    cache['sim_brf'] = [results[i]['sim_brf'] for i in range(args.niter)]
    cache['extinction'] = np.stack([results[i]['extinction'] for i in range(args.niter)])
    cache['chi2'] = np.array([results[i]['chi2'] for i in range(args.niter)])

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE, 'wb') as f:
        pickle.dump(cache, f)
    print(f'wrote {CACHE}')
    print('chi2:', np.round(cache['chi2'], 2))


if __name__ == '__main__':
    main()
