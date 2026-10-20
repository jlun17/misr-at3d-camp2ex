#!/bin/bash
# Create the conda environments used by the pipeline and figure scripts from the specs in envs/.
#
#   envs/create_envs.sh [--prefix-dir DIR] [env ...]     (default: all six)
#
# Each env is built from envs/<env>.linux-64.lock.txt (exact conda packages), then
# envs/<env>.pip.txt with --no-deps (exact pip packages). at3d is compiled last from the pinned AT3D
# commit with --no-build-isolation, so it builds against the env's numpy; this needs gfortran and a C
# compiler on PATH (see envs/README.md). AT3D runs `f2py` from PATH, so the env's bin/ is put first.
# Finally the packages in envs/<env>.conda-reinstall.txt, if present, are removed and reinstalled from
# conda: in the original env, those conda packages overwrote pip's copies after at3d was built.
#
# --prefix-dir DIR  create the envs as DIR/<env> instead of named envs in $CONDA_BASE/envs.
#                   The pipeline activates envs by name, so add DIR to conda's envs_dirs to use them.

set -e
ENVS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONDA_BASE=${CONDA_BASE:-$(conda info --base)}
CONDA=$CONDA_BASE/bin/conda
PREFIX_DIR=
ENVS=()

while [ $# -gt 0 ]; do
    case $1 in
        --prefix-dir) PREFIX_DIR=$(mkdir -p "$2" && cd "$2" && pwd); shift 2 ;;
        *) ENVS+=("$1"); shift ;;
    esac
done
[ ${#ENVS[@]} -gt 0 ] || ENVS=(misr pyhdf at3d_k9 at3d_pure_k9 vis2 vis2_clone)

for env in "${ENVS[@]}"; do
    [ -f "$ENVS_DIR/$env.linux-64.lock.txt" ] || { echo "No spec for $env"; exit 1; }
    if [ -n "$PREFIX_DIR" ]; then
        prefix=$PREFIX_DIR/$env
    else
        prefix=$CONDA_BASE/envs/$env
    fi
    echo "=== $env -> $prefix"
    $CONDA create -y -p "$prefix" --file "$ENVS_DIR/$env.linux-64.lock.txt"

    pip_reqs=$(mktemp)
    grep -v '^at3d @' "$ENVS_DIR/$env.pip.txt" > "$pip_reqs" || true
    if [ -s "$pip_reqs" ]; then
        "$prefix/bin/python" -m pip install --no-deps -r "$pip_reqs"
    fi
    rm -f "$pip_reqs"

    at3d=$(grep '^at3d @' "$ENVS_DIR/$env.pip.txt" || true)
    if [ -n "$at3d" ]; then
        # AT3D's setup.py runs the `f2py` found on PATH; it must be this env's (numpy 1.21.2), or the
        # generated wrappers check array shapes differently from the original builds.
        PATH="$prefix/bin:$PATH" "$prefix/bin/python" -m pip install --no-deps --no-build-isolation \
            --no-cache-dir "$at3d"
    fi
    if [ -f "$ENVS_DIR/$env.conda-reinstall.txt" ]; then
        # Conda packages that originally overwrote pip's copy of the same package (see find_conda_overwrites.py).
        # Drop conda's record of them (pip has replaced their files), then install them again so their files
        # are the ones in use; pip's dist-info stays behind, as in the original env.
        names=$(grep '^http' "$ENVS_DIR/$env.conda-reinstall.txt" | sed 's#.*/##; s#-[^-]*-[^-]*$##')
        $CONDA remove -y -p "$prefix" --force $names
        $CONDA install -y -p "$prefix" --file "$ENVS_DIR/$env.conda-reinstall.txt"
    fi
    "$prefix/bin/python" -m pip check || echo "WARNING: pip check reported issues for $env (see above)"
done
