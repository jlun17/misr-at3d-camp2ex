#!/bin/bash

#SBATCH --job-name=VC
#SBATCH -n 12
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00

# min_optical_path.nc for every V11 retrieval (Fig 7); the pipeline's `vc` stage runs the same command.
# Submit from the repository root (or set PROJECT_ROOT). Conda comes from $CONDA_BASE (default
# `conda info --base`); partition and mail options from SBATCH_PARTITION, SBATCH_MAIL_USER, ...

if [ -z "$PROJECT_ROOT" ]; then
    if [ -n "$SLURM_JOB_ID" ]; then
        PROJECT_ROOT=$SLURM_SUBMIT_DIR
    else
        PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    fi
fi
[ -f "$PROJECT_ROOT/src/veiledCore.py" ] || { echo "Not the repository root: $PROJECT_ROOT"; exit 1; }

source "${CONDA_BASE:-$(conda info --base)}/bin/activate" vis2_clone

python $PROJECT_ROOT/src/veiledCore.py $PROJECT_ROOT/experiments/CAMP2Ex_RF17/V11/
