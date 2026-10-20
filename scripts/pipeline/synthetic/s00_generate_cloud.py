"""OPTIONAL: draw a new stochastic TradeCumulus cloud field (the Fig 8 field and the Fig 9-10 source).

Not run by default. The manuscript field is data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc,
which is byte-identical to Synthetic/cloud_gen/cloud_fields/TradeCu/density/field07.nc: the 8th draw from
an interactive session in which the parameters were edited between draws. A new draw from this script
is a different field, so the data record ships the original as a pipeline input.

Source: generate_clouds.ipynb (copied from Synthetic/cloud_gen), cells idx 0, 1, 3, 6, plus generate_clouds.py.
Conda env: at3d_pure_k9 (the notebook kernel was at3d_pure, which no longer imports at3d: libgfortran.so.3 is missing)
Requires: aster_subroutine, compiled with `f2py -c aster_subroutines.f90 -m aster_subroutine` in this directory.
Output: data/synthetic/cloud_fields/TradeCu/{density,figures}/fieldNN.{nc,png}
Changes: the output path points to OUT_ROOT/data/synthetic.
"""
import generate_clouds as gc
import aster_subroutine as ast
import xarray as xr
import scipy.stats as st
import numpy as np
import matplotlib.pyplot as plt
import os
import collections
from scipy.optimize import curve_fit

def cloud_mean_tau(cloud):
    return np.mean(cloud.optical_depth.data[np.where(cloud.optical_depth.data > 0)])

def cloud_std_cth(cloud):
    return np.nanstd(cloud.cth.data)

def calc_lambda(cloud, maxD=7, bins=np.arange(0,7,0.1)):
    totalpixels = np.count_nonzero(~np.isnan(cloud.mask.data))
    outmask, totalflag, number = ast.flag_each_cloud(cloud.mask.data)
    # onns, nnpair = ast.nns(outmask,totalflag)
    # edge = ast.perimeter(outmask,totalflag)
    c = collections.Counter(outmask.flatten())
    del c[0]
    cloudypixels = sum(c.values())
    cloudfraction = cloudypixels/totalpixels
    cloud['outmask'] = (['x','y'], outmask)
    cloud = cloud.assign_coords(cloud_element=('cloud_element', list(c.keys())))
    cloud['numpixels'] = (['cloud_element'], list(c.values()))
    cloud['cloud_area'] = cloud.numpixels * cloud.delx * cloud.dely
    cloud['equiv_diameter'] = (4 * cloud.cloud_area / np.pi)**0.5

    tmpcloud = cloud.isel(cloud_element=np.where(cloud.equiv_diameter.data < maxD)[0]).copy(deep=True)
    bins_list = list(bins)
    weights = np.ones_like(tmpcloud.equiv_diameter.data)/tmpcloud.sizes['cloud_element']
    n, bins = np.histogram(tmpcloud.equiv_diameter.data, bins=bins_list, weights=weights)
    bin_center = (bins[1:] + bins[:-1])*0.5
    pars2, cov2 = curve_fit(f=line_law, xdata=np.log(bin_center[n!=0]), ydata=np.log(n[n!=0]))
    cloud.attrs['parm0'] = pars2[0]
    cloud.attrs['parm1'] = pars2[1]
    cloud.attrs['cf_calc'] = cloudfraction
    return cloud

def set_properties(cloud):
    cloud['optical_depth'] = cloud.density.integrate('z')
    cloud['cth'] = cloud.z.where(cloud.density > 0).max('z')
    cloud['cbh'] = cloud.z.where(cloud.density > 0).min('z')
    cloud['thickness'] = cloud.cth - cloud.cbh
    cloud['mask'] = cloud.cth.notnull()
    rho_l = 1000 # kg/m^3
    cloud['lwc'] = (2/3) * cloud.density * 1e-3 * rho_l * cloud.reff * 1e-6 # kg/m^3
    cloud['lwp'] = cloud.lwc.integrate('z') * 1e3 * 1e3 # g/m^2
    cloud['nan_lwc'] = cloud.lwc.copy(deep=True)
    cloud.nan_lwc.data[cloud.lwc.data == 0] = np.nan
    cloud['lwc_h_std'] = cloud.nan_lwc.std(['x'], skipna=True)
    cloud['lwc_fc'] = cloud.lwc_h_std / cloud.nan_lwc.mean(['x'], skipna=True)
    if(cloud.cf < 0.99):
        cloud = calc_lambda(cloud)
    return cloud

def line_law(x, a, b):
    return (a - b*(x))

def calc_relstd(cf):
    percentile = st.norm.ppf(1.0-cf)
    r = st.truncnorm.rvs(a=percentile, b=np.inf, size=100000)
    b = (r-r.min())
    b /= b.mean()
    b *= 0.4/b.mean()
    return b.std()/b.mean()


def plotCloud(cloud, savebase=None, filename=None):
    f, axs = plt.subplots(2, 5, figsize=(27, 8))
    cloud.cth.plot(ax=axs[0,0])
    axs[0,0].set_title('Cloud Top Height [km]')

    cloud.optical_depth.plot(ax=axs[0,1])
    axs[0,1].set_title('Cloud Optical Depth')

    cloud['mask'].plot(cmap='gray', ax=axs[0,2])

    cloud.lwp.plot(ax=axs[0,3])
    axs[0,3].set_title('LWP [g/m^2]')

    cloud.lwc_fc.plot(x='y', ax=axs[0,4])

    h = axs[1,0].hist(cloud.cth.data[np.bitwise_not(np.isnan(cloud.cth.data))], bins=np.linspace(np.min(cloud.z.data), np.max(cloud.z.data), 40))
    cth_mean = np.nanmean(cloud.cth.data)
    cth_std = cloud_std_cth(cloud)
    axs[1,0].vlines(cth_mean, 0, np.max(h[0]), 'k', label='cloud-mean cth: {:.3f} km'.format(cth_mean))
    axs[1,0].vlines([cth_mean-cth_std, cth_mean+cth_std], 0, np.max(h[0]), 'k', linestyles='dashed', label='std cth: {:.3f} km\nrelstd: {:.3f}'.format(cth_std, cth_std/cloud.thickness.mean().data))
    axs[1,0].legend()
    axs[1,0].set_xlabel('Cloud Top Height [km]')

    h = axs[1,1].hist(cloud.optical_depth.data[cloud.optical_depth.data > 0], bins=np.logspace(-2, 3, 40))
    mean_tau = cloud_mean_tau(cloud)
    axs[1,1].vlines(mean_tau, 0, np.max(h[0]), 'k', label='cloud-mean tau: {:.2f}'.format(mean_tau))
    axs[1,1].legend()
    # axs[1,1].text(0.8, 0.8, 'mean tau: {:.2f}'.format(mean_tau))
    axs[1,1].set_xscale('log')
    axs[1,1].set_xlabel('Optical depth')

    txt = '\n'.join([f'{key:<15s} {value:<n}' for key, value in cloud.attrs.items()])
    axs[1,2].text(0.0, 0.0, txt, fontsize='medium', fontfamily='monospace')
    axs[1,2].set_axis_off()

    h = axs[1,3].hist(cloud.lwp.data[cloud.lwp.data > 0], bins=np.logspace(-1, 3, 40))
    mean_lwp = np.mean(cloud.lwp.data[np.where(cloud.lwp.data > 0)])
    axs[1,3].vlines(mean_lwp, 0, np.max(h[0]), 'k', label='cloud-mean lwp: {:.2f} g/m^2'.format(mean_lwp))
    axs[1,3].legend()
    # axs[1,1].text(0.8, 0.8, 'mean tau: {:.2f}'.format(mean_tau))
    axs[1,3].set_xscale('log')
    axs[1,3].set_xlabel('LWP [g/m^2]')

    if(cloud.cf < 0.99):
        tmpcloud = cloud.isel(cloud_element=np.where(cloud.equiv_diameter.data < 7)[0]).copy(deep=True)
        bins_list = list(np.arange(0,7,0.1))
        weights = np.ones_like(tmpcloud.equiv_diameter.data)/tmpcloud.sizes['cloud_element']
        n, bins, patches = axs[1,4].hist(x=tmpcloud.equiv_diameter.data, bins=bins_list, histtype=u'step', weights=weights, label='Observations')
        # n[n==0]=1
        bin_center = (bins[1:] + bins[:-1])*0.5
        # pars2, cov2 = curve_fit(f=line_law, xdata=np.log(bin_center), ydata=np.log(n))
        axs[1,4].plot(bin_center, np.exp(line_law(np.array(np.log(bin_center)), *(tmpcloud.parm0,tmpcloud.parm1))), linestyle='--', linewidth=1.5, color='black', label='Line Fit ($\lambda$=%.2f)' % tmpcloud.parm1)
        axs[1,4].legend()
        axs[1,4].set_xscale('log')
        axs[1,4].set_yscale('log')
        axs[1,4].set_xlabel('Cloud Equivalent Diameter (km)')
        axs[1,4].set_ylabel('Normalized Frequency')
        axs[1,4].grid()
        axs[1,4].set_xlim(1,10)
    else:
        axs[1,4].set_axis_off()

    if(savebase != None):
        figsavebase = savebase + '/figures'
        densavebase = savebase + '/density'
        os.makedirs(figsavebase, exist_ok=True)
        os.makedirs(densavebase, exist_ok=True)

        figsavename = figsavebase + '/' + filename + '00.png'
        densavename = densavebase + '/' + filename + '00.nc'

        i = 0
        while(os.path.isfile(figsavename) or os.path.isfile(densavename)):
            figsavename = '{}/{}{:02d}.png'.format(figsavebase, filename, i)
            densavename = '{}/{}{:02d}.nc'.format(densavebase, filename, i)
            i += 1

        f.savefig(figsavename)
        cloud.to_netcdf(densavename)


nx = 149
ny = 149
dx = 1.0
dy = 1.0
dz = 0.040
zmin = 0.0
zmax = 3.0
beta = -2
beta_ext = -5.0/3.0
cf = 0.115
ext_rel_std = 0.1
tau_mean = 5
relstd = calc_relstd(cf)
thickness_mean = 0.45
tau_power=5.0/3.0
veff = 0.07
N0 = 100.0
cbase=0.450
filter_sigma=0.5
cloud = gc.generate_cloud(nx, ny, dx, dy, dz, zmin, zmax, beta, beta_ext, cf, ext_rel_std,
                        tau_mean, relstd, thickness_mean, tau_power, veff, N0, cbase, filter_sigma)
cloud = set_properties(cloud)

outpath = os.path.join(os.environ.get('OUT_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')), 'data', 'synthetic', 'cloud_fields', 'TradeCu')
plotCloud(cloud, savebase=outpath, filename='field')
