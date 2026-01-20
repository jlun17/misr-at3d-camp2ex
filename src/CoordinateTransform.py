"""Coordinate transforms between MISR SOM coordinates and the AT3D grid.

The helper exposes a single class, :class:`CoordinateTransform`, that stores
domain geometry and applies a translation-rotation-translation sequence to map
MISR Space Oblique Mercator (SOM) coordinates into the AT3D model reference
frame. All inputs and outputs share the same linear units (e.g., meters).
"""

import numpy as np
import json

class CoordinateTransform:
    """Convert between MISR SOM coordinates and the AT3D model grid.

    Parameters
    ----------
    center_som_x, center_som_y : float
        SOM coordinates of the AT3D domain center.
    gamma : float
        Rotation in radians from the SOM +x axis toward east used to align the
        SOM frame with the model frame.
    domain_len_x, domain_len_y : float
        AT3D domain lengths along x and y (same units as SOM coordinates).
    """

    def __init__(self, center_som_x, center_som_y, gamma, domain_len_x, domain_len_y):
        self.center_som_x = center_som_x
        self.center_som_y = center_som_y
        self.gamma = gamma
        self.domain_len_x = domain_len_x
        self.domain_len_y = domain_len_y

    def __repr__(self):
        s = f'Domain center som x: {self.center_som_x}\n'
        s+= f'Domain center som y: {self.center_som_y}\n'
        s+= f'AT3D domain length x: {self.domain_len_x}\n'
        s+= f'AT3D domain length y: {self.domain_len_y}\n'
        s+= f'gamma: {self.gamma} radians'
        return s

    def SOM2AT3D(self, X, Y):
        """Map SOM coordinates to AT3D grid coordinates.

        Steps: (1) translate to place the origin at the domain center, (2)
        rotate by ``gamma`` (SOM +x toward east) to align with the model grid,
        and (3) translate to shift the origin to the lower-left corner of the
        AT3D domain.

        Parameters
        ----------
        X, Y : array-like or float
            SOM x and y coordinates.

        Returns
        -------
        tuple of array-like or float
            Transformed x and y coordinates in the AT3D frame.
        """

        # 1. Translation setting origin to domain center
        Xt = X - self.center_som_x
        Yt = Y - self.center_som_y
        # 2. Rotation about the origin orienting with the model frame
        Xtr = Xt * np.cos(self.gamma) + Yt * np.sin(self.gamma)
        Ytr = -Xt * np.sin(self.gamma) + Yt * np.cos(self.gamma)
        # 3. Translation setting corner of domain
        Xtrt = Xtr + (self.domain_len_x / 2)
        Ytrt = Ytr + (self.domain_len_y / 2)
        return Xtrt, Ytrt