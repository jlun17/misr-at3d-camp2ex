"""
This script retruns the optical properties of a given MISR aersol mixture for 
one of MISR spectral bands. The extinction is scaled to match the user-specified
aerosol optical depth (aod). The vertical distribution is determined based on 
aerosol mixture type to match the MISR aerosol products as detailed in Kahn and 
Gaitley (2015).

References
----------
Kahn, R. A., & Gaitley, B. J. (2015). An analysis of global aerosol type as 
retrieved by MISR. Journal of Geophysical Research: Atmospheres, 120(9), 4248–4281.

Example usage
-------------
    expr_dir = '../dev/'
    rte_grid = xr.load_dataset('{}rte_grid.nc'.format(expr_dir))
    aerosol_optical_properties = get_MISR_mixture_optical_properties(
        band=0.67,
        mixture=21,
        aod=0.2,
        rte_grid=rte_grid,
        acp_file='../data/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc',
        legendre_order=20,
        g_tol=1e-2
    )
"""

import xarray as xr
import numpy as np
import at3d

def get_MISR_mixture_optical_properties(band, mixture, aod, rte_grid, acp_file, legendre_order=12, g_tol=1e-3, res_tol=1):
    # Read in MISR aerosol data
    acp_all = xr.load_dataset(acp_file)
    acp = acp_all.sel(mixture=mixture, band=band, method='nearest').copy(deep=True)

    # Perform Legendre function expansion
    x = np.cos(acp.theta.data)
    y = acp.phase.data
    legendre_coeffs_P11, leg_quality = np.polynomial.legendre.legfit(x, y, legendre_order, full=True)

    legendre_coeffs_P11 /= legendre_coeffs_P11[0] # normalization

    assert np.abs(leg_quality[0]) <= res_tol, 'Residual tolerance not met. Residual: {:f}'.format(leg_quality[0][0])
    assert np.abs(legendre_coeffs_P11[1]/3 - acp.g.data) <= g_tol, 'Asymmetry tolerance not met. Expected g = {:f} and got g = {:f}'.format(acp.g.data, legendre_coeffs_P11[1]/3)

    StokesIndex = 6
    legendreIndex = legendre_order + 1
    PhaseFunctionIndex = 1

    phase_function_table = np.zeros((StokesIndex, legendreIndex, PhaseFunctionIndex))
    phase_function_table[0, :, 0] = legendre_coeffs_P11
    phase_function_indicies = np.zeros((1, rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z']))

    # Plug aerosol profile into rte_grid
    rte_grid = aerosol_vertical_distribution(aod, mixture, rte_grid)

    extinction = np.tile(rte_grid.z_ext.data, (rte_grid.dims['x'], rte_grid.dims['y'], 1))
    ssalb = acp.ssalb.data * np.ones((rte_grid.dims['x'], rte_grid.dims['y'], rte_grid.dims['z']))

    # Generate optical properties
    aerosol_optical_properties = at3d.medium.make_optical_properties(
        grid=rte_grid,
        extinction=extinction,
        ssalb=ssalb,
        phase_function_indices=phase_function_indicies,
        phase_function_table=phase_function_table,
        phase_function_weights=None
    )
    aerosol_optical_properties = aerosol_optical_properties.assign_attrs(
        mixture=acp.mixture.data,
        band=acp.band.data,
        leg_residuals=leg_quality[0]
    )
    return aerosol_optical_properties

def aerosol_vertical_distribution(aod, mixture, rte_grid):
    z = rte_grid.z.data
    if(mixture <= 50):
        H = 2
        B0 = -aod / (H*(np.exp(-10/H) - 1))
        B = B0 * np.exp(-z/H)
        B[z > 10] = 0
    else:
        H = 10
        B0 = -aod / (H*(np.exp(-3/H) - 1))
        B = B0 * np.exp(-(z-3)/H)
        B[z < 3] = 0
        B[z > 6] = 0
    rte_grid['z_ext'] = (['z'], B)
    rte_grid_minus1 = rte_grid.isel(z = slice(0, -1)).copy(deep=True)
    tau_minus1 = rte_grid_minus1.z_ext.integrate('z').data
    h = rte_grid.z.data[-1] - rte_grid.z.data[-2]
    xmax = rte_grid_minus1.z_ext.data[-1]
    del_tau = aod - tau_minus1
    compensation_extinction = ((2*del_tau)/h) - xmax
    B[-1] = compensation_extinction
    rte_grid['z_ext'] = (['z'], B)
    return rte_grid

if __name__ == '__main__':
    expr_dir = '../dev/'
    rte_grid = xr.load_dataset('{}rte_grid.nc'.format(expr_dir))
    aerosol_optical_properties = get_MISR_mixture_optical_properties(
        band=0.67,
        mixture=22,
        aod=0.2,
        rte_grid=rte_grid,
        acp_file='../data/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc',
        legendre_order=20,
        g_tol=1e-2
    )
    aerosol_optical_properties