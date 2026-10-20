#!/bin/bash
# Re-export the environment specs in envs/ from the installed conda envs (run on the machine that has them).
#   envs/<env>.yml                full spec (conda + pip), no build strings, prefix removed
#   envs/<env>.linux-64.lock.txt  exact conda packages (conda create --file)
#   envs/<env>.pip.txt            exact pip packages, installed after the lockfile (pip install --no-deps -r)
#   envs/<env>.conda-reinstall.txt  lockfile lines for conda packages that overwrote a pip install of the
#                                 same package (find_conda_overwrites.py); reinstalled last, only if any
# at3d was installed from a local checkout of https://github.com/CloudTomography/AT3D whose installed
# sources match commit bcb1562, the commit that checkout was on from 2024-11-29 to 2026-07-29 (git
# reflog), covering every env install; the pip lines are rewritten to that public commit.

set -e
ENVS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONDA_BASE=${CONDA_BASE:-$(conda info --base)}
CONDA=$CONDA_BASE/bin/conda
AT3D='at3d @ git+https://github.com/CloudTomography/AT3D.git@bcb15626cec1d21996ea5213fc2c99c36b9a27a1'

for env in misr pyhdf at3d_k9 at3d_pure_k9 vis2 vis2_clone; do
    $CONDA env export -n $env --no-builds | grep -v '^prefix:' \
        | sed "s#^\( *\)- at3d==.*#\1- $AT3D#" > $ENVS_DIR/$env.yml
    $CONDA list -n $env --explicit --md5 > $ENVS_DIR/$env.linux-64.lock.txt
    $CONDA list -n $env | awk '$4 == "pypi" {print $1 "==" $2}' \
        | sed "s#^at3d==.*#$AT3D#" > $ENVS_DIR/$env.pip.txt
    reinstall=$("$CONDA_BASE/envs/$env/bin/python" "$ENVS_DIR/find_conda_overwrites.py" \
        "$CONDA_BASE/envs/$env" "$ENVS_DIR/$env.linux-64.lock.txt")
    rm -f $ENVS_DIR/$env.conda-reinstall.txt
    [ -n "$reinstall" ] && printf '@EXPLICIT\n%s\n' "$reinstall" > $ENVS_DIR/$env.conda-reinstall.txt
    echo "$env: $(grep -c '^http' $ENVS_DIR/$env.linux-64.lock.txt) conda, $(wc -l < $ENVS_DIR/$env.pip.txt) pip," \
         "$(echo -n "$reinstall" | grep -c .) conda reinstalled over pip"
done
