#!/bin/bash

#SBATCH --job-name=0p150
#SBATCH -p node
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate at3d_pure_k9

python /data/keeling/a/johntl3/b/LundstromPub2025/src/main/run_at3d.py /data/keeling/a/johntl3/b/LundstromPub2025/experiments/CAMP2Ex_RF17/V07/aerosol/0p150/config.yml > /data/keeling/a/johntl3/b/LundstromPub2025/experiments/CAMP2Ex_RF17/V07/aerosol/0p150/at3d.log
