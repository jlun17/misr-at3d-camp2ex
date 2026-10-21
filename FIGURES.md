# Figure Provenance — Lundstrom et al. 2026

Source code and data behind each figure in *The Practical Application of Atmospheric
Tomography with 3D Radiative Transfer to the Multi-Angle Imaging SpectroRadiometer*
(Lundstrom et al. 2026).

- Repository: `LundstromPub2025`, branch `pub-prep`, traced at commit `a582cad` (2026-10-16).
- Repo root: `/data/keeling/a/johntl3/b/LundstromPub2025`. In-repo paths below are relative to it.
  `/data/keeling/a/johntl3/b` is the same directory as `/data/gdi/b/johntl3`, which is why notebook
  output sometimes shows `/data/gdi/...` paths.
- Synthetic experiments (Figs 8–10) were run in `/data/keeling/a/johntl3/b/Synthetic`, which is **not** under
  version control. The files the figures read are copied to `data/synthetic/`, and the producer scripts to
  `scripts/pipeline/synthetic/`.
- `PIPELINE.md` describes how every input file is rebuilt (`scripts/pipeline/run_pipeline.sh`). Unused code and
  data are in `archive/`, which mirrors the original paths.
- **Cell convention:** `idx` is the 0-based cell position in the notebook JSON; `In[n]` is the saved
  execution count. The "cell N" numbers in `CLAUDE.md` mostly match `In[n]` (hbc2 is the exception: they match
  1-based positions there). The two notations are given side by side below.

## Summary

| Fig | Script (`scripts/figures/`) | Image (`figures/manuscript/`) | Source notebook | Cell | Retrievals / data |
|---|---|---|---|---|---|
| 2 | `fig02_volume.py` | `fig02_volume.png` | `notebooks/figures/3Dextinction.ipynb` | idx 4 · In[13] | V11 `default` |
| 3 | `fig03_profiles.py` | `fig03_profiles.png` | `notebooks/figures/extinction.ipynb` | idx 11 · In[15] | V11 default, unconstrained, periodic, surf4p0, aod0p150, aod0p250 |
| 4 | `fig04_chi2.py` | `fig04_chi2.png` | `notebooks/figures/chi2.ipynb` | idx 5 · In[6] | V11 default, unconstrained, periodic, surf4p0, aod0p150, aod0p250 |
| 5 | `fig05_brf.py` | `fig05_brf.png` | `notebooks/figures/ForwardSim_VS_Obs_pub.ipynb` | idx 6 · In[23] | V11 `default` |
| 6 | `fig06_cloudmotion.py` | `fig06_cloudmotion.png` | `notebooks/figures/ForwardSim_VS_Obs3.ipynb` | idx 6 · In[7] | V11 CTM_unc, unconstrained, CTP_unc |
| 7 | `fig07_insitu.py` | `fig07_insitu.png` | `notebooks/figures/CAMP2Ex_insitu_reduced.ipynb` | idx 12 · In[13] | V11 retrievals + CAMP2Ex P-3B in situ (FCDP, 2DS10, MetNav) |
| 8 | `fig08_clouds.py` | `fig08_clouds.png` | `Synthetic/analysis/lundstrom2025_figures.ipynb` | idx 20 · In[11] | Synthetic TradeCumulus stochastic cloud field (`data/synthetic/`) |
| 9 | `fig09_hbc.py` | `fig09_hbc.png` | `notebooks/HBC/hbc2.ipynb` | idx 5 · In[37] | Synthetic HBC runs, TradeCumulus (`data/synthetic/`) |
| 10 | `fig10_periodic.py` | `fig10_periodic.png` | `notebooks/HBC/hbc2.ipynb` | idx 6 · In[44] | Synthetic HBC runs, TradeCumulus (`data/synthetic/`) |
| 11 | `fig11_target.py` | `fig11_target.png` | `notebooks/figures/extinction.ipynb` | idx 13 · In[19] | V11 periodic vs default |
| B1 | `figB1_surface.py` | `figB1_surface.png` | `notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb` | idx 6 · In[11] | 1D SHDOM runs in `output1D/` |
| S1, S3, …, S17 (odd) | `figS_volume.py` | `S01_volume_unconstrained.png` … `S17_volume_CTP_unc.png` | `notebooks/figures/3DextinctionSI.ipynb` | idx 4 · In[11] | 9 V11 sensitivity runs (see SI section) |
| S2, S4, …, S18 (even) | `figS_brf.py` | `S02_brf_unconstrained.png` … `S18_brf_CTP_unc.png` | `notebooks/figures/ForwardSim_VS_Obs_pub.ipynb` | idx 8 · In[30] | same 9 V11 runs |

The per-figure sections below describe the source notebooks. The scripts are copies of those notebook cells.
Where a notebook never saved a figure (3, 4, 5, 6, 7, 9, 10, 11, B1), "Output: not saved" refers to the notebook;
the script saves it.

## Regenerating the figures

Each figure has a script in `scripts/figures/`. The script is copied from its notebook cells with no logic
changes: unused imports, helper functions, commented-out code and display-only cells are dropped, and a save
line is added. Scripts that already saved in the notebook keep their own save call, with only the output path
changed to `figures/manuscript/`.

```bash
sbatch scripts/figures/run_figures.sh                              # all figures
sbatch scripts/figures/run_figures.sh fig04_chi2.py fig09_hbc.py   # selected figures
```

`run_figures.sh` does the following:
- runs the scripts from `scripts/figures/`, so the notebooks' `PROJECT_ROOT = Path().resolve().parent.parent`
  still resolves to the repo root;
- puts `notebooks/figures/` and `notebooks/HBC/` on `PYTHONPATH`, so `cmap_dict`, `extinction_compare_metrics`
  and `HBC` import unchanged;
- activates each figure's original conda env: `vis2_clone` for figs 3, 7, 11 and B1, `vis2` for the rest.

Run time and inputs:
- Most CAMP2Ex scripts load all 22 V11 retrievals.
- `fig03_profiles.py` and `fig11_target.py` also run the full all-pairs comparison from `extinction.ipynb`
  cell 7. That cell is kept whole because `Retrieval.get_extinction` modifies the extinction fields in place, so
  dropping any of its comparisons could change the results.
- `fig07_insitu.py` needs the `min_optical_path.nc` files produced by `calc_VC.sh` (pipeline stage `vc`).

---

## Common loading path for V11 retrievals (Figs 2–7, 11, S1–S18)

All CAMP2Ex notebooks load the retrievals the same way:

```python
es_dir = PROJECT_ROOT / 'experiments' / 'CAMP2Ex_RF17' / 'V11'
exset = ExperimentSet(es_dir)
exset.set_retrieval_list()
exset.load_retrievals(iteration=-1, extinction_th=[0.3, np.inf])
```

Code:
- `src/ExperimentSet.py`: recursively collects every directory under `V11/` that contains an `iterations/`
  subdirectory, skipping paths that match `high_res`. `*_obsolete` directories **are** loaded; after archiving,
  only `default_obsolete` and `surf_wind/surf4p0_obsolete` remain (the restart sources of `default` and `surf4p0`). The retrieval
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
| `CVM/SC` (archived) | iter023 | `_U1p3_V2p4` | `CVM_LCL_CTH_SC_R3_5_6_7.nc` | CVM | V11g |
| `cloud_motion/{ATM,ATP,CTM,CTP}` (archived) | 013 / 019 / 024 / 024 | `_{ATM,ATP,CTM,CTP}` | `CVM_LCL_CTH_SC_R7_{track}.nc` | cloud-motion correction | V11d |
| `cloud_motion/{ATM,ATP,CTM,CTP}_unc` | 046 / 044 / 051 / 026 | `_{track}` | `CVM_unconstrained_mod.nc` | cloud motion + unconstrained CVM | V11f |
| `default_obsolete` | iter030 | `_U1p3_V2p4` | R7 | superseded by `default` | V11a |
| `surf_wind/surf4p0_obsolete` | iter030 | `_U1p3_V2p4` | R7 | superseded by `surf4p0` | V11a |
| `CVM/unconstrained_obsolete` (archived) | iter026 | `_U1p3_V2p4` | `CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc` | superseded by `unconstrained` | V11a |
| `cloud_motion/*_unc_obsolete` (archived) | 025 / 028 / 028 / 014 | `_{track}` | `CVM_LCL_CTH_SC_R0_1_2_3_4_5_6_7.nc` | superseded by `*_unc` | V11e |
| `high_res` (archived) | — | — | `CVM_LCL_CTH_SC_R7_high_res.nc` | excluded by `ExperimentSet` | V11c |

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
- **Output:** not saved. idx 8 in the same notebook saves the equivalent panels for the nine sensitivity runs
  (the even-numbered Figures S2–S18), but `default` is not among them.

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
  - idx 3: for each retrieval, `solvers_retrieval[0.67].medium['cloud'].extinction`, joined with
    `experiments/CAMP2Ex_RF17/V11/<retrieval>/min_optical_path.nc` (produced by `calc_VC.sh`; see
    "Veiled-core optical paths" below).
  - The default CVM, `data/V11/CVM_LCL_CTH_SC_R7.nc`, provides `distance_to_cloud`.
  - Shell/core split: a voxel counts as "Cloud Core" when `isVeiled = min_optical_path >= 5`; otherwise it is
    "Cloud Shell".
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
  - Upstream: `calc_VC.sh` and `src/veiledCore.py` (produce `min_optical_path.nc`)
- **Output:** not saved.

## Figure 8: Synthetic cloud field summary

- **Notebook / cell:** `/data/keeling/a/johntl3/b/Synthetic/analysis/lundstrom2025_figures.ipynb`, idx 20 (In[11]).
  The script reads the field from `data/synthetic/`.
  - Prerequisites: idx 0 (imports, `savefigs = True`), idx 1 (`set_labels`), idx 18 (`plot_square`),
    idx 19 (load).
- **Plot:** 2×2 grid of cloud-top height, cloud mask, liquid water path and optical depth for the Trade Cumulus
  field. Yellow squares mark the 5 km and 17 km domains centred on (74, 74).
- **Data:** `data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc` (a copy of
  `Synthetic/IO/thesis/TradeCumulus/len149/ex00_density.nc`, itself identical to
  `Synthetic/cloud_gen/cloud_fields/TradeCu/density/field07.nc`), cropped to
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
  - Periodic runs: `data/synthetic/thesis_periodic_V2/TradeCumulus/len{005..019}/` (copied from
    `Synthetic/IO/thesis_periodic_V2/`)
  - Open runs: `data/synthetic/thesis/TradeCumulus/len{005..019}/` (copied from `Synthetic/IO/thesis/`)
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
  configs (pipeline stage `b1`, `scripts/pipeline/surface1D/figB1_shdom1d.py`):
  - `configs_expr02_fast/`: the wind 4.0 runs.
  - `configs_expr02_slow/`: the wind 0.67 runs.
  - They use `data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc`, `MIXTURE_default_ERA5.nc` and
    `configs_SHDOM_1D/mu*phi*.json`.
- **Code:** `src/utils/util.py` (`load_sensor_dict`, `save_sensor_dict`), `src/main/run_at3d.py` (`load_config`).
- **Output:** not saved.

---

## Supporting Information: Figures S1–S18

The SI figures come in pairs, one pair per sensitivity run. Within each pair, the odd-numbered figure is the 3D
extinction field and the even-numbered figure is the forward simulation vs MISR. Both notebooks loop over
`['unconstrained', 'surf4p0', 'aod0p150', 'aod0p250', 'periodic', 'ATM_unc', 'ATP_unc', 'CTM_unc', 'CTP_unc']`
and write `frame{i:02d}.png`. So `frameNN` from the 3D extinction notebook is S(2·NN + 1), and `frameNN` from the
forward-sim notebook is S(2·NN + 2).

| 3D extinction | Forward sim vs MISR | Retrieval | Dir under `V11/` | Final iterate | Plot title |
|---|---|---|---|---|---|
| S1 (`frame00`) | S2 (`frame00`) | `unconstrained` | `CVM/unconstrained` | iter040 | unconstrained |
| S3 (`frame01`) | S4 (`frame01`) | `surf4p0` | `surf_wind/surf4p0` | iter028 | surf4p0 |
| S5 (`frame02`) | S6 (`frame02`) | `aod0p150` | `aerosol/aod0p150` | iter036 | aod0p150 |
| S7 (`frame03`) | S8 (`frame03`) | `aod0p250` | `aerosol/aod0p250` | iter051 | aod0p250 |
| S9 (`frame04`) | S10 (`frame04`) | `periodic` | `HBC/periodic` | iter037 | periodic |
| S11 (`frame05`) | S12 (`frame05`) | `ATM_unc` | `cloud_motion/ATM_unc` | iter046 (not converged; the pipeline restarts it, see `PIPELINE.md`) | AT− |
| S13 (`frame06`) | S14 (`frame06`) | `ATP_unc` | `cloud_motion/ATP_unc` | iter044 | AT+ |
| S15 (`frame07`) | S16 (`frame07`) | `CTM_unc` | `cloud_motion/CTM_unc` | iter051 | CT− |
| S17 (`frame08`) | S18 (`frame08`) | `CTP_unc` | `cloud_motion/CTP_unc` | iter026 | CT+ |

The obs file, CVM and other inputs for each run are listed in the V11 retrieval table above.

### Figures S1, S3, …, S17: 3D extinction fields of the sensitivity runs

- **Notebook / cell:** `notebooks/figures/3DextinctionSI.ipynb`, idx 4 (In[11]).
  - Prerequisites: idx 0 (setup, Kaleido temp dir `tmp/kaleido_tmp`), idx 1 (imports), idx 3 (load, In[4]).
- **Plot:** the same Plotly `go.Volume` rendering as Figure 2, applied to each run's
  `solvers_retrieval[0.67].medium['cloud'].extinction`.
  - Settings: isomin 1, isomax 40, opacity 0.1, 30 surfaces, Blues colorscale, 750×650 px, fixed camera.
  - The cloud-motion runs are titled AT−/AT+/CT−/CT+.
- **Data:** final iterates of the nine runs listed in the table above.
- **Code:** `src/ExperimentSet.py`, `src/Retrieval.py`. External: `plotly`, `kaleido`.
- **Output:** `experiments/CAMP2Ex_RF17/V11/figures/3DextinctionSI/frames/frame00.png` to `frame08.png`, written
  by `fig.write_image`. idx 5 bundles them into `.../3DextinctionSI/3Dextinction.html` using
  `notebooks/figures/figs_to_html.py`.

### Figures S2, S4, …, S18: AT3D forward simulation vs MISR for the sensitivity runs

- **Notebook / cell:** `notebooks/figures/ForwardSim_VS_Obs_pub.ipynb`, idx 8 (In[30]).
  - Prerequisites: idx 1–2 (imports), idx 3 (`plot_F_vs_MISR` and plot settings), idx 4 (load), idx 7
    (`savekwargs`: png, 300 dpi, tight bounding box).
- **Plot:** the same 3×9 layout as Figure 5: MISR observed BRF, AT3D simulated BRF and AT3D − MISR for each
  camera, with the 17.6 km domain border drawn in red. The suptitle names the run.
- **Data:** for each run, the final iterate (simulated BRF) and its `obs_file` (MISR BRF).
  - The `_unc` runs use the matching `_H1400_{ATM,ATP,CTM,CTP}.nc` obs file.
  - All other runs use `_U1p3_V2p4.nc`.
- **Code:** `src/Retrieval.py`, `src/ExperimentSet.py`, `src/utils/util.py`, `notebooks/figures/figs_to_html.py`.
- **Output:** `experiments/CAMP2Ex_RF17/V11/figures/AT3D_VS_MISR/frames/frame00.png` to `frame08.png`, written by
  `plt.savefig`. idx 9 bundles them into `.../figures/AT3D_VS_MISR/AT3D_VS_MISR.html`.

---

## Upstream provenance of the V11 retrievals

`PIPELINE.md` gives the producer of every input file, with the git commit it ran at, and the pipeline that
rebuilds them. The notes below describe how the original runs were made.

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
   - `data/V11/gen_CVM_unc_mod.ipynb` produces `CVM_unconstrained_mod.nc` (now in
     `scripts/pipeline/camp2ex/`; the original is archived).
   - `RTG_default.nc` came from `MISR_preprocess2.ipynb` (deleted in `8277215`). `Make_RTE_grid.ipynb`
     (archived) produced only `RTG_high_res.nc`.
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

### Veiled-core optical paths (`min_optical_path.nc`, used by Fig 7)

- **Job:** `calc_VC.sh`, a Slurm script (12 tasks, 64 GB, conda env `vis2_clone`) that runs
  `python src/veiledCore.py experiments/CAMP2Ex_RF17/V11/`.
- **Inputs:** `src/veiledCore.py` loads the whole V11 set through the common loading path (`ExperimentSet`,
  `iteration=-1`, `extinction_th=[0.3, inf]`), so `*_obsolete` runs are included. For each retrieval it uses
  the final iterate's cloud extinction at 0.67 µm.
- **Computation:** for every voxel with extinction > 0, it marches horizontally in 8 azimuths (0°–315°).
  - The march stays at the voxel's own z.
  - The step is half the horizontal grid spacing.
  - Extinction is trilinearly interpolated (`RegularGridInterpolator`; outside the grid it is 0).
  - The march accumulates extinction × step and stops when extinction drops below 0.3 km⁻¹.
  - The voxel's value is the **minimum** optical path over the 8 directions. The work runs in parallel with
    `multiprocessing.Pool`.
- **Output:** `experiments/CAMP2Ex_RF17/V11/<retrieval>/min_optical_path.nc`. It holds the cloud medium dataset
  plus a new `min_optical_path` variable (x, y, z).

## Known issues / caveats

- **Notebook outputs vs script outputs:**
  - In the notebooks, figures 3, 4, 5, 6, 7, 9, 10, 11 and B1 exist only as embedded output.
  - The notebooks save the SI figures as generic `frameNN.png` files under `experiments/CAMP2Ex_RF17/V11/figures/`.
  - The scripts in `scripts/figures/` save every figure to `figures/manuscript/` with descriptive names.
- **`CLAUDE.md` cell numbers:** they mostly correspond to execution counts `In[n]`, not cell positions. For
  example, Figure 11's "cell 19" is idx 13 (In[19]), while idx 19 is an unexecuted histogram cell.
- **Obsolete runs in the pairwise statistics:** the `*_obsolete` retrievals are loaded and included in the
  all-pairs statistics in `extinction.ipynb` idx 7. The figures only plot non-obsolete names, but names are
  matched by leaf directory, so obsolete names must not collide with current ones.
- **Stale CSV restart path:** V11b's `restart_iter` for `surf4p0` points at
  `surf_wind/surf4p0/iterations/iter030.nc`. After the renaming, that file is in
  `surf_wind/surf4p0_obsolete/iterations/`.
