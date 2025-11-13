from pathlib import Path
import at3d
import warnings
import numpy as np
import xarray as xr
from src.utils.util import load_config, load_sensor_dict, save_sensor_dict
import src.Tau1D

"""
Module: Retrieval
Provides the Retrieval class for loading and inspecting AT3D retrieval outputs.

This module exposes:
- Retrieval: convenience wrapper to load an experiment directory, iterate retrieval files,
  and inspect results (extinction histograms, maxima, etc.).

Docstring style: numpy-style for compatibility with Sphinx + napoleon.
"""
class Retrieval:
    """
    Holds a single AT3D retrieval or preprocessing for a retrieval.

    Parameters
    ----------
    root_dir : str | pathlib.Path
        Path to the experiment root directory. The class expects a structure with
        a `config.yml` file and an `iterations/` directory with `iter*.nc` files.

    Attributes
    ----------
    root_dir : pathlib.Path
        Root directory of the experiment.
    exp_name : str
        Name of the experiment (basename of root_dir).
    iter_dir : pathlib.Path
        Directory containing iteration NetCDF files.
    config : dict
        Parsed configuration loaded from `config.yml`.
    obs : at3d.containers.SensorDict
        Observations used for the AT3D retrieval.
    wavelengths : list
        Unique solver wavelengths from the sensor object.
    cvm : xarray.Dataset
        Cloud volume mask dataset loaded from the config path.
    iteration : str | None
        The currently loaded iteration file stem (e.g. 'iter000').
    sensors_retrieval : at3d.containers.SensorDict | None
        Forward simulated images for the currently loaded retrieval iteration.
    solvers_retrieval : at3d.containers.SolverDict | None
        Radiative transfer solver for the currently loaded retreival iteration.
    rte_grid : xarray.Dataset | None
        Radiative transfer grid for the curently loaded retreival iteration.
    LUT : xarray.Dataset | None
        Look up table mapping column optical depth to radiance.

    Examples
    --------
    >>> r = Retrieval('/path/to/exp')
    >>> r.load_retrieval(-1)
    """
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.exp_name = root_dir.name
        self.iter_dir = self.root_dir / 'iterations'
        self.config = load_config(self.root_dir / 'config.yml')
        self.obs = load_sensor_dict(self.config['obs_file'])
        self.obs = convert_to_BRF(self.obs)
        self.masks = self.obs.make_forward_sensors()
        self.wavelengths = self.obs.get_unique_solvers()
        self.cvm = xr.load_dataset(self.config['cloud_volume_mask_file'])
        self.iteration = None
        self.sensors_retrieval = None
        self.solvers_retrieval = None
        self.rte_grid = None
        self.LUT = None

    def __repr__(self):
        """Return the experiment root path as string."""
        return str(self.root_dir)
    
    def load_retrieval(self, iteration=-1, quiet=True):
        """
        Load retrieval outputs for a given iteration.

        Parameters
        ----------
        iteration : int, optional
            Index into sorted iteration files (default: -1 -> last).
        quiet : bool, optional
            If True, suppress warnings during forward model load.

        Raises
        ------
        IndexError
            If no iteration files are found or the requested index is out of range.
        """
        iter_files = sorted(self.iter_dir.glob('iter*.nc'))
        iter_file = iter_files[iteration]
        self.iteration = iter_file.stem
        if quiet:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', Warning)
                self.sensors_retrieval, self.solvers_retrieval, self.rte_grid = at3d.util.load_forward_model(iter_file)
        else:
            self.sensors_retrieval, self.solvers_retrieval, self.rte_grid = at3d.util.load_forward_model(iter_file)
        self.sensors_retrieval = convert_to_BRF(self.sensors_retrieval)

        # Calculate optical path and optical depth for each sensor. Modifies sensor in place.
        # Note: Non-cloud constituents are assumed to be plane parallel and their optical 
        # depths are subtracted from the total optical depth.
        background_optical_depth = {}
        for wavelength in self.solvers_retrieval:
            tmp_tau = 0
            for medium in self.solvers_retrieval[wavelength].medium:
                if(medium != 'cloud'):
                    tmp_taus = np.unique(self.solvers_retrieval[wavelength].medium[medium].extinction.integrate('z').data)
                    assert len(tmp_taus) == 1, "{} max tau: {} and min tau: {}".format(medium, np.max(tmp_taus), np.min(tmp_taus))
                    tmp_tau += tmp_taus[0]
            background_optical_depth[wavelength] = tmp_tau

        for instrument in self.sensors_retrieval:
            for cam in self.sensors_retrieval[instrument]['sensor_list']:
                self.solvers_retrieval[float(cam.wavelength.data)].optical_path(cam)
                cam['optical_path'].attrs['mode'] = 'AT3D'
                cam['optical_depth'] = cam.optical_path*cam.ray_mu
                cam['optical_depth'].attrs['mode'] = 'AT3D'
                cam['optical_depth'] = cam.optical_depth - background_optical_depth[float(cam.wavelength.data)]
                cam['optical_depth'].attrs['background_optical_depth'] = background_optical_depth[float(cam.wavelength.data)]
                cam['optical_path'] = cam.optical_depth / cam.ray_mu
                cam['optical_path'].attrs['background_optical_depth'] = background_optical_depth[float(cam.wavelength.data)]

        # Add a standard optical depth mask and ray containment masks
        for instrument in self.sensors_retrieval:
            self.add_threshold_mask(self.sensors_retrieval, instrument, 'tau0.3mask', 'optical_depth', 0.3)
            self.add_ray_containment_mask()

    def get_chi2(self, S_1, variable='I', mask_conds={}):
        """Compute chi squared given an inverse error covariance matrix
        
        Parameters
        ----------
        S_1 : callable
            Function that takes y as input that return the inverse 
            error covariance matrix.
        variable : string
            Observable to comput chi squared on. Typically it is 'I'.
        mask_conds : dict
            Masking conditions to pass to obs_vec.
        
        Returns
        -------
        chi2 : float
            Chi squared value.
        """
        F = obs_vec(self.sensors_retrieval, variable, self.masks, mask_conds)
        y = obs_vec(self.obs, variable, self.masks, mask_conds)
        return chi2(y, F, S_1(y))

    def add_ray_containment_mask(self, mask_name='ray_containment'):
        """Determine a mask of which rays pass through the retreival domain or not.
        
        Lables each ray with:
            0: Ray neither starts nor finishes within the domain
            1: Ray partially passes through the retrieval domain
            2: Ray completely passes through the retreival domain
        
        Note: Rays that partially pass through the domain but don't start or end within 
        the domain will be labled with 0. For large domains and moderate viewing angles
        the number of missed rays is minimal. The issue becomes worse with high viewing
        zenith angles and/or small domains.

        Parameters
        ----------
        mask_name : str
            Sets the name of the mask in the self.masks attribute
        """

        for instrument in self.obs:
            for cam, cam_mask in zip(self.obs[instrument]['sensor_list'], self.masks[instrument]['sensor_list']):
                phi = np.degrees(cam.ray_phi.data)
                theta = np.degrees(np.arccos(cam.ray_mu.data))
                z = np.unique(cam.ray_z.data)
                assert len(z) == 1, "Sensor altitude is not constant"
                z = z[0]
                assert z == np.max(self.rte_grid.z.data), "Sensor is not at the top of the domain"
                deltax, deltay = at3d.preprocessing.project_to_altitude(theta, phi, -z)
                ray_x_top = cam.ray_x.data
                ray_y_top = cam.ray_y.data
                ray_x_bot = ray_x_top + deltax
                ray_y_bot = ray_y_top + deltay
                bbox_x_low = np.min(self.rte_grid.x.data)
                bbox_x_high = np.max(self.rte_grid.x.data)
                bbox_y_low = np.min(self.rte_grid.y.data)
                bbox_y_high = np.max(self.rte_grid.y.data)
                top_in = np.logical_and(
                    np.logical_and(ray_x_top > bbox_x_low, ray_x_top < bbox_x_high),
                    np.logical_and(ray_y_top > bbox_y_low, ray_y_top < bbox_y_high)
                )
                bot_in = np.logical_and(
                    np.logical_and(ray_x_bot > bbox_x_low, ray_x_bot < bbox_x_high),
                    np.logical_and(ray_y_bot > bbox_y_low, ray_y_bot < bbox_y_high)
                )
                mask = np.zeros(cam.dims['nrays'])
                mask[top_in] += 1
                mask[bot_in] += 1
                cam_mask[mask_name] = (['nrays'], mask)
                cam_mask[mask_name].attrs['Mask Key'] = '0: Ray neither starts nor finishes within the domain\n1:Ray partially passes through the domain\n2: Ray is fully coontained within the domain' 


    def add_threshold_mask(self, sensors_th, instrument, mask_name, variable, thresholds):
        """Apply a camera-by-camera threshold mask.

        Modifies the self.masks attribute in place with the threshold mask.
        Mask returns 1 if the `variable` >= threshold.
        
        Parameters
        ----------
        sensors_th : at3d.containers.SensorDict
            Dataset containing the variable to apply threshold to.
        instrument : str
            Instrument in the sensor dict to apply the mask to.
        mask_name : str
            Name to call the mask.
        variable : str
            Variable to apply the threshold to (i.e., 'I', 'brf', 'optical_depth', ect.).
        thresholds : dict | float
            Key corresponds to the name of each sensor (i.e. 'DF').
            Values hold the threshold. If thresholds is a float, then theshold 
            is applied uniformly over all cameras.
        """
        th = thresholds
        for cam_th, cam_mask in zip(sensors_th[instrument]['sensor_list'], self.masks[instrument]['sensor_list']):
            if(isinstance(thresholds, dict)):
                th = thresholds[cam_th.name]
            cam_mask[mask_name] = (cam_th[variable] >= th).astype(np.int64)
            cam_mask[mask_name].attrs[f'{variable} threshold'] = th

    def plot_extinction_hist(self, medium, ax, **kwargs):
        """
        Plot histograms of extinction for each solver wavelength.

        Histograms do not include where extinction == 0 (only extinction > 0).

        Parameters
        ----------
        medium : str
            Name of the retrieval medium to index (e.g. 'aerosol', 'cloud').
        ax : matplotlib.axes.Axes
            Axes object on which to plot.
        **kwargs : dict
            Passed to matplotlib.axes.Axes.hist (e.g., bins=, log=).
        """
        for w in self.wavelengths:
            extinction = self.solvers_retrieval[w].medium[medium].extinction.data
            ax.hist(np.ravel(extinction[extinction > 0]), label='{} {} {}'.format(self.exp_name, w, medium), **kwargs)
            ax.set_xlabel(r'extinction (km$^{-1}$)')
    
    def get_cloud_volume_stats(self, wavelength, medium, extinction_th=[0, np.inf], tau_th=[0, np.inf]):
        # Threshold cloud
        cloud = self.solvers_retrieval[wavelength].medium[medium]
        cloud = threshold_cloud(cloud, extinction_th=extinction_th, tau_th=tau_th)

        # Calculate masked optical depth
        cloud['tau'] = cloud.extinction.integrate(['z'])
        # Set zero extinction to nan
        extinction = cloud.extinction.data
        extinction[extinction == 0] = np.nan

        stats = {
            'retrieval': str(self.root_dir),
            'cloud fraction': ((cloud.tau > 0).sum() / cloud.tau.size).data,
            'tau bar': cloud.tau.where(cloud.tau > 0).mean().data,
            'volume': cloud.cloud_volume_mask.integrate(['x','y','z']).data,
            'cloudy voxel count': cloud.cloud_volume_mask.sum().data,
            'min extinction': np.nanmin(extinction),
            'q5': np.nanpercentile(extinction, 5),
            'q25': np.nanpercentile(extinction, 25),
            'q50': np.nanpercentile(extinction, 50),
            'q75': np.nanpercentile(extinction, 75),
            'q95': np.nanpercentile(extinction, 95),
            'max extinction': np.nanmax(extinction),
            'mean extinction': np.nanmean(extinction),
            'std extinction': np.nanstd(extinction)
        }
        return stats

    def max_extinction(self, wavelength, medium):
        """
        Return maximum extinction value for a given solver wavelength and medium.

        Parameters
        ----------
        wavelength :
            Solver wavelength key used in solvers_retrieval.
        medium : str
            Medium name.

        Returns
        -------
        float
            Maximum extinction (numpy float) across the grid.
        """
        extinction = self.solvers_retrieval[wavelength].medium[medium].extinction.data
        return np.max(extinction)
    
    def load_LUT(self, LUT_file):
        LUT_file = Path(LUT_file)
        if LUT_file.exists():
            self.LUT = load_sensor_dict(LUT_file)
            return True
        else:
            return False
    
    def generate_1D_LUT(self, wavelength, taus, cloud_base, cloud_top, LUT_outfile=None):
        if not self.load_LUT(LUT_outfile):
            self.LUT = src.Tau1D.generate_1D_LUT(
                self.solvers_retrieval[wavelength],
                self.obs,
                self.rte_grid,
                taus,
                cloud_base,
                cloud_top
            )
            if(LUT_outfile):
                save_sensor_dict(LUT_outfile, self.LUT)

    def retrieve_1D_tau(self, outfile=None):
        if(outfile is not None):
            outfile = Path(outfile)
            if(outfile.exists()):
                self.obs = load_sensor_dict(outfile)
            else:
                if(self.LUT is None):
                    raise Exception("Must load a LUT first")
                self.obs = src.Tau1D.retrieve_tau1D(self.obs, self.LUT)
                save_sensor_dict(outfile, self.obs)
        else:
            if(self.LUT is None):
                raise Exception("Must load a LUT first")
            self.obs = src.Tau1D.retrieve_tau1D(self.obs, self.LUT)

def threshold_cloud(cloud, extinction_th=[0, np.inf], tau_th=[0, np.inf]):
    cloud = cloud.copy(deep=True)
    # Get the unthresholded extinction
    extinction = cloud.extinction
    # Get the thresholded extinction mask
    ext_mask = np.logical_and(extinction > extinction_th[0], extinction <= extinction_th[1]).astype(np.int64)
    # Get the unthresholded optical depth
    tau = extinction.integrate(['z'])
    # Get the thresholded optical depth mask
    tau_mask = np.logical_and(tau > tau_th[0], tau <= tau_th[1]).astype(np.int64)
    # Combine the optical depth and extinction thresholds
    cloud_volume_mask = ext_mask.data.copy()
    cloud_volume_mask[tau_mask.data == 0] = 0
    cloud['cloud_volume_mask'] = (['x','y','z'], cloud_volume_mask)
    cloud.cloud_volume_mask.attrs['extinction_th'] = extinction_th
    cloud.cloud_volume_mask.attrs['tau_th'] = tau_th
    # Update extinction field to be masked
    cloud['extinction'] = cloud.cloud_volume_mask * cloud.extinction
    cloud.extinction.attrs['extinction_th'] = extinction_th
    cloud.extinction.attrs['tau_th'] = tau_th
    return cloud

def convert_to_BRF(sensors):
    for instrument in sensors:
        for i, cam in enumerate(sensors[instrument]['sensor_list']):
            cam['brf'] = (np.pi * cam.I) / cam.mu0
            sensors[instrument]['sensor_list'][i] = cam
    return sensors

def obs_vec(sensor, variable, masks, mask_conds):
    """Convert an observable from a sensor dict into a vector according to a mask.

    Parameters
    ----------
    sensor : at3d.containers.SensorDict
        A dataset containg the sensors.
    variable : string
        The variable contained within each sensor to be vectorized.
    masks : at3d.containers.SensorDict
        A dataset mirroring the structure of the sensor, but containing masks
    mask_conds : dict
        A dictionary where the key is the name of the mask and the value is a tuple
        with equality conditions for the mask. If it is empty, no mask is applied.
    
    Returns
    -------
    vec : np.array
        A masked vectorized version of the variable from the sensors.
    """
    vec = np.array([])
    for instrument in sensor:
        for cam, cam_mask in zip(sensor[instrument]['sensor_list'], masks[instrument]['sensor_list']):
            mask = np.ones(cam.dims['nrays'], dtype=bool)
            for m in mask_conds:
                mask = np.logical_and(
                    mask,
                    np.logical_or(cam_mask[m].data == mask_conds[m][0], cam_mask[m].data == mask_conds[m][1])
                )
            vec = np.append(vec, cam[variable].data[mask])
    return vec

def chi2(y, F, S_1):
    """Compute the chi squared"""
    m = len(y)
    return 0.5 * (1/m) * np.matmul(y-F, np.matmul(S_1, y-F))