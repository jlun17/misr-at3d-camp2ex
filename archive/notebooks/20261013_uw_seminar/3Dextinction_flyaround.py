# conda vis2
"""Fly-around animation of the retrieved 3D cloud extinction field.

Renders one PNG per camera position with plotly/kaleido (in parallel), then
stitches the frames into an MP4 with ffmpeg. The camera makes one full orbit
around the domain while gently rising/descending and zooming in/out; all
camera parameters are periodic, so the video loops seamlessly.

Usage:
    python 3Dextinction_flyaround.py                # full render
    python 3Dextinction_flyaround.py --nframes 24   # quick preview
"""
import argparse
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
sys.path.append(str(PROJECT_ROOT))

FRAME_DIR = HERE / '3Dextinction_frames' / 'flyaround'
CACHE = HERE / '3Dextinction_frames' / 'cloud_default_0.67.npz'
OUTFILE = HERE / '3Dextinction_flyaround.mp4'

isomin = 1
isomax = 40
opacity = 0.1
surface_count = 30
cmin = 0
cmax = 40


def load_cloud():
    """Load the default retrieval's cloud extinction (cached to npz after first load)."""
    if CACHE.exists():
        d = np.load(CACHE)
        return d['x'], d['y'], d['z'], d['ext']

    from src.ExperimentSet import ExperimentSet
    es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
    exset = ExperimentSet(es_dir)
    exset.set_retrieval_list()
    exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])
    cloud = exset.get_retrieval('default').solvers_retrieval[0.67].medium['cloud']
    x, y, z, ext = cloud.x.data, cloud.y.data, cloud.z.data, cloud.extinction.data
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, x=x, y=y, z=z, ext=ext)
    return x, y, z, ext


def make_figure(x, y, z, ext, bgcolor):
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    data = go.Volume(
        x=X.flatten(),
        y=Y.flatten(),
        z=Z.flatten(),
        value=ext.flatten(),
        isomin=isomin,
        isomax=isomax,
        opacity=opacity,
        surface_count=surface_count,
        showscale=False,
        cmin=cmin,
        cmax=cmax,
        colorscale='Blues',
    )
    layout = go.Layout(autosize=False, width=750, height=650)
    fig = go.Figure(data=data, layout=layout)
    scene = dict(
        xaxis=dict(title='', tickvals=[], range=[-1, 18.6]),
        yaxis=dict(title='', tickvals=[], range=[-1, 18.6]),
        zaxis=dict(title='', tickvals=[], range=[-0.1, 1.5]),
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=0.5),
    )
    fig.update_layout(
        margin={'b': 0, 'l': 0, 'r': 0, 't': 0, 'pad': 0},
        font={'size': 16},
        scene=scene,
        # video frames have no alpha channel, so use an opaque background
        paper_bgcolor=bgcolor,
    )
    return fig


def camera_path(nframes, phi0=-0.33*np.pi, theta_lo=68, theta_hi=55,
                radius_far=2.1, radius_near=2.0):
    """One full orbit starting from the notebook's still-frame view.

    theta (zenith angle) and radius each make one smooth excursion per orbit:
    the camera climbs to a higher viewpoint and moves closer halfway around,
    then returns to the starting view.
    """
    s = np.arange(nframes) / nframes          # [0, 1), so frame 0 == frame N
    w = 0.5 * (1 - np.cos(2*np.pi*s))         # 0 -> 1 -> 0
    phi = phi0 + 2*np.pi*s
    theta = np.radians(theta_lo + (theta_hi - theta_lo) * w)
    radius = radius_far + (radius_near - radius_far) * w

    cameras = []
    for p, t, r in zip(phi, theta, radius):
        h = r * np.sin(t)
        cameras.append(dict(
            up=dict(x=0, y=0, z=1.0),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=h*np.cos(p), y=h*np.sin(p), z=r*np.cos(t)),
        ))
    return cameras


# kaleido 0.2.1 leaks ~200 MB of WebGL memory per volume render; restarting its
# Chromium subprocess every few frames keeps memory bounded (otherwise frame
# rendering eventually fails with "gl-fbo: Framebuffer failed")
KALEIDO_RESTART_EVERY = 4

# per-worker globals so the figure is built once per process
_fig = None
_scale = None
_nrendered = 0


def _init_worker(fig_json, scale):
    global _fig, _scale
    import plotly.io as pio
    _fig = pio.from_json(fig_json)
    _scale = scale


def _render(args):
    global _nrendered
    import plotly.io as pio
    i, camera = args
    _fig.update_layout(scene_camera=camera)
    _fig.write_image(str(FRAME_DIR / f'frame_{i:04d}.png'), scale=_scale)
    _nrendered += 1
    if _nrendered % KALEIDO_RESTART_EVERY == 0:
        pio.kaleido.scope._shutdown_kaleido()  # relaunched on next write_image
    return i


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--nframes', type=int, default=360)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--scale', type=float, default=1,
                        help='kaleido scale factor (750x650 base size)')
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--bgcolor', default='white')
    parser.add_argument('--skip-render', action='store_true',
                        help='only re-encode existing frames')
    parser.add_argument('--resume', action='store_true',
                        help='keep existing frames and render only the missing ones '
                             '(frames must come from the same settings)')
    parser.add_argument('--out', type=Path, default=OUTFILE)
    args = parser.parse_args()

    if not args.skip_render:
        FRAME_DIR.mkdir(parents=True, exist_ok=True)
        if not args.resume:
            for f in FRAME_DIR.glob('frame_*.png'):
                f.unlink()

        fig = make_figure(*load_cloud(), bgcolor=args.bgcolor)
        todo = [(i, cam) for i, cam in enumerate(camera_path(args.nframes))
                if not (FRAME_DIR / f'frame_{i:04d}.png').exists()]
        print(f'rendering {len(todo)}/{args.nframes} frames', flush=True)
        with Pool(args.workers, initializer=_init_worker,
                  initargs=(fig.to_json(), args.scale)) as pool:
            for n, _ in enumerate(pool.imap_unordered(_render, todo), 1):
                print(f'\rrendered {n}/{len(todo)}', end='', flush=True)
        print()

    # the system ffmpeg has no libx264, so fall back to openh264 at a high bitrate
    encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'],
                              capture_output=True, text=True).stdout
    if 'libx264' in encoders:
        codec = ['-c:v', 'libx264', '-crf', '18']
    else:
        codec = ['-c:v', 'libopenh264', '-b:v', '12M']

    # pad to even dimensions as required by yuv420p
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', str(args.fps),
        '-i', str(FRAME_DIR / 'frame_%04d.png'),
        '-vf', f'pad=ceil(iw/2)*2:ceil(ih/2)*2:color={args.bgcolor}',
        *codec, '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        str(args.out),
    ], check=True)
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
