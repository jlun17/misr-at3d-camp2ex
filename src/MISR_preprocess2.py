import pymap3d as pm
import xarray as xr
import numpy as np
import at3d
import netCDF4 as nc
import os
import warnings

def _LN2ENU(lat, lon, mu_m, phi_m, ref_lat, ref_lon):
    """
    Transform geodetic coordinates, lat and lon, and local north angles, mu_m 
    and phi_m, into East, North, Up coordinates and angles relative to the 
    geodetic point at ref_lat and ref_lon. Calculates the position of a point,
    P, which lies one unit distance away from point M in the direction of the
    angle. First computes P in ENU coordiantes relative to M, then converts to
    geodetic coordinates, then convertes to ENU coordiantes reltive to the
    reference point, R.

    Parameters
    ----------
    lat : N-dimensional np.array
        Geodetic latitude coordinates to be converted to ENU.
    lon : N-dimensional np.array
        Geodetic longitude coordiantes to be converted to ENU.
    mu_m : N-dimensional np.array
        Cosine of the zenith angle measured from local up.
    phi_m : N-dimensional np.array
        Azimuthal angle in radians measured from local North going clockwise.
    ref_lat : float
        Geodetic latitude coordinate, which transformed coordinates and angles
        are relative to.
    ref_lon : float
        Geodetic longitude coordinate, which transformed coordinates and angles
        are relative to.
    
    Returns
    -------
    mu_r : N-dimensional np.array
        Cosine of the zenith angle relative to reference point up.
    phi_r : N-dimensional np.array
        Azimuthal angle in radians relative to the reference point. Measured 
        from reference East going counterclockwise.
    M_e_r : N-dimensional np.array
        East coordiantes relative to the reference point.
    M_n_r : N-dimensional np.array
        North coordiantes relative to the reference point.
    M_u_r : N-dimensional np.array
        Up coordiantes relative tothe reference point.

    Notes
    -----
    Assumes all points lie on the WGS84 reference ellipsoid.
    """
    wgs84 = pm.Ellipsoid('wgs84')
    M_e_r, M_n_r, M_u_r = pm.geodetic2enu(lat, lon, np.zeros(lat.shape), ref_lat, ref_lon, 0.0, ell=wgs84, deg=True)
    P_e_m = np.multiply((1 - mu_m**2)**0.5, np.sin(phi_m))
    P_n_m = np.multiply((1 - mu_m**2)**0.5, np.cos(phi_m))
    P_u_m = mu_m
    P_lat, P_lon, P_alt = pm.enu2geodetic(P_e_m, P_n_m, P_u_m, lat, lon, np.zeros(lat.shape), ell=wgs84, deg=True)
    P_e_r, P_n_r, P_u_r = pm.geodetic2enu(P_lat, P_lon, P_alt, ref_lat, ref_lon, 0.0, ell=wgs84, deg=True)
    MP_e_r = P_e_r - M_e_r
    MP_n_r = P_n_r - M_n_r
    MP_u_r = P_u_r - M_u_r
    phi_r = np.arctan2(MP_n_r, MP_e_r)
    mu_r = (1 - MP_e_r**2 - MP_n_r**2)**0.5
    return mu_r, phi_r, M_e_r, M_n_r, M_u_r

def LN2ENU(misr_data_LN):
    """
    Transform from Local North to East, North, Up coordinates relative to the 
    center of the MISR data. Uses the center values for viewing angles - only 
    valid for domain sizes < (17.6 km)^2.

    Parameters
    ----------
    misr_data_LN : xr.Dataset
        Must have variables 'lat275', 'lon275', 'VZA_center' (degrees), 
        'VAA_center' (degrees), 'center'.
    
    Returns
    -------
    misr_data_ENU : xr.Dataset
        Input parameter misr_data_LN converted to ENU coordinates with 
        coordinates and angles relative to the center coordinate. Drops old
        coordinates and angles.

    Notes
    -----
    For larger domain sizes, one should diverge from assuming view angles are 
    uniform at every pixel as is done here.
    """
    misr_data_ENU = misr_data_LN.copy(deep=True)
    lat = misr_data_LN.lat275.data
    lon = misr_data_LN.lon275.data
    mu_m = np.zeros(shape=(misr_data_LN.dims['camera'], lat.shape[0], lat.shape[1]))
    phi_m = np.zeros(shape=(misr_data_LN.dims['camera'], lat.shape[0], lat.shape[1]))
    mu_r = np.zeros(shape=(misr_data_LN.dims['camera'], lat.shape[0], lat.shape[1]))
    phi_r = np.zeros(shape=(misr_data_LN.dims['camera'], lat.shape[0], lat.shape[1]))
    for i in range(misr_data_LN.dims['camera']):
        mu_m[i,:,:] = np.cos(np.radians(misr_data_LN.VZA_center.data[i]))
        phi_m[i,:,:] = np.radians(misr_data_LN.VAA_center.data[i])
        mu_r[i,:,:], phi_r[i,:,:], E, N, U = _LN2ENU(lat, lon, mu_m[i,:,:], phi_m[i,:,:], 
                                                    misr_data_LN.center_lat.data, misr_data_LN.center_lon.data)
    misr_data_ENU['E'] = (['y275', 'x275'], E/1000)
    misr_data_ENU['N'] = (['y275', 'x275'], N/1000)
    misr_data_ENU['U'] = (['y275', 'x275'], U/1000)
    misr_data_ENU['mu'] = (['camera', 'y275', 'x275'], mu_r)
    misr_data_ENU['phi'] = (['camera', 'y275', 'x275'], phi_r)
    misr_data_ENU = misr_data_ENU.drop(['lat275', 'lon275', 'lat17600', 'lon17600', 
                                    'SZA', 'SAA', 'VZA', 'VAA', 'VZA_center',
                                    'VAA_center'])
    misr_data_ENU['E'] = misr_data_ENU.E.assign_attrs(units='km')
    misr_data_ENU['N'] = misr_data_ENU.N.assign_attrs(units='km')
    misr_data_ENU['U'] = misr_data_ENU.U.assign_attrs(units='km')
    misr_data_ENU['mu'] = misr_data_ENU.mu.assign_attrs(description='cos(Viewing Zenith Angle)')
    misr_data_ENU['phi'] = misr_data_ENU.phi.assign_attrs(units='radians', description='Viewing Azimuth Angle')
    SAA_rad = np.radians(-misr_data_ENU.SAA_center.data + 90)
    SAA = np.degrees(np.arctan2(np.sin(SAA_rad), np.cos(SAA_rad)))
    misr_data_ENU['SAA_center'] = SAA
    # misr_data_ENU = misr_data_ENU.assign_attrs({'SAA_center': SAA})
    return misr_data_ENU

def _project_to_U2(E1, N1, U1, mu, phi, U2):
    """
    Helper function to project_to_U2. Take ENU coordinate (E1, N1, U1) and 
    project it along the line according to mu and phi to a new altitude of U2.
    """
    dU = U2 - U1
    dE = np.multiply(np.multiply(dU, np.tan(np.arccos(mu))), np.cos(phi))
    dN = np.multiply(np.multiply(dU, np.tan(np.arccos(mu))), np.sin(phi))
    E2 = E1 + dE
    N2 = N1 + dN
    return E2, N2

def project_to_U2(misr_data_ENU, U2):
    """
    Propagates rays to altitude given by U2.

    Parameters
    ----------
    misr_data_ENU : xr.Dataset
        MISR data transformed to ENU coordinates. Must have variables 'E', 'N', 
        'U', 'mu', 'phi' (radians).
    
    Returns
    -------
    misr_data_ENU : xr.Dataset
        Modified MISR dataset with coordiantes of projected rays.
    """
    E2 = np.zeros(misr_data_ENU.mu.data.shape)
    N2 = np.zeros(misr_data_ENU.mu.data.shape)
    # U2 = np.ones(misr_data_ENU.mu.data.shape)*10000
    for i in range(misr_data_ENU.dims['camera']):
        E1 = misr_data_ENU.E.data
        N1 = misr_data_ENU.N.data
        U1 = misr_data_ENU.U.data
        mu = misr_data_ENU.mu.data[i,:,:]
        phi = misr_data_ENU.phi.data[i,:,:]
        E2[i,:,:], N2[i,:,:] = _project_to_U2(E1, N1, U1, mu, phi, U2[i,:,:])
    misr_data_ENU['E2'] = (['camera', 'y275', 'x275'], E2)
    misr_data_ENU['N2'] = (['camera', 'y275', 'x275'], N2)
    misr_data_ENU['U2'] = (['camera', 'y275', 'x275'], U2)
    misr_data_ENU['E2'] = misr_data_ENU.E2.assign_attrs(units=misr_data_ENU.E.units)
    misr_data_ENU['N2'] = misr_data_ENU.N2.assign_attrs(units=misr_data_ENU.E.units)
    misr_data_ENU['U2'] = misr_data_ENU.U2.assign_attrs(units=misr_data_ENU.E.units)
    return misr_data_ENU

def TOA_extent(rte_grid, misr_data_ENU):
    """
    Roughly captures the projected extent at the top of the rte grid from the 
    DF to DA cameras.
    """
    xmin, ymin, zmin = rte_grid.x.data.min(), rte_grid.y.data.min(), rte_grid.z.data.min()
    xmax, ymax, zmax = rte_grid.x.data.max(), rte_grid.y.data.max(), rte_grid.z.data.max()
    altitude = zmax
    bb_8points = np.array(list(at3d.sensor.itertools.product([xmin, xmax], [ymin, ymax], [zmin, zmax]))).T
    
    DA = misr_data_ENU.sel(camera='DA').copy(deep=True)
    mu = DA.mu.data[0,0]
    phi = DA.phi.data[0,0]
    alpha = np.sqrt(1 - mu ** 2) * np.cos(phi) / mu
    beta = np.sqrt(1 - mu ** 2) * np.sin(phi) / mu
    projection_matrix = np.array([
        [1, 0, -alpha, alpha * altitude],
        [0, 1, -beta, beta * altitude],
        [0, 0, 0, altitude]
    ])
    DA_projected_bb = at3d.sensor._homography_projection(projection_matrix, bb_8points)

    DF = misr_data_ENU.sel(camera='DF').copy(deep=True)
    mu = DF.mu.data[0,0]
    phi = DF.phi.data[0,0]
    alpha = np.sqrt(1 - mu ** 2) * np.cos(phi) / mu
    beta = np.sqrt(1 - mu ** 2) * np.sin(phi) / mu
    projection_matrix = np.array([
        [1, 0, -alpha, alpha * altitude],
        [0, 1, -beta, beta * altitude],
        [0, 0, 0, altitude]
    ])
    DF_projected_bb = at3d.sensor._homography_projection(projection_matrix, bb_8points)
    
    lower = np.min(DA_projected_bb, axis=1)
    upper = np.max(DF_projected_bb, axis=1)
    return lower, upper

def make_sensor(misr_data_ENU, camera, min_extent, max_extent, wavelength):
    """
    Create a single camera sensor dataset that segments the misr data according 
    to the min and max extents.

    Parameters
    ----------
    misr_data_ENU : xr.Dataset
        MISR dataset projected to the top of the retreival domain with 
        coordiantes in 'E2', 'N2', and 'U2'.
    camera : string
        Name of the camera to select from the MISR dataset.
    min_extent : np.array
        [x_min, y_min] coordiantes of lower left corner of bounding box.
    max_extent : np.array
        [x_max, y_max] coordiantes of upper right corner of bounding box.
    
    Returns
    -------
    sensor : xr.Dataset
        Sensor dataset with "radiance" loaded into it.
    """
    misr_data_cam = misr_data_ENU.sel(camera=camera).copy(deep=True)
    condition = (misr_data_cam.E2.data >= min_extent[0]) & (misr_data_cam.E2.data <= max_extent[0]) & \
                (misr_data_cam.N2.data >= min_extent[1]) & (misr_data_cam.N2.data <= max_extent[1])
    x = misr_data_cam.E2.data[condition]
    y = misr_data_cam.N2.data[condition]
    z = misr_data_cam.U2.data[condition]
    mu = misr_data_cam.mu.data[condition]
    phi = misr_data_cam.phi.data[condition]
    stokes = np.array(['I']*len(x))
    sensor = at3d.sensor.make_sensor_dataset(x, y, z, mu, phi, stokes, wavelength, fill_ray_variables=True)
    mu0 = np.cos(np.radians(misr_data_cam.SZA_center.data))
    sensor['I'] = (['nrays'], misr_data_cam.brf.data[condition]*mu0/np.pi)
    sensor['I'] = sensor.I.assign_attrs(long_name='Radiance/(Solar flux on a horizonal surface) = I/F_0 = BRF * mu0 / pi')
    sensor = sensor.assign_attrs(name=camera)
    sensor = sensor.assign_attrs(mu0=mu0)
    sensor = sensor.assign_attrs(SAA=misr_data_cam.SAA_center.data)
    sensor = sensor.assign_attrs(u=misr_data_ENU.u, v=misr_data_ENU.v)
    return sensor

