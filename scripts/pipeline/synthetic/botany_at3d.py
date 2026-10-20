"""
Parameters
----------
space_carve: dict
    'threshold': list
        camera by camera threshold
    'agreement': tuple
        First element is number of rays threshold
        Second element is number of sensors threshold
objective_function: dict
    parallel_solve_kwargs: dict
        'n_jobs': int
            number of parallel threads
        'mpi_comm': None
        'verbose': boolean
        'maxiter': int
        'init_solution': boolean
    gradient_kwargs: dict
        'cost_function': string
            Often L2
        'exact_single_scatter': boolean
    uncertainty_kwargs: dict
        'add_noise': boolean
at3d: dict
    'max_iters': int
        Maximum number of optimization iterations (i.e. number of Jacobian
        evaluations).
    'init_extinction': float
        Extinction [1/km] for at3d initialization. Uniform throughout unknowns.
"""

import at3d
import numpy as np
from collections import OrderedDict
import yaml
import os
import sys

infile = sys.argv[1]
with open(infile, "r") as file:
    indata = yaml.load(file, Loader=yaml.FullLoader)
wavelen = indata['source']['wavelength']

filename = os.path.splitext(infile)[0] + '_syntheticObs.nc'
sensor_dict_obs, solver_dict_obs, rte_grid_obs = at3d.util.load_forward_model(filename)

# Space carving
spc_crv = indata['space_carve']
sensor_list = []
for i, sensor in enumerate(sensor_dict_obs[indata['sensors']['name']]['sensor_list']):
    copied = sensor.copy(deep=True)
    weights = np.zeros(sensor.sizes['nrays'])
    ray_mask =np.zeros(sensor.sizes['nrays'], dtype=int)
    ray_mask_pixel = np.zeros(sensor.npixels.size, dtype=int)
    thresh = spc_crv['threshold'][i]
    ray_mask_pixel[np.where(sensor.I.data > thresh)] = 1
    copied['weights'] = ('nrays',sensor.I.data)
    copied['cloud_mask'] = ('nrays', ray_mask_pixel[sensor.pixel_index.data])
    sensor_list.append(copied)
bcflag = 0
if(solver_dict_obs[wavelen].numerical_params.x_boundary_condition.data == 'open'):
    bcflag += 1
if(solver_dict_obs[wavelen].numerical_params.y_boundary_condition.data == 'open'):
    bcflag += 2
space_carver = at3d.space_carve.SpaceCarver(rte_grid_obs, bcflag = bcflag)
carved_volume = space_carver.carve(sensor_list, agreement=spc_crv['agreement'])
carved_volume.mask[0] = carved_volume.mask[-1] = carved_volume.mask[:,0] = carved_volume.mask[:,-1] = carved_volume.mask[:,:,-1] = 0.0
carved_volume.to_netcdf(os.path.splitext(infile)[0] + '_carvedVolume.nc')

# Make sensor dict forward. This is the object that will store the evaluation of
# the forward model at each iteration.
sensor_dict_forward = sensor_dict_obs.make_forward_sensors()

# Uncertainty model to the observations
uncertainty = at3d.uncertainties.RadiometricNoiseUncertainty(1e-7, 1e-5)
sensor_dict_obs.add_uncertainty_model(indata['sensors']['name'], uncertainty)

# prepare all of the static inputs to the solver just copy pasted from forward model
surfaces = OrderedDict()
numerical_parameters = OrderedDict()
sources = OrderedDict()
num_stokes = OrderedDict()
background_optical_scatterers = OrderedDict()
for key in sensor_dict_obs.get_unique_solvers():
    surfaces[key] = solver_dict_obs[key].surface
    numerical_parameters[key] = solver_dict_obs[key].numerical_params
    sources[key] = solver_dict_obs[key].source
    num_stokes[key] = solver_dict_obs[key]._nstokes
    background_optical_scatterers[key] = {'rayleigh': solver_dict_obs[key].medium['rayleigh']}

# Make unknown scatterers
optical_properties = solver_dict_obs[wavelen].medium['cloud'].copy(deep=True)
optical_properties = optical_properties.drop_vars('extinction')
grid_to_optical_props = at3d.medium.GridToOpticalProperties(rte_grid_obs,
                                                            'cloud',
                                                            wavelen,
                                                            optical_properties)
mask = carved_volume.mask.copy(deep=True).data
unknown_scatterer = at3d.medium.UnknownScatterer(grid_to_optical_props,
                                                 extinction=(None, at3d.transforms.StateToGridMask(mask=mask)))
unknown_scatterers = at3d.containers.UnknownScatterers(unknown_scatterer)

# Make solver dict forward
solver_dict_forward = at3d.containers.SolversDict()
state_gen = at3d.medium.StateGenerator(solver_dict_forward,
                                       unknown_scatterers,
                                       surfaces,
                                       numerical_parameters,
                                       sources,
                                       background_optical_scatterers,
                                       num_stokes)
min_bounds, max_bounds = state_gen.transform_bounds()
solver_dict_forward

# Make objective function
obj_fcn = indata['objective_function']
parallel_solve_kwargs = obj_fcn['parallel_solve_kwargs']
gradient_kwargs = obj_fcn['gradient_kwargs']
uncertainty_kwargs = obj_fcn['uncertainty_kwargs']
objective_function = at3d.optimize.ObjectiveFunction.LevisApproxUncorrelatedL2(
    sensor_dict_obs,
    solver_dict_forward,
    sensor_dict_forward,
    unknown_scatterers,
    state_gen,
    state_gen.project_gradient_to_state,
    parallel_solve_kwargs=parallel_solve_kwargs,
    gradient_kwargs=gradient_kwargs,
    uncertainty_kwargs=uncertainty_kwargs,
    min_bounds=min_bounds,
    max_bounds=max_bounds
)

def save(optimizer):
    base = os.path.splitext(infile)[0] + '_iterations/'
    os.makedirs(base, exist_ok=True)
    outFile = base + 'iter{:03d}.nc'.format(optimizer.iteration)
    at3d.util.save_forward_model(outFile, sensor_dict_forward, solver_dict_forward)
    return {'None': None}
callback = at3d.callback.CallbackFn(save)

optimizer = at3d.optimize.Optimizer(objective_function,
                                    prior_fn=None,
                                    callback_fn=callback,
                                    method='L-BFGS-B',
                                    options={'maxiter': indata['at3d']['max_iters'],
                                             'maxls': 10,
                                             'disp': True,
                                             'gtol': 1e-16,
                                             'ftol': 1e-8})

# Set initial state
initial_gridded_extinction = carved_volume.mask.data.astype(float)
initial_gridded_extinction[:, :, :] *= indata['at3d']['init_extinction']
initial_1d_extinction = state_gen._unknown_scatterers['cloud'].variables['extinction'].state_to_grid.inverse_transform(initial_gridded_extinction)
x0 = state_gen._unknown_scatterers['cloud'].variables['extinction'].coordinate_transform.inverse_transform(initial_1d_extinction)

## SAVE INITIAL STATE
state_gen(x0)
sensor_dict_forward.get_measurements(solver_dict_forward)
base = os.path.splitext(infile)[0] + '_iterations/'
os.makedirs(base, exist_ok=True)
outFile = base + 'iter{:03d}.nc'.format(0)
at3d.util.save_forward_model(outFile, sensor_dict_forward, solver_dict_forward)

# Do optimization and save results
import warnings
warnings.filterwarnings('ignore')
result = optimizer.minimize(x0)

outFile = base + 'iter{:03d}.nc'.format(optimizer.iteration + 1)
at3d.util.save_forward_model(outFile, sensor_dict_forward, solver_dict_forward)

outFile = os.path.splitext(infile)[0] + '_optimized.nc'
at3d.util.save_forward_model(outFile, sensor_dict_forward, solver_dict_forward)