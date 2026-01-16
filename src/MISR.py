import MisrToolkit as mtk
from typing import Union, List
import numpy as np
import xarray as xr
from pathlib import Path

def convergenceAngle(
        path: int, 
        lat: float,
        lon: float, 
        dlon: float = 1e-5
    ) -> float:
    """Compute the angle between the positive SOM x-axis and the local east direction."""
    x0, y0 = mtk.latlon_to_somxy(path, lat, lon)
    x1, y1 = mtk.latlon_to_somxy(path, lat, lon+dlon)
    gamma = np.arctan2(y1 - y0, x1 - x0)
    return gamma

def hdf2xr(
        hdf_name: Union[str, Path], 
        grid_name: str, 
        field_name_list: List[str], 
        region: mtk.MtkRegion
    ) -> xr.Dataset:
    """Convert MISR HDF grid data to xarray Dataset for a specified region.
    
    Parameters
    ----------
    hdf_name : str | Path
        Path to the MISR HDF file.
    grid_name : str
        Name of the grid within the HDF file to extract data from.
    field_name_list : list[str]
        List of field names to extract from the grid.
    region : mtk.MtkRegion
        The spatial region to extract data for.

    Returns
    -------
    xr.Dataset
        An xarray Dataset containing the specified fields and convergence angle.
    """
    file = mtk.MtkFile(str(hdf_name))
    path = file.attr_get("Path_number")

    grid = file.grid(grid_name)
    res = grid.attr_get('Block_size.resolution_x')
    map = region.snap_to_grid(path, res)
    lat, lon = map.create_latlon()
    som_x = np.arange(map.som.ulc.x, map.som.lrc.x+res, res)
    som_y = np.arange(map.som.ulc.y, map.som.lrc.y+res, res)

    gamma = np.zeros_like(lat)
    for i in range(lat.shape[0]):
        for j in range(lat.shape[1]):
            gamma[i, j] = convergenceAngle(path, lat[i,j], lon[i,j])

    xarr = xr.Dataset(
        data_vars={
            'lat': (['som_x', 'som_y'], lat),
            'lon': (['som_x', 'som_y'], lon),
            'gamma': (['som_x', 'som_y'], gamma)
        },
        coords=dict(
            som_x = som_x,
            som_y = som_y
        ),
        attrs=dict(
            path = path,
            orbit = file.orbit,
            block_range = region.block_range(path),
            resolution = res
        )
    )
    xarr['gamma'].attrs['description'] = 'angle between the positive SOM x-axis and the local east direction'
    xarr['gamma'].attrs['long_name'] = 'Convergence angle'
    xarr['gamma'].attrs['units'] = 'radians'

    for field_name in field_name_list:
        xarr[field_name] = (['som_x', 'som_y'], grid.field(field_name).read(region).data())

    return xarr
    
def grp2xr(
        data_dir: Union[str, Path],
        path: int,
        orbit: int, 
        cam_list: List[str], 
        region: mtk.MtkRegion, 
        grid_name: str ='RedBand', 
        field_name: str ='Red Brf'
    ) -> xr.Dataset:
    """Convert a set of MISR Georectified Radiance Product files into xarray.
    
    Note: All view angles must have common resolution

    Parameters
    ----------
    data_dir : str | Path
        Directory containing the MISR GRP HDF files.
    path : int
        MISR path number.
    orbit : int
        MISR orbit number.
    cam_list : list[str]
        List of camera/view angles to include (e.g., ['an', 'af', 'aa', ...]).
    region : mtk.MtkRegion
        The spatial region to extract data for.
    grid_name : str, optional
        Name of the grid within the HDF file to extract data from, by default 'RedBand'.
    field_name : str, optional
        Name of the field to extract from the grid, by default 'Red Brf'.
    
    Returns
    -------
    xr.Dataset
        An xarray Dataset containing the specified field for each camera and the convergence angle.
    """
    grp_files = [data_dir / f'MISR_AM1_GRP_ELLIPSOID_GM_P{path:03d}_O{orbit:06d}_{c.upper()}_F03_0024.hdf' for c in cam_list]
    file = mtk.MtkFile(str(grp_files[0]))
    path = file.attr_get("Path_number")

    grid = file.grid(grid_name)
    res = grid.attr_get('Block_size.resolution_x')
    map = region.snap_to_grid(path, res)
    lat, lon = map.create_latlon()
    som_x = np.arange(map.som.ulc.x, map.som.lrc.x+res, res)
    som_y = np.arange(map.som.ulc.y, map.som.lrc.y+res, res)

    gamma = np.zeros_like(lat)
    for i in range(lat.shape[0]):
        for j in range(lat.shape[1]):
            gamma[i, j] = convergenceAngle(path, lat[i,j], lon[i,j])

    xarr = xr.Dataset(
        data_vars={
            'lat': (['som_x', 'som_y'], lat),
            'lon': (['som_x', 'som_y'], lon),
            'gamma': (['som_x', 'som_y'], gamma)
        },
        coords=dict(
            som_x = som_x,
            som_y = som_y,
            camera = cam_list
        ),
        attrs=dict(
            path = path,
            orbit = file.orbit,
            block_range = region.block_range(path),
            resolution = res
        )
    )
    brf = np.zeros(shape=(len(cam_list), len(som_x), len(som_y)))
    for i in range(brf.shape[0]):
        file = mtk.MtkFile(str(grp_files[i]))
        grid = file.grid(grid_name)
        field = grid.field(field_name)
        brf[i,:,:] = field.read(region).data()
    xarr['brf'] = (['camera', 'som_x', 'som_y'], brf)
    xarr['brf'].attrs['long_name'] = field_name
    return xarr
