"""Figure 2: 3D extinction field of the V11 default retrieval.

Source: notebooks/figures/3Dextinction.ipynb, cells 0, 1, 3, 4 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig02_volume.png
"""
# conda vis2
from pathlib import Path
import os
import sys
import tempfile
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Use a project-local temp directory so Kaleido/Chromium does not crash when /tmp is full.
KALEIDO_TMP = PROJECT_ROOT / "tmp" / "kaleido_tmp"
KALEIDO_TMP.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(KALEIDO_TMP)
tempfile.tempdir = str(KALEIDO_TMP)

# Reduce reliance on shared memory and GPU in constrained Linux environments.
_extra_kaleido_args = ("--disable-dev-shm-usage", "--disable-gpu", "--single-process")
for _arg in _extra_kaleido_args:
    if _arg not in pio.kaleido.scope.chromium_args:
        pio.kaleido.scope.chromium_args += (_arg,)

from src.ExperimentSet import ExperimentSet

es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])

isomin=1
isomax=40
opacity=0.1
surface_count=30
cmin=0
cmax=40

rnames = ['default']
outdir = PROJECT_ROOT / 'figures' / 'manuscript'

rs = [exset.get_retrieval(r) for r in rnames]

for i, r in enumerate(rs):
    cloud = r.solvers_retrieval[0.67].medium['cloud']

    X, Y, Z = np.meshgrid(cloud.x.data, cloud.y.data, cloud.z.data, indexing='ij')
    data = go.Volume(
        x=X.flatten(),
        y=Y.flatten(),
        z=Z.flatten(),
        value=cloud.extinction.data.flatten(),
        isomin=isomin,
        isomax=isomax,
        opacity=opacity,
        surface_count=surface_count,
        showscale=True,
        cmin=cmin,
        cmax=cmax,
        colorscale='Blues',
        colorbar=dict(
            title='',
            titleside='right',
            tickmode='array',
            tickvals=[cmin, 0.5*(cmin+cmax), cmax],
            ticktext=['Low', 'Medium', 'High'],
            len=0.4,
            thickness=20,
            tickfont={'size': 20}
        )
    )
    layout = go.Layout(autosize=False, width=750, height=650)
    fig = go.Figure(data=data, layout=layout)
    pad = {'b':0, 'l':0, 'r':0, 't':20, 'pad':0}
    font = {'size':16}

    scene = dict(
        xaxis=dict(title='x (km)', tickvals=[0, 4.4, 8.8, 13.2, 17.6], range=[-1, 18.6]),
        yaxis=dict(title='y (km)', tickvals=[0, 4.4, 8.8, 13.2, 17.6], range=[-1, 18.6]),
        zaxis=dict(title='z (km)', tickvals=[0, 1.4], range=[-0.1, 1.5]),
        aspectmode='manual',
        aspectratio=dict(x=1,y=1,z=0.5)
    )

    theta = np.radians(50)
    phi = -0.38*np.pi
    radius = 2.4
    h = radius * np.sin(theta)

    camera = dict(
        up=dict(x=0, y=0, z=1.0),
        center=dict(x=0, y=0, z=0),
        eye=dict(x=h*np.cos(phi), y=h*np.sin(phi), z=radius*np.cos(theta))
    )
    fig.update_layout(
        scene_camera=camera,
        margin=pad,
        font=font,
        scene=scene,
    )

    outfile = outdir / 'fig02_volume.png'
    fig.write_image(str(outfile))
