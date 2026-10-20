"""Figure 7: AT3D retrieved extinction vs CAMP2Ex P-3B in situ extinction by altitude (V11).

Source: notebooks/figures/CAMP2Ex_insitu_reduced.ipynb, cells 0-6, 8, 12 (0-based).
Requires experiments/CAMP2Ex_RF17/V11/<retrieval>/min_optical_path.nc (produced by calc_VC.sh).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig07_insitu.png
"""
# conda env 'vis2_clone'
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import xarray as xr
from cmap_dict import cmap

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import src.CAMP2Ex as cx
from src.ExperimentSet import ExperimentSet
from src.utils.util import set_labels

plt.style.use('seaborn-v0_8-paper')

es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])

cvm = exset.get_retrieval('default').cvm.drop_vars(['delx', 'dely'])
cvm['cloud_top_heights'] = cvm.z.where(cvm.cloud_volume_mask == 1).max(dim="z")
cvm['distance_to_cloud_top'] = cvm.z - cvm.cloud_top_heights
cvm['cloud_base_heights'] = cvm.z.where(cvm.cloud_volume_mask == 1).min(dim="z")
cvm['distance_to_cloud_base'] = cvm.z - cvm.cloud_base_heights
distance_to_cloud = cvm.distance_to_cloud_base.clip(max=0) + cvm.distance_to_cloud_top.clip(min=0)
cvm["distance_to_cloud"] = distance_to_cloud
cvm = cvm.drop_vars(['cloud_top_heights', 'cloud_base_heights'])
cvm = cvm.to_dataframe()
df_list = []

for r in list(exset.retrievals.values()):
    tmp_ext = r.solvers_retrieval[0.67].medium['cloud'].extinction.copy(deep=True)
    df_tmp = tmp_ext.drop_vars(['reff', 'veff']).to_dataframe()
    df_tmp = df_tmp.join(cvm)
    tmp_vc = xr.load_dataset(r.root_dir / 'min_optical_path.nc').min_optical_path.to_dataframe()
    df_tmp = df_tmp.join(tmp_vc)
    df_tmp['source'] = r.exp_name
    df_list.append(df_tmp[df_tmp['extinction'] > 0.0])

df_at3d = pd.concat(df_list)

df_at3d = df_at3d.reset_index()
df_at3d['x'] *= 1000
df_at3d['y'] *= 1000
df_at3d['z'] *= 1000

bins = np.arange(-50, 1451, 100)
df_at3d['altitude_bin'] = pd.cut(df_at3d['z'], bins=bins)

dtc_bins = np.arange(-0.45, 1.051, 0.1)
df_at3d['distance_to_cloud_bin'] = pd.cut(df_at3d['distance_to_cloud'], bins=dtc_bins)

df_at3d['isVeiled'] = df_at3d['min_optical_path'] >= 5

RAW_DATA = PROJECT_ROOT / 'data' / 'raw'
nav_file = RAW_DATA / 'CAMP2Ex_SPEC' / 'CAMP2EX-MetNav_P3B_20191001_R0.ict'
fcdp_file = RAW_DATA / 'CAMP2Ex_SPEC' / 'PaulLawson' / 'CAMP2Ex-FCDP_P3B_20191001_R1.ict'
tds_file = RAW_DATA / 'CAMP2Ex_SPEC' / 'PaulLawson' / 'CAMP2Ex-2DS10_P3B_20191001_R0.ict'
df_p3 = cx.load_FCDP_2DS(fcdp_file, tds_file, nav_file, breakpoint=40, resample='2s')
df_p3['source'] = 'in situ'

# The sample at time t is part of the cloud element e if
# the extinction at time t > 0.3 
# and there is another sample t' \in e such that |t-t'| < 3
# In other words, it takes 3 seconds of clear air to separate two clouds
df_p3['sample_optical_path'] = df_p3['ext_km'] * df_p3['Length_m'] * 1e-3
ext_th = 0.3
t_th = pd.Timedelta(3, 's')
df_p3['cloud_pass'] = -1
cloud_pass = 1
inCloud = False
t_last_cloud = df_p3.index[0]
for row in df_p3.itertuples():
    if(not inCloud):
        if(row.ext_km > ext_th):
            inCloud = True
            t_last_cloud = row.Index
            df_p3.at[row.Index, 'cloud_pass'] = cloud_pass
    else:
        if(row.ext_km > ext_th):
            t_last_cloud = row.Index
            df_p3.at[row.Index, 'cloud_pass'] = cloud_pass
        elif(row.Index - t_last_cloud < t_th):
            df_p3.at[row.Index, 'cloud_pass'] = cloud_pass
        else:
            df_p3.loc[t_last_cloud+pd.Timedelta(1, 's'):row.Index, 'cloud_pass'] = -1
            inCloud = False
            cloud_pass += 1

g = df_p3.groupby('cloud_pass')['sample_optical_path']
df_p3['forward_optical_path'] = g.cumsum()
df_p3['backward_optical_path'] = g.apply(lambda s: s[::-1].cumsum()[::-1]).reset_index(level=0, drop=True)
df_p3['optical_path'] = df_p3[['forward_optical_path', 'backward_optical_path']].min(axis=1)
df_p3['pass_length'] = df_p3.groupby('cloud_pass')['Length_m'].transform('sum')
df_p3['isVeiled'] = df_p3['optical_path'] >= 5

bins = np.arange(-50, 1251, 100)
df_at3d['altitude_bin'] = pd.cut(df_at3d['z'], bins=bins)
df_p3['altitude_bin'] = pd.cut(df_p3['GPS_Altitude'], bins=bins)

start_time = pd.to_datetime('2019-10-02 00:00:00')
end_time = pd.to_datetime('2019-10-02 02:00:00')

df_p3_sub = df_p3[
    (df_p3['ext_km'] > 0.3)
    & (df_p3.index > start_time)
    & (df_p3.index < end_time)
    & (df_p3['GPS_Altitude'] < 1250)
    & ~(
        ((df_p3.index >= pd.to_datetime('2019-10-02 00:35:00')) & (df_p3.index <= pd.to_datetime('2019-10-02 00:36:00')))
        | ((df_p3.index >= pd.to_datetime('2019-10-02 01:45:00')) & (df_p3.index <= pd.to_datetime('2019-10-02 01:46:30')))
    )
]
df_p3_sub = df_p3_sub.reset_index().rename(columns={'ext_km':'extinction'})

df_at3d['x_tmp'] = 17600 - df_at3d['x']
df_at3d['y_tmp'] = 17600 - df_at3d['y']
df_at3d['D'] = df_at3d.loc[:,['x','y','x_tmp','y_tmp']].min(axis=1)

df_p3_sub['D'] = 99999

df_p3_at3d = pd.concat([
    df_at3d.loc[:, ['extinction', 'altitude_bin', 'source', 'isVeiled', 'D']],
    df_p3_sub.loc[:, ['extinction', 'altitude_bin', 'source', 'isVeiled', 'D']]
], ignore_index=True)

pltlist = ['in situ', 'default', 'surf4p0', 'aod0p150', 'aod0p250', 'periodic', 'unconstrained']

altitude_order = [f'({bins[i]}, {bins[i+1]}]' for i in range(len(bins) - 2, -1, -1)]
# Only show altitude bins that contain in situ samples
insitu_bins = set(df_p3_at3d.loc[df_p3_at3d['source'] == 'in situ', 'altitude_bin'].dropna().astype(str))
altitude_order = [b for b in altitude_order if b in insitu_bins]

cmap['in situ'] = 'cyan'

box_kwargs = {
    'x': 'extinction',
    'y': 'altitude_bin',
    'hue': 'source',
    'hue_order': pltlist,
    'palette': cmap,
    'order': altitude_order,
    'whis':(0, 100),
    'width': 1.0,   # hue group fills the whole altitude bin -> max spacing between dodged boxes
    'gap': 0.25,    # shrink each box within its slot so neighbouring boxes stay visually separated
}
fs_title = None #16
fs_ax = None #14
fs_labels = None #12
fs_count = 9

def annotate_counts(a, df, x_text):
    """Write the sample count to the left of each dodged box."""
    sample_counts = df.groupby(['altitude_bin', 'source']).size().unstack(fill_value=0)
    # Convert categorical index to string for comparison
    sample_counts.index = sample_counts.index.astype(str)
    n = len(pltlist)
    for i, altitude in enumerate(altitude_order):
        if altitude not in sample_counts.index:
            continue
        for j, source in enumerate(pltlist):
            if source in sample_counts.columns:
                count = sample_counts.loc[altitude, source]
                if count > 0:
                    # Same dodge offsets seaborn uses for the boxes
                    y_pos = i + (j - (n - 1) / 2) * box_kwargs['width'] / n
                    a.text(x_text, y_pos+0.015, f'{count}', ha='right', va='center', fontsize=fs_count)

f, ax = plt.subplots(1, 3, figsize=(6.5,9), sharex=False, sharey=True)
f.subplots_adjust(wspace=0.0, hspace=0.0, top=0.97, bottom=0.11)

sns.boxplot(df_p3_at3d[df_p3_at3d['source'].isin(pltlist)], ax=ax[0], legend=False, **box_kwargs)
annotate_counts(ax[0], df_p3_at3d, -3)
ax[0].set_xlim(-48, 170)
ax[0].set_ylabel('altitude bin (m)', fontsize=fs_ax)
ax[0].set_xlabel(r'extinction (km$^{-1}$)', fontsize=fs_ax)
ax[0].set_title('All samples', fontsize=fs_title)
ax[0].grid(axis='x')

sns.boxplot(df_p3_at3d[(df_p3_at3d['source'].isin(pltlist)) & (df_p3_at3d['isVeiled'] == False)], legend=False, ax=ax[1], **box_kwargs)
annotate_counts(ax[1], df_p3_at3d[df_p3_at3d['isVeiled'] == False], -2)
ax[1].set_xlim(-15, 37)
ax[1].set_xlabel(r'extinction (km$^{-1}$)', fontsize=fs_ax)
ax[1].set_title('Cloud Shell', fontsize=fs_title)
ax[1].grid(axis='x')

sns.boxplot(df_p3_at3d[(df_p3_at3d['source'].isin(pltlist)) & (df_p3_at3d['isVeiled'] == True)], ax=ax[2], legend=True, **box_kwargs)
annotate_counts(ax[2], df_p3_at3d[df_p3_at3d['isVeiled'] == True], -3)
ax[2].set_xlim(-40, 170)
ax[2].set_xlabel(r'extinction (km$^{-1}$)', fontsize=fs_ax)
ax[2].set_title('Cloud Core', fontsize=fs_title)
ax[2].grid(axis='x')
set_labels(ax.flatten())

handles, labels = ax[2].get_legend_handles_labels()
ax[2].get_legend().remove()
f.legend(handles, labels, loc='lower center', ncol=4, frameon=False, fontsize=fs_labels)

for a in ax.flatten():
    a.tick_params(axis='both', labelsize=fs_labels)
    # Separator lines between altitude bins (categories sit at integer y, so edges are at i + 0.5).
    # Drawn on top (zorder=3) since they fall in the gap between hue groups and would otherwise be hidden.
    for i in range(len(altitude_order) - 1):
        a.axhline(i + 0.5, color='0.6', linewidth=0.6, zorder=0)

plt.savefig(PROJECT_ROOT / 'figures' / 'manuscript' / 'fig07_insitu.png', format='png', dpi=300, bbox_inches='tight', transparent=False)
