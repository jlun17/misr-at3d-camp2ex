import numpy as np
from scipy.stats import wasserstein_distance
from scipy.spatial.distance import dice, jaccard, hamming

def fcn_rel_bias(r1, r2):
    """Bias of r2 relative to r1"""
    return 100 * (np.nansum(np.abs(r2)) - np.nansum(np.abs(r1))) / (np.nansum(np.abs(r1)))

def fcn_abs_bias(r1, r2):
    """Bias of r2 relative to r1"""
    return (np.nansum(np.abs(r2)) - np.nansum(np.abs(r1)))

def fcn_MBE(r1, r2):
    """Mean bias error"""
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return (1/len(r1)) * np.sum(r2 - r1)

def fcn_rel_rmse(r1, r2):
    """RMSE of r2 relative to r1"""
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return 100 * (np.sum((r2 - r1)**2)**0.5) / (np.sum(r1**2)**0.5)

def fcn_RMSD(r1, r2):
    """Root Mean Squared Difference"""
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return ((1/len(r1)) * np.sum((r2 - r1)**2))**0.5

def fcn_wasserstein(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    return wasserstein_distance(np.ravel(r1), np.ravel(r2))

def fcn_pearson_corr(r1, r2):
    cond = np.logical_or(np.logical_not(np.isnan(r1)), np.logical_not(np.isnan(r2)))
    r1 = r1[cond]
    r2 = r2[cond]
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1bar = np.mean(r1)
    r2bar = np.mean(r2)
    return (np.sum((r1 - r1bar) * (r2 - r2bar))) / (np.sum((r1 - r1bar)**2)**0.5 * np.sum((r2 - r2bar)**2)**0.5)

def fcn_dice_dissimilarity(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1 = r1 >= 0.3
    r2 = r2 >= 0.3
    return dice(np.ravel(r1), np.ravel(r2))

def fcn_jaccard(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1 = r1 >= 0.3
    r2 = r2 >= 0.3
    return 1 - jaccard(np.ravel(r1), np.ravel(r2))

def fcn_simple_matching_coef(r1, r2):
    r1[np.isnan(r1)] = 0
    r2[np.isnan(r2)] = 0
    r1 = r1 >= 0.3
    r2 = r2 >= 0.3
    return 1 - hamming(np.ravel(r1), np.ravel(r2))

stat_dict = {
    'Relative Bias (%)':{
        'fcn': fcn_rel_bias,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -60, 'vmax': 60}
    },
    'Mear Bias Error $[km^{-1}]$':{
        'fcn': fcn_MBE,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'RdBu_r', 'vmin': -170, 'vmax': 170}
    },
    'Relative RMSD (%)':{
        'fcn': fcn_rel_rmse,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 100}
    },
    'RMSD $[km^{-1}]$':{
        'fcn': fcn_RMSD,
        'heat_kwargs': {'fmt': '.0f', 'cmap': 'Reds', 'vmin': 0, 'vmax': 90}
    },
    'Pearson Correlation':{
        'fcn': fcn_pearson_corr,
        'heat_kwargs': {'fmt': '.2f', 'cmap': 'BrBG', 'vmin': -1, 'vmax': 1}
    },
    'Jaccard Index':{
        'fcn': fcn_jaccard,
        'heat_kwargs': {'fmt': '.2f', 'cmap': 'Greens', 'vmin': 0, 'vmax': 1}
    },
}
