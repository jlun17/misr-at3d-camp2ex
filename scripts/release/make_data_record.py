"""Build the data record: the processed and retrieval files the manuscript figures and the pipeline read,
packed as one archive that unpacks into the repository root.

Usage: python scripts/release/make_data_record.py OUT_DIR

Writes OUT_DIR/LundstromPub2025_data_record.tar.gz and OUT_DIR/DATA_RECORD.sha256. The checksum list is
also inside the archive, so after unpacking, `scripts/release/verify_data_record.sh` (run in the
repository root) checks every file.

Contents (paths relative to the repository root):
- experiments/CAMP2Ex_RF17/V11/<run>/: for each retrieval the figure scripts load, the final iterate
  (iterations/iterNNN.nc, the only one src/Retrieval.py reads with iteration=-1), min_optical_path.nc
  (Fig 7), and loss.csv and at3d.log as the record of convergence. config.yml and run_at3d.sh are in git.
- data/V11/: observations and cloud volume masks.
- data/interim/: RTE grid, background scatterers, MISR extracts, and the Fig B1 observation file.
- data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc: converted from the raw HDF by pipeline step s01.
- data/synthetic/: the synthetic cloud field and atmosphere (pipeline inputs with no download), and the
  synthetic observations and retrievals Figs 9 and 10 read.
- mie_tables/red_mie_table.nc: the Water Mie table the retrievals used (a rebuild differs at float32
  rounding).
- notebooks/surface_parameterization_testing/output1D/: the 1D surface simulations Fig B1 reads.

Not included: raw files that scripts/download/ fetches (MISR HDF, ERA5, CAMP2Ex in situ), anything
tracked in git, and archive/.
"""
import hashlib
import sys
import tarfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_NAME = 'LundstromPub2025_data_record.tar.gz'
CHECKSUM_NAME = 'DATA_RECORD.sha256'

V11 = 'experiments/CAMP2Ex_RF17/V11'
# Retrievals the figure scripts load (ExperimentSet loads every directory with iterations/, skipping
# high_res): the 10 in scripts/pipeline/camp2ex/job_list_V11.csv and the first attempts of the two that
# were restarted.
RETRIEVALS = [
    'default', 'default_obsolete',
    'aerosol/aod0p150', 'aerosol/aod0p250',
    'HBC/periodic',
    'surf_wind/surf4p0', 'surf_wind/surf4p0_obsolete',
    'CVM/unconstrained',
    'cloud_motion/ATM_unc', 'cloud_motion/ATP_unc', 'cloud_motion/CTM_unc', 'cloud_motion/CTP_unc',
]
RETRIEVAL_FILES = ['min_optical_path.nc', 'loss.csv', 'at3d.log']
DIRECTORIES = [
    'data/V11',
    'data/interim',
    'data/synthetic',
    'notebooks/surface_parameterization_testing/output1D',
]
FILES = [
    'data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.nc',
    'mie_tables/red_mie_table.nc',
]


def record_files():
    """Paths, relative to PROJECT_ROOT, of every file in the data record."""
    files = []
    for run in RETRIEVALS:
        run_dir = PROJECT_ROOT / V11 / run
        iterations = sorted((run_dir / 'iterations').glob('iter*.nc'))
        if not iterations:
            sys.exit(f'No iterations in {run_dir}')
        files.append(iterations[-1])
        files += [run_dir / f for f in RETRIEVAL_FILES]
    for d in DIRECTORIES:
        found = sorted(p for p in (PROJECT_ROOT / d).rglob('*') if p.is_file())
        if not found:
            sys.exit(f'No files in {PROJECT_ROOT / d}')
        files += found
    files += [PROJECT_ROOT / f for f in FILES]
    missing = [f for f in files if not f.is_file()]
    if missing:
        sys.exit('Missing: ' + ', '.join(str(f) for f in missing))
    return [f.relative_to(PROJECT_ROOT) for f in files]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.split('\n\n')[1])
    out_dir = Path(sys.argv[1]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = record_files()
    checksums = out_dir / CHECKSUM_NAME
    with open(checksums, 'w') as f:
        for rel in files:
            f.write(f'{sha256(PROJECT_ROOT / rel)}  {rel}\n')
    print(f'{len(files)} files, {sum((PROJECT_ROOT / r).stat().st_size for r in files) / 1e9:.2f} GB')

    with tarfile.open(out_dir / ARCHIVE_NAME, 'w:gz') as tar:
        for rel in files:
            tar.add(PROJECT_ROOT / rel, arcname=str(rel))
        tar.add(checksums, arcname=CHECKSUM_NAME)
    print(f'Wrote {out_dir / ARCHIVE_NAME} and {checksums}')


if __name__ == '__main__':
    main()
