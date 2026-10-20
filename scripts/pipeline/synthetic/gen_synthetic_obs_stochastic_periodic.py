"""
This script should take in a cloud field and run SHDOM on it.

Parameters
----------
numerical_parameters: dict
    Modify the default numerical parameters with the dict of modified parameters.
rte: dict
    'nx': int
        Number of x gridpoints on base rte grid
    'ny': int
        Number of y gridpoints on base rte grid
    'nz': int
        Number of z gridpoints on base rte grid
medium: dict
    'size_distribution': string
        'gamma'
            'reff': float
                Effective radius
            'veff': float
                Effective variance in same units as radius
            'normalization': str
                Choice of size distribution normalization from 'density' [g m^-3]
                'geometric_extinction' [km^-1] (extinction calculated using a
                fixed extinction efficiency of 2), 'number_concentration' [# cm^-3].
        'lognormal'
            'reff': float
                Effective radius
            'veff': float
                Effective variance
            'normalization': str
                Choice of size distribution normalization from 'density' [g m^-3]
                'geometric_extinction' [km^-1] (extinction calculated using a
                fixed extinction efficiency of 2), 'number_concentration' [# cm^-3].
    'density': string
        Path to netcdf. Dataset with 'density': (x, y, z). Values should
        correspond with choice of normalization above.
source: dict
    'wavelength': float
        Monochromatic wavelength [micron]
    'solar_zenith_angle': float
        Degrees. Points in direction of solar beam. Up is 0 degrees, down is 180
        degrees. Cos(solar_zenith_angle) must be negative.
    'solar_azimuth_angle': float
        Degrees. Points in direction of solar beam. (i.e. 90 degrees means the
        solar beam is pointing in the +y direction)
surface: dict
    'type': string
        'lambertian'
            'albedo': float
            'ground_temperature': float
                Units of Kelvin. Optional
        'wave_fresnel'
            'real_refractive_index': float
            'imaginary_refractive_index': float
                Negative for absorbing surfaces
            'surfact_wind_speed': float
                Units of m/s
            'ground_temperature': float
                Units of Kelvin. Optional
sensors: dict
    'name': string
        Instrument name
    'type': string
        Choice from 
        'orthographic'
            'x_resolution': float
                Pixel resolution [km] in x axis
            'y_resolution': float
                Pixel resolution [km] in y axis
            'azimuth': list
                Azimuth angle [deg] of the measurements (direction of photons)
            'zenith': list
                Zenith angle [deg] of the measurements (direction of photons)
        'perspective'
            Not implemented
        'domaintop'
            Not implemented
"""

import at3d
import yaml
import numpy as np
import xarray as xr
import os
import sys

# infile = '/data/keeling/a/johntl3/b/Synthetic/IO/dev/ex01.yml'
infile = sys.argv[1]
with open(infile, "r") as file:
    indata = yaml.load(file, Loader=yaml.FullLoader)
wavelen = indata['source']['wavelength']

# Medium
med = indata['medium']
rte = indata['rte']
cloud = xr.load_dataset(med['density'])
# cloud = cloud.assign_coords(x=cloud.xm.data/1000, y=cloud.ym.data/1000, z=cloud.zm.data/1000)
# cloud = cloud.assign(density=(['x','y','z'], cloud.density.transpose('xt', 'yt', 'zt').data))
rte_grid = at3d.grid.make_grid(cloud.x.diff('x')[0].data,
                                cloud.x.size,
                                cloud.y.diff('y')[0].data,
                                cloud.y.size,
                                cloud.z.data,
                                nx=rte['nx'],
                                ny=rte['ny'],
                                nz=rte['nz'])
cloud_scatterer = rte_grid.copy(deep=True)
cloud_scatterer['density'] = (('x','y','z'), cloud.density.data)
cloud_scatterer['reff'] = (('x','y','z'), cloud.reff.data)
cloud_scatterer['veff'] = (('x','y','z'), cloud.veff.data)
if(med['size_distribution'] == 'gamma'):
    size_distribution_function = at3d.size_distribution.gamma
    # cloud_scatterer['reff'] = (('x','y','z'), np.ones(cloud.density.shape) * med['reff'])
    # cloud_scatterer['veff'] = (('x','y','z'), np.ones(cloud.density.shape) * med['veff'])
mie_table = {}
mie_table[wavelen] = at3d.mie.get_mono_table('Water',(wavelen, wavelen),
                                            max_integration_radius=200.0,
                                            minimum_effective_radius=0.5,
                                            relative_dir=os.path.join(os.environ.get('OUT_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')), 'data', 'synthetic', 'mie_tables'),
                                            verbose=False)
optical_property_generator = at3d.medium.OpticalPropertyGenerator(
    'cloud',
    mie_table,
    size_distribution_function,
    reff=np.logspace(np.log10(0.9),np.log10(70.0),70), #np.array([med['reff']-0.01, med['reff'], med['reff']+0.01]),
    veff=np.linspace(0.04,0.9,4), #np.array([med['veff']-0.01, med['veff'], med['veff']+0.01]),
    density_normalization=med['normalization']
)
optical_properties = optical_property_generator(cloud_scatterer)

atmosphere = xr.open_dataset(med['atmosphere'])
rayleigh_scattering = at3d.rayleigh.to_grid(wavelen,atmosphere,rte_grid)
if(rte['nx'] != None):
    rayleigh_scattering[wavelen] = rayleigh_scattering[wavelen].assign(nx=rte['nx'])
if(rte['ny'] != None):
    rayleigh_scattering[wavelen] = rayleigh_scattering[wavelen].assign(ny=rte['ny'])
if(rte['nz'] != None):
    rayleigh_scattering[wavelen] = rayleigh_scattering[wavelen].assign(nz=rte['nz'])
medium = {'rayleigh':rayleigh_scattering[wavelen],
          'cloud':optical_properties[wavelen]}

# Numerical Parameters
config = at3d.configuration.get_config()
for k in indata['numerical_params'].keys():
    config[k] = indata['numerical_params'][k]
config['x_boundary_condition'] = 'periodic'
config['y_boundary_condition'] = 'periodic'

# Source
src = indata['source']
source = at3d.source.solar(src['wavelength'], 
                           np.cos(np.radians(src['solar_zenith_angle'])), 
                           src['solar_azimuth_angle'])

# Surface
surf = indata['surface']
if(surf['type'] == 'lambertian'):
    surface = at3d.surface.lambertian(albedo=surf['albedo'])
elif(surf['type'] == 'wave_fresnel'):
    nr = surf['nr']
    ni = surf['ni']
    v = surf['v']
    surface = at3d.surface.wave_fresnel(nr, ni, v)

# Create solver
solvers_dict = at3d.containers.SolversDict()
solver = at3d.solver.RTE(numerical_params=config, surface=surface, source=source, medium=medium, num_stokes=1)
solvers_dict.add_solver(wavelen, solver)

# Sensors
snsrs = indata['sensors']
sensors_dict = at3d.containers.SensorsDict()
for i in range(len(snsrs['zenith'])):
    sensor = at3d.sensor.orthographic_projection(wavelen,
                                                 rte_grid,
                                                 snsrs['x_resolution'],
                                                 snsrs['y_resolution'],
                                                 snsrs['azimuth'][i],
                                                 snsrs['zenith'][i],
                                                 altitude='TOA',
                                                 stokes='I',
                                                 sub_pixel_ray_args={'method': None})
    sensors_dict.add_sensor(snsrs['name'], sensor)

# Save unsolved forward model
outFile = os.path.splitext(infile)[0] + '_notSolved.nc'
at3d.util.save_forward_model(outFile, sensors_dict, solvers_dict)

# Run SHDOM and save
sensors_dict.get_measurements(solvers_dict,
                              n_jobs=1,
                              mpi_comm=None,
                              maxiter=100,
                              verbose=True,
                              init_solution=True,
                              setup_grid=True,
                              destructive=False,
                              overwrite_solver=False)
outFile = os.path.splitext(infile)[0] + '_syntheticObs.nc'
at3d.util.save_forward_model(outFile, sensors_dict, solvers_dict)