# Conda environments

These are the six conda environments that produced the manuscript data and figures, exported from the
machine they ran on (Keeling, Linux x86-64). They are exported as-is rather than merged, so every step
runs in the same package set it originally ran in.

| Env | Python | Used by |
|---|---|---|
| `misr` | 3.6 | pipeline `s02`, `s02b` (MisrToolkit) |
| `pyhdf` | 3.13 | pipeline `s01` |
| `at3d_k9` | 3.10 | pipeline `s03` |
| `at3d_pure_k9` | 3.10 | pipeline `s00`, `s04`–`s10`, every V11 retrieval (`src/main/run_at3d.py`), all `synthetic` steps |
| `vis2` | 3.10 | Figs 2, 4, 5, 6, 8, 9, 10 and the even and odd SI figures |
| `vis2_clone` | 3.10 | pipeline `vc` (`src/veiledCore.py`) and `b1`; Figs 3, 7, 11, B1 |

The env names are fixed: `scripts/pipeline/run_pipeline.sh`, `scripts/figures/run_figures.sh` and the
generated retrieval jobs activate them by name.

## Files

For each env:
- `<env>.linux-64.lock.txt`: the exact conda packages, with URLs and md5 checksums.
- `<env>.pip.txt`: the exact pip packages, installed on top of the conda packages with `--no-deps`.
  The at3d envs and `vis2`/`vis2_clone` have most of their Python packages from pip.
- `<env>.conda-reinstall.txt` (`vis2`, `vis2_clone`): eight conda packages (numpy 1.26.4, matplotlib
  3.8.4, pandas 2.2.2, scipy 1.13.0, contourpy, fonttools, packaging, python-dateutil) that were installed
  over pip's older copies after at3d was built. `conda list` and pip still report pip's versions, but
  conda's files are the ones in use. `find_conda_overwrites.py` detects this from file hashes, and
  `create_envs.sh` replays the order (lockfile, pip, at3d, then these packages, removed and reinstalled from conda). scipy was left mixed:
  files that exist only in pip's 1.10.1 remain next to 1.13.0, and a rebuild reproduces that.
- `<env>.yml`: the same information as one `conda env export` file, for reading.

`export_envs.sh` regenerates all three from the installed envs.

## Creating the envs

```bash
envs/create_envs.sh                    # all six, as named envs in $(conda info --base)/envs
envs/create_envs.sh at3d_pure_k9 vis2  # selected envs
envs/create_envs.sh --prefix-dir DIR   # as DIR/<env>; add DIR to `envs_dirs` in ~/.condarc to activate by name
```

Requirements:
- conda on Linux x86-64; the lockfiles are platform-specific.
- Network access to conda.anaconda.org, repo.anaconda.com, PyPI and GitHub.
- gfortran and a C compiler on PATH. at3d is compiled from source, and `MisrToolkit` is built from its
  PyPI source distribution.

## Pinned sources

- **at3d** (`at3d_k9`, `at3d_pure_k9`, `vis2`, `vis2_clone`): commit `bcb15626cec1d21996ea5213fc2c99c36b9a27a1`
  of https://github.com/CloudTomography/AT3D (2022-09-08, version 4.1.0).
  - The envs were installed from a local checkout that sat at this commit from 2024-11-29 to 2026-07-29
    (git reflog), which covers every env install, and all 27 installed Python files match it.
  - Later commits do not build as-is: from 2023 `setup.py` lists `src/particle_flow.f90`, which is not
    in the repository.
  - The compiled Fortran extension depends on the local compiler. AT3D's README tests with GCC 11.3 and
    requires `-fallow-argument-mismatch` for GCC ≥ 10.
  - It is installed with `--no-build-isolation` so it builds against the env's numpy 1.21.2.
- **MisrToolkit 1.5.1** (`misr`): PyPI source distribution of https://github.com/nasa/MISR-Toolkit.

## Envs that changed since the original runs

- `misr` no longer contains `pyhdf`, which the ACP conversion (`s01`) originally ran with. `s01` uses
  the `pyhdf` env instead.
- `at3d_pure` ran the 2024 open-boundary synthetic experiments and the cloud generator. It no longer
  imports at3d on Keeling (`libgfortran.so.3` missing), so it is not exported, and those steps use
  `at3d_pure_k9`, which has the same at3d version. `PIPELINE.md` shows the resulting outputs agree
  (radiances identical).
