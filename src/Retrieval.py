from pathlib import Path
import at3d
import warnings
import numpy as np
import xarray as xr
from src.utils.util import load_config, load_sensor_dict

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