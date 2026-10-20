#!/bin/bash

#SBATCH --job-name=flyaround
#SBATCH -p node
#SBATCH -N 1
#SBATCH -c 16
#SBATCH --mem 48GB
#SBATCH --time=0-04:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate vis2

cd /data/keeling/a/johntl3/b/LundstromPub2025/notebooks/20261013_uw_seminar

python 3Dextinction_flyaround.py --workers ${SLURM_CPUS_PER_TASK} --resume > 3Dextinction_frames/flyaround_render.log 2>&1
