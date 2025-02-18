#!/bin/bash

#SBATCH --job-name=example
#SBATCH -p node
#SBATCH -n 4
#SBATCH --mem 64GB
#SBATCH --time=10-00:00:00
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=FAIL
#SBATCH --mail-type=END
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate at3d_pure

python /data/keeling/a/johntl3/b/LundstromPub2025/example/scripts/run_at3d.py > /data/keeling/a/johntl3/b/LundstromPub2025/example/keeling/logs/example.log
