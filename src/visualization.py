import sys
sys.path.append('/data/keeling/a/johntl3/b/LundstromPub2025/src')

import os

import at3d
import numpy as np
import xarray as xr
import glob
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import imageio.v2 as imageio

from util import load_sensor_dict

# # These are some parameters to make figures nice (and big)
# params = {'legend.fontsize': 'x-large',
#          'axes.labelsize': 'x-large',
#          'axes.titlesize': 'x-large',
#          'xtick.labelsize': 'x-large',
#          'ytick.labelsize': 'x-large'}

# plt.rcParams.update(params)

plt.style.use('seaborn-v0_8-talk')

# Movie Making
def make_movie(outfile, nframes=None, fps=3, bounce=True):
    images = []
    dir = os.path.dirname(outfile)
    files = np.sort(glob.glob(dir + '/*.png'))
    if nframes != None:
        for i in range(nframes):
            fi = files[i]
            images.append(imageio.imread(fi))
        if(bounce):
            for i in range(nframes-2, 0, -1):
                fi = files[i]
                images.append(imageio.imread(fi))
    else:
        for fi in files:
           images.append(imageio.imread(fi))
    imageio.mimsave(outfile, images, loop=15, duration=3, fps=fps)
    print('Movie saved at {}'.format(outfile))

### MISR Observation Plots
def plot_misr_data(filename, fig, ax, vmax=0.8, cbar_loc='right'):
    misr_data = xr.load_dataset(filename)
    brf = misr_data.brf.data
    for i in range(brf.shape[0]):
        c = ax[i].imshow(brf[i,:,:], cmap='gray', vmin=0, vmax=vmax, aspect='equal')
        ax[i].set_xticks([])
        ax[i].set_yticks([])
        ax[i].set_title('{}\nVZA={:.1f}\nVAA={:.1f}'.format(misr_data.camera.data[i], misr_data.VZA_center.data[i], misr_data.VAA_center.data[i]))
    if(cbar_loc != None):
        plt.colorbar(c, ax=ax[:], shrink=0.7, location=cbar_loc)
    fig.suptitle('Registered to Ellipsoid')

def misr_obs_frames(misr_obs_file, out_dir, s=2, overlay_sampling=False, vmin=None, vmax=None):
    os.makedirs(out_dir, exist_ok=True)
    misr_obs = xr.load_dataset(misr_obs_file)
    for i in range(misr_obs.dims['camera']):
        f, ax = plt.subplots(1, 1, figsize=(5,5))
        title = '{}\nVZA = {:.1f}\nVAA = {:.1f}\nz = ellipsoid'.format(
            misr_obs.camera.data[i],
            misr_obs.VZA_center.data[i],
            misr_obs.VAA_center.data[i]
        )
        c = ax.scatter(
            misr_obs.lon275.data,
            misr_obs.lat275.data,
            s=s,
            c=misr_obs.brf.data[i,:,:],
            vmin=vmin,
            vmax=vmax,
            marker='s',
            cmap='gray'
        )
        if(overlay_sampling):
            ax.scatter(misr_obs.lon17600.data.ravel(), misr_obs.lat17600.data.ravel())
            ax.scatter(misr_obs.center_lon.data, misr_obs.center_lat.data)
        ax.set_title(title)
        # plt.colorbar(c, shrink=0.7, label='brf')
        f.savefig('{}frame{:03d}.png'.format(out_dir, i))
        plt.close(f)


def plot_misr_data_map(filename, fig, ax, vmax=0.5, cbar_loc=None, s=2.0):
    misr_data = xr.load_dataset(filename)
    for i in range(misr_data.dims['camera']):
        title = '{}\nVZA = {:.1f}\nVAA = {:.1f}'.format(misr_data.camera.data[i],
                                                        misr_data.VZA_center.data[i],
                                                        misr_data.VAA_center.data[i])
        c = ax[i].scatter(
            misr_data.lon275.data,
            misr_data.lat275.data,
            s=s,
            c=misr_data.brf.data[i,:,:],
            vmax=vmax,
            marker='s',
            cmap='gray'
        )
        ax[i].set_title(title)
    fig.supxlabel('Longitude')
    fig.supylabel('Latitude')
    fig.suptitle('Registered to Ellipsoid')
    if(cbar_loc != None):
        plt.colorbar(c, ax=ax[:], shrink=0.7, location=cbar_loc, label='brf')

def overlay_sampling(filename, fig, ax):
    misr_data = xr.load_dataset(filename)
    for i in range(misr_data.dims['camera']):
        ax[i].scatter(misr_data.lon17600.data.ravel(), misr_data.lat17600.data.ravel())
        ax[i].scatter(misr_data.center_lon.data, misr_data.center_lat.data)

def plot_sun_view_grometry(filename, ax):
    misr_data = xr.load_dataset(filename)
    ax.scatter(np.radians(misr_data.SAA_center.data), misr_data.SZA_center.data, s=200.0, marker='*', c='y')
    for i in range(len(misr_data.camera.data)):
        ax.text(np.radians(misr_data.VAA_center.data[i]), misr_data.VZA_center.data[i], misr_data.camera.data[i], c='tab:orange')
    ax.set_ylim([0,90])
    ax.set_rticks([30, 60, 90])
    ax.set_rlabel_position(67.5)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title('Sun/View Geometry\n(Direction of photons)')

## AT3D Observation Plots
def plot_measurements(filename, instrument, fig, ax, s=2, vmin=None, vmax=None, set_title=True):
    sensor_dict = load_sensor_dict(filename)
    sensor_list = sensor_dict[instrument]['sensor_list']
    for i, cam in enumerate(sensor_list):
        z = np.unique(cam.ray_z.data)
        if(len(z) == 1):
            title = '{}\nz={} km'.format(cam.name, z[0])
        else:
            title = '{}\nz=non-uniform'.format(cam.name)
        c = ax[i].scatter(cam.ray_x.data, cam.ray_y.data, s=s, c=cam.I.data*np.pi/cam.mu0, marker='s', cmap='gray', vmin=vmin, vmax=vmax)
        if(set_title):
            ax[i].set_title(title)
    return c

def at3d_obs_frames(filename, instrument, out_dir, s=2, vmin=None, vmax=None):
    sensor_dict = load_sensor_dict(filename)
    sensor_list = sensor_dict[instrument]['sensor_list']
    os.makedirs(out_dir, exist_ok=True)
    for i, cam in enumerate(sensor_list):
        z = np.unique(cam.ray_z.data)
        f, ax = plt.subplots(1, 1, figsize = (5, 5))
        ax.scatter(cam.ray_x.data, cam.ray_y.data, s=s, c=cam.I.data*np.pi/cam.mu0, marker='s', cmap='gray', vmin=vmin, vmax=vmax)
        ax.set_xlim([-5, 24])
        ax.set_ylim([-11, 28])
        if(len(z) == 1):
            title = '{}\nz={} km'.format(cam.name, z[0])
        else:
            title = '{}\nz=non-uniform'.format(cam.name)
        ax.set_title(title)
        f.savefig('{}/frame{:03d}.png'.format(out_dir, i))
        plt.close(f)

## AT3D Plots
def brf_diff_frames(measurements_file, iter_dir, out_dir, instrument, s=2, brf_vmin=0, brf_vmax=0.5, diff_range=0.25):
    os.makedirs(out_dir, exist_ok=True)
    sensor_dict_obs = load_sensor_dict(measurements_file)
    sensor_list_obs = sensor_dict_obs[instrument]['sensor_list']
    iter_files = np.sort(glob.glob(iter_dir + 'iter*.nc'))
    for j, iter_file in enumerate(iter_files):
        fig, ax = plt.subplots(3, 9, figsize=(15, 7), sharex=True, sharey=True)
        sensor_dict_at3d = load_sensor_dict(iter_file)
        sensor_list_at3d = sensor_dict_at3d[instrument]['sensor_list']
        for i, (cam_obs, cam_at3d) in enumerate(zip(sensor_list_obs, sensor_list_at3d)):
            assert cam_obs.name == cam_at3d.name
            assert np.array_equal(cam_obs.ray_x.data, cam_at3d.ray_x.data)
            assert np.array_equal(cam_obs.ray_y.data, cam_at3d.ray_y.data)
            assert np.array_equal(cam_obs.ray_z.data, cam_at3d.ray_z.data)
            brf_obs = cam_obs.I.data*np.pi/cam_obs.mu0
            brf_at3d = cam_at3d.I.data*np.pi/cam_at3d.mu0
            brf_diff = brf_obs - brf_at3d
            z = np.unique(cam_obs.ray_z.data)
            if(len(z) == 1):
                title = '{}\nz={} km'.format(cam_obs.name, z[0])
            else:
                title = '{}\nz=non-uniform'.format(cam_obs.name)
            c0 = ax[0, i].scatter(cam_obs.ray_x.data, cam_obs.ray_y.data, s=s, c=brf_obs, marker='s', cmap='gray', vmin=brf_vmin, vmax=brf_vmax)
            c1 = ax[1, i].scatter(cam_obs.ray_x.data, cam_obs.ray_y.data, s=s, c=brf_at3d, marker='s', cmap='gray', vmin=brf_vmin, vmax=brf_vmax)
            c2 = ax[2, i].scatter(cam_obs.ray_x.data, cam_obs.ray_y.data, s=s, c=brf_diff, marker='s', cmap='RdBu', vmin=-diff_range, vmax=diff_range)
            ax[0, i].set_title(title)
        plt.colorbar(c1, ax=ax[0:2,:], location='right', shrink=0.8, label='brf')
        plt.colorbar(c2, ax=ax[2,:], location='right', shrink=0.8, label='obs-at3d')
        sup_title = os.path.basename(iter_file).split('.')[0]
        plt.suptitle(sup_title)
        fig.savefig('{}{}.png'.format(out_dir, sup_title))
        plt.close(fig)

def optical_depth_frames(iter_dir, out_dir, vmin=None, vmax=None, log=True):
    os.makedirs(out_dir, exist_ok=True)
    iter_files = np.sort(glob.glob(iter_dir + 'iter*.nc'))
    for i, iter_file in enumerate(iter_files):
        fig, ax = plt.subplots(1, 1, figsize=(8,6))
        sensors, solvers, rte_grid = at3d.util.load_forward_model(iter_file)
        if(log):
            solvers[0.67].medium['cloud'].extinction.integrate('z').plot(y='y', ax=ax, norm=colors.LogNorm(), vmin=vmin, vmax=vmax, cbar_kwargs={'label': 'optical depth'})
        else:
            solvers[0.67].medium['cloud'].extinction.integrate('z').plot(y='y', ax=ax, vmin=vmin, vmax=vmax, cbar_kwargs={'label': 'optical depth'})
        title = os.path.basename(iter_file).split('.')[0]
        ax.set_title(title)
        fig.savefig('{}{}.png'.format(out_dir, title))
        plt.close(fig)

def extinction_cross_section_frames(iter_dir, out_dir, dim='x', loc=1, vmin=None, vmax=None, log=True):
    # warnings.filterwarnings("ignore")
    os.makedirs(out_dir, exist_ok=True)
    iter_files = np.sort(glob.glob(iter_dir + 'iter*.nc'))
    for i, iter_file in enumerate(iter_files):
        fig, ax = plt.subplots(1, 1, figsize=(8,6))
        sensors, solvers, rte_grid = at3d.util.load_forward_model(iter_file)
        if(log):
            if(dim=='x'):
                solvers[0.67].medium['cloud'].extinction.sel(x=loc, method='nearest').plot(y='z', ax=ax, norm=colors.LogNorm(), vmin=vmin, vmax=vmax)
            elif(dim=='y'):
                solvers[0.67].medium['cloud'].extinction.sel(y=loc, method='nearest').plot(y='z', ax=ax, norm=colors.LogNorm(), vmin=vmin, vmax=vmax)
        else:
            if(dim=='x'):
                solvers[0.67].medium['cloud'].extinction.sel(x=log, method='nearest').plot(y='z', ax=ax, vmin=vmin, vmax=vmax)
            elif(dim=='y'):
                solvers[0.67].medium['cloud'].extinction.sel(y=log, method='nearest').plot(y='z', ax=ax, vmin=vmin, vmax=vmax)
        sup_title = os.path.basename(iter_file).split('.')[0]
        plt.suptitle(sup_title)
        fig.savefig('{}{}.png'.format(out_dir, sup_title))
        plt.close(fig)

def CAMP2Ex_insitu_compare(cloud, p3, f, ax, thresh=0):
    pristine = p3.aerosols.data == 0
    trans = p3.aerosols.data == 1
    polluted = p3.aerosols.data == 2

    prist_color = 'tab:green'
    trans_color = 'tab:gray'
    poll_color = 'tab:brown'
    
    cond = cloud.ext_ravel.data > thresh
    ax.scatter(cloud.ext_ravel.data[cond], cloud.Z.data[cond]*1000)

    ax.scatter(p3.ext_km.data[pristine], p3.GPS_Altitude[pristine], c=prist_color, label='pristine')
    ax.scatter(p3.ext_km.data[trans], p3.GPS_Altitude[trans], c=trans_color, label='trans')
    ax.scatter(p3.ext_km.data[polluted], p3.GPS_Altitude[polluted], c=poll_color, label='polluted')

    ax.set_xlabel('Extinction (1/km)')
    ax.set_ylabel('Altitude (m)')
    ax.grid()
    ax.legend()
    ax.set_xscale('log')
