import at3d
import yaml
import xarray as xr
import numpy as np
from scipy import interpolate
import sys

def load_data(expr):
    yml = expr + '.yml'
    with open(yml, "r") as file:
        indata = yaml.load(file, Loader=yaml.FullLoader)
    density = xr.load_dataset(indata['medium']['density'])
    obs = expr + '_syntheticObs.nc'
    sensor_dict, solver_dict, rte_grid = at3d.util.load_forward_model(obs)
    return indata, density, sensor_dict, solver_dict, rte_grid
def transform_sensors(sensor_dict, instrument, xshift, yshift):
    for sensor in sensor_dict[instrument]['sensor_list']:
        sensor.cam_x.data -= xshift
        sensor.cam_y.data -= yshift
        sensor.ray_x.data -= xshift
        sensor.ray_y.data -= yshift

expr_sm = sys.argv[1]
expr_lg = sys.argv[2]
indata_sm, density_sm, sensor_dict_sm, solver_dict_sm, rte_grid_sm = load_data(expr_sm)
indata_lg, density_lg, sensor_dict_lg, solver_dict_lg, rte_grid_lg = load_data(expr_lg)

xshift = (np.min(density_sm.x.data) - np.min(density_lg.x.data))
yshift = (np.min(density_sm.y.data) - np.min(density_lg.y.data))
transform_sensors(sensor_dict_lg, indata_lg['sensors']['name'], xshift, yshift)

snsr_list_sm = sensor_dict_sm[indata_sm['sensors']['name']]['sensor_list']
snsr_list_lg = sensor_dict_lg[indata_sm['sensors']['name']]['sensor_list']
for (snsr_sm, snsr_lg) in zip(snsr_list_sm, snsr_list_lg):
    lg_cords = np.array([snsr_lg.ray_x.data, snsr_lg.ray_y.data]).T
    interp = interpolate.LinearNDInterpolator(lg_cords, snsr_lg.I.data.ravel())
    I = interp(snsr_sm.cam_x.data, snsr_sm.cam_y.data)
    snsr_sm.I.data = I

outFile = expr_sm + 'em_syntheticObs.nc'
at3d.util.save_forward_model(outFile, sensor_dict_sm, solver_dict_sm)
