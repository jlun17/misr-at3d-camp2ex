from pathlib import Path
import at3d
import warnings
import numpy as np
import xarray as xr
from src.utils.util import load_config, load_sensor_dict
from collections import OrderedDict

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
    
    def get_cloud_volume_stats(self, wavelength, medium, extinction_th=0, tau_th=0):
        # Threshold cloud
        cloud = self.solvers_retrieval[wavelength].medium[medium].copy(deep=True)
        cloud = threshold_cloud(cloud, extinction_th=extinction_th, tau_th=tau_th)

        # Count number of cloudy voxels after thresholding
        N = cloud.cloud_volume_mask.sum().data
        # Compute cloud volume of the thresholded mask
        cloud_volume = cloud.cloud_volume_mask.integrate(['x','y','z']).data
        # Calculate masked optical depth
        cloud['tau'] = cloud.extinction.integrate(['z'])
        # Calculate thresholded cloud mean optical depth
        tau_bar = cloud.tau.where(cloud.tau > 0).mean().data
        # Calculate thresholded cloud fraction
        cloud_fraction = ((cloud.tau > 0).sum() / cloud.tau.size).data
        return N, cloud_volume, tau_bar, cloud_fraction

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
            self.LUT = xr.open_dataset(LUT_file)
            print(f'LUT loaded from {str(LUT_file)}')
        else:
            print('Generating LUT...')
            self.LUT = self.generate_1D_LUT()
            print('LUT Generated.')
            print(f'Saved LUT to {str(LUT_file)}')

    def generate_1D_LUT(self):
        assert len(self.wavelengths == 1)
        wavelength = self.wavelengths[0]

        ## Create rte_grid with same vertical grid, but only a 3 x 3 in the horizontal
        rte_grid = at3d.grid.make_grid(self.rte_grid.delx.data, 3, self.rte_grid.dely.data, 3, self.rte_grid.z.data)

        ## Define cloud base and cloud top
        cb = 0.4
        ct = 0.7
        i_low = np.argwhere(rte_grid.z.data >= cb)[0][0]
        i_up = np.argwhere(rte_grid.z.data <= ct)[-1][0]
        thickness = rte_grid.z.data[i_up] - rte_grid.z.data[i_low]
        ## Define optical depths in LUT
        tausA = np.linspace(0, 4.75, 20)
        tausB = np.logspace(np.log10(5), 2, 40)
        taus = np.append(tausA, tausB)

        ## Make a sensor to observe radiance
        LUT_sensors = at3d.containers.SensorsDict()
        LUT_sensor = at3d.sensor.orthographic_projection(
            wavelength=wavelength,
            bounding_box=rte_grid,
            x_resolution=rte_grid.delx.data,
            y_resolution=rte_grid.dely.data,
            azimuth=0,
            zenith=0,
            altitude='TOA',
            stokes='I',
            sub_pixel_ray_args={'method': None}
        )
        LUT_sensors.add_sensor('LUT_sensor', LUT_sensor)

        ## Set up LUT solver with the features of the retreival solver
        # Numerical parameters
        numerical_parameters = self.solvers_retrieval[wavelength].numerical_params
        numerical_parameters['ip_flag'] = 3 # Set to independent pixel approximation
        numerical_parameters['split_accuracy'] = 1e-3
        # Surface
        surface = self.solvers_retrieval[wavelength].surface

        # Source
        source = self.solvers_retrieval[wavelength].source

        # Medium
        medium = OrderedDict()
        medium['background'] = self.solvers_retrieval[wavelength].medium['background'].isel(x=slice(0,3), y=slice(0,3))
        medium['cloud'] = self.solvers_retrieval[wavelength].medium['cloud'].isel(x=slice(0,3), y=slice(0,3))

        Is = np.zeros(taus.shape)
        num_unique = np.zeros(taus.shape)
        diff = np.zeros(taus.shape)
        LUT_solvers = at3d.containers.SolversDict()
        for i, tau in enumerate(taus):
            ext = np.zeros((rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z']))
            ext[:, :, i_low:i_up] = tau/thickness
            medium['cloud']['extinction'] = (['x','y','z'], ext)

            LUT_solver = at3d.solver.RTE(
                numerical_params = numerical_parameters,
                medium = medium,
                source = source,
                surface = surface,
                num_stokes = 1
            )
            LUT_solvers.add_solver(wavelength, LUT_solver)
            LUT_sensors.get_measurements(LUT_solvers)

            cam = LUT_sensors['LUT_sensor']['sensor_list'][0]
            num_unique[i] = len(np.unique(cam.I.data))
            diff[i] = np.max(cam.I.data) - np.min(cam.I.data)
            # assert num_unique[i] <= 3, "Tau = {}\n{}".format(tau, cam.I)
            Is[i] = np.mean(cam.I.data)
        LUT = xr.Dataset(
            coords = dict(I=Is),
            data_vars = dict(
                tau=(['I'], taus),
                num_unique = (['I'], num_unique),
                diff = (['I'], diff)
            )
        )
        assert np.all(np.diff(LUT.tau.data) > 0), "LUT tau not monotonic"
        assert np.all(np.diff(LUT.I.data) > 0), "LUT I not monotonic"
        return LUT
    
def threshold_cloud(cloud, extinction_th=0, tau_th=0):
    # Get the unthresholded extinction
    extinction = cloud.extinction
    # Get the thresholded extinction mask
    ext_mask = (extinction > extinction_th).astype(np.int64)
    # Get the unthresholded optical depth
    tau = extinction.integrate(['z'])
    # Get the thresholded optical depth mask
    tau_mask = (tau > tau_th).astype(np.int64)
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

def generate_1D_LUT(solver, sensor, taus):
    """
    Construct a lookup table (LUT) relating total column optical depth to mean measured 
    radiance using 1D radiative transfer.

    Parameters
    ----------
    solver : at3d.solver
    """