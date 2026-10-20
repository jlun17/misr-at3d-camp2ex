#!/bin/bash

#SBATCH --job-name=LUT
#SBATCH -p node
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate vis2_clone

python /data/keeling/a/johntl3/b/LundstromPub2025/scripts/gen_LUT_V08.py