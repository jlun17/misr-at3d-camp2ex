"""Figure B1: MISR BRF vs SHDOM angular resolution (n_mu) for 0.67 and 4.0 m/s surface wind (1D runs).

Source: notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb, cells 1, 2, 4, 5, 6 (0-based).
Reads the 1D SHDOM output in notebooks/surface_parameterization_testing/output1D/.
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/figB1_surface.png
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.utils.util import load_sensor_dict

plt.style.use('seaborn-v0_8-paper')

outdir = PROJECT_ROOT / 'notebooks' / 'surface_parameterization_testing' / 'output1D'

df = pd.DataFrame()
for sensor_file in outdir.glob('*.nc'):
    wind_speed = float(sensor_file.stem.split('_')[0][4:].replace('p', '.'))
    n_mu = int(sensor_file.stem.split('_')[1][2:])
    n_phi = int(sensor_file.stem.split('_')[2][3:])
    sensor_list = load_sensor_dict(sensor_file)
    for sensor in sensor_list['MISR']['sensor_list']:
        tmp_df = sensor.drop([
            'cam_x', 
            'cam_y', 
            'cam_z', 
            'cam_mu', 
            'cam_phi', 
            'ray_mu', 
            'ray_phi', 
            'wavelength', 
            'stokes', 
            'ray_x', 
            'ray_y', 
            'ray_z', 
            'pixel_index', 
            'ray_weight', 
            'use_subpixel_rays'
        ]).to_dataframe().reset_index()
        tmp_df['wind_speed'] = wind_speed
        tmp_df['n_mu'] = n_mu
        tmp_df['n_phi'] = n_phi
        tmp_df['camera'] = sensor.name
        tmp_df['brf'] = (tmp_df['I'] * np.pi) / sensor.mu0
        df = pd.concat([df, tmp_df])

df_grp = df.groupby(['n_mu', 'wind_speed', 'camera']).brf.aggregate('mean').reset_index()

cams = ['DF', 'DA', 'CF', 'CA', 'BF', 'BA', 'AF', 'AA', 'AN']
f, ax = plt.subplots(3, 3, figsize=(6.5, 5.5), sharex=True, sharey=True)
for a, cam in zip(ax.flatten(), cams):
    df_grp[
        (df_grp['camera'] == cam) &
        (df_grp['n_mu'] >= 16) &
        (df_grp['wind_speed'] == 0.67)
    ].plot.line(x='n_mu', y='brf', ax=a, color='k', label='0.67 m/s', legend=False)
    df_grp[
        (df_grp['camera'] == cam) &
        (df_grp['n_mu'] >= 16) &
        (df_grp['wind_speed'] == 4.0)
    ].plot.line(x='n_mu', y='brf', ax=a, color='k', ls='--', label='4.0 m/s', legend=False)
    a.grid()
    a.set_title(cam)
    a.set_xscale('log', base=2)
f.tight_layout()
ax[1,2].legend(title='Surface Wind Speed')
ax[0,0].set_ylabel('brf')
ax[1,0].set_ylabel('brf')
ax[2,0].set_ylabel('brf')

plt.savefig(PROJECT_ROOT / 'figures' / 'manuscript' / 'figB1_surface.png', format='png', dpi=300, bbox_inches='tight', transparent=False)
