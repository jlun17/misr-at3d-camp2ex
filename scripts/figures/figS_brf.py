"""Figures S2, S4, ..., S18: AT3D forward simulation vs MISR for the nine V11 sensitivity retrievals.

Source: notebooks/figures/ForwardSim_VS_Obs_pub.ipynb, cells 1-4, 7, 8 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/S02_brf_unconstrained.png ... S18_brf_CTP_unc.png
"""
# conda vis2
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

plt.style.use('seaborn-v0_8-paper')

from src.ExperimentSet import ExperimentSet

def get_pixels(r, i):
    misr = r.obs['MISR']['sensor_list'][i]
    at3d = r.sensors_retrieval['MISR']['sensor_list'][i]
    x = misr.ray_x.data
    y = misr.ray_y.data
    m = misr.brf.data
    a = at3d.brf.data
    return misr, at3d, x, y, m, a

def plot_F_vs_MISR(f, ax, r, plot_kwargs, diff_kwargs, contr_kwargs, contr=True, dom_boarder=False):

    for i in range(9):
        (misr, at3d, x, y, m, a) = get_pixels(r, i)
        ax[0,i].tricontourf(x, y, m, **plot_kwargs)
        c1 = ax[1,i].tricontourf(x, y, a, **plot_kwargs)
        c2 = ax[2, i].tricontourf(x, y, a-m, **diff_kwargs)
        if(contr):
            ax[0, i].tricontour(x, y, a-m, **contr_kwargs)
            ax[1, i].tricontour(x, y, a-m, **contr_kwargs)
            ax[2, i].tricontour(x, y, a-m, colors='k', levels=contr_kwargs['levels'])
        ax[0,i].set_title(misr.name)

    # Two stacked colorbars in the right margin
    # [left, bottom, width, height] in figure-fraction coords
    cax1 = f.add_axes([0.88, 0.55, 0.016, 0.33])  # top: BRF
    cax2 = f.add_axes([0.88, 0.12, 0.016, 0.33])  # bottom: difference
    f.colorbar(c1, cax=cax1, label='BRF',
            ticks=[0.0, 0.1, 0.2, 0.3, 0.4])
    f.colorbar(c2, cax=cax2, label='BRF Difference',
            ticks=[diff_kwargs['vmin'], 0.0, diff_kwargs['vmax']])

    title = str(r.exp_name)
    if(title == 'ATM_unc'):
        title = r'$\text{AT}-$'
    elif(title == 'ATP_unc'):
        title = r'$\text{AT}+$'
    elif(title == 'CTM_unc'):
        title = r'$\text{CT}-$'
    elif(title == 'CTP_unc'):
        title = r'$\text{CT}+$'
    plt.suptitle(title)
    ticks = [0.0, 8.8, 17.6]
    box_kwargs = {'ls':'--', 'lw':0.7, 'c':'r'}
    for a in ax.flat:
        if(dom_boarder):
            a.plot([0, 0], [0, 17.6], **box_kwargs)
            a.plot([0, 17.6], [0, 0], **box_kwargs)
            a.plot([17.6, 17.6], [0, 17.6], **box_kwargs)
            a.plot([0, 17.6], [17.6, 17.6], **box_kwargs)
        a.set_xticks(ticks)
        a.set_xticklabels(ticks, rotation=90)
        a.set_yticks(ticks)

vrange = 0.18
plot_kwargs = {
    'cmap':'gray',
    'vmin':0,
    'vmax':0.4,
    'levels':np.linspace(0, 0.4, 50)
}
diff_kwargs = {
    'cmap':'RdBu_r',
    'vmin':-vrange,
    'vmax':vrange,
    'levels':np.linspace(-vrange, vrange, 100)
}
contr_kwargs = diff_kwargs.copy()
contr_kwargs['levels'] = np.array([0.05])

es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])

savekwargs = {
    'format': 'png',
    'dpi':300,
    'bbox_inches':'tight',
    'transparent':False
}

outdir = PROJECT_ROOT / 'figures' / 'manuscript'

sublist = ['unconstrained', 'surf4p0', 'aod0p150', 'aod0p250', 'periodic', 'ATM_unc', 'ATP_unc', 'CTM_unc', 'CTP_unc']

for i,rname in enumerate(sublist):
    r = exset.get_retrieval(rname)
    f, ax = plt.subplots(3, 9, figsize=(6.5, 2.5), sharex=True, sharey=True)
    plt.subplots_adjust(wspace=0.12, hspace=0.07, right=0.865, bottom=0.25, top=0.83)
    plot_F_vs_MISR(f, ax, r, plot_kwargs, diff_kwargs, contr_kwargs, contr=False, dom_boarder=True)
    f.supxlabel('x (km)')
    f.supylabel('y (km)')
    plt.savefig(outdir / f'S{2*i+2:02d}_brf_{rname}.png', **savekwargs)
    plt.close(f)
