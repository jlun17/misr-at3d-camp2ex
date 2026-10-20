"""Crop the 149 km TradeCumulus field to the small retrieval domains and zero their edge columns.

Source: subset_stochastic.ipynb (copied from Synthetic/IO/thesis), cells idx 0-2.
Conda env: at3d_pure_k9 (the notebook kernel was at3d_pure, which no longer imports at3d: libgfortran.so.3 is missing)
Input:  data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc
Output: data/synthetic/thesis/TradeCumulus/len{005,007,009,011,015,019}/ex00_density.nc
Changes: paths point to OUT_ROOT/data/synthetic; fields restricted to TradeCumulus, the only field the
         manuscript uses.
"""
import xarray as xr
import os

SYN = os.path.join(os.environ.get('OUT_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')), 'data', 'synthetic')

cu_path = os.path.join(SYN, 'thesis', 'TradeCumulus')

fields = [cu_path]
lengths = [5, 7, 9, 11, 15, 19]
length_strs = ['/len{:03d}'.format(i) for i in lengths]
large = '/len149'
expr = '/ex00'

for f in fields:
    largeFile = f + large + expr + '_density.nc'
    cloud = xr.load_dataset(largeFile)
    cx = cloud.sizes['x'] // 2
    cy = cloud.sizes['y'] // 2
    for l, ls in zip(lengths, length_strs):
        dx = dy = l // 2
        outfile = f + ls + expr + '_density.nc'
        os.makedirs(f + ls, exist_ok=True)
        tmpcloud = cloud.isel(x=slice(cx-dx, cx+dx+1), y=slice(cy-dy, cy+dy+1)).copy(deep=True)
        tmpdensity = tmpcloud.density.data
        tmpdensity[:,0,:] = tmpdensity[:,-1,:] = tmpdensity[0,:,:] = tmpdensity[-1,:,:] = 0.0
        tmpcloud['density'] = (['x','y','z'], tmpdensity)
        tmpcloud.to_netcdf(outfile)
