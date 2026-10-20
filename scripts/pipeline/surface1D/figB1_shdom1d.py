"""1D (independent-pixel) SHDOM clear-sky simulations over a wind-roughened ocean for Fig B1.

Source: notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb, cells idx 1, 2 and the
        commented-out cell idx 3. The notebook ran cell idx 3 once per config directory by editing
        config_dir; this script loops over both.
Conda env: vis2_clone (the notebook kernel)
Inputs: notebooks/surface_parameterization_testing/configs_expr02_{slow,fast}/*.yml,
        configs_SHDOM_1D/*.json, data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc (camp2ex/s03),
        data/interim/MIXTURE_default_ERA5.nc (camp2ex/s06)
Output: notebooks/surface_parameterization_testing/output1D/wind{0p67,4p0}_mu{N}_phi{2N}.nc
Changes: config_dir is looped over; obs_file, background_scatterers_file and outdir are OUT_ROOT-relative.
"""
from pathlib import Path
import os
import sys
import xarray as xr
import numpy as np
import at3d
from collections import OrderedDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_ROOT = Path(os.environ.get('OUT_ROOT', PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT))

from src.utils.util import load_sensor_dict, save_sensor_dict
from src.main.run_at3d import load_config

outdir = OUT_ROOT / 'notebooks' / 'surface_parameterization_testing' / 'output1D'
outdir.mkdir(parents=True, exist_ok=True)
config_dirs = [
    PROJECT_ROOT / 'notebooks' / 'surface_parameterization_testing' / 'configs_expr02_slow',
    PROJECT_ROOT / 'notebooks' / 'surface_parameterization_testing' / 'configs_expr02_fast',
]

for config_dir in config_dirs:
    for config_file in config_dir.glob('*.yml'):
        config = load_config(config_file)
        for key in ['obs_file', 'background_scatterers_file']:
            config[key] = OUT_ROOT / config[key].relative_to(PROJECT_ROOT)

        # Load rte grid and observations
        # rte_grid = xr.load_dataset(config['rte_grid_file'])
        obs = load_sensor_dict(config['obs_file'])

        # Make forward sensors
        forward_sensors = obs.make_forward_sensors()
        wavelength = forward_sensors.get_unique_solvers()[0]

        # Define surface reflectance model based on surface wind speed
        m_water = 1.33197 - 1j*2.41e-8
        surface = at3d.surface.wave_fresnel(np.real(m_water), np.imag(m_water), config['surface_wind_speed'])

        # Load SHODM numerical parameters
        numerical_parameters = at3d.configuration.get_config(config['config_file_name'])

        # Set solar source
        source = at3d.source.solar(
            wavelength,
            -1*obs['MISR']['sensor_list'][0].mu0,
            obs['MISR']['sensor_list'][0].SAA,
            solarflux=1.0,
            skyrad=0.0
        )

        # Load background atmosphere
        background_properties = xr.load_dataset(config['background_scatterers_file'])
        medium = {
            'background': background_properties.isel(x=slice(0,1), y=slice(0,1)).copy(deep=True)
        }

        # Set polarization
        num_stokes = OrderedDict()
        num_stokes[wavelength] = 1

        # Set forward model
        solver = at3d.solver.RTE(
            numerical_params = numerical_parameters,
            surface = surface,
            source = source,
            medium = medium,
            num_stokes = 1
        )
        solvers = at3d.containers.SolversDict()
        solvers.add_solver(wavelength, solver)

        # Forward simulate initialization
        forward_sensors.get_measurements(solvers)

        # Save
        n_mu = numerical_parameters.num_mu_bins.data
        n_phi = numerical_parameters.num_phi_bins.data
        sfc_wind = str(config['surface_wind_speed']).replace('.', 'p')
        outfile = outdir / f'wind{sfc_wind}_mu{n_mu}_phi{n_phi}.nc'
        save_sensor_dict(outfile, forward_sensors)
