import numpy as np
import at3d
import xarray as xr
import pylab as py
import scipy.stats as st
import copy
import scipy.ndimage as ndi
import scipy.spatial as ss

np.random.seed(1)

def generate_cloud(nx,ny, dx, dy, dz, zmin, zmax, beta, beta_ext, cf, ext_rel_std, tau_mean, relstd,
                  thickness_mean=0.35, tau_power=5.0/3.0, veff=0.07, N0=200.0, cbase=0.45, filter_sigma=0.5):

    nz = int((zmax - cbase)/dz)
    z = np.arange(zmin, zmax+dz, dz)

    X,Y,Z = np.meshgrid(np.arange(0,dx*nx, dx), np.arange(0,dy*ny, dy),
                       z, indexing='ij')
    positions = np.stack([X.ravel(),Y.ravel(),Z.ravel()], axis=-1)

    tree = ss.KDTree(positions)

    generator = at3d.generate.GaussianFieldGenerator(nx, ny, 1, beta, domain_size=[nx*dx, ny*dy, nz*dz])
    field = generator.generate_field()

    percentile = st.norm.ppf(1.0-cf)

    field[np.where(field < percentile)] = np.nan
    ranks = st.rankdata(field[np.where(~np.isnan(field))]).astype(int) - 1

    r = st.truncnorm.rvs(a=percentile, b=np.inf, size=ranks.size)
    r -= percentile
    r *= thickness_mean/r.mean()

    if cf > 0.99:
        r -= thickness_mean
        r *= thickness_mean*relstd/r.std()
        r += thickness_mean

    thickness = np.zeros(field.shape)*np.nan
    thickness[np.where(~np.isnan(field))] = np.sort(r)[ranks]

    generator_3d = at3d.generate.GaussianFieldGenerator(nx, ny, z.size, beta_ext, domain_size=[nx*dx, ny*dy, z.max()-z.min()])
    ext = generator_3d.generate_field()

    big_z = np.repeat(np.repeat(z[None, None,:], nx, axis=0), ny, axis=1)
    means = (big_z-cbase)**(tau_power - 1.0)
    means[np.where(means < 0.0)] = np.nan
    means[np.where(big_z-cbase > thickness)] = np.nan

    means[np.where(np.isnan(thickness))[0],
         np.where(np.isnan(thickness))[1],:] = np.nan

    tau = np.nansum(0.5*(means[...,1:] + means[...,:-1])*dz, axis=-1)
    means *= tau_mean/np.nanmean(tau[np.where(tau>0.0)])
    ext = np.exp(ext)
    ext -= ext.mean()
    ext /= ext.std()
    ext *= means*ext_rel_std/np.nanstd(ext)
    ext += means - np.nanmean(ext)

    ext[np.where(np.isnan(ext))] = 0.0
    ext[np.where(ext < 0.0)] = 0.0

    k = (1.0-veff)*(1.0-2*veff)
    reff = np.sqrt(1e3*np.nanmean(means, axis=(0,1))/(2*np.pi*k*N0))[None,None]*np.ones(ext.shape)
    reff[np.where(reff < 1.0)] = 1.0
    reff[np.where(np.isnan(reff))] = 1.0

    Ns = np.zeros(ext.shape)
    Ns[np.where(ext > 0.0)] = (1e3*ext/(2*np.pi*k*reff**2))[np.where(ext > 0.0)]

    # replace edge with smoothed value to approximate cloud edge dilution
    if filter_sigma is not None:
        #ext2 = ndi.gaussian_filter(ext, sigma=filter_sigma, mode='wrap', truncate=2.0)
        Ns2 = ndi.gaussian_filter(Ns, sigma=filter_sigma, mode='wrap', truncate=2.0)

        query_mask = np.where((Ns2 > 0.0)&(Ns==0.0))
        queries = np.stack([X[query_mask], Y[query_mask], Z[query_mask]],axis=-1)
        d,i = tree.query(queries, k=9)
        Ns[np.unravel_index(i, ext.shape)] = Ns2[np.unravel_index(i, ext.shape)]
        Ns[np.where(Ns < 10.0)] = 0.0
        ext[np.unravel_index(i, ext.shape)] = (1e-3*Ns*2*np.pi*k*reff**2)[np.unravel_index(i, ext.shape)]

    # reff
    reff[np.where(reff < 1.0)] = 1.0
    reff[np.where(ext ==0.0)] = 1.0

    # no cloud on the top grid point.
    ext[...,-1] = 0.0

    tau = np.nansum(0.5*(ext[...,1:] + ext[...,:-1])*dz, axis=-1)
    ext *= tau_mean/np.nanmean(tau[np.where(tau > 0.0)])

    cloud = at3d.grid.make_grid(dx, nx, dy, ny, z=z)
    cloud['density'] = (['x','y','z'], ext)
    cloud['reff'] = (['x','y','z'], reff)
    cloud['veff'] = (['x','y','z'], np.ones(reff.shape)*veff)

    # good_zs = np.where(cloud.density.max(('x','y')).data > 0)
    # goodz1 = max(good_zs[0][0]-1,0)
    # goodz2 = min(good_zs[0][-1]+1,cloud.z.size-1)
    # cloud = cloud.sel(z=slice(cloud.z[goodz1], cloud.z[goodz2])) # john modification: return the whole domain

    cloud.attrs['N0'] = N0
    cloud.attrs['filter_sigma'] = filter_sigma
    cloud.attrs['beta'] = beta
    cloud.attrs['beta_ext'] = beta_ext
    cloud.attrs['zmin'] = zmin
    cloud.attrs['zmax'] = zmax
    cloud.attrs['tau_power'] = tau_power
    cloud.attrs['thickness_mean'] = thickness_mean
    cloud.attrs['cbase'] = cbase
    cloud.attrs['tau_mean'] = tau_mean
    cloud.attrs['cf'] = cf
    cloud.attrs['ext_rel_std'] = ext_rel_std
    cloud.attrs['relstd'] = relstd

    return cloud


if __name__ == '__main__':

    import sys
    import os

    config_filepath = sys.argv[1]
    out_directory = sys.argv[2]
    config = xr.load_dataset(config_filepath)

    relstds = config.relstd.values
    taus = config.tau_mean.values
    cfs = config.cf.values
    betas = config.beta.values
    N0s = config.N0.values

    for i,(relstd, tau_mean, cf, beta, N0) in enumerate(zip(relstds, taus, cfs, betas, N0s)):

        cloud = generate_cloud(int(config.nx.values), int(config.ny.values), float(config.dx.values), float(config.dy.values), float(config.dz.values),
                    float(config.zmin.values), float(config.zmax.values), beta, float(config.beta_ext.values), cf, float(config.ext_rel_std.values),
                    tau_mean, relstd, filter_sigma=float(config.filter_sigma.values), N0=N0)

        cloud_name = 'Cloud_' + str(i).zfill(3) + '.nc'
        cloud.to_netcdf(os.path.join(out_directory, cloud_name))
