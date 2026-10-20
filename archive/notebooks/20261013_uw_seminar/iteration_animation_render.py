# conda vis2
"""Animation of the AT3D retrieval converging, one frame per iteration.

Reads iteration_animation_frames/cache.pkl (made by iteration_animation_extract.py)
and renders, for each iteration:
    * the 9 MISR cameras (top row) vs. the AT3D forward-simulated images (bottom row)
    * chi^2 vs. iteration, one new dot per frame
    * a view of the retrieved cloud extinction, in three versions:
        maxy     - maximum extinction along y (x-z image)
        transect - vertical y-z transect near x = 4.0 km
        3d       - plotly volume render (fixed camera, as in figures/3Dextinction.ipynb)
    * an "Iteration: N" counter

Outputs (all in iteration_animation/):
    combined_{maxy,transect,3d}.mp4   all panels in one video
    strip.mp4, chi2.mp4, counter.mp4,
    cloud_{maxy,transect,3d}.mp4      individual panels for laying out in PowerPoint
All videos share the same frame timing, so they stay in step when started together.
PNG frames are kept under iteration_animation_frames/.

Usage:
    python iteration_animation_render.py                  # everything
    python iteration_animation_render.py --preview 0 15   # PNGs of a few frames only
    python iteration_animation_render.py --chi2-log       # log chi^2 axis
"""
import argparse
import os
import pickle
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
CACHE = HERE / 'iteration_animation_frames' / 'cache.pkl'
FRAME_DIR = HERE / 'iteration_animation_frames'
OUT_DIR = HERE / 'iteration_animation'

# MISR nominal view zenith angles (+ forward, - aft), in the order shown
CAM_ANGLES = {'DF': 70.5, 'CF': 60.0, 'BF': 45.6, 'AF': 26.1, 'AN': 0.0,
              'AA': -26.1, 'BA': -45.6, 'CA': -60.0, 'DA': -70.5}
CAM_ORDER = list(CAM_ANGLES)

DOMAIN = (0.0, 17.6)  # retrieval domain extent in x and y (km)
IMG_LIM = (0.0, 17.6)  # extent shown for each MISR image (km)
BRF_KW = dict(cmap='gray', vmin=0, vmax=0.4, levels=np.linspace(0, 0.4, 50), extend='both')
EXT_KW = dict(cmap='gist_heat_r', vmin=0, vmax=45)
EXT_LABEL = r'extinction (km$^{-1}$)'
TRANSECT_X = 4.0
FONTSIZE = 13
DPI = 200
FPS_IN = 2  # 0.5 s per iteration

# plotly volume settings, from figures/3Dextinction.ipynb
VOL_KW = dict(isomin=1, isomax=40, opacity=0.1, surface_count=30, cmin=0, cmax=40,
              colorscale='Blues', showscale=False)

plt.rcParams.update({'font.size': FONTSIZE, 'axes.titlesize': FONTSIZE,
                     'axes.labelsize': FONTSIZE})


def load_cache():
    with open(CACHE, 'rb') as f:
        c = pickle.load(f)
    # put cameras in Df -> Da order
    names = [n.upper() for n in c['cam_names']]
    c['cam_index'] = [names.index(n) for n in CAM_ORDER]
    c['niter'] = len(c['chi2'])
    c['ix_transect'] = int(np.argmin(np.abs(c['x'] - TRANSECT_X)))
    return c


def angle_label(name):
    a = CAM_ANGLES[name]
    return '0' if a == 0 else f'{a:+.1f}'


# ---------------------------------------------------------------------------
# panels
# ---------------------------------------------------------------------------
def strip_axes(fig, left, bottom, width, height_per_cell):
    """2 x 9 grid of square axes with zero padding; returns axes[row, col]."""
    w = width / 9
    ax = np.empty((2, 9), dtype=object)
    for row in range(2):
        for col in range(9):
            ax[row, col] = fig.add_axes([left + col * w,
                                         bottom + (1 - row) * height_per_cell,
                                         w, height_per_cell])
    return ax


def draw_strip(ax, c, it):
    box = [DOMAIN[0], DOMAIN[1], DOMAIN[1], DOMAIN[0], DOMAIN[0]], \
          [DOMAIN[0], DOMAIN[0], DOMAIN[1], DOMAIN[1], DOMAIN[0]]
    for col, name in enumerate(CAM_ORDER):
        k = c['cam_index'][col]
        x, y = c['ray_x'][k], c['ray_y'][k]
        for row, brf in enumerate([c['obs_brf'][k], c['sim_brf'][it][k]]):
            a = ax[row, col]
            a.tricontourf(x, y, brf, **BRF_KW)
            a.plot(*box, ls='--', lw=0.8, c='0.75')
            a.set_xlim(IMG_LIM)
            a.set_ylim(IMG_LIM)
            a.set_xticks([])
            a.set_yticks([])
            a.set_facecolor('black')
            for s in a.spines.values():
                s.set_color('white')
                s.set_linewidth(0.6)
        ax[0, col].set_title(angle_label(name), pad=3)


def draw_chi2(ax, c, it, log=False):
    chi2 = c['chi2']
    n = c['niter']
    ax.plot(np.arange(it + 1), chi2[:it + 1], 'o', c='C0', ms=6)
    ax.set_xlim(-0.6, n - 0.4)
    if log:
        ax.set_yscale('log')
        ax.set_ylim(chi2.min() / 1.3, chi2.max() * 1.3)
    else:
        ax.set_ylim(0, chi2.max() * 1.08)
    ax.set_xticks(np.arange(0, n, 3))
    ax.set_xlabel('Iteration')
    ax.set_ylabel(r'$\chi^2$')
    ax.grid(True, which='both', lw=0.5, c='0.85')
    ax.set_axisbelow(True)


def trim_white(img, pad=10):
    """Crop the white margin plotly leaves around the 3D scene."""
    rows, cols = np.nonzero((img[..., :3] < 0.98).any(axis=-1))
    return img[max(rows.min() - pad, 0):rows.max() + pad,
               max(cols.min() - pad, 0):cols.max() + pad]


def draw_cloud(ax, c, it, kind, cax=None, vol_png=None):
    ext = np.where(c['extinction'][it] > 0, c['extinction'][it], np.nan)
    if kind == '3d':
        ax.imshow(trim_white(plt.imread(vol_png)))
        ax.axis('off')
        return
    if kind == 'maxy':
        field = np.nanmax(ext, axis=1).T  # (z, x)
        h, xlabel = c['x'], 'x (km)'
    else:  # transect
        field = ext[c['ix_transect']].T  # (z, y)
        h, xlabel = c['y'], 'y (km)'
    m = ax.pcolormesh(h, c['z'], field, shading='nearest', **EXT_KW)
    if kind == 'transect':
        icx = int(np.argmin(np.abs(c['cvm_x'] - c['x'][c['ix_transect']])))
        ax.contour(c['cvm_y'], c['cvm_z'], c['cvm'][icx].T.astype(float),
                   levels=[0.5], colors='k', linewidths=0.6)
        ax.set_title(f'x = {c["x"][c["ix_transect"]]:.1f} km', fontsize=FONTSIZE - 2, pad=3)
    ax.set_xlim(DOMAIN)
    ax.set_ylim(0, c['z'].max())
    ax.set_xticks([0, 4.4, 8.8, 13.2, 17.6])
    ax.set_xlabel(xlabel)
    ax.set_ylabel('z (km)')
    if cax is not None:
        cb = plt.colorbar(m, cax=cax, extend='max')
        cb.set_label(EXT_LABEL)
        cb.set_ticks([0, 15, 30, 45])


def draw_counter(fig, it, x=0.5, y=0.5, size=FONTSIZE + 9):
    fig.text(x, y, f'Iteration: {it}', ha='center', va='center', fontsize=size)


# ---------------------------------------------------------------------------
# 3D volume frames (plotly)
# ---------------------------------------------------------------------------
def render_volumes(c, outdir):
    import plotly.graph_objects as go
    import plotly.io as pio

    # kaleido/Chromium workarounds from figures/3Dextinction.ipynb
    kaleido_tmp = PROJECT_ROOT / 'tmp' / 'kaleido_tmp'
    kaleido_tmp.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(kaleido_tmp)
    tempfile.tempdir = str(kaleido_tmp)
    for arg in ('--disable-dev-shm-usage', '--disable-gpu', '--single-process'):
        if arg not in pio.kaleido.scope.chromium_args:
            pio.kaleido.scope.chromium_args += (arg,)

    outdir.mkdir(parents=True, exist_ok=True)
    X, Y, Z = np.meshgrid(c['x'], c['y'], c['z'], indexing='ij')
    theta, phi, radius = np.radians(68), -0.33 * np.pi, 2.0
    h = radius * np.sin(theta)
    camera = dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0),
                  eye=dict(x=h * np.cos(phi), y=h * np.sin(phi), z=radius * np.cos(theta)))
    ticks = [0, 4.4, 8.8, 13.2, 17.6]
    scene = dict(
        xaxis=dict(title='x (km)', tickvals=ticks, range=[-1, 18.6]),
        yaxis=dict(title='y (km)', tickvals=ticks, range=[-1, 18.6]),
        zaxis=dict(title='z (km)', tickvals=[0, 1.4], range=[-0.1, 1.5]),
        aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.5),
    )
    paths = []
    for it in range(c['niter']):
        out = outdir / f'vol_{it:02d}.png'
        paths.append(out)
        if out.exists():
            continue
        fig = go.Figure(go.Volume(x=X.flatten(), y=Y.flatten(), z=Z.flatten(),
                                  value=c['extinction'][it].flatten(), **VOL_KW),
                        go.Layout(autosize=False, width=750, height=600))
        fig.update_layout(scene=scene, scene_camera=camera, font={'size': 16},
                          margin={'b': 0, 'l': 0, 'r': 0, 't': 0, 'pad': 0})
        fig.write_image(str(out), scale=2)
        if (it + 1) % 4 == 0:  # kaleido leaks WebGL memory; restart it
            pio.kaleido.scope._shutdown_kaleido()
        print(f'volume {it}', flush=True)
    return paths


# ---------------------------------------------------------------------------
# frame builders
# ---------------------------------------------------------------------------
def frame_combined(c, it, kind, chi2_log, vol_png=None):
    W, H = 12.0, 7.6
    fig = plt.figure(figsize=(W, H))
    # image strip: full width at the bottom, zero padding
    sw = 0.98
    cell = sw * W / 9 / H  # square cells, in figure-height units
    ax = strip_axes(fig, (1 - sw) / 2, 0.01, sw, cell)
    draw_strip(ax, c, it)
    top = 0.01 + 2 * cell + 0.07  # leave room for the angle labels
    ph = 0.86 - top
    if kind == '3d':
        draw_cloud(fig.add_axes([0.02, top - 0.03, 0.44, ph + 0.08]), c, it, kind, vol_png=vol_png)
    else:
        draw_cloud(fig.add_axes([0.07, top + 0.04, 0.33, ph - 0.04]), c, it, kind,
                   cax=fig.add_axes([0.415, top + 0.04, 0.013, ph - 0.04]))
    draw_chi2(fig.add_axes([0.6, top + 0.04, 0.37, ph - 0.04]), c, it, chi2_log)
    draw_counter(fig, it, y=0.94)
    return fig


def frame_strip(c, it):
    W = 12.0
    cell = W / 9
    H = 2 * cell + 0.35
    fig = plt.figure(figsize=(W, H))
    draw_strip(strip_axes(fig, 0, 0, 1, cell / H), c, it)
    return fig


def frame_cloud(c, it, kind, vol_png=None):
    if kind == '3d':
        fig = plt.figure(figsize=(5, 4))
        draw_cloud(fig.add_axes([0, 0, 1, 1]), c, it, kind, vol_png=vol_png)
        return fig
    fig = plt.figure(figsize=(5.5, 3.6))
    draw_cloud(fig.add_axes([0.14, 0.17, 0.66, 0.73]), c, it, kind,
               cax=fig.add_axes([0.83, 0.17, 0.03, 0.73]))
    return fig


def frame_chi2(c, it, chi2_log):
    fig = plt.figure(figsize=(5.5, 3.6))
    draw_chi2(fig.add_axes([0.16, 0.17, 0.8, 0.78]), c, it, chi2_log)
    return fig


def frame_counter(c, it):
    fig = plt.figure(figsize=(3.2, 0.75))
    draw_counter(fig, it, size=FONTSIZE + 11)
    return fig


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor='white')
    plt.close(fig)


def encode(frame_dir, out):
    # the system ffmpeg has no libx264, so fall back to openh264 at a high bitrate
    encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'],
                              capture_output=True, text=True).stdout
    codec = ['-c:v', 'libx264', '-crf', '16'] if 'libx264' in encoders \
        else ['-c:v', 'libopenh264', '-b:v', '8M']
    out.parent.mkdir(parents=True, exist_ok=True)
    # 2 input frames/s (0.5 s per iteration), written at 30 fps so every player
    # (incl. PowerPoint) handles it; pad to even dimensions for yuv420p
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-framerate', str(FPS_IN), '-i', str(frame_dir / 'frame_%02d.png'),
        '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white', '-r', '30',
        *codec, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out),
    ], check=True)
    print(f'wrote {out}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--preview', type=int, nargs='*',
                        help='only render combined PNGs for these iterations')
    parser.add_argument('--chi2-log', action='store_true')
    parser.add_argument('--kinds', nargs='*', default=['maxy', 'transect', '3d'])
    args = parser.parse_args()

    c = load_cache()
    print('chi2:', np.round(c['chi2'], 2), flush=True)
    vol = render_volumes(c, FRAME_DIR / 'volume') if '3d' in args.kinds else None

    if args.preview is not None:
        for it in args.preview:
            for kind in args.kinds:
                save(frame_combined(c, it, kind, args.chi2_log, vol and vol[it]),
                     FRAME_DIR / 'preview' / f'combined_{kind}_{it:02d}.png')
        return

    jobs = {f'combined_{k}': (lambda it, k=k: frame_combined(c, it, k, args.chi2_log, vol and vol[it]))
            for k in args.kinds}
    jobs.update({f'cloud_{k}': (lambda it, k=k: frame_cloud(c, it, k, vol and vol[it]))
                 for k in args.kinds})
    jobs['strip'] = lambda it: frame_strip(c, it)
    jobs['chi2'] = lambda it: frame_chi2(c, it, args.chi2_log)
    jobs['counter'] = lambda it: frame_counter(c, it)

    for name, make in jobs.items():
        d = FRAME_DIR / name
        for it in range(c['niter']):
            save(make(it), d / f'frame_{it:02d}.png')
        encode(d, OUT_DIR / f'{name}.mp4')


if __name__ == '__main__':
    main()
