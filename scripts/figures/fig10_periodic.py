"""Figure 10: synthetic HBC test, relative bias and RMSD of the periodic retrieval vs the open retrieval.

Source: notebooks/HBC/hbc2.ipynb, cells 0, 1, 2, 6 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig10_periodic.png
"""
from HBC import HBC, add_adjusted_stats
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.utils.util import set_labels
from notebooks.figures.extinction_compare_metrics import stat_dict

plt.style.use('seaborn-v0_8-paper')

comparisons = [
    ('control_open', 'truth'),
    ('control_periodic', 'truth'),
    ('open', 'truth'),
    ('periodic', 'truth'),
    ('control_open', 'control_periodic'),
    ('periodic', 'open')
]

lens = [5, 7, 9, 11, 15, 19]
cloud_field = 'TradeCumulus'
periodic_bases = [f'/data/keeling/a/johntl3/b/Synthetic/IO/thesis_periodic_V2/{cloud_field}/len{l:03d}/ex00' for l in lens]
open_bases = [f'/data/keeling/a/johntl3/b/Synthetic/IO/thesis/{cloud_field}/len{l:03d}/ex00' for l in lens]
df = []
for pb, ob in zip(periodic_bases, open_bases):
    h = HBC(pb, ob)
    df.append(h.calc_stats(comparisons, stat_dict))
df = pd.concat(df)

df, report = add_adjusted_stats(df)

if report:
    print(f"{len(report)} issue(s) found:")
    for msg in report:
        print(" -", msg)

def plot_r1_and_r2_single(df, r1_name, r2_name, x_axis='T', stat_name=None, ax=None):
    sub = df[(df['r1_name'] == r1_name) & (df['r2_name'] == r2_name)]
    if ax is None:
        f, ax = plt.subplots(1, 1, figsize=(6.5,3))
    sub[(sub['stat_name'] == stat_name)].pivot(columns='R',values='stat',index=x_axis).iloc[:, ::-1].plot(marker='o', ax=ax)
    ax.grid()
    ax.set_ylabel(stat_name)
    ax.set_title(stat_name)

plot_kwargs = {
    'df': df[(df['T'] >= 4) & (df['R'] >= 6)],
    'r1_name': 'periodic',
    'r2_name': 'open',
    'x_axis': 'R-T'
}

f, ax = plt.subplots(1, 2, figsize=(6.5,2.5), sharex=True, sharey=False)
f.subplots_adjust(hspace=0.3, wspace=0.25, top=0.925)
plot_r1_and_r2_single(stat_name='Relative Bias (%)', ax=ax[0], **plot_kwargs)
plot_r1_and_r2_single(stat_name='Relative RMSD (%)', ax=ax[1], **plot_kwargs)

ax[0].set_xticks(np.arange(2,15,2))
ax[0].minorticks_off()

ax[1].get_legend().remove()

ax[0].set_xlabel(r'$R-T \text{ (km)}$')
ax[1].set_xlabel(r'$R-T \text{ (km)}$')

set_labels(ax.flatten())

plt.savefig(PROJECT_ROOT / 'figures' / 'manuscript' / 'fig10_periodic.png', format='png', dpi=300, bbox_inches='tight', transparent=False)
