# Data pipeline — Lundstrom et al. 2026

`scripts/pipeline/` rebuilds every file the manuscript figures read, starting from raw MISR, ERA5 and
CAMP2Ex data, and then regenerates the figures. It covers:
- the observation files, cloud volume masks (CVMs), RTE grid and background scatterers;
- the 12 V11 retrievals the figures use;
- `min_optical_path.nc` (Fig 7);
- the synthetic HBC experiments (Figs 8–10);
- the 1D surface simulations (Fig B1).

Each pipeline script is the notebook code **at the git commit that produced the file the figures use**.
Only input and output paths change, plus the parameters that one notebook used to produce several files,
which become command-line arguments. Every script header names its source notebook, commit, cells, conda
env and any changes. The few parameters that no commit records are marked **[FLAGGED]**. Each one was
recovered from the existing data files, and the rebuilt files match the originals (see Verification).

## Running it

```bash
# On the login node; the script only writes retrieval configs and submits Slurm jobs.
scripts/pipeline/run_pipeline.sh --out-root /path/to/build                 # everything
scripts/pipeline/run_pipeline.sh --out-root /path/to/build --stages pre,b1 # selected stages
scripts/pipeline/run_pipeline.sh --out-root /path/to/build --dry-run       # print sbatch commands only
```

- `--out-root` is where `data/`, `mie_tables/`, `experiments/` and `output1D/` are written. If it is
  not the repo root, the pipeline inputs (below) are symlinked in from the repo.
- `--out-root` defaults to the repo root. That is meant for a fresh checkout that contains only the
  pipeline inputs; the driver refuses to run `pre` when `data/V11/` is already populated.
- The `figures` stage runs `scripts/figures/run_figures.sh`, which reads from the repo root, so it is
  submitted only when `--out-root` is the repo root.
- Stages: `pre`, `retrievals`, `vc`, `synthetic`, `b1`, `figures`. A stage run without its upstream
  stage assumes the upstream outputs already exist under `--out-root`.
- Job logs go to `<out-root>/logs/pipeline/`. Retrieval logs (`at3d.log`, `slurm-*.out`) go to each
  retrieval directory, as before.

Approximate wall time on Keeling `node`:
- `pre`: under 30 min.
- Each retrieval: 1.5–19 h. `default` and `surf4p0` are two runs in sequence.
- `vc`: about 1 h.
- `synthetic`: the 149 km SHDOM run plus 24 small retrievals.
- `b1`: about 1 h.

## Pipeline inputs

These are the only files no script produces. Everything else is rebuilt.

| File | Used by |
|---|---|
| `data/raw/MISR/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{DF,CF,BF,AF,AN,AA,BA,CA,DA}_F03_0024.hdf` | s02, s02b |
| `data/raw/MISR/MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf` | s02, s02b |
| `data/raw/MISR/MISR_AM1_TC_CLOUD_P117_O105254_F01_0001.hdf` | s02 |
| `data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.hdf` | s01 |
| `data/raw/era5/ERA5_upper_CAMP2Ex_RF17_wide.nc`, `ERA5_surface_CAMP2Ex_RF17_wide_extra.nc` | s04 |
| `data/raw/CAMP2Ex_SPEC/CAMP2EX-MetNav_P3B_20191001_R0.ict`, `PaulLawson/CAMP2Ex-{FCDP_P3B_20191001_R1,2DS10_P3B_20191001_R0}.ict` | Fig 7 (read directly) |
| `data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc` | synthetic (and Fig 8 directly) |
| `data/synthetic/ancillary/AFGL_summer_mid_lat.nc` | synthetic |

`len149/ex00_density.nc` is a stochastic cloud field. It is byte-identical to
`Synthetic/cloud_gen/cloud_fields/TradeCu/density/field07.nc`, the 8th draw of an interactive session.
`synthetic/s00_generate_cloud.py` reproduces that code, but a new run draws a different field, so the
original is a pipeline input. The driver does not run `s00_generate_cloud.py`.

No script downloads the raw data. The files are the MISR L1B2 ellipsoid (GRP_ELLIPSOID_GM, F03_0024),
geometric parameters (GP_GMP), TC_CLOUD and ACP mixture products for path 117, orbit 105254 (2019-10-02);
ERA5 pressure-level and single-level data; and the CAMP2Ex P-3B RF17 merges.

## Stages

`C = scripts/pipeline/camp2ex`, `S = scripts/pipeline/synthetic`. Paths are relative to `--out-root`.

### `pre`: CAMP2Ex retrieval inputs

| Script | Source (commit) | Env | Output |
|---|---|---|---|
| `C/s00_mie_table.py` | `src/main/run_at3d.py` get_mono_table call | at3d_pure_k9 | `mie_tables/red_mie_table.nc` |
| `C/s01_acp_mixture.py` | `tmp/src_old/MISR_ACP_preprocess.ipynb` (= `b3cf83e^:src_old/…`) | pyhdf | `data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc` |
| `C/s02_misr_preprocess.py` | `MISR_preprocessA.ipynb` (HEAD) | misr | `data/interim/MISR_{RAD,GEO,CTH,CMV}_O105254_*.nc` |
| `C/s02b_misr_obs_default.py` | `MISR_preprocess1.ipynb` (`8277215^`) | misr | `data/interim/MISR_OBS_CAMP2Ex_RF17_default.nc` |
| `C/s03_rte_grid.py` | `MISR_preprocess2.ipynb` (`8277215^`), s=1.5 **[FLAGGED]** | at3d_k9 | `data/interim/RTG_default.nc`, `AT3D_OBS_CAMP2Ex_RF17_default.nc` (Fig B1) |
| `C/s04_era5_atmosphere.py` | `ERA5_atmosphere.ipynb` (HEAD) | at3d_pure_k9 | `data/interim/ATMOS_ERA5_CAMP2Ex_RF17_default.nc` |
| `C/s05_misr_aerosol.py <aod>` | `MISR_aerosol.ipynb` (HEAD), leg_ord=20 **[FLAGGED]** | at3d_pure_k9 | `data/interim/AEROSOL_MISR_21_0p{150,200,250}.nc` |
| `C/s06_mix_background.py` | `mix_background.ipynb` (HEAD), ERA5 file names **[FLAGGED]** | at3d_pure_k9 | `data/interim/MIXTURE_default_ERA5{,_0p150,_0p250}.nc` |
| `C/s07_obs.py <u> <v> [suffix]` | `MISR2AT3D_OBS.ipynb` (`a29d0eb`; tracks `993661c`) | at3d_pure_k9 | `data/V11/AT3D_OBS_bbox_…_H1400_{U1p3_V2p4,ATM,ATP,CTM,CTP}.nc` |
| `C/s08_cvm.py <regions>` | `CVM_LCL_CTH_SC.ipynb` (`a29d0eb`) | at3d_pure_k9 | `data/V11/CVM_LCL_CTH_SC_R7.nc`, `…_R0_1_2_3_4_5_6_7.nc` |
| `C/s09_cvm_unc_mod.py` | `data/V11/gen_CVM_unc_mod.ipynb` (untracked; copied to `C/`) | at3d_pure_k9 | `data/V11/CVM_unconstrained_mod.nc` |

The observation winds:
- **Default** (u, v) = (1.3, 2.4) m/s. This value is typed into the `a29d0eb` notebook; no derivation
  of it is recorded.
- **Cloud-motion tracks:** ATM (1.9, 5.1), ATP (0.7, −0.3), CTM (−0.3, 2.7), CTP (2.9, 2.1). These are
  the saved output of `notebooks/investigation/pre_retrieval/MISR_CloudMotionVectors.ipynb`. That
  notebook rotates (1.3, 2.4) using the instrument heading from a TC_CLOUD v2026 file that is not in
  `data/raw`, so the values are passed to `s07_obs.py` directly.
- The `[suffix]` argument writes the track files under their final names. The original files were
  renamed by hand from the `U…_V…` names the notebook writes.

### `retrievals`: the 12 V11 retrievals

`C/s10_make_configs.py` is the config writer from `automation/csv2yml.ipynb`, with sbatch and the git
commit removed. It reads `C/job_list_V11.csv` and writes `config.yml` and `run_at3d.sh` into each
`experiments/CAMP2Ex_RF17/V11/<run>/`. The driver then submits each `run_at3d.sh`, which runs
`src/main/run_at3d.py` (unchanged) in `at3d_pure_k9`.

| Run | Original job list | Notes |
|---|---|---|
| `default_obsolete` | V11a (`default/`) | stage 1 of `default` |
| `default` | V11b (`default_restart/`) | restarts from the last iterate of `default_obsolete` (originally iter030) |
| `aerosol/aod0p150`, `aerosol/aod0p250` | V11a | |
| `HBC/periodic` | V11a | `misr_config_periodic.json` |
| `surf_wind/surf4p0_obsolete` | V11a (`surf_wind/surf4p0/`) | stage 1 of `surf4p0` |
| `surf_wind/surf4p0` | V11b (`surf_wind/surf4p0_restart/`) | restarts from the last iterate of `surf4p0_obsolete` (originally iter030) |
| `CVM/unconstrained` | V11f | |
| `cloud_motion/{ATM,ATP,CTM,CTP}_unc` | V11f | |

The original V11 job lists are kept in `automation/job_lists/CAMP2Ex_RF17_V11{a..g}.csv`. Their paths
predate the renames `default` → `default_obsolete`, `default_restart` → `default`, and likewise for
`surf4p0`. That is why the `restart_iter` in the existing `default/config.yml` no longer points at the
file the run actually restarted from. `job_list_V11.csv` uses the final names, and resolves the restart
file when the job starts.

### `vc`: `min_optical_path.nc` (Fig 7)

`src/veiledCore.py` runs over every retrieval in `experiments/CAMP2Ex_RF17/V11/`, as `calc_VC.sh` does
(env `vis2_clone`, 12 tasks). It runs after all 12 retrievals finish.

### `synthetic`: HBC experiments (Figs 9, 10)

These are copied from `/data/keeling/a/johntl3/b/Synthetic`, which is not under version control. Paths
now point to `data/synthetic/`, and only the TradeCumulus field is run. Domain sizes are len005, 007,
009, 011, 015 and 019.

| Step | Script | Original |
|---|---|---|
| Mie table | `S/s00_mie_table.py` | computed by each run from `relative_dir='../mie_tables'` |
| Domain subsets | `S/s01_subset.py` | `Synthetic/IO/thesis/subset_stochastic.ipynb` |
| Configs | `S/ex00_ymlWriter.py`, `S/ex00em_ymlWriter.py`; the periodic directory gets copies | `Synthetic/IO/thesis/*_ymlWriter.py` |
| Synthetic obs, open | `S/gen_synthetic_obs_stochastic.py` (also len149) | `Synthetic/scripts/` |
| Emulated obs | `S/emulate_obs_stochastic.py` (from len149) | `Synthetic/scripts/` |
| Retrievals, open | `S/botany_at3d.py` (`ex00`, `ex00em`) | `Synthetic/scripts/` |
| Synthetic obs, periodic | `S/gen_synthetic_obs_stochastic_periodic.py` | `Synthetic/scripts/` |
| Retrievals, periodic | `S/botany_at3d_V2.py` (`ex00`, `ex00em`; `ex00em` uses the open emulated obs) | `Synthetic/scripts/` |

The job layout follows `Synthetic/IO/thesis/batch_writer.ipynb` (open) and
`Synthetic/IO/thesis_periodic_V2/batch_writer.ipynb` (periodic); both are copied to `S/`.

### `b1`: 1D surface simulations (Fig B1)

`scripts/pipeline/surface1D/figB1_shdom1d.py` is the commented-out cell idx 3 of
`notebooks/surface_parameterization_testing/sufrace_parameterization.ipynb`. It is looped over
`configs_expr02_slow` and `configs_expr02_fast`, runs in `vis2_clone`, and writes
`notebooks/surface_parameterization_testing/output1D/`.

## Deviations from the original runs

**[FLAGGED] parameters.** No committed notebook state records these; each was recovered from the
files themselves.
- `s03`: `s = 1.5` m/s. The committed notebook has 0.67. `AT3D_OBS_CAMP2Ex_RF17_default.nc` (2025-07-16)
  has u=0.856 and v=1.232, which is 1.5 m/s at 34.8°, the value at `cd4a47d`. This affects only the
  Fig B1 obs file; `RTG_default.nc` does not depend on it.
- `s05`: `leg_ord = 20`. The notebook has 166. The V11 aerosol files have 21 Legendre terms.
- `s06`: input `ATMOS_ERA5_CAMP2Ex_RF17_default.nc` and output `MIXTURE_default_ERA5*.nc`. The committed
  notebook uses the dropsonde atmosphere and `MIXTURE_default.nc`.

**Conda environments that changed since the original runs.**
- `misr` no longer has `pyhdf`, so `s01` uses the `pyhdf` env.
- `at3d_pure` no longer imports at3d: `libgfortran.so.3` is missing on Keeling. It ran the 2024
  open-boundary synthetic jobs and the cloud generator, and the pipeline uses `at3d_pure_k9` (also
  at3d 4.1.0) for those instead.

**Not bit-reproducible.**
- **Retrieval stopping point.** `run_at3d.py` stops L-BFGS-B on `ftol` or an abnormal line search.
  `maxiter=100` is hard-coded and never reached. A rerun is deterministic on the same node type and
  software stack. On different hardware it can stop at a different iteration than the archived runs
  (e.g. `default` at iter032). This includes the two stage-1 runs, which originally ended at iter030
  on an abnormal line search.
- **Water Mie table.** The rebuilt `red_mie_table.nc` matches the existing one in `extinction`,
  `scatter` and `nleg`. `legendre` differs in 2 % of entries by at most 1.2e-7 relative, which is
  float32 rounding. The existing table predates the repository, and `run_at3d.py` loads whichever table
  is in the repo's `mie_tables/`.
- **Synthetic cloud field.** Random; see Pipeline inputs.

## Verification

Run on 2026-10-20 with `--out-root /data/gdi/b/johntl3/LundstromPub2025_pipeline_test --stages pre,b1`,
comparing with `python scripts/pipeline/compare_outputs.py <out-root>`. That script compares every
variable, dimension and attribute in every netCDF group.

| File | Result |
|---|---|
| `data/V11/AT3D_OBS_bbox_…_H1400_{U1p3_V2p4,ATM,ATP,CTM,CTP}.nc` | identical |
| `data/V11/CVM_LCL_CTH_SC_R7.nc`, `…_R0_1_2_3_4_5_6_7.nc`, `CVM_unconstrained_mod.nc` | identical |
| `data/interim/RTG_default.nc` | identical |
| `data/interim/ATMOS_ERA5_CAMP2Ex_RF17_default.nc` | identical |
| `data/interim/AEROSOL_MISR_21_0p{150,200,250}.nc` | identical |
| `data/interim/MIXTURE_default_ERA5{,_0p150,_0p250}.nc` | identical |
| `data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc` | identical |
| `data/interim/MISR_{GEO,CMV}_*.nc` | identical |
| `data/interim/MISR_{RAD,CTH}_*.nc`, `MISR_OBS_CAMP2Ex_RF17_default.nc` | coordinate rounding only (`gamma` ≤ 3.5e-9, `lat` ≤ 3.6e-15); the obs and CVMs built from them are identical |
| `mie_tables/red_mie_table.nc` | float32 rounding in `legendre` (see above) |
| `data/interim/AT3D_OBS_CAMP2Ex_RF17_default.nc` (with s=1.5) | same rays, `I` and attributes; ray geometry differs by ≤ 1e-8 (carried over from the `MISR_OBS` coordinate rounding) |
| `notebooks/surface_parameterization_testing/output1D/*.nc` (all 10) | radiances `I` identical; ray geometry differs by ≤ 1e-8, inherited from the obs file |
| `data/synthetic/thesis/TradeCumulus/len005/ex00_density.nc` (s01) | byte-identical |
| `data/synthetic/thesis_periodic_V2/TradeCumulus/len005/ex00_syntheticObs.nc` | identical |
| `data/synthetic/thesis/TradeCumulus/len005/ex00_syntheticObs.nc` | identical except cloud `legcoef` ≤ 3.8e-37 (radiances identical); originally run in `at3d_pure` |
| All 29 figures, re-rendered after archiving and the path edits | pixel-identical to renders made before archiving |

## Archive

Code and data that no figure and no pipeline stage uses were moved to `archive/`, which mirrors the
original paths. Tracked files were moved with git renames, so their history is kept. The archive
includes:
- **Experiments:** `experiments/CAMP2Ex_RF17/V00–V10, V12` and `experiments/tmp`.
- **V11 runs no figure plots:** `CVM/SC`, `CVM/unconstrained_obsolete`, `cloud_motion/{ATM,ATP,CTM,CTP}`,
  `cloud_motion/*_unc_obsolete` and `high_res`, plus `V11/figures` (old notebook outputs).
- **Data:** `data/V12`; the V11 CVMs used only by those runs; unused `data/interim` and `data/raw` files.
- **Notebooks:** presentation notebooks (`20261013_uw_seminar`, `AMS_Madison_2026_figures`,
  `MAIA_2026_STM_figures`), `investigation/` (except `pre_retrieval/MISR_CloudMotionVectors.ipynb`),
  and unused figure and preprocessing notebooks.
- **Other:** `tmp/`, `NK1990_1D_Retrieval/`, the V08 LUT scripts, old Slurm logs, and the non-V11 job lists.

Archiving the extra V11 retrievals changes which retrievals `ExperimentSet` loads. The figures were
re-rendered afterwards and compared with renders made before archiving (see Verification).
