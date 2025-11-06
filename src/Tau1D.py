from pathlib import Path
import numpy as np
import at3d
from collections import OrderedDict
from scipy.interpolate import interp1d

def generate_1D_LUT(solver, sensors, rte_grid, taus, cloud_base, cloud_top):
    """
    Construct a lookup table (LUT) relating total column optical depth to mean measured 
    radiance using 1D radiative transfer.

    Parameters
    ----------
    solver : at3d.solver.RTE
        Radiative transfer solver to run SHDOM.
    sensors : at3d.containers.SensorsDict
        A dataset containing the sensor pixel geometries, wavelength and
        Stokes observables. May also contain ray variables.
    rte_grid : xarray.Dataset
        Radiative transfer grid corresponding to the solver medium.
    taus : np.ndarray
        Optical depths to be mapped to radiance.
    cloud_base : float
        Plane parallel cloud base height in km. Will be snapped to rte_grid.z.
    cloud_top : float
        Plane parallel cloud top height in km. Will be snapped to rte_grid.z.

    Returns
    -------
    LUT : at3d.containers.SensorsDict
        Maps optical depth to radiance computed using 1D radiative transfer.
    """

    # Create rte_grid with same vertical grid, but only a 1 x 1 in the horizontal
    rte_grid = at3d.grid.make_grid(0.275, 1, 0.275, 1, rte_grid.z.data)

    # Define cloud base and cloud top
    i_low = np.argwhere(rte_grid.z.data >= cloud_base)[0][0]
    i_up = np.argwhere(rte_grid.z.data <= cloud_top)[-1][0]
    thickness = rte_grid.z.data[i_up] - rte_grid.z.data[i_low]

    # Make a LUT sensor as a copy of the sensor
    forward_sensors = sensors.make_forward_sensors()
    LUT = _init_LUT(forward_sensors)

    ## Set up LUT solver with the features of the retreival solver
    # Numerical parameters
    numerical_parameters = solver.numerical_params
    numerical_parameters['x_boundary_condition'] = 'periodic'
    numerical_parameters['y_boundary_condition'] = 'periodic'
    numerical_parameters['ip_flag'] = 3 # Set to independent pixel approximation
    numerical_parameters['split_accuracy'] = 1e-3
    # Surface
    surface = solver.surface
    # Source
    source = solver.source
    # Medium
    medium_full = solver.medium
    medium = OrderedDict()
    for m in medium_full:
        medium[m] = medium_full[m].isel(x=slice(0,1), y=slice(0,1)).copy(deep=True)
        if(m != 'cloud'):
            assert medium[m].extinction.integrate('z').data > 0, f"{m} optical depth is zero. Is this a problem with the boundary?"
    # Num stokes
    num_stokes = solver.numerical_params.num_stokes.data

    ## Calculate 1D radiance for each optical depth
    LUT_solvers = at3d.containers.SolversDict()
    for i, tau in enumerate(taus):
        # Modify the cloud extinction in the medium
        ext = np.zeros((rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z']))
        ext[:, :, i_low:i_up] = tau/thickness
        medium['cloud']['extinction'] = (['x', 'y', 'z'], ext)
        # Create a RTE solver for the 1D solution
        LUT_solver = at3d.solver.RTE(
            numerical_params = numerical_parameters,
            medium = medium,
            source = source,
            surface = surface,
            num_stokes = num_stokes
        )
        LUT_solvers.add_solver(float(solver.wavelength), LUT_solver)
        # Run 1D radiative transfer
        forward_sensors.get_measurements(LUT_solvers)
        # Record results
        LUT = _append_to_LUT(LUT, forward_sensors, tau)
    return LUT

def retrieve_tau1D(obs, LUT):
    """Perform a 1D optical depth retreival.
    
    Parameters
    ----------
    obs : at3d.containers.SensorsDict
        A dataset containing the observations to be inverted.
    LUT : at3d.containers.SensorsDict
        The lookup table mapping radiance to 1D optical depth.
        Sensors in the LUT must correspons to the sensors in the obs.
    
    Returns
    -------
    obs : at3d.containers.SensorsDict
        An updated observation dataset with the retrieved optical 
        depth and optical path.
    """
    for instrument in obs:
        for i, cam in enumerate(obs[instrument]['sensor_list']):
            tau = np.zeros(cam.dims['npixels'])
            for j in range(cam.dims['npixels']):
                LUT_I = LUT[instrument]['sensor_list'][i].I.data[j,:]
                LUT_tau = LUT[instrument]['sensor_list'][i].tau.data
                tau_interp = interp1d(LUT_I, LUT_tau, kind='cubic', bounds_error=False)
                tau[j] = tau_interp(cam.I.data[j])
            obs[instrument]['sensor_list'][i]['optical_depth'] = (['nrays'], tau)
            obs[instrument]['sensor_list'][i]['optical_depth'].attrs['mode'] = '1D LUT'
            obs[instrument]['sensor_list'][i]['optical_path'] = (['nrays'], tau/cam.ray_mu.data)
            obs[instrument]['sensor_list'][i]['optical_path'].attrs['mode'] = '1D LUT'
    return obs

def _init_LUT(forward_sensors):
    LUT = forward_sensors.make_forward_sensors()
    for instrument in LUT:
        for i, cam in enumerate(LUT[instrument]['sensor_list']):
            LUT[instrument]['sensor_list'][i] = cam.assign_coords(tau=np.array([])).drop('I')
    return LUT

def _append_to_LUT(LUT, forward_sensors, tau):
    for instrument in LUT:
        for i, cam in enumerate(LUT[instrument]['sensor_list']):
            forward_I = forward_sensors[instrument]['sensor_list'][i].I.data[:, np.newaxis]
            if('I' in cam):
                LUT_I = cam.I.data
                I = np.append(LUT_I, forward_I, axis=1)
                tmp_cam = cam.drop('I')
            else:
                I = forward_I
                tmp_cam = cam
            tmp_cam = tmp_cam.assign_coords(tau=np.append(cam.tau.data, tau))
            tmp_cam['I'] = (['npixels', 'tau'], I)
            LUT[instrument]['sensor_list'][i] = tmp_cam
    return LUT
