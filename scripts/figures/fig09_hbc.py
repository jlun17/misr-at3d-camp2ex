"""Figure 9: synthetic HBC test, adjusted relative RMSD and bias of open and periodic retrievals vs their controls.

Source: notebooks/HBC/hbc2.ipynb, cells 0, 1, 2, 4, 5 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig09_hbc.png
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
periodic_bases = [f'{PROJECT_ROOT}/data/synthetic/thesis_periodic_V2/{cloud_field}/len{l:03d}/ex00' for l in lens]
open_bases = [f'{PROJECT_ROOT}/data/synthetic/thesis/{cloud_field}/len{l:03d}/ex00' for l in lens]
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

def plot_r1_and_r2(df, r1_name, r2_name, x_axis='T', stat_list=None, ax=None, title=True):
    sub = df[(df['r1_name'] == r1_name) & (df['r2_name'] == r2_name)]
    if stat_list is None:
        stat_list = sub['stat_name'].unique()
    if ax is None:
        f, ax = plt.subplots(1, len(stat_list), figsize=(5*len(stat_list),5))
    for i, s in enumerate(stat_list):
        sub[(sub['stat_name'] == s)].pivot(columns='R',values='stat',index=x_axis).iloc[:, ::-1].plot(marker='o', ax=ax[i])
        ax[i].grid()
        ax[i].set_ylabel(s)
        ax[i].set_title(s)
    if(title):
        plt.suptitle(f'R1 = {r1_name}, R2 = {r2_name}')

x_axis = 'R-T'
f, ax = plt.subplots(2, 2, figsize=(6.5,5), sharex=True, sharey=False)
plot_r1_and_r2(
    df=df[(df['T'] >= 4) & (df['R'] >= 6)],
    r1_name='open',
    r2_name='control_open',
    x_axis=x_axis,
    stat_list=['adjusted Relative RMSD (%)', 'adjusted Relative Bias (%)'],
    ax=ax[:,0],
    title=False
)
plot_r1_and_r2(
    df=df[(df['T'] >= 4) & (df['R'] >= 6)],
    r1_name='periodic',
    r2_name='control_periodic',
    x_axis=x_axis,
    stat_list=['adjusted Relative RMSD (%)', 'adjusted Relative Bias (%)'],
    ax=ax[:,1],
    title=False
)
ax[0,0].set_title('Open')
ax[1,0].set_title('Open')
ax[0,1].set_title('Periodic')
ax[1,1].set_title('Periodic')

# Trade Cumulus Settings
if(cloud_field == 'TradeCumulus'):
    ax[0,0].set_ylim([0, 70])
    ax[0,1].set_ylim([0, 70])
    ax[1,0].set_ylim([-80, 80])
    ax[1,1].set_ylim([-80, 80])

# Transition settings
if(cloud_field == 'Transition'):
    ax[0,0].set_ylim([0, 130])
    ax[0,1].set_ylim([0, 130])
    ax[1,0].set_ylim([-125, 125])
    ax[1,1].set_ylim([-125, 125])

ax[0,1].get_legend().remove()
ax[1,0].get_legend().remove()
ax[1,1].get_legend().remove()
ax[0,1].set_ylabel('')
ax[1,1].set_ylabel('')

ax[0,0].set_xticks(np.arange(2,15,2))
ax[0,0].minorticks_off()

ax[1,0].set_xlabel(r'$R-T \text{ (km)}$')
ax[1,1].set_xlabel(r'$R-T \text{ (km)}$')

set_labels(ax.flatten())

plt.savefig(PROJECT_ROOT / 'figures' / 'manuscript' / 'fig09_hbc.png', format='png', dpi=300, bbox_inches='tight', transparent=False)
