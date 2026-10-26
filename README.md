# Atmospheric Tomography with 3D Radiative Transfer applied to the Multi-angle Imaging SpectroRadiometer

This repository contains code to reproduce all figures associated with Lundstrom et al. (2026). It is
archived on Zenodo as the software record [10.5281/zenodo.23677453](https://doi.org/10.5281/zenodo.23677453),
with the data record [10.5281/zenodo.23677122](https://doi.org/10.5281/zenodo.23677122).

Lundstrom, J., Di Girolamo, L., and Loveridge J. R. (2026; in review). The Practical Application of Atmospheric Tomography with 3D Radiative Transfer to the Multi-angle Imaging SpectroRadiometer. Journal of Geophysical Research: Atmospheres.

## Requirements

- Linux x86-64 with conda. The environment lockfiles in `envs/` are platform-specific.
- gfortran and a C compiler on PATH, because at3d is compiled from source.
- Network access to conda.anaconda.org, repo.anaconda.com, PyPI and GitHub.
- Slurm is optional. Every script also runs directly in the shell.
- The data record, `LundstromPub2025_data_record.tar.gz`, from Zenodo:
  [10.5281/zenodo.23677122](https://doi.org/10.5281/zenodo.23677122). It is 166 MB compressed and
  1.12 GB unpacked.

All commands below are run from the repository root.

## Reproducing the figures from the data record

The data record holds the processed files the figures read: the 10 V11 retrievals, the observations and
cloud volume masks, the synthetic HBC runs and the Fig B1 runs. No retrieval is rerun.

```bash
git clone https://github.com/jlun17/misr-at3d-camp2ex.git && cd misr-at3d-camp2ex
envs/create_envs.sh vis2 vis2_clone                    # the two conda envs the figure scripts use
tar -xzf /path/to/LundstromPub2025_data_record.tar.gz -C .   # unpacks into the repo root
scripts/release/verify_data_record.sh                  # checks every file against DATA_RECORD.sha256
scripts/download/download_camp2ex.sh                   # CAMP2Ex P-3B in situ files for Fig 7 (no login)
bash scripts/figures/run_figures.sh                    # all figures -> figures/manuscript/
```

- With Slurm, run `sbatch scripts/figures/run_figures.sh` instead. Site options come from sbatch's
  environment variables, e.g. `SBATCH_PARTITION`.
- To make selected figures, pass the script names: `bash scripts/figures/run_figures.sh fig04_chi2.py fig09_hbc.py`.
- The figures should match the published ones pixel for pixel. This was tested on 2026-10-21 from a fresh
  clone.
- `FIGURES.md` maps each figure (2–11, B1, S1–S18) to its script, image file, source notebook and input data.

## Reproducing the figures from scratch

The pipeline rebuilds every file in the data record from the raw MISR, ERA5 and CAMP2Ex data. It then
reruns the 10 V11 retrievals, the synthetic HBC experiments and the Fig B1 simulations, and finally makes
the figures. Each retrieval takes 1.5–19 h. With Slurm all 10 run in parallel.

1. Create all six conda environments (see `envs/README.md`):

   ```bash
   envs/create_envs.sh
   ```

2. Download the raw data. Each script checks the files against the ones used for the manuscript.

   ```bash
   scripts/download/download_misr.sh          # 12 MISR granules, ~2.2 GB (NASA Earthdata Login)
   python scripts/download/download_era5.py   # 2 ERA5 files (CDS account, ~/.cdsapirc, pip install cdsapi)
   scripts/download/download_camp2ex.sh       # 3 CAMP2Ex in situ files (no login)
   ```

3. Extract the two synthetic inputs from the data record. The synthetic cloud field is a random draw that
   cannot be regenerated, and no download exists for either file. Extract only these two files: the
   pipeline refuses to overwrite a populated `data/V11/`.

   ```bash
   tar -xzf /path/to/LundstromPub2025_data_record.tar.gz -C . \
       data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc \
       data/synthetic/ancillary/AFGL_summer_mid_lat.nc
   ```

4. Run the pipeline:

   ```bash
   scripts/pipeline/run_pipeline.sh --dry-run    # print the commands without running anything
   scripts/pipeline/run_pipeline.sh              # with Slurm: submits a chain of jobs; safe on a login node
   scripts/pipeline/run_pipeline.sh --local      # without Slurm: runs every step in this shell
   ```

   - The output goes to the repo root, and the last stage writes the figures to `figures/manuscript/`.
   - To build somewhere else, add `--out-root DIR`. The `figures` stage runs only when the output root is
     the repo root.
   - To run part of the pipeline, use `--stages`. The stages are `pre`, `retrievals`, `vc`, `synthetic`,
     `b1` and `figures`.
   - Logs go to `logs/pipeline/`.

5. Optionally, compare the rebuilt files with the data record:
   `python scripts/pipeline/compare_outputs.py DIR`, where `DIR` is a build made with `--out-root`.

The rebuilt figures are not expected to be identical to the published ones:
- **Retrievals.** A retrieval can stop at a different L-BFGS-B iteration on different hardware or
  software. Whether it converges or needs a restart can also change.
- **`cloud_motion/ATM_unc`.** This retrieval did not converge in V11 and was not restarted. The
  published Figs S11 and S12 show that unconverged run. The pipeline restarts it, so those two figures
  will differ.
- **Mie table.** The rebuilt Mie table differs from the archived one only in float32 rounding.

`PIPELINE.md` covers the rest: every stage, the source notebook and commit of each script, the three
parameters that no commit records and were recovered from the data files, and the verification against
the original files.

## Repository layout

| Path | Contents |
|---|---|
| `src/` | retrieval driver (`src/main/run_at3d.py`) and the analysis classes the figures use |
| `scripts/figures/` | one script per figure, plus `run_figures.sh` |
| `scripts/pipeline/` | the data pipeline (`run_pipeline.sh`) |
| `scripts/download/` | download scripts and checksums for the raw MISR, ERA5 and CAMP2Ex data |
| `scripts/release/` | builds and verifies the data record |
| `notebooks/` | the original figure and preprocessing notebooks, which the scripts were copied from |
| `configs/`, `automation/` | retrieval solver configs and the original V11 job lists |
| `envs/` | conda environment lockfiles and `create_envs.sh` |
| `archive/` | code and data that no figure or pipeline stage uses, kept at their original relative paths |

## License

The code is released under the MIT License (see `LICENSE`).
