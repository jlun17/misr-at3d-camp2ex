"""Figure 4: chi-squared by MISR camera for the V11 retrievals.

Source: notebooks/figures/chi2.ipynb, cells 0-5 (0-based).
Run via scripts/figures/run_figures.sh (sets the working directory and PYTHONPATH).
Output: figures/manuscript/fig04_chi2.png
"""
# conda vis2
from pathlib import Path
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from cmap_dict import cmap

PROJECT_ROOT = Path().resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

plt.style.use('seaborn-v0_8-paper')

from src.ExperimentSet import ExperimentSet

es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])

def misr_S_1(y):
    return np.diag(1 / (0.04 * y)**2)

camera = np.array([])
chi2 = np.array([])
source = np.array([])

exp_name = np.array([])
chi2_exp = np.array([])
for r in list(exset.retrievals.values()):
    cam_tmp, chi2_tmp = r.get_chi2_by_camera(misr_S_1, 'MISR',  'I')
    source_tmp = [r.exp_name] * len(chi2_tmp)
    camera = np.append(camera, cam_tmp)
    chi2 = np.append(chi2, chi2_tmp)
    source = np.append(source, source_tmp)

    chi2_exp_tmp = r.get_chi2(misr_S_1, 'I')
    exp_name = np.append(exp_name, r.exp_name)
    chi2_exp = np.append(chi2_exp, chi2_exp_tmp)

df = pd.DataFrame({'camera':camera, 'chi2':chi2, 'source':source})
df_overall = pd.DataFrame({'exp_name':exp_name, 'chi2':chi2_exp}).set_index('exp_name')

sublist = ['default', 'unconstrained', 'periodic', 'surf4p0', 'aod0p150', 'aod0p250']

df_mod = df[df['source'].isin(sublist)].pivot(columns='source', index='camera', values='chi2')

cam_order = ['DF', 'CF', 'BF', 'AF', 'AN', 'AA', 'BA', 'CA', 'DA']
ax = df_mod.loc[cam_order].plot(kind='line', marker='o', color=cmap)
ax.grid()
ax.set_ylabel(r'$\chi^2$')

leg = ax.legend()

# find max label width so padding is consistent
labels = [t.get_text() for t in leg.get_texts()]
max_len = max(len(l) for l in labels)

for text in leg.get_texts():
    tmp_ex = text.get_text()
    tmp_chi2 = df_overall.loc[tmp_ex]['chi2']
    text.set_text(fr'{tmp_ex:<{max_len}}  $\chi^2={tmp_chi2:6.1f}$')
    text.set_fontfamily('monospace')

plt.savefig(PROJECT_ROOT / 'figures' / 'manuscript' / 'fig04_chi2.png', format='png', dpi=300, bbox_inches='tight', transparent=False)
