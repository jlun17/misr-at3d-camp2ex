# %%
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import at3d
import netCDF4 as nc
import os
from collections import OrderedDict

# %%
def load_measurements(file_name):
    """
    Load from netCDF the sensors that were saved using 'save_forward_model'
    above. Adapted from at3d.util.load_forward_model.
    """
    dataset = nc.Dataset(file_name)

    groups = dataset.groups
    sensors = groups['sensors'].groups
    sensor_dict = at3d.containers.SensorsDict()

    for key, sensor in sensors.items():
        sensor_list = []
        for i, image in sensor.groups.items():
            sensor_dataset = xr.open_dataset(xr.backends.NetCDF4DataStore(dataset[
                'sensors/{}/{}'.format(key, i)]))
            sensor_dataset['stokes'] = (['stokes_index'],sensor_dataset['stokes'].data.astype(bool))
            sensor_dataset['use_subpixel_rays'] = sensor_dataset['use_subpixel_rays'].data.astype(bool)
            sensor_dict.add_sensor(key, sensor_dataset)
    return sensor_dict


# %%
expr_dir = '../dev/'

# %%
rte_grid = xr.load_dataset('{}rte_grid.nc'.format(expr_dir))
measurements = load_measurements('{}measurements.nc'.format(expr_dir))

# %%
uncertainty = at3d.uncertainties.RadiometricNoiseUncertainty(1e-6, 1e-3)
measurements.add_uncertainty_model('MISR', uncertainty)

# %%
forward_sensors = measurements.make_forward_sensors()
wavelength = forward_sensors.get_unique_solvers()[0]

# %%
# Surface wind speed comes from ERA5 reanalysis - 
# see ./ancillary/CAMP2Ex_RF17_ERA5_Surface.ipynb
surfaces = OrderedDict()
m_water = 1.33197 - 1j*2.41e-8
surface_wind_speed = 0.538
surfaces[wavelength] = at3d.surface.wave_fresnel(np.real(m_water), np.imag(m_water), surface_wind_speed)

# %%
numerical_parameters = OrderedDict()
config_file_name = '../configs/misr_config.json'
numerical_parameters[wavelength] = at3d.configuration.get_config(config_file_name)

# %%
sources = OrderedDict()
sources[wavelength] = at3d.source.solar(
    wavelength,
    -1*measurements['MISR']['sensor_list'][0].mu0,
    measurements['MISR']['sensor_list'][0].SAA,
    solarflux=1.0,
    skyrad=0.0
)

# %%
background_optical_scatterers = OrderedDict()
merged_properties = xr.load_dataset('{}atmos_aerosol_merge.nc'.format(expr_dir))
background_optical_scatterers[wavelength] = {}
background_optical_scatterers[wavelength]['background'] = merged_properties

# %%
mie_mono_table = at3d.mie.get_mono_table(
    'Water',
    (wavelength, wavelength),
    max_integration_radius=65.0,
    minimum_effective_radius=5.5,
    relative_dir='../mie_tables',
    verbose=False
)
mie_mono_tables = OrderedDict()
mie_mono_tables[wavelength] = mie_mono_table
# mie_mono_table.to_netcdf('../mie_tables/red_mie_table.nc')

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

# %%
cloud = rte_grid.copy(deep=True)
cloud['density'] = (['x','y','z'], np.zeros((rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z'])))
# See ./ancillary/CAMP2Ex_SPEC.ipynb for Re calculation
reff_profile = 4.41088483 * rte_grid.z.data + 2.991867942556189
reff = np.tile(reff_profile, (rte_grid.dims['x'], rte_grid.dims['y'], 1))
cloud['reff'] = (['x','y','z'], reff)
cloud['veff'] = (['x','y','z'], np.ones(cloud.density.shape) * 0.1)
cloud_optical_properties = cloud_optical_prop_gen(cloud)

# %%
grid_to_optical_properties = at3d.medium.GridToOpticalProperties(
    rte_grid,
    'cloud',
    wavelength,
    fixed_dataset=cloud_optical_properties[wavelength].drop_vars('extinction')
)

## TODO: Create real cloud volume mask
# cloud_volume_mask = np.zeros(shape=(rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z']))
# cloud_volume_mask[:,:,np.bitwise_and(rte_grid.z.data >= 0.4, rte_grid.z.data <= 1.4)] = 1
cloud_volume_mask = xr.load_dataset('{}cloud_volume_mask_03.nc'.format(expr_dir))['cloud_volume_mask'].data
cloud_volume_mask[0,:,:] = cloud_volume_mask[-1,:,:] = cloud_volume_mask[:,0,:] = cloud_volume_mask[:,-1,:] = 0.0
extinction_coordinate_transform = None
extinction_state2grid_transform = at3d.transforms.StateToGridMask(mask=cloud_volume_mask)
extinction_transforms = (extinction_coordinate_transform, extinction_state2grid_transform)

cloud_unknown_scatterer = at3d.medium.UnknownScatterer(grid_to_optical_properties, extinction=extinction_transforms)
unknown_scatterers = at3d.containers.UnknownScatterers(cloud_unknown_scatterer)

# %%
num_stokes = OrderedDict()
num_stokes[wavelength] = 1

# %%
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

# %%
extinction_init = cloud_volume_mask.astype(float)*0.1
extinction_init_1d = state_gen._unknown_scatterers['cloud'].variables['extinction'].state_to_grid.inverse_transform(extinction_init)
x0 = state_gen._unknown_scatterers['cloud'].variables['extinction'].coordinate_transform.inverse_transform(extinction_init_1d)
state_gen(x0)

# %%
forward_sensors.get_measurements(solvers)

# %%
parallel_solve_kwargs = {
    'n_jobs': 1,
    'mpi_comm': None, 
    'verbose': True, 
    'maxiter': 100, 
    'init_solution': True
}

objective_function = at3d.optimize.ObjectiveFunction.LevisApproxUncorrelatedL2(
    measurements,
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

# %%
def save(optimizer):
    base = '{}iterations/'.format(expr_dir)
    os.makedirs(base, exist_ok=True)
    if(optimizer.iteration == None):
        outFile = '{}iter{:03d}.nc'.format(base, 0)
    else:
        outFile = '{}iter{:03d}.nc'.format(base, optimizer.iteration)
    at3d.util.save_forward_model(outFile, forward_sensors, solvers)
    return {'None': None}
callback = at3d.callback.CallbackFn(save)

# %%
optimizer = at3d.optimize.Optimizer(objective_function, callback_fn=callback)

# %%
# Save initial conditions
save(optimizer)

# %%
result = optimizer.minimize(x0)

# %%
outFile = '{}iterations/iter{:03d}.nc'.format(expr_dir, optimizer.iteration+1)
at3d.util.save_forward_model(outFile, forward_sensors, solvers)

# %%



