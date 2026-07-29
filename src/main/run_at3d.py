# conda env 'at3d_pure_k9'

import pathlib
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

import sys
sys.path.append(str(PROJECT_ROOT))

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import at3d
import netCDF4 as nc
from collections import OrderedDict
from src.utils.util import load_sensor_dict
import yaml
import time

def load_config(filename=PROJECT_ROOT / 'configs' / 'at3d_default_config.yml'):
    with open(filename, 'r') as file:
        config = yaml.safe_load(file)
    required_keys = [
        'obs_file', 'rte_grid_file', 'background_scatterers_file',
        'cloud_volume_mask_file', 'config_file_name', 'surface_wind_speed',
        'a', 'b', 'error_cov_sf', 'restart_iter', 'out_path'
    ]
    for key in required_keys:
        assert key in config, f'{key} not in config'
    
    # Convert paths in the config to pathlib.Path objects
    required_keys.remove('surface_wind_speed')
    required_keys.remove('a')
    required_keys.remove('b')
    required_keys.remove('error_cov_sf')
    if(config['restart_iter'].lower() == 'none'):
        required_keys.remove('restart_iter')
    for key in required_keys:
        config[key] = PROJECT_ROOT / config[key]
    return config

if __name__ == '__main__':
    if(len(sys.argv) > 1):
        config = load_config(sys.argv[1])
    elif(len(sys.argv) == 1):
        config = load_config() # load default config
    else:
        config = None

    iter_dir = config['out_path'] / 'iterations'
    supp_file = config['out_path'] / 'loss.csv'

    # Define output files
    iter_dir.mkdir(parents=True, exist_ok=True)
    assert not any(iter_dir.iterdir()), f"Iterations already saved in {iter_dir}.\nSpecify a new output location."

    # Load rte grid and observations
    rte_grid = xr.load_dataset(config['rte_grid_file'])
    obs = load_sensor_dict(config['obs_file'])

    # add sensor uncertainty model
    uncertainty = at3d.uncertainties.NullUncertainty('L2', scaling_factor=config['error_cov_sf'])
    obs.add_uncertainty_model('MISR', uncertainty)

    # Make forward sensors
    forward_sensors = obs.make_forward_sensors()
    wavelength = forward_sensors.get_unique_solvers()[0]

    # Define surface reflectance model based on surface wind speed
    surfaces = OrderedDict()
    m_water = 1.33197 - 1j*2.41e-8
    surfaces[wavelength] = at3d.surface.wave_fresnel(np.real(m_water), np.imag(m_water), config['surface_wind_speed'])

    # Load SHODM numerical parameters
    numerical_parameters = OrderedDict()
    numerical_parameters[wavelength] = at3d.configuration.get_config(config['config_file_name'])

    # Set solar source
    sources = OrderedDict()
    sources[wavelength] = at3d.source.solar(
        wavelength,
        -1*obs['MISR']['sensor_list'][0].mu0,
        obs['MISR']['sensor_list'][0].SAA,
        solarflux=1.0,
        skyrad=0.0
    )

    # Load background atmosphere
    background_optical_scatterers = OrderedDict()
    background_properties = xr.load_dataset(config['background_scatterers_file'])
    background_optical_scatterers[wavelength] = {}
    background_optical_scatterers[wavelength]['background'] = background_properties

    # Generate cloud optical properties
    mie_mono_table = at3d.mie.get_mono_table(
        'Water',
        (wavelength, wavelength),
        max_integration_radius=65.0,
        minimum_effective_radius=5.5,
        relative_dir=PROJECT_ROOT / 'mie_tables',
        verbose=False
    )
    mie_mono_tables = OrderedDict()
    mie_mono_tables[wavelength] = mie_mono_table
    # mie_mono_table.to_netcdf(PROJECT_ROOT / 'mie_tables' / 'red_mie_table.nc')
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
    reff_profile = config['a'] * rte_grid.z.data + config['b']
    reff = np.tile(reff_profile, (rte_grid.dims['x'], rte_grid.dims['y'], 1))
    cloud['reff'] = (['x','y','z'], reff)
    cloud['veff'] = (['x','y','z'], np.ones(cloud.density.shape) * 0.1)
    cloud_optical_properties = cloud_optical_prop_gen(cloud)

    # Generate unknown scatterers
    grid_to_optical_properties = at3d.medium.GridToOpticalProperties(
        rte_grid,
        'cloud',
        wavelength,
        fixed_dataset=cloud_optical_properties[wavelength].drop_vars('extinction')
    )
    cloud_volume_mask = xr.load_dataset(config['cloud_volume_mask_file'])['cloud_volume_mask'].data
    if(numerical_parameters[wavelength].x_boundary_condition.data == 'open'):
        cloud_volume_mask[0,:,:] = cloud_volume_mask[-1,:,:] = 0
    if(numerical_parameters[wavelength].y_boundary_condition.data == 'open'):
        cloud_volume_mask[:,0,:] = cloud_volume_mask[:,-1,:] = 0
    extinction_coordinate_transform = None
    extinction_state2grid_transform = at3d.transforms.StateToGridMask(mask=cloud_volume_mask)
    extinction_transforms = (extinction_coordinate_transform, extinction_state2grid_transform)
    cloud_unknown_scatterer = at3d.medium.UnknownScatterer(grid_to_optical_properties, extinction=extinction_transforms)
    unknown_scatterers = at3d.containers.UnknownScatterers(cloud_unknown_scatterer)

    # Set polarization
    num_stokes = OrderedDict()
    num_stokes[wavelength] = 1

    # Set forward model
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

    # Initialize extinction
    if(type(config['restart_iter']) == pathlib.PosixPath):
        restart_sensor, restart_solver, restart_rte_grid = at3d.util.load_forward_model(config['restart_iter'])
        extinction_init = restart_solver[wavelength].medium['cloud'].extinction.data
    else:
        extinction_init = cloud_volume_mask.astype(float)*0.1
    extinction_init_1d = state_gen._unknown_scatterers['cloud'].variables['extinction'].state_to_grid.inverse_transform(extinction_init)
    x0 = state_gen._unknown_scatterers['cloud'].variables['extinction'].coordinate_transform.inverse_transform(extinction_init_1d)
    state_gen(x0)

    # Forward simulate initialization
    forward_sensors.get_measurements(solvers)

    # Set objective function
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

    # Callback function
    def save(optimizer):
        if(optimizer.iteration == None):
            outFile = iter_dir / 'iter{:03d}.nc'.format(0)
        else:
            outFile = iter_dir / 'iter{:03d}.nc'.format(optimizer.iteration)
        at3d.util.save_forward_model(outFile, forward_sensors, solvers)
        with open(supp_file, mode='a') as file:
            file.write('{}, {}, {}\n'.format(optimizer.iteration, optimizer.objective_fn.loss, optimizer.objective_fn._total_obj_fn_time))
        return {'None': None}
    callback = at3d.callback.CallbackFn(save)

    # Generate supplementary file
    with open(supp_file, mode='a') as file:
        file.write('iteration, loss, total_obj_fn_time\n')

    # Setup optimizer
    options = {'maxiter': 100, 'maxls': 25, 'disp': True, 'gtol': 1e-16, 'ftol': 1e-8}
    optimizer = at3d.optimize.Optimizer(objective_function, callback_fn=callback, options=options)

    # Save initial conditions
    save(optimizer)

    # Perform retrieval
    start_time = time.time()
    result = optimizer.minimize(x0)
    end_time = time.time()

    # Save final retrieval
    outFile = iter_dir / 'iter{:03d}.nc'.format(optimizer.iteration+1)
    at3d.util.save_forward_model(outFile, forward_sensors, solvers)

    # Print execution time
    print('Execution time: {} seconds'.format(end_time - start_time))

