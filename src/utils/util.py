import warnings
import os
import at3d
import netCDF4 as nc
import xarray as xr
from pathlib import Path
import yaml
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def save_sensor_dict(file_name, sensors):
    """
    Method to save only a Sensor Dict object. Useful for preparing real 
    satellite observations to be used in a retreival. Adapted from 
    at3d.util.save_forward_model.

    Parameters
    ----------
    file_name : string
        The path to the file that will be created and saved to. If it exists, an
        integer is appended to the file name until it can be created safely.
    sensors : at3d.containers.SensorsDict
    """
    if not isinstance(sensors, at3d.containers.SensorsDict):
        raise TypeError(
            "`sensors` should be an instance of '{}'".format(at3d.containers.SensorsDict)
        )
    
    # make a safe file name. We always want one that works
    # as we might have spent a lot of time to make the input data.
    counter = 1
    initial_file_name = Path(file_name)
    file_name = initial_file_name
    while file_name.exists():
        if counter > 1:
            file_name = initial_file_name.with_name(f"{initial_file_name.stem}_{counter}.nc")
        else:
            file_name = initial_file_name.with_name(f"{initial_file_name.stem}_{counter}.nc")
        counter += 1

    if counter > 1:
        warnings.warn("file_name '{}' already exists, your file is now at '{}'".format(
            initial_file_name,file_name), category=RuntimeWarning)

    save_file = nc.Dataset(file_name, 'w')
    save_file.close()
    for i, (key, sensor) in enumerate(sensors.items()):
        for j, image in enumerate(sensor['sensor_list']):
            image.to_netcdf(file_name, 'a', group='sensors/{}/{:d}'.format(key, j))
    print('Saved sensors to: {}'.format(file_name))

def load_sensor_dict(file_name):
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