# conda env 'at3d_pure'

import sys
sys.path.append('/data/keeling/a/johntl3/b/LundstromPub2025/src')

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import at3d
import netCDF4 as nc
import os
from collections import OrderedDict
from util import load_sensor_dict

## INPUT
obs_file = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/intermediate_data/AT3D_OBS_CAMP2Ex_RF17_default_1400.nc'
rte_grid_file = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/intermediate_data/RTG_1400.nc'
background_scatterers_file = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/intermediate_data/MIXTURE_default.nc'
cloud_volume_mask_file = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/intermediate_data/CVM_LCL.nc'
config_file_name = '/data/keeling/a/johntl3/b/LundstromPub2025/configs/misr_config.json'
surface_wind_speed = 0.67 # m/s
# Reff(z) = a*z + b
a = 4.292 # um / km
b = 2.623 # um

## OUTPUT
iter_dir = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/AT3D_output/V00/CVM/LCL/iterations/'
supp_file = '/data/keeling/a/johntl3/b/LundstromPub2025/CAMP2Ex_RF17/AT3D_output/V00/CVM/LCL/loss.csv'

# Define output files
os.makedirs(iter_dir, exist_ok=False)

# Mie table directory
mie_dir = '/data/keeling/a/johntl3/b/LundstromPub2025/mie_tables/'

rte_grid = xr.load_dataset(rte_grid_file)
obs = load_sensor_dict(obs_file)

# add sensor uncertainty model
uncertainty = at3d.uncertainties.RadiometricNoiseUncertainty(1e-6, 1e-3)
obs.add_uncertainty_model('MISR', uncertainty)

forward_sensors = obs.make_forward_sensors()
wavelength = forward_sensors.get_unique_solvers()[0]

# Surface wind speed comes from ERA5 reanalysis - 
# see ./ancillary/CAMP2Ex_RF17_ERA5_Surface.ipynb
surfaces = OrderedDict()
m_water = 1.33197 - 1j*2.41e-8
surfaces[wavelength] = at3d.surface.wave_fresnel(np.real(m_water), np.imag(m_water), surface_wind_speed)

numerical_parameters = OrderedDict()
numerical_parameters[wavelength] = at3d.configuration.get_config(config_file_name)

sources = OrderedDict()
sources[wavelength] = at3d.source.solar(
    wavelength,
    -1*obs['MISR']['sensor_list'][0].mu0,
    obs['MISR']['sensor_list'][0].SAA,
    solarflux=1.0,
    skyrad=0.0
)

background_optical_scatterers = OrderedDict()
background_properties = xr.load_dataset(background_scatterers_file)
background_optical_scatterers[wavelength] = {}
background_optical_scatterers[wavelength]['background'] = background_properties

mie_mono_table = at3d.mie.get_mono_table(
    'Water',
    (wavelength, wavelength),
    max_integration_radius=65.0,
    minimum_effective_radius=5.5,
    relative_dir=mie_dir,
    verbose=False
)
mie_mono_tables = OrderedDict()
mie_mono_tables[wavelength] = mie_mono_table
# mie_mono_table.to_netcdf('{}red_mie_table.nc'.format(mie_dir))

cloud_optical_prop_gen = at3d.medium.OpticalPropertyGenerator(
    'cloud',
    mie_mono_tables,
    at3d.size_distribution.gamma,
    particle_density=1.0,
    maxnphase=None,
    interpolation_mode='exact',
    density_normalization='density',
    reff=np.linspace(1, 30, 20),
    veff=np.linspace(0.01, 0.2, 5)
)

cloud = rte_grid.copy(deep=True)
cloud['density'] = (['x','y','z'], np.zeros((rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z'])))
reff_profile = a * rte_grid.z.data + b
reff = np.tile(reff_profile, (rte_grid.dims['x'], rte_grid.dims['y'], 1))
cloud['reff'] = (['x','y','z'], reff)
cloud['veff'] = (['x','y','z'], np.ones(cloud.density.shape) * 0.1)
cloud_optical_properties = cloud_optical_prop_gen(cloud)

grid_to_optical_properties = at3d.medium.GridToOpticalProperties(
    rte_grid,
    'cloud',
    wavelength,
    fixed_dataset=cloud_optical_properties[wavelength].drop_vars('extinction')
)

cloud_volume_mask = xr.load_dataset(cloud_volume_mask_file)['cloud_volume_mask'].data
cloud_volume_mask[0,:,:] = cloud_volume_mask[-1,:,:] = cloud_volume_mask[:,0,:] = cloud_volume_mask[:,-1,:] = 0.0
extinction_coordinate_transform = None
extinction_state2grid_transform = at3d.transforms.StateToGridMask(mask=cloud_volume_mask)
extinction_transforms = (extinction_coordinate_transform, extinction_state2grid_transform)

cloud_unknown_scatterer = at3d.medium.UnknownScatterer(grid_to_optical_properties, extinction=extinction_transforms)
unknown_scatterers = at3d.containers.UnknownScatterers(cloud_unknown_scatterer)

num_stokes = OrderedDict()
num_stokes[wavelength] = 1

solvers = at3d.containers.SolversDict()
state_gen = at3d.medium.StateGenerator(
    solvers,
    unknown_scatterers,
    surfaces,
    numerical_parameters,
    sources,
    background_optical_scatterers,
    num_stokes
)
min_bounds, max_bounds = state_gen.transform_bounds()

extinction_init = cloud_volume_mask.astype(float)*0.1
extinction_init_1d = state_gen._unknown_scatterers['cloud'].variables['extinction'].state_to_grid.inverse_transform(extinction_init)
x0 = state_gen._unknown_scatterers['cloud'].variables['extinction'].coordinate_transform.inverse_transform(extinction_init_1d)
state_gen(x0)

forward_sensors.get_measurements(solvers)

parallel_solve_kwargs = {
    'n_jobs': 1,
    'mpi_comm': None, 
    'verbose': True, 
    'maxiter': 100, 
    'init_solution': True
}

objective_function = at3d.optimize.ObjectiveFunction.LevisApproxUncorrelatedL2(
    obs,
    solvers,
    forward_sensors,
    unknown_scatterers,
    state_gen,
    state_gen.project_gradient_to_state,
    parallel_solve_kwargs=parallel_solve_kwargs,
    gradient_kwargs={'cost_function': 'L2', 'exact_single_scatter':True},
    uncertainty_kwargs={'add_noise':False},
    min_bounds=min_bounds, 
    max_bounds=max_bounds
)

def save(optimizer):
    if(optimizer.iteration == None):
        outFile = '{}iter{:03d}.nc'.format(iter_dir, 0)
    else:
        outFile = '{}iter{:03d}.nc'.format(iter_dir, optimizer.iteration)
    at3d.util.save_forward_model(outFile, forward_sensors, solvers)
    with open(supp_file, mode='a') as file:
        file.write('{}, {}, {}\n'.format(optimizer.iteration, optimizer.objective_fn.loss, optimizer.objective_fn._total_obj_fn_time))
    return {'None': None}
callback = at3d.callback.CallbackFn(save)

with open(supp_file, mode='a') as file:
    file.write('iteration, loss, total_obj_fn_time\n')

optimizer = at3d.optimize.Optimizer(objective_function, callback_fn=callback)

# Save initial conditions
save(optimizer)

result = optimizer.minimize(x0)

outFile = '{}iter{:03d}.nc'.format(iter_dir, optimizer.iteration+1)
at3d.util.save_forward_model(outFile, forward_sensors, solvers)



