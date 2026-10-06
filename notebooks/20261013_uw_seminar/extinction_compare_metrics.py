import numpy as np
from scipy.stats import wasserstein_distance
from scipy.spatial.distance import dice, jaccard, hamming

def fcn_MBE(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return (1/len(r1)) * np.sum(r1 - r2)

def fcn_RMSD(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return ((1/len(r1)) * np.sum((r1 - r2)**2))**0.5

def fcn_rel_bias(r1, r2):
    return 100 * (np.nansum(np.abs(r1)) - np.nansum(np.abs(r2))) / (np.nansum(np.abs(r2)))

def fcn_rel_rmsd(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return 100 * (np.sum((r1 - r2)**2)**0.5) / (np.sum(r2**2)**0.5)

def fcn_cf(r1, r2):
    return calc_cf(r1) - calc_cf(r2)

def fcn_ncloud(r1, r2):
    return calc_ncloud(r1) - calc_ncloud(r2)

def fcn_rel_vol(r1, r2):
    return 100 * (calc_ncloud(r1) - calc_ncloud(r2)) / calc_ncloud(r2)

def fcn_rel_bias_intersection(r1, r2):
    r1b = r1 > 0
    r2b = r2 > 0
    M11 = (r1b == True) & (r2b == True)
    return fcn_rel_bias(r1[M11], r2[M11])

def fcn_rel_rmsd_intersection(r1, r2):
    r1b = r1 > 0
    r2b = r2 > 0
    M11 = (r1b == True) & (r2b == True)
    return fcn_rel_rmsd(r1[M11], r2[M11])

def fcn_pearson_corr(r1, r2):
    cond = np.logical_or(np.logical_not(np.isnan(r1)), np.logical_not(np.isnan(r2)))
    r1 = r1[cond]
    r2 = r2[cond]
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1bar = np.mean(r1)
    r2bar = np.mean(r2)
    return (np.sum((r1 - r1bar) * (r2 - r2bar))) / (np.sum((r1 - r1bar)**2)**0.5 * np.sum((r2 - r2bar)**2)**0.5)

def fcn_jaccard(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1 = r1 > 0.0
    r2 = r2 > 0.0
    return 1 - jaccard(np.ravel(r1), np.ravel(r2))

def fcn_inv_jaccard(r1, r2):
    r1b = r1 > 0
    r2b = r2 > 0
    M11 = (r1b == True) & (r2b == True)
    M01 = (r1b == False) & (r2b == True)
    M10 = (r1b == True) & (r2b == False)
    # return np.sum(M10) / (np.sum(M01) + np.sum(M10) + np.sum(M11))
    return np.sum(M10) / (np.sum(M01) + np.sum(M10))

def calc_cf(r):
    r = np.atleast_3d(r)
    tmp = np.nansum(r, axis=2)
    cf = np.sum(tmp > 0) / np.size(tmp)
    return cf

def calc_ncloud(r):
    r[np.isnan(r)] = 0
    tmp = r > 0
    return np.sum(tmp)

stat_dict = {
    'Relative Bias (%)':{
        'fcn': fcn_rel_bias,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -60, 'vmax': 60}
    },
    'Relative RMSD (%)':{
        'fcn': fcn_rel_rmsd,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 100}
    },
    'Relative Bias Intersection (%)':{
        'fcn': fcn_rel_bias_intersection,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -60, 'vmax': 60}
    },
    # 'Mear Bias Error $[km^{-1}]$':{
    #     'fcn': fcn_MBE,
    #     'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -170, 'vmax': 170}
    # },
    'Relative RMSD Intersection (%)':{
            'fcn': fcn_rel_rmsd_intersection,
            'heat_kwargs': {'fmt': '.0f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 100}
        },
    # 'RMSD $[km^{-1}]$':{
    #     'fcn': fcn_RMSD,
    #     'heat_kwargs': {'fmt': '.0f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 90}
    # },
    # 'Delta Cloud Fraction': {
    #     'fcn': fcn_cf,
    #     'heat_kwargs': {'fmt': '.3f', 'cmap': 'RdBu_r', 'vmin': -0.3, 'vmax': 0.3}
    # },
    # 'Delta Number Cloud Points': {
    #     'fcn': fcn_ncloud,
    #     'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -4000, 'vmax': 4000}
    # },
    # 'Relative Volume Enhancement (%)': {
    #     'fcn': fcn_rel_vol,
    #     'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -100, 'vmax': 100}
    # },
    # 'Pearson Correlation':{
    #     'fcn': fcn_pearson_corr,
    #     'heat_kwargs': {'fmt': '.2f', 'cmap': 'BrBG', 'vmin': -1, 'vmax': 1}
    # },
    'Jaccard Index':{
        'fcn': fcn_jaccard,
        'heat_kwargs': {'fmt': '.2f', 'cmap': 'Greens', 'vmin': 0, 'vmax': 1}
    },
    'Inverse Jaccard':{
        'fcn': fcn_inv_jaccard,
        'heat_kwargs': {'fmt': '.2f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 1}
    }
}
