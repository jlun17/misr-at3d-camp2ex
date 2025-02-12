import warnings
import os
import at3d
import netCDF4 as nc
import xarray as xr

def save_measurements(file_name, sensors):
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
    initial_file_name = file_name
    while os.path.exists(file_name):
        if counter > 1:
            file_name = '{}_{}.nc'.format(file_name[:-5], counter)
        else:
            file_name = '{}_{}.nc'.format(file_name[:-3], counter)
        counter += 1

    if counter > 1:
        warnings.warn("file_name '{}' already exists, your file is now at '{}'".format(
            initial_file_name,file_name), category=RuntimeWarning)

    save_file = nc.Dataset(file_name, 'w')
    save_file.close()
    for i, (key, sensor) in enumerate(sensors.items()):
        for j, image in enumerate(sensor['sensor_list']):
            image.to_netcdf(file_name, 'a', group='sensors/{}/{:d}'.format(key, j))

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
