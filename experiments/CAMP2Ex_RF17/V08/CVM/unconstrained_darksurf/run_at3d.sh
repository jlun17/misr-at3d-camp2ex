#!/bin/bash

#SBATCH --job-name=unconstrained_darksurf
#SBATCH -p node
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate at3d_pure_k9

python /data/keeling/a/johntl3/b/LundstromPub2025/src/main/run_at3d.py /data/keeling/a/johntl3/b/LundstromPub2025/experiments/CAMP2Ex_RF17/V08/CVM/unconstrained_darksurf/config.yml > /data/keeling/a/johntl3/b/LundstromPub2025/experiments/CAMP2Ex_RF17/V08/CVM/unconstrained_darksurf/at3d.log
