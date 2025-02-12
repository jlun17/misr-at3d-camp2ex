#!/bin/bash

#SBATCH --job-name=rf17_03
#SBATCH -p node
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate at3d_pure

python /data/keeling/a/johntl3/b/LundstromPub2025/src/MISR_at3d.py > /data/keeling/a/johntl3/b/LundstromPub2025/dev/at3d_rf17_03.log
