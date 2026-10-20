#!/bin/bash

#SBATCH --job-name=figures
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=2-00:00:00

# Regenerate manuscript figures into figures/manuscript/.
#   sbatch scripts/figures/run_figures.sh                          # all figures
#   sbatch scripts/figures/run_figures.sh fig04_chi2.py fig09_hbc.py  # selected figures
#   bash scripts/figures/run_figures.sh                            # without Slurm
#
# Submit from the repository root (or set PROJECT_ROOT): under sbatch the script runs from a spooled copy,
# so its own location does not identify the repository. Conda comes from $CONDA_BASE
# (default `conda info --base`); partition and mail options from SBATCH_PARTITION, SBATCH_MAIL_USER, ...
#
# The scripts are copied from the figure notebooks and, like them, locate the repository with
# Path().resolve().parent.parent and import helper modules that live next to the notebooks.
# This wrapper therefore runs them from scripts/figures/ with those notebook directories on PYTHONPATH.

if [ -z "$PROJECT_ROOT" ]; then
    if [ -n "$SLURM_JOB_ID" ]; then
        PROJECT_ROOT=$SLURM_SUBMIT_DIR
    else
        PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
    fi
fi
[ -f "$PROJECT_ROOT/scripts/figures/run_figures.sh" ] || { echo "Not the repository root: $PROJECT_ROOT"; exit 1; }
CONDA_BASE=${CONDA_BASE:-$(conda info --base)}
SCRIPT_DIR=$PROJECT_ROOT/scripts/figures

cd $SCRIPT_DIR
export PYTHONPATH=$PROJECT_ROOT/notebooks/figures:$PROJECT_ROOT/notebooks/HBC
mkdir -p $PROJECT_ROOT/figures/manuscript

# Conda environment used by each figure's source notebook.
declare -A ENV=(
    [fig02_volume.py]=vis2
    [fig03_profiles.py]=vis2_clone
    [fig04_chi2.py]=vis2
    [fig05_brf.py]=vis2
    [fig06_cloudmotion.py]=vis2
    [fig07_insitu.py]=vis2_clone
    [fig08_clouds.py]=vis2
    [fig09_hbc.py]=vis2
    [fig10_periodic.py]=vis2
    [fig11_target.py]=vis2_clone
    [figB1_surface.py]=vis2_clone
    [figS_volume.py]=vis2
    [figS_brf.py]=vis2
)

if [ $# -gt 0 ]; then
    scripts=("$@")
else
    scripts=(fig02_volume.py fig03_profiles.py fig04_chi2.py fig05_brf.py fig06_cloudmotion.py
             fig07_insitu.py fig08_clouds.py fig09_hbc.py fig10_periodic.py fig11_target.py
             figB1_surface.py figS_volume.py figS_brf.py)
fi

failed=()
for s in "${scripts[@]}"; do
    env=${ENV[$s]}
    if [ -z "$env" ]; then
        echo "Unknown script: $s"
        failed+=("$s")
        continue
    fi
    echo "=== $s ($env) $(date)"
    source "$CONDA_BASE/bin/activate" $env
    python $s || failed+=("$s")
done

echo "=== done $(date)"
if [ ${#failed[@]} -gt 0 ]; then
    echo "FAILED: ${failed[*]}"
    exit 1
fi
