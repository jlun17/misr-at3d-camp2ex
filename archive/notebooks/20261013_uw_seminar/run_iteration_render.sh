#!/bin/bash

#SBATCH --job-name=iter_render
#SBATCH -p node
#SBATCH -N 1
#SBATCH -c 4
#SBATCH --mem 32GB
#SBATCH --time=0-02:00:00
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=johntl3@illinois.edu

source ~/miniconda3/bin/activate vis2

cd /data/keeling/a/johntl3/b/LundstromPub2025/notebooks/20261013_uw_seminar

python iteration_animation_render.py > iteration_animation_render.log 2>&1
python iteration_animation_render.py --preview 0 15 >> iteration_animation_render.log 2>&1
