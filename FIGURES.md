# Figure Provenance — Lundstrom et al. 2026

Source code and data behind each figure in *The Practical Application of Atmospheric
Tomography with 3D Radiative Transfer to the Multi-Angle Imaging SpectroRadiometer*
(Lundstrom et al. 2026).

- Repository: `LundstromPub2025`, branch `pub-prep`, traced at commit `a582cad` (2026-10-16).
- Repo root: `/data/keeling/a/johntl3/b/LundstromPub2025`. In-repo paths below are relative to it.
  `/data/keeling/a/johntl3/b` is the same directory as `/data/gdi/b/johntl3`, which is why notebook
  output sometimes shows `/data/gdi/...` paths.
- Synthetic experiments (Figs 8–10) live in `/data/keeling/a/johntl3/b/Synthetic`, which is **not** under
  version control.
- **Cell convention:** `idx` is the 0-based cell position in the notebook JSON; `In[n]` is the saved
  execution count. The "cell N" numbers in `CLAUDE.md` mostly match `In[n]` (hbc2 is the exception: they match
  1-based positions there). The two notations are given side by side below.

## Summary

| Fig | Notebook | Cell | Retrievals / data | Saved image |
|---|---|---|---|---|
| 2 | `notebooks/figures/3Dextinction.ipynb` | idx 4 · In[13] | V11 `default` | `experiments/CAMP2Ex_RF17/V11/figures/3Dextinction/frames/frame00.png` |
| 3 | `notebooks/figures/extinction.ipynb` | idx 11 · In[15] | V11 default, unconstrained, periodic, surf4p0, aod0p150, aod0p250 | not saved |
| 4 | `notebooks/figures/chi2.ipynb` | idx 5 · In[6] | V11 default, unconstrained, periodic, surf4p0, aod0p150, aod0p250 | not saved |
| 5 | `notebooks/figures/ForwardSim_VS_Obs_pub.ipynb` | idx 6 · In[23] | V11 `default` | not saved |
| 6 | `notebooks/figures/ForwardSim_VS_Obs3.ipynb` | idx 6 · In[7] | V11 CTM_unc, unconstrained, CTP_unc | not saved |
| 7 | `notebooks/figures/CAMP2Ex_insitu_reduced.ipynb` | idx 12 · In[13] | V11 retrievals + CAMP2Ex P-3B in situ (FCDP, 2DS10, MetNav) | not saved |
| 8 | `Synthetic/analysis/lundstrom2025_figures.ipynb` | idx 20 · In[11] | Synthetic TradeCumulus LES field | `Synthetic/analysis/lundstrom_et_al_MS_cloud_summaries.png` |
| 9 | `notebooks/HBC/hbc2.ipynb` | idx 5 · In[37] | Synthetic HBC runs, TradeCumulus | not saved |
| 10 | `notebooks/HBC/hbc2.ipynb` | idx 6 · In[44] | Synthetic HBC runs, TradeCumulus | not saved |
| 11 | `notebooks/figures/extinction.ipynb` | idx 13 · In[19] | V11 periodic vs default | not saved |
| B1 | `notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb` | idx 6 · In[11] | 1D SHDOM runs in `output1D/` | not saved |

"Not saved" means no cell writes the image to disk. The figure exists only as the PNG embedded in the
notebook's stored output.

---

## Common loading path for V11 retrievals (Figs 2–7, 11)

All CAMP2Ex notebooks load the retrievals the same way:

```python
es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])
```

Code:
- `src/ExperimentSet.py`: recursively collects every directory under `V11/` that contains an `iterations/`
  subdirectory, skipping paths that match `high_res`. `*_obsolete` directories **are** loaded. The retrieval
  name is the leaf directory name (e.g. `HBC/periodic` → `periodic`).
- `src/Retrieval.py`: for each retrieval it reads `config.yml`, the last file of
  `sorted(iterations/iter*.nc)` (via `at3d.util.load_forward_model`), the `obs_file`, and the
  `cloud_volume_mask_file`.
- `src/utils/util.py`: provides `load_config`, `load_sensor_dict` and `set_labels` (panel letters).
- External: `at3d`.

### V11 retrievals

Inputs (full paths in each `config.yml`):
- Observations: `data/V11/AT3D_OBS_bbox_O105254_P117_R00275_X17950487_18003012_Y0193187_0245712_H1400<suffix>.nc`
- Cloud volume masks (CVM): `data/V11/`
- RTE grid: `data/interim/RTG_default.nc`
- Background scatterers: `data/interim/MIXTURE_default_ERA5*.nc`
- Solver config: `configs/misr_config*.json`

Common to all runs: `a=2.86`, `b=6.14`, `error_cov_sf=1e7`.

| Retrieval (dir under `V11/`) | Final iterate | Obs suffix | CVM | Differs from default | Job list |
|---|---|---|---|---|---|
| `default` | iter032 | `_U1p3_V2p4` | `CVM_LCL_CTH_SC_R7.nc` | — (restart of the original run from its iter030) | V11b |
| `aerosol/aod0p150` | iter036 | `_U1p3_V2p4` | R7 | `MIXTURE_default_ERA5_0p150.nc` | V11a |
| `aerosol/aod0p250` | iter051 | `_U1p3_V2p4` | R7 | `MIXTURE_default_ERA5_0p250.nc` | V11a |
| `HBC/periodic` | iter037 | `_U1p3_V2p4` | R7 | `misr_config_periodic.json` | V11a |
| `surf_wind/surf4p0` | iter028 | `_U1p3_V2p4` | R7 | surface wind 4.0 m/s (restart) | V11b |
| `CVM/unconstrained` | iter040 | `_U1p3_V2p4` | `CVM_unconstrained_mod.nc` | unconstrained CVM | V11f |
| `CVM/SC` | iter023 | `_U1p3_V2p4` | `CVM_LCL_CTH_SC_R3_5_6_7.nc` | CVM | V11g |
| `cloud_motion/{ATM,ATP,CTM,CTP}` | 013 / 019 / 024 / 024 | `_{ATM,ATP,CTM,CTP}` | `CVM_LCL_CTH_SC_R7_{track}.nc` | cloud-motion correction | V11d |
| `cloud_motion/{ATM,ATP,CTM,CTP}_unc` | 046 / 044 / 051 / 026 | `_{track}` | `CVM_unconstrained_mod.nc` | cloud motion + unconstrained CVM | V11f |
| `default_obsolete` | iter030 | `_U1p3_V2p4` | R7 | superseded by `default` | V11a |
| `surf_wind/surf4p0_obsolete` | iter030 | `_U1p3_V2p4` | R7 | superseded by `surf4p0` | V11a |
| `CVM/unconstrained_obsolete` | iter026 | `_U1p3_V2p4` | `CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc` | superseded by `unconstrained` | V11a |
| `cloud_motion/*_unc_obsolete` | 025 / 028 / 028 / 014 | `_{track}` | `CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc` | superseded by `*_unc` | V11e |
| `high_res` | — | — | `CVM_LCL_CTH_SC_R7_high_res.nc` | excluded by `ExperimentSet` | V11c |

---

## Figure 2: 3D extinction field

- **Notebook / cell:** `notebooks/figures/3Dextinction.ipynb`, idx 4 (In[13]).
  - Prerequisites: idx 0 (setup, Kaleido temp dir `tmp/kaleido_tmp`), idx 1 (imports), idx 3 (load).
- **Plot:** Plotly `go.Volume` of `r.solvers_retrieval[0.67].medium['cloud'].extinction`. Settings: isomin 1,
  isomax 40, opacity 0.1, 30 surfaces, Blues colorscale.
- **Data:** `experiments/CAMP2Ex_RF17/V11/default/iterations/iter032.nc`, with its obs and CVM files
  (see the table above).
- **Code:** `src/ExperimentSet.py`, `src/Retrieval.py`. External: `plotly`, `kaleido`.
- **Output:** `experiments/CAMP2Ex_RF17/V11/figures/3Dextinction/frames/frame00.png`, written by
  `fig.write_image`.
  - `notebooks/figures/V11_3Dextinction/` and `V11_3Dextinction.html` are older outputs that the current
    notebook does not produce.

## Figure 3: Extinction vertical profiles and per-level comparison

- **Notebook / cell:** `notebooks/figures/extinction.ipynb`, idx 11 (In[15]).
  - Prerequisites: idx 0–1 (imports), idx 2 (load), idx 4–6 (comparison functions).
  - idx 7 must run first: it fills `stat_dict[...]['dfCompare' | 'dfCompareSlice' | 'dfComapreTarget']` by
    comparing **every pair** of loaded retrievals, using cloud extinction at 0.67 µm.
- **Plot:** 3×2 panel.
  - Quartile profiles of extinction against z, using `exset.to_dataframe(0.67, 'cloud', 'extinction')`.
  - Cloudy-voxel counts per level, compared with the `default` CVM.
  - Per-slice metrics relative to `r2 = 'default'`.
  - Retrievals plotted: `['default', 'unconstrained', 'periodic', 'surf4p0', 'aod0p150', 'aod0p250']`.
- **Data:**
  - Final iterates of those six V11 retrievals.
  - `data/V11/CVM_LCL_CTH_SC_R7.nc`, the `default` CVM.
- **Code:**
  - `notebooks/figures/extinction_compare_metrics.py` (`stat_dict`: metric functions)
  - `notebooks/figures/cmap_dict.py` (`cmap`: retrieval colours)
  - `src/ExperimentSet.py`, `src/Retrieval.py`, `src/utils/util.py`
- **Output:** not saved.

## Figure 4: χ² by MISR camera

- **Notebook / cell:** `notebooks/figures/chi2.ipynb`, idx 5 (In[6]).
  - Prerequisites: idx 2 (load).
  - idx 3 computes χ² with `r.get_chi2_by_camera(misr_S_1, 'MISR', 'I')` and `r.get_chi2(misr_S_1, 'I')`,
    where `S⁻¹ = diag(1/(0.04·y)²)`.
  - idx 4 selects the retrievals.
- **Plot:** χ² for each camera, ordered DF → DA, with the overall χ² shown in the legend.
- **Data:**
  - Retrievals: `default`, `unconstrained`, `periodic`, `surf4p0`, `aod0p150`, `aod0p250`.
  - Observed MISR BRF from each `obs_file`.
  - Simulated BRF from each final iterate.
- **Code:** `src/Retrieval.py` (`get_chi2`, `get_chi2_by_camera`), `src/ExperimentSet.py`,
  `notebooks/figures/cmap_dict.py`.
- **Output:** not saved.

## Figure 5: AT3D forward simulation vs MISR observations

- **Notebook / cell:** `notebooks/figures/ForwardSim_VS_Obs_pub.ipynb`, idx 6 (In[23]).
  - Prerequisites: idx 3 (`plot_F_vs_MISR`), idx 4 (load), idx 5 (`r = default`).
- **Plot:** 3×9 grid, one column per MISR camera. Rows are MISR observed BRF (`r.obs['MISR']`), AT3D
  simulated BRF (`r.sensors_retrieval['MISR']`), and their difference.
- **Data:**
  - `experiments/CAMP2Ex_RF17/V11/default/iterations/iter032.nc`
  - `data/V11/AT3D_OBS_bbox_..._H1400_U1p3_V2p4.nc`
- **Code:** `src/Retrieval.py`, `src/ExperimentSet.py`, `src/utils/util.py`,
  `notebooks/figures/figs_to_html.py`.
- **Output:** not saved.
  - idx 8 writes `experiments/CAMP2Ex_RF17/V11/figures/AT3D_VS_MISR/frames/frame00–08.png` for the
    *other* retrievals, but `default` is not in that list.
  - idx 9 bundles those frames into `.../figures/AT3D_VS_MISR.html`.

## Figure 6: Cloud-motion sensitivity, DF camera

- **Notebook / cell:** `notebooks/figures/ForwardSim_VS_Obs3.ipynb`, idx 6 (In[7]).
  - Prerequisites: idx 1–2 (setup/imports), idx 3 (`get_pixels`, `plot_F_vs_MISR_single_cam`), idx 4 (load),
    idx 5 (plot settings).
- **Plot:** 3×3 grid, DF camera only.
  - Rows: `track='CT'` runs `CTM_unc`, `unconstrained`, `CTP_unc`.
  - Columns: MISR, AT3D, and AT3D − MISR.
  - A `ray_containment` mask contour at level 0.04 is drawn over the panels.
- **Data:**
  - `V11/cloud_motion/CTM_unc/iterations/iter051.nc`, with obs `_H1400_CTM.nc`
  - `V11/CVM/unconstrained/iterations/iter040.nc`, with obs `_U1p3_V2p4.nc`
  - `V11/cloud_motion/CTP_unc/iterations/iter026.nc`, with obs `_H1400_CTP.nc`
  - All three use CVM `data/V11/CVM_unconstrained_mod.nc`.
- **Code:** `src/Retrieval.py` (`obs`, `sensors_retrieval`, `masks`), `src/ExperimentSet.py`,
  `src/utils/util.py`.
- **Output:** not saved. The `figs_to_html(...)` call is commented out.

## Figure 7: Comparison with CAMP2Ex in situ extinction

- **Notebook / cell:** `notebooks/figures/CAMP2Ex_insitu_reduced.ipynb`, idx 12 (In[13]).
  - Prerequisites: idx 0–6 and idx 8.
- **Plot:** 1×3 box plots of extinction by altitude bin for "All samples", "Cloud Shell" and "Cloud Core".
  Sources: `['in situ', 'default', 'surf4p0', 'aod0p150', 'aod0p250', 'periodic', 'unconstrained']`.
- **Retrieval data:**
  - idx 2: the common V11 loading path.
  - idx 3: for each retrieval, `solvers_retrieval[0.67].medium['cloud'].extinction` and
    `experiments/CAMP2Ex_RF17/V11/<retrieval>/min_optical_path.nc`.
  - The shell/core split uses the `default` CVM, `data/V11/CVM_LCL_CTH_SC_R7.nc`.
- **In situ data** (idx 4, via `cx.load_FCDP_2DS(..., breakpoint=40, resample='2s')`):
  - `data/raw/CAMP2Ex_SPEC/CAMP2EX-MetNav_P3B_20191001_R0.ict`
  - `data/raw/CAMP2Ex_SPEC/PaulLawson/CAMP2Ex-FCDP_P3B_20191001_R1.ict`
  - `data/raw/CAMP2Ex_SPEC/PaulLawson/CAMP2Ex-2DS10_P3B_20191001_R0.ict`
- **Sample filter** (idx 6):
  - Time between 2019-10-02 00:00 and 02:00 UTC.
  - `ext_km > 0.3` and `GPS_Altitude < 1250`.
  - Excludes 00:35–00:36 and 01:45–01:46:30.
- **Code:**
  - `src/CAMP2Ex.py` (`load_FCDP_2DS`)
  - `src/Retrieval.py`, `src/ExperimentSet.py`, `src/utils/util.py`
  - `notebooks/figures/cmap_dict.py`
- **Output:** not saved.

## Figure 8: Synthetic cloud field summary

- **Notebook / cell:** `/data/keeling/a/johntl3/b/Synthetic/analysis/lundstrom2025_figures.ipynb`, idx 20 (In[11]).
  - Prerequisites: idx 0 (imports, `savefigs = True`), idx 1 (`set_labels`), idx 18 (`plot_square`),
    idx 19 (load).
- **Plot:** 2×2 grid of cloud-top height, cloud mask, liquid water path and optical depth for the Trade Cumulus
  field. Yellow squares mark the 5 km and 17 km domains centred on (74, 74).
- **Data:** `/data/keeling/a/johntl3/b/Synthetic/IO/thesis/TradeCumulus/len149/ex00_density.nc`, cropped to
  71×71 columns around the centre.
  - idx 19 also loads `.../Transition/len149/ex00_density.nc`, but this figure does not use it.
- **Code:** `/data/keeling/a/johntl3/b/Synthetic/analysis/visualization.py` (imported as `vis`).
  External: `xarray`, `at3d`.
- **Output:** `/data/keeling/a/johntl3/b/Synthetic/analysis/lundstrom_et_al_MS_cloud_summaries.png`
  (300 dpi).

## Figure 9: Synthetic HBC test, retrieval vs control

- **Notebook / cell:** `notebooks/HBC/hbc2.ipynb`, idx 5 (In[37]).
  - Prerequisites: idx 0 (imports), idx 1 (comparison pairs), idx 2 (load), idx 4 (`plot_r1_and_r2`).
- **Plot:** 2×2 grid.
  - Left column: `open` vs `control_open`. Right column: `periodic` vs `control_periodic`.
  - Rows: adjusted relative RMSD (%) and adjusted relative bias (%) against R − T.
  - Filter: T ≥ 4, R ≥ 6.
- **Data** (idx 2): `cloud_field = 'TradeCumulus'`, `lens = [5, 7, 9, 11, 15, 19]`.
  - Periodic runs: `/data/keeling/a/johntl3/b/Synthetic/IO/thesis_periodic_V2/TradeCumulus/len{005..019}/`
  - Open runs: `/data/keeling/a/johntl3/b/Synthetic/IO/thesis/TradeCumulus/len{005..019}/`
  - Each directory provides `ex00_syntheticObs.nc` (truth), `ex00em_optimized.nc` (retrieval) and
    `ex00_optimized.nc` (control).
- **Code:**
  - `notebooks/HBC/HBC.py` (`HBC`, `add_adjusted_stats`)
  - `notebooks/figures/extinction_compare_metrics.py` (`stat_dict`)
  - `src/utils/util.py` (`set_labels`)
- **Output:** not saved.

## Figure 10: Synthetic HBC test, periodic vs open

- **Notebook / cell:** `notebooks/HBC/hbc2.ipynb`, idx 6 (In[44]). The plotting function
  `plot_r1_and_r2_single` is defined in the same cell.
- **Plot:** 1×2 panels of relative bias (%) and relative RMSD (%) against R − T for `periodic` vs `open`.
  Filter: T ≥ 4, R ≥ 6.
- **Data / code:** same as Figure 9.
- **Output:** not saved.
- idx 7 (In[8]) is a loop that draws diagnostic figures for every comparison pair. It is not a manuscript
  figure.

## Figure 11: CAMP2Ex periodic vs open boundary conditions against target size

- **Notebook / cell:** `notebooks/figures/extinction.ipynb`, idx 13 (In[19]).
  - Prerequisites: idx 0–2.
  - idx 6: `compare_extinction_targets`, with `T = np.arange(0, 17.61, 0.55)`.
  - idx 7: fills `stat_dict`.
- **Plot:** 1×2 panels of relative bias (%) and relative RMSD (%) for `periodic` relative to `default`,
  plotted against R − T = 17.6 − T km. Uses `stat_dict[...]['dfComapreTarget']`.
- **Data:**
  - `V11/HBC/periodic/iterations/iter037.nc`
  - `V11/default/iterations/iter032.nc`
  - Both runs' CVM, `data/V11/CVM_LCL_CTH_SC_R7.nc`.
- **Code:** same as Figure 3.
- **Output:** not saved.

## Figure B1: Surface parameterization (angular resolution vs wind speed)

- **Notebook / cell:** `notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb`, idx 6 (In[11]).
  - Prerequisites: idx 2 (paths), idx 4 (read output), idx 5 (grouping).
- **Plot:** 3×3 grid, one panel per MISR camera. BRF (`I·π/μ0`) against `n_mu` on a log₂ axis, for n_mu ≥ 16.
  Solid line: 0.67 m/s wind. Dashed line: 4.0 m/s.
- **Data:** `notebooks/surface_parameterization_testing/output1D/wind{0p67,4p0}_mu{8,16,32,64,128}_phi{16..256}.nc`
  (10 files). Wind speed, n_mu and n_phi are parsed from the file names.
- **How the data were generated:** idx 3, now commented out, ran 1D SHDOM forward simulations from these yml
  configs:
  - `configs_expr02_fast/`: the wind 4.0 runs.
  - `configs_expr02_slow/`: the wind 0.67 runs.
  - They use `data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc`, `MIXTURE_default_ERA5.nc` and
    `configs_SHDOM_1D/mu*phi*.json`.
- **Code:** `src/utils/util.py` (`load_sensor_dict`, `save_sensor_dict`), `src/main/run_at3d.py` (`load_config`).
- **Output:** not saved.

---

## Upstream provenance of the V11 retrievals

1. **Raw data** (`data/raw/`):
   - MISR L1B2 ellipsoid radiances: `MISR/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{cam}_F03_0024.hdf`.
   - Other MISR products: `GP_GMP` geometry, `TC_CLOUD`, `AS_AEROSOL`, `ACP_MIXTURE`.
   - Other campaign and reanalysis data: `era5/`, `CAMP2Ex_Dropsonde/`, `CAMP2Ex_RSP/`, `CAMP2Ex_SPEC/`.
   - The MISR files are read by `src/MISR.py`.
2. **Preprocessing** (`notebooks/preprocessing/`):
   - `MISR2AT3D_OBS.ipynb` turns `data/interim/MISR_RAD_*` and `MISR_GEO_*` into
     `AT3D_OBS_bbox_*_H1400_*.nc`. The notebook now writes to `data/V12/`; the V11 obs files in `data/V11/`
     came from an earlier run of it.
   - `CVM_LCL_CTH_SC*.ipynb` produce the `CVM_LCL_CTH_SC_R*.nc` masks.
   - `data/V11/gen_CVM_unc_mod.ipynb` produces `CVM_unconstrained_mod.nc`.
   - `Make_RTE_grid.ipynb` produces the RTE grid (`RTG_*`).
   - `ERA5_atmosphere.ipynb`, `MISR_aerosol.ipynb` and `mix_background.ipynb` produce the background
     scatterers (`MIXTURE_*`).
3. **Job lists:** `automation/job_lists/CAMP2Ex_RF17_V11{a..g}.csv`. Each row is one run.
   - Columns: `out_path, restart_iter, obs_file, rte_grid_file, background_scatterers_file,
     cloud_volume_mask_file, config_file_name, surface_wind_speed, a, b, error_cov_sf`.
   - V11a: default, aod0p150, aod0p250, unconstrained, periodic, surf4p0.
   - V11b: restarts of default and surf4p0 from iter030.
   - V11c: high_res.
   - V11d: cloud motion ATM/ATP/CTM/CTP.
   - V11e: the four `*_unc` runs with CVM R0–7.
   - V11f: the four `*_unc` runs and `unconstrained`, with `CVM_unconstrained_mod.nc`.
   - V11g: `CVM/SC`.
4. **Submission:** `automation/csv2yml.ipynb` reads one CSV; the file name is hard-coded, so it was edited for
   each letter. For each row it:
   - writes `<out_path>/config.yml` and `<out_path>/run_at3d.sh`;
   - submits the job with `sbatch`, using conda env `at3d_pure_k9`, 4 tasks and 64 GB;
   - commits the repository.
5. **Retrieval:** `src/main/run_at3d.py <out_path>/config.yml` runs L-BFGS for at most 100 iterations. It
   writes `iterations/iter###.nc`, `loss.csv` and `at3d.log`.
6. **Post-hoc renaming:** superseded runs were renamed to `*_obsolete` by hand. Their `config.yml` still shows
   the original `out_path`. The current `default` and `surf4p0` directories hold the V11b restart runs;
   their configs show `out_path: .../*_restart/`.

## Known issues / caveats

- **Figures with no saved image:** 3, 4, 5, 6, 7, 9, 10, 11 and B1 exist only as embedded notebook output.
  Adding `savefig` calls would make them reproducible as files.
- **`CLAUDE.md` cell numbers:** they mostly correspond to execution counts `In[n]`, not cell positions. For
  example, Figure 11's "cell 19" is idx 13 (In[19]), while idx 19 is an unexecuted histogram cell.
- **Obsolete runs in the pairwise statistics:** the `*_obsolete` retrievals are loaded and included in the
  all-pairs statistics in `extinction.ipynb` idx 7. The figures only plot non-obsolete names, but names are
  matched by leaf directory, so obsolete names must not collide with current ones.
- **Stale CSV restart path:** V11b's `restart_iter` for `surf4p0` points at
  `surf_wind/surf4p0/iterations/iter030.nc`. After the renaming, that file is in
  `surf_wind/surf4p0_obsolete/iterations/`.
- **`min_optical_path.nc` (Fig 7):** this file exists in every retrieval directory, but no notebook traced here
  generates it.
