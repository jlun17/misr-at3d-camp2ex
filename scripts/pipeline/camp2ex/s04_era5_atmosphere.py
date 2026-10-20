"""Molecular (Rayleigh) atmosphere on the RTE grid from ERA5.

Source: notebooks/preprocessing/ERA5_atmosphere.ipynb (HEAD), cells idx 0-2 and 4 (Default section).
Conda env: at3d_pure_k9 (the notebook header says at3d_metpy; its kernel is at3d_pure_k9)
Inputs: data/raw/era5/ERA5_upper_CAMP2Ex_RF17_wide.nc, data/raw/era5/ERA5_surface_CAMP2Ex_RF17_wide_extra.nc,
        data/interim/RTG_default.nc (s03)
Output: data/interim/ATMOS_ERA5_CAMP2Ex_RF17_default.nc
Changes: data paths are OUT_ROOT-relative; plotting dropped.
"""
import xarray as xr
import numpy as np
import at3d

from pathlib import Path
import os
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
INTERIM_DATA = OUT_ROOT / 'data' / 'interim'
RAW_DATA = OUT_ROOT / 'data' / 'raw'

## INPUT
# ERA Upper
era_upper_file = RAW_DATA / 'era5' / 'ERA5_upper_CAMP2Ex_RF17_wide.nc'
era_upper = xr.load_dataset(era_upper_file)
# ERA surface
era_surf_file = RAW_DATA / 'era5' / 'ERA5_surface_CAMP2Ex_RF17_wide_extra.nc'
era_surf = xr.load_dataset(era_surf_file)
# Wavelength
wavelength = 0.67

interp_time = [np.datetime64('2019-10-02T02:40:00')]
interp_lat = 19.266
interp_lon = 119.724

era_upper_interp = era_upper.interp(valid_time=interp_time).isel(valid_time=0)
era_upper_interp = era_upper_interp.interp(latitude = interp_lat)
era_upper_interp = era_upper_interp.interp(longitude = interp_lon)
era_surf_interp = era_surf.interp(valid_time=interp_time).isel(valid_time=0)
era_surf_interp = era_surf_interp.interp(latitude = interp_lat)
era_surf_interp = era_surf_interp.interp(longitude = interp_lon)

# Convert geopotential (m^2 s^-2) to altitude
Re = 6.371e6 # m
g = 9.80665 # m s^-2
Phi = era_upper_interp.z.data
z = (Phi * Re) / (g * Re - Phi)
z *= 1e-3

T = np.append([era_surf_interp.t2m.data], era_upper_interp.t.data)
P = np.append([era_surf_interp.sp.data*1e-2], era_upper_interp.pressure_level.data)
z = np.append([0], z)

atmosphere = xr.Dataset(
    data_vars={
        'temperature': (['z'], T),
        'pressure': (['z'], P)
    },
    coords={
        'z': z
    }
)

"""
Account for the molecular atmosphere above the domain by changing the extinction in the top layer.
This algorithm ensures that the 'compensated' optical depth agrees with the 'exact' optical depth.
"""
rte_grid_file = INTERIM_DATA / 'RTG_default.nc'
rte_grid = xr.load_dataset(rte_grid_file)
out_file = INTERIM_DATA / 'ATMOS_ERA5_CAMP2Ex_RF17_default.nc'

atmosphere_optical_properties = at3d.rayleigh.to_grid(wavelength, atmosphere, rte_grid)

rte_grid_exact = rte_grid.copy(deep=True)
rte_grid_exact['z'] = atmosphere.z
atmosphere_optical_properties_exact = at3d.rayleigh.to_grid(wavelength, atmosphere, rte_grid_exact)
tau_exact = atmosphere_optical_properties_exact[wavelength].isel(x=0,y=0).extinction.integrate('z').data

rte_grid_minus1 = rte_grid.copy(deep=True)
rte_grid_minus1['z'] = rte_grid.z[:-1]
atmosphere_optical_properties_minus1 = at3d.rayleigh.to_grid(wavelength, atmosphere, rte_grid_minus1)
tau_minus1 = atmosphere_optical_properties_minus1[wavelength].isel(x=0,y=0).extinction.integrate('z').data

del_tau = tau_exact - tau_minus1
h = rte_grid.z.data[-1] - rte_grid.z.data[-2]
xmax = atmosphere_optical_properties_minus1[wavelength].isel(x=0,y=0, z=-1).extinction.data
compensation_extinction = ((2*del_tau)/h) - xmax
atmosphere_optical_properties_comp = {}
atmosphere_optical_properties_comp[wavelength] = atmosphere_optical_properties[wavelength].copy(deep=True)
extinction = atmosphere_optical_properties[wavelength].extinction.copy(deep=True).data
extinction[:,:,-1] = compensation_extinction
atmosphere_optical_properties_comp[wavelength]['extinction'] = (['x','y','z'], extinction)

atmosphere_optical_properties_comp[wavelength].to_netcdf(out_file)
