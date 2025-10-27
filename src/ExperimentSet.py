from pathlib import Path
from src.Retrieval import Retrieval

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
        self.retrieval_list = []
        self.retrievals = []

    def set_retrieval_list(self):
        """
        Discover retrieval directories under self.root_dir and set self.retrieval_list.

        A directory is considered a retrieval if it contains an 'iterations' subdirectory.
        The discovery traverses subdirectories recursively.
        """
        self.retrieval_list = self._traverse(self.root_dir)

    def load_retrievals(self, iteration=None):
        """
        Instantiate Retrieval objects for each path in self.retrieval_list.

        Parameters
        ----------
        iteration : int, optional
            If provided, passed to each Retrieval.load_retrieval call to load a specific iteration.
            If not provided, the last iteration is loaded.
        """
        for retrieval in self.retrieval_list:
            R = Retrieval(retrieval)
            if iteration:
                R.load_retrieval(iteration)
            self.retrievals.append(R)

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