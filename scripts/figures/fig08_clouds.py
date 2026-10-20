"""Figure 8: summary of the synthetic Trade Cumulus cloud field (CTH, cloud mask, LWP, optical depth).

Source: /data/keeling/a/johntl3/b/Synthetic/analysis/lundstrom2025_figures.ipynb,
cells 0, 1 (set_labels only), 18 (plot_square only), 19 (Trade Cumulus only), 20 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig08_clouds.png
"""
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-paper')
savefigs = True

def set_labels(ax_flat):
    labels = ['a)', 'b)', 'c)', 'd)', 'e)', 'f)', 'g)', 'h)', 'i)']
    for i, a in enumerate(ax_flat):
        a.set_title(labels[i], fontfamily='serif', loc='left', fontsize='medium', fontweight='bold')

def plot_square(c, r, ax):
    w = r/2
    ax.plot([c-w, c-w], [c-w, c+w], 'y')
    ax.plot([c+w, c+w], [c-w, c+w], 'y')
    ax.plot([c-w, c+w], [c-w, c-w], 'y')
    ax.plot([c-w, c+w], [c+w, c+w], 'y')

trcu_file = '../../data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc'
trcu = xr.load_dataset(trcu_file)
R = 71
L = 74 - R//2
H = 74 + R//2 + 1
trcu = trcu.isel(x=slice(L, H), y=slice(L, H))

cth_cmap = 'cividis'
cm_cmap = 'gray'
lwp_cmap = 'plasma'
od_cmap = 'viridis'
square_rs = np.array([5, 17])
square_cs = np.array([74, 74])
f, ax = plt.subplots(2, 2, figsize=(6.5, 5), sharex=True, sharey=True)

trcu.cth.plot(y='y', ax=ax[0, 0], cmap=cth_cmap, cbar_kwargs={'label':'CTH [km]'})
trcu.mask.plot(y='y', ax=ax[0, 1], cmap=cm_cmap, cbar_kwargs={'label':'Cloud Mask'})
trcu.lwp.plot(y='y', ax=ax[1, 0], cmap=lwp_cmap, cbar_kwargs={'label':r'LWP [gm$^{-2}$]'})
trcu.optical_depth.plot(y='y', ax=ax[1, 1], cmap=od_cmap, cbar_kwargs={'label':'Optical Depth'})

for a in ax.flatten():
    for i in range(square_cs.shape[0]):
        plot_square(square_cs[i], square_rs[i], a)
    a.set_xlabel('x [km]')

ax[0, 0].set_title('Cloud Top Heights')
ax[0, 1].set_title('Cloud Mask')
ax[1, 0].set_title('Liquid Water Path')
ax[1, 1].set_title('Optical Depth')

ax[0, 0].set_ylabel('y [km]')
ax[1, 0].set_ylabel('y [km]')

ax[0,0].set_xlabel('')
ax[0,1].set_xlabel('')
ax[0,1].set_ylabel('')
ax[1,1].set_ylabel('')

set_labels(ax.flatten())

if(savefigs):
    plt.savefig(
        '../../figures/manuscript/fig08_clouds.png',
        format='png',
        dpi=300,
        bbox_inches='tight',
        transparent=False
    )
