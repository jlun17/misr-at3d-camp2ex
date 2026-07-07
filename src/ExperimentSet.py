from pathlib import Path
import pandas as pd
import numpy as np
from src.Retrieval import Retrieval, threshold_cloud

"""
Module: ExperimentSet
Provides ExperimentSet, a small helper to discover and load "retrieval"
subdirectories in a dataset tree. A retrieval directory is any directory that
contains a subdirectory named 'iterations'. The ExperimentSet collects paths to
those retrieval directories and can instantiate Retrieval objects for them.
"""
class ExperimentSet:
    """
    Container for a collection of AT3D retrieval experiments discovered under a root directory.

    Parameters
    ----------
    root_dir : str | pathlib.Path
        Top-level directory to search for retrieval experiments.

    Attributes
    ----------
    root_dir : pathlib.Path
        Root directory used for discovery.
    retrieval_list : list[pathlib.Path]
        List of directories identified as retrievals (contain an 'iterations' subdirectory).
    retrievals : list
        List of instantiated Retrieval objects corresponding to retrieval_list.

    Examples
    --------
    >>> E = ExperimentSet('/path/to/experiments')
    >>> E.set_retrieval_list()
    >>> E.load_retrievals(iteration=-1)
    """
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        # self.retrieval_list = []
        self.retrievals = {}

    def __repr__(self):
        s = ''
        for i, name in enumerate(self.retrievals.keys()):
            s += f'{i+1}: {name}\n'
        return s

    def set_retrieval_list(self):
        """
        Discover retrieval directories under self.root_dir and set self.retrieval_list.

        A directory is considered a retrieval if it contains an 'iterations' subdirectory.
        The discovery traverses subdirectories recursively.
        """
        paths = self._traverse(self.root_dir)
        self.retrievals = {Path(p): None for p in paths}

    def load_retrievals(self, iteration=None, extinction_th=[0, np.inf], tau_th=[0, np.inf]):
        """
        Instantiate Retrieval objects for each path in self.retrieval_list.

        Parameters
        ----------
        iteration : int, optional
            If provided, passed to each Retrieval.load_retrieval call to load a specific iteration.
            If not provided, the last iteration is loaded.
        extinction_th : list, optional
            Extinction threshold passed to Retrieval.load_retrieval.
        tau_th : list, optional
            Optical depth threshold passed to Retrieval.load_retrieval.
        """
        for rpath in self.retrievals:
            R = Retrieval(rpath)
            if iteration:
                R.load_retrieval(iteration, extinction_th=extinction_th, tau_th=tau_th)
            self.retrievals[rpath] = R

    def get_retrieval(self, exp_name):
        for r in self.retrievals.values():
            if(r.exp_name == exp_name):
                return r
        return None

    def to_dataframe(self, wavelength, medium, variable, name_map=None):
        """Convert retrieval results to a dataframe for a given wavelength, medium, and variable"""
        rows = []
        for rpath in self.retrievals:
            R = self.retrievals[rpath]
            df = R.to_dataframe(wavelength, medium, variable, name_map=name_map)
            rows.append(df)
        df = pd.concat(rows, ignore_index=True)
        return df

    def chi2(self, S_1, variable, mask_conds):
        """Compute the chi squared for each retreival and return the results in a dataframe"""
        rows = []
        for rpath in self.retrievals:
            R = self.retrievals[rpath]
            c2 = R.get_chi2(S_1, variable, mask_conds)
            row = {
                'retrieval': str(rpath),
                'chi2': c2
            }
            rows.append(row)
        df = pd.DataFrame(rows, columns=[s for s in row])
        return df.set_index('retrieval')

    def cloud_stats(self, wavelength, medium):
        rows = []
        for rpath in self.retrievals:
            R = self.retrievals[rpath]
            stats = R.get_cloud_volume_stats(wavelength, medium)
            rows.append(stats)
        df = pd.DataFrame(rows, columns=[s for s in stats])
        return df.set_index('retrieval')

    def compare_to(self, reference_key, wavelength, medium, extinction_th=[0, np.inf], tau_th=[0, np.inf]):
        ref = self.retrievals[reference_key]
        rows = []
        for rpath in self.retrievals:
            R = self.retrievals[rpath]
            stats = _compare(R, ref, wavelength, medium, extinction_th=extinction_th, tau_th=tau_th)
            rows.append(stats)
        df = pd.DataFrame(rows, columns=[s for s in stats])
        return df.set_index('retrieval')

    def _traverse(self, dir_path):
        """
        Recursively traverse dir_path and return a list of retrieval directories.

        Parameters
        ----------
        dir_path : pathlib.Path
            Directory to traverse.

        Returns
        -------
        list[pathlib.Path]
            Directories that contain an 'iterations' subdirectory.
        """
        results = []
        iterations = dir_path / 'iterations'
        if(iterations.is_dir()):
            results.append(dir_path)
            return results
        for n in dir_path.iterdir():
            if n.is_dir():
                results.extend(self._traverse(n))
        return results
    
def _compare(r, rref, wavelength, medium, extinction_th=[0, np.inf], tau_th=[0, np.inf]):
    r_cloud = r.solvers_retrieval[wavelength].medium[medium]
    r_ext = threshold_cloud(r_cloud, extinction_th=extinction_th, tau_th=tau_th).extinction.data
    rref = rref.solvers_retrieval[wavelength].medium[medium]
    rref_ext = threshold_cloud(rref, extinction_th=extinction_th, tau_th=tau_th).extinction.data
    rel_difference = 100 * (np.sum((r_ext - rref_ext)**2))**0.5 / (np.sum(rref_ext)**2)**0.5
    rel_bias = 100 * (np.sum(np.abs(r_ext)) - np.sum(np.abs(rref_ext))) / (np.sum(np.abs(rref_ext)))
    stats = {
        'retrieval': str(r.root_dir),
        'relative bias': rel_bias,
        'relative difference': rel_difference
    }
    return stats