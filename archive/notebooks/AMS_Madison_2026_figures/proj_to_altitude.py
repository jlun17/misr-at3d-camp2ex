import numpy as np
import xarray as xr


def project_sensor_to_altitude(sensor: xr.Dataset, altitude: float, min_mu: float = 1e-8) -> xr.Dataset:
    """
    Project a sensor's pixel-level (cam_*) and ray-level (ray_*) geometry onto the
    horizontal plane z = `altitude`.

    Convention: (mu, phi) describe the *direction of photon travel*, i.e. the vector
    pointing from a scene point toward the sensor:
        direction = (sqrt(1 - mu**2) * cos(phi),
                     sqrt(1 - mu**2) * sin(phi),
                     mu)
    So the scene point that produced a given (x, y, z, mu, phi) satisfies:
        (x, y, z) = point + t * direction   for some t >= 0
    Solving the z-component for t and substituting into x, y gives the projected
    (x, y) at the requested altitude.

    Parameters
    ----------
    sensor : xr.Dataset
        Sensor dataset with cam_x/y/z, cam_mu/phi (dim npixels) and
        ray_x/y/z, ray_mu/phi (dim nrays).
    altitude : float
        Target altitude (same units/coords as cam_z / ray_z).
    min_mu : float
        Rays with |mu| below this are treated as horizontal (never cross a
        different altitude) and marked invalid.

    Returns
    -------
    xr.Dataset
        A deep copy of `sensor` with cam_x/y/z and ray_x/y/z overwritten by their
        projected positions, plus new boolean masks `cam_valid` (npixels) and
        `ray_valid` (nrays) indicating which projections succeeded. Global attrs
        are preserved as-is; `sensor.attrs['position']` etc. still describe the
        *original* sensor pose. A new attr `projected_to_altitude` records what
        was done.
    """

    def _project(x, y, z, mu, phi):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)
        mu = np.asarray(mu, dtype=float)
        phi = np.asarray(phi, dtype=float)

        sin_theta = np.sqrt(np.clip(1.0 - mu**2, 0.0, None))
        dx = sin_theta * np.cos(phi)
        dy = sin_theta * np.sin(phi)
        # dz = mu

        with np.errstate(divide="ignore", invalid="ignore"):
            t = (z - altitude) / mu

        valid = np.isfinite(t) & (t >= 0) & (np.abs(mu) > min_mu)

        x_proj = np.where(valid, x - t * dx, np.nan)
        y_proj = np.where(valid, y - t * dy, np.nan)
        z_proj = np.where(valid, altitude, np.nan)

        return x_proj, y_proj, z_proj, valid

    projected = sensor.copy(deep=True)

    cam_x, cam_y, cam_z, cam_valid = _project(
        sensor["cam_x"].values, sensor["cam_y"].values, sensor["cam_z"].values,
        sensor["cam_mu"].values, sensor["cam_phi"].values,
    )
    ray_x, ray_y, ray_z, ray_valid = _project(
        sensor["ray_x"].values, sensor["ray_y"].values, sensor["ray_z"].values,
        sensor["ray_mu"].values, sensor["ray_phi"].values,
    )

    projected["cam_x"].values[:] = cam_x
    projected["cam_y"].values[:] = cam_y
    projected["cam_z"].values[:] = cam_z
    projected["ray_x"].values[:] = ray_x
    projected["ray_y"].values[:] = ray_y
    projected["ray_z"].values[:] = ray_z

    projected["cam_valid"] = (("npixels",), cam_valid)
    projected["ray_valid"] = (("nrays",), ray_valid)

    projected.attrs["projected_to_altitude"] = float(altitude)

    n_invalid_cam = int((~cam_valid).sum())
    n_invalid_ray = int((~ray_valid).sum())
    if n_invalid_cam or n_invalid_ray:
        import warnings
        warnings.warn(
            f"project_sensor_to_altitude: {n_invalid_cam} pixel(s) and "
            f"{n_invalid_ray} ray(s) could not be projected to altitude={altitude} "
            "(horizontal ray or wrong-side intersection) and are set to NaN. "
            "See 'cam_valid'/'ray_valid'."
        )

    return projected