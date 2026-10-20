"""Compare files rebuilt by the pipeline with the existing ones.

Usage: python compare_outputs.py <build_root> [relative_path ...]
With no paths, compares the preprocessing outputs listed in PREPROCESSING below.

For each file: IDENTICAL if every variable, dimension and attribute in every group matches exactly;
otherwise the largest absolute difference of each differing variable and any differing attributes.
"""
import sys
from pathlib import Path
import numpy as np
import netCDF4 as nc

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OBS = 'AT3D_OBS_bbox_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712_H1400'
PREPROCESSING = [
    'mie_tables/red_mie_table.nc',
    'data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc',
    'data/interim/MISR_RAD_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712.nc',
    'data/interim/MISR_GEO_O105254_P117_R17600_X17959150_17994350_Y0201850_0237050.nc',
    'data/interim/MISR_CTH_O105254_P117_R01100_X17950900_18002600_Y0193600_0245300.nc',
    'data/interim/MISR_CMV_O105254_P117_R17600_X17959150_17994350_Y0201850_0237050.nc',
    'data/interim/MISR_OBS_CAMP2Ex_RF17_default.nc',
    'data/interim/RTG_default.nc',
    'data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc',
    'data/interim/ATMOS_ERA5_CAMP2Ex_RF17_default.nc',
    'data/interim/AEROSOL_MISR_21_0p150.nc',
    'data/interim/AEROSOL_MISR_21_0p200.nc',
    'data/interim/AEROSOL_MISR_21_0p250.nc',
    'data/interim/MIXTURE_default_ERA5.nc',
    'data/interim/MIXTURE_default_ERA5_0p150.nc',
    'data/interim/MIXTURE_default_ERA5_0p250.nc',
    *[f'data/V11/{OBS}_{s}.nc' for s in ['U1p3_V2p4', 'ATM', 'ATP', 'CTM', 'CTP']],
    'data/V11/CVM_LCL_CTH_SC_R7.nc',
    'data/V11/CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc',
    'data/V11/CVM_unconstrained_mod.nc',
]


def compare_group(a, b, prefix, diffs):
    if set(a.dimensions) != set(b.dimensions):
        diffs.append(f'{prefix}dimensions {sorted(a.dimensions)} vs {sorted(b.dimensions)}')
    else:
        for d in a.dimensions:
            if len(a.dimensions[d]) != len(b.dimensions[d]):
                diffs.append(f'{prefix}{d}: size {len(a.dimensions[d])} vs {len(b.dimensions[d])}')
    for k in sorted(set(a.ncattrs()) | set(b.ncattrs())):
        va = a.getncattr(k) if k in a.ncattrs() else None
        vb = b.getncattr(k) if k in b.ncattrs() else None
        if not np.array_equal(np.asarray(va, dtype=object), np.asarray(vb, dtype=object)):
            diffs.append(f'{prefix}@{k}: {va!r} vs {vb!r}')
    for v in sorted(set(a.variables) | set(b.variables)):
        if v not in a.variables or v not in b.variables:
            diffs.append(f'{prefix}{v}: only in {"rebuilt" if v in a.variables else "existing"}')
            continue
        xa, xb = a.variables[v][...], b.variables[v][...]
        if np.shape(xa) != np.shape(xb):
            diffs.append(f'{prefix}{v}: shape {np.shape(xa)} vs {np.shape(xb)}')
        elif np.asarray(xa).dtype.kind in 'fiuc':
            fa, fb = np.ma.filled(xa.astype(float), np.nan), np.ma.filled(xb.astype(float), np.nan)
            if not np.array_equal(fa, fb, equal_nan=True):
                diffs.append(f'{prefix}{v}: max |diff| {np.nanmax(np.abs(fa - fb)):.3e}')
        elif not np.array_equal(np.asarray(xa), np.asarray(xb)):
            diffs.append(f'{prefix}{v}: values differ')
    for g in sorted(set(a.groups) | set(b.groups)):
        if g not in a.groups or g not in b.groups:
            diffs.append(f'{prefix}{g}/: only in {"rebuilt" if g in a.groups else "existing"}')
        else:
            compare_group(a.groups[g], b.groups[g], f'{prefix}{g}/', diffs)


if __name__ == '__main__':
    build_root = Path(sys.argv[1])
    paths = sys.argv[2:] or PREPROCESSING
    n_identical = 0
    for p in paths:
        rebuilt, existing = build_root / p, PROJECT_ROOT / p
        if not rebuilt.exists() or not existing.exists():
            print(f'MISSING    {p} (rebuilt: {rebuilt.exists()}, existing: {existing.exists()})')
            continue
        diffs = []
        with nc.Dataset(rebuilt) as a, nc.Dataset(existing) as b:
            compare_group(a, b, '', diffs)
        if diffs:
            print(f'DIFFERENT  {p}')
            for d in diffs:
                print(f'    {d}')
        else:
            n_identical += 1
            print(f'IDENTICAL  {p}')
    print(f'{n_identical}/{len(paths)} identical')
