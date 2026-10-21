#!/bin/bash
# Run one retrieval, restarting it from its last iterate if L-BFGS-B does not report convergence.
#
#   run_until_converged.sh OUT_DIR      (OUT_DIR holds config.yml; the at3d conda env must be active)
#
# Environment:
#   PROJECT_ROOT   repository root (set by the run_at3d.sh that s10_make_configs.py writes)
#   MAX_RESTARTS   restarts allowed per retrieval (default 1). When they are used up, the last attempt
#                  is kept as the result whether or not it converged.
#
# Convergence: at3d.log contains L-BFGS-B's "CONVERGENCE: ..." message. Anything else (in V11,
# ABNORMAL_TERMINATION_IN_LNSRCH) counts as not converged.
#
# A non-converged attempt is moved to <run>_obsolete (then <run>_obsolete2, ...), the naming used for the
# hand-made V11 restarts of default and surf4p0, and the next attempt runs in <run>/ with restart_iter set
# to the last iterations/iter*.nc of the moved attempt. src/main/run_at3d.py loads that file's cloud
# extinction as its initial state and starts a fresh L-BFGS-B. The figure scripts find retrievals by
# directory name, so the final attempt is always <run>/.

set -e
out=$(cd "$1" && pwd)
max_restarts=${MAX_RESTARTS:-1}
[ -n "$PROJECT_ROOT" ] || { echo "PROJECT_ROOT is not set"; exit 1; }

# Paths in config.yml are relative to PROJECT_ROOT when they lie inside it (see s10_make_configs.py).
config_path() { case $1 in "$PROJECT_ROOT"/*) echo "${1#$PROJECT_ROOT/}" ;; *) echo "$1" ;; esac; }

for ((restart = 0; ; restart++)); do
    echo "=== $(basename "$out"): attempt $((restart + 1)) $(date)"
    python "$PROJECT_ROOT/src/main/run_at3d.py" "$out/config.yml" > "$out/at3d.log"
    if grep -q "CONVERGENCE:" "$out/at3d.log"; then
        echo "converged: $(grep -o 'CONVERGENCE: .*' "$out/at3d.log" | tail -n 1)"
        exit 0
    fi
    reason=$(tail -n 1 "$out/at3d.log")
    if [ $restart -ge $max_restarts ]; then
        echo "not converged ($reason) after $restart restart(s); keeping this attempt"
        exit 0
    fi

    # Move this attempt aside and restart from its last iterate.
    suffix=_obsolete; n=1
    while [ -e "${out}$suffix" ]; do n=$((n + 1)); suffix=_obsolete$n; done
    prev=${out}$suffix
    echo "not converged ($reason); moving attempt to $(basename "$prev") and restarting"
    mv "$out" "$prev"
    mkdir "$out"
    sed -i "s#^out_path: \(.*\)/\$#out_path: \1$suffix/#" "$prev/config.yml"
    last=$(ls "$prev"/iterations/iter*.nc | sort | tail -n 1)
    sed "s#^restart_iter: .*#restart_iter: $(config_path "$last")#" "$prev/config.yml" \
        | sed "s#^out_path: \(.*\)$suffix/\$#out_path: \1/#" > "$out/config.yml"
    cp "$prev/run_at3d.sh" "$out/"
done
