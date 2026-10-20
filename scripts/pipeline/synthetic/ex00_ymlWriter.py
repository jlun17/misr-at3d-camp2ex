import yaml
import os

# Synthetic data root (was /data/keeling/a/johntl3/b/Synthetic); see scripts/pipeline/synthetic/run_synthetic.sh
SYN = os.path.join(os.environ.get('OUT_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')), 'data', 'synthetic')

y = {}

# Observation input parameters
y['numerical_params'] = {}
y['numerical_params']['max_total_mb'] = 64000.0
y['numerical_params']['num_mu_bins'] = 2 # CHECK THIS
y['numerical_params']['num_phi_bins'] = 4 # CHECK THIS

y['rte'] = {}
y['rte']['nx'] = None # CHECK THIS
y['rte']['ny'] = None # CHECK THIS
y['rte']['nz'] = None # CHECK THIS

y['medium'] = {}
y['medium']['atmosphere'] = os.path.join(SYN, 'ancillary', 'AFGL_summer_mid_lat.nc')
y['medium']['size_distribution'] = 'gamma'
y['medium']['normalization'] = 'geometric_extinction' # Options: 'density', 'geometric_extinction', 'number_concentration'
# y['medium']['density'] = '' # CHANGE THIS (i.e. {path}/ex00_density.nc)

y['source'] = {}
y['source']['wavelength'] = 0.67 #micron
y['source']['solar_zenith_angle'] = 210 #degrees
y['source']['solar_azimuth_angle'] = 90 #degrees

y['surface'] = {}
y['surface']['type'] = 'lambertian'
y['surface']['albedo'] = 0.05

y['sensors'] = {}
y['sensors']['name'] = 'MISR'
y['sensors']['type'] = 'orthographic'
y['sensors']['x_resolution'] = 0.1
y['sensors']['y_resolution'] = 0.1
y['sensors']['azimuth'] = [180, 180, 180, 180, 0, 0, 0, 0, 0] # CHECK THIS
# y['sensors']['azimuth'] = [90, 90, 90, 90, 270, 270, 270, 270, 270] # CHECK THIS
y['sensors']['zenith'] = [70.5, 60.0, 45.6, 26.1, 0.0, 26.1, 45.6, 60.0, 70.5]

# AT3D input parameters
y['space_carve'] = {}
y['space_carve']['threshold'] = 9*[0]
y['space_carve']['agreement'] = (0, 0)

y['objective_function'] = {}
y['objective_function']['parallel_solve_kwargs'] = {}
y['objective_function']['parallel_solve_kwargs']['n_jobs'] = 1
y['objective_function']['parallel_solve_kwargs']['mpi_comm'] = None
y['objective_function']['parallel_solve_kwargs']['verbose'] = True
y['objective_function']['parallel_solve_kwargs']['maxiter'] = 100
y['objective_function']['parallel_solve_kwargs']['init_solution'] = True
y['objective_function']['gradient_kwargs'] = {}
y['objective_function']['gradient_kwargs']['cost_function'] = 'L2'
y['objective_function']['gradient_kwargs']['exact_single_scatter'] = True
y['objective_function']['uncertainty_kwargs'] = {}
y['objective_function']['uncertainty_kwargs']['add_noise'] = False

y['at3d'] = {}
y['at3d']['init_extinction'] = 0.1 # km^-1
y['at3d']['max_iters'] = 200

stcu_path = os.path.join(SYN, 'thesis', 'StratoCumulus')
cu_path = os.path.join(SYN, 'thesis', 'TradeCumulus')
tr_path = os.path.join(SYN, 'thesis', 'Transition')

fields = [cu_path] # was [stcu_path, cu_path, tr_path]; the manuscript uses TradeCumulus only
lengths = ['/len005', '/len007', '/len009', '/len011', '/len015', '/len019', '/len149']
expr = '/ex00'
for f in fields:
    for l in lengths:
        base = f + l
        y['medium']['density'] = '{}{}_density.nc'.format(base, expr)
        os.makedirs(base, exist_ok=True)
        filename = base + expr + '.yml'
        r = 'y'
        if(os.path.isfile(filename)):
            r = input("Overwrite {}? (y or n) ".format(filename))

        if(r == 'y'):
            with open(filename, 'w') as file:
                documents = yaml.dump(y, file)
            print('File saved at {} '.format(filename))
        else:
            print('File not saved')
