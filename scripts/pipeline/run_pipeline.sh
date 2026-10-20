#!/bin/bash
# Build every input to every manuscript figure, then the figures, as a chain of Slurm jobs
# (or sequentially in this shell with --local).
#
#   scripts/pipeline/run_pipeline.sh [--out-root DIR] [--stages LIST] [--local] [--dry-run]
#
#   --out-root DIR  where data/, mie_tables/, experiments/ and output1D/ are written (default: repo root).
#                   For a directory other than the repo root, the pipeline inputs listed in PIPELINE.md
#                   are symlinked in from the repo first.
#   --stages LIST   comma-separated subset of: pre, retrievals, vc, synthetic, b1, figures (default: all).
#                   A stage whose upstream stage is not in LIST assumes that stage's outputs already exist.
#   --local         run every step in order in this shell instead of submitting Slurm jobs.
#   --dry-run       print the commands instead of running or submitting them.
#
# Environment:
#   CONDA_BASE      conda installation holding the envs in envs/ (default: `conda info --base`).
#   sbatch reads site options from its own environment variables, e.g. SBATCH_PARTITION,
#   SBATCH_ACCOUNT, SBATCH_MAIL_USER and SBATCH_MAIL_TYPE.
#
# Stages (see PIPELINE.md for the full DAG and the source commit of each script):
#   pre         camp2ex/s00-s09: Mie table, MISR and ERA5 preprocessing, RTE grid, aerosol, background
#               scatterers, observations, cloud volume masks
#   retrievals  camp2ex/s10 writes config.yml and run_at3d.sh for the 12 runs in job_list_V11.csv, then
#               runs them; default and surf4p0 wait for their *_obsolete stage-1 runs
#   vc          src/veiledCore.py -> min_optical_path.nc in every V11 retrieval (Fig 7)
#   synthetic   synthetic/: open and periodic HBC experiments for Figs 9 and 10
#   b1          surface1D/figB1_shdom1d.py -> output1D/ (Fig B1)
#   figures     scripts/figures/run_figures.sh (only when --out-root is the repo root)

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PIPE=$PROJECT_ROOT/scripts/pipeline
OUT_ROOT=$PROJECT_ROOT
STAGES=pre,retrievals,vc,synthetic,b1,figures
DRY_RUN=0
LOCAL=0

while [ $# -gt 0 ]; do
    case $1 in
        --out-root) OUT_ROOT=$(mkdir -p "$2" && cd "$2" && pwd); shift 2 ;;
        --stages)   STAGES=$2; shift 2 ;;
        --local)    LOCAL=1; shift ;;
        --dry-run)  DRY_RUN=1; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done
CONDA_BASE=${CONDA_BASE:-$(conda info --base 2>/dev/null)}
[ -n "$CONDA_BASE" ] || { echo "conda not found; set CONDA_BASE"; exit 1; }
export OUT_ROOT PROJECT_ROOT CONDA_BASE

has_stage() { [[ ",$STAGES," == *",$1,"* ]]; }

LOG_DIR=$OUT_ROOT/logs/pipeline
mkdir -p $LOG_DIR

# Pipeline inputs: raw data that no script produces (PIPELINE.md, "Pipeline inputs").
INPUTS=(
    data/raw/MISR/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{DF,CF,BF,AF,AN,AA,BA,CA,DA}_F03_0024.hdf
    data/raw/MISR/MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf
    data/raw/MISR/MISR_AM1_TC_CLOUD_P117_O105254_F01_0001.hdf
    data/raw/MISR/MISR_AM1_ACP_MIXTURE_F06_0022.hdf
    data/raw/era5/ERA5_upper_CAMP2Ex_RF17_wide.nc
    data/raw/era5/ERA5_surface_CAMP2Ex_RF17_wide_extra.nc
    data/synthetic/thesis/TradeCumulus/len149/ex00_density.nc
    data/synthetic/ancillary/AFGL_summer_mid_lat.nc
)
for f in "${INPUTS[@]}"; do
    if [ "$OUT_ROOT" != "$PROJECT_ROOT" ] && [ ! -e "$OUT_ROOT/$f" ]; then
        mkdir -p "$(dirname "$OUT_ROOT/$f")"
        ln -s "$PROJECT_ROOT/$f" "$OUT_ROOT/$f"
    fi
    [ -e "$OUT_ROOT/$f" ] || { echo "Missing pipeline input: $OUT_ROOT/$f"; exit 1; }
done

# Each step sets JOB_ID: the Slurm job id, or a placeholder for --local and --dry-run.
JOB_ID=
N_STEPS=0
next_placeholder() { N_STEPS=$((N_STEPS + 1)); JOB_ID=$((1000 + N_STEPS)); }

# submit NAME ENV DEPS NTASKS CMD: run CMD in conda env ENV after the comma-separated job ids DEPS.
submit() {
    local name=$1 env=$2 deps=$3 ntasks=$4 cmd=$5
    local wrapped="source $CONDA_BASE/bin/activate $env && $cmd"
    local args=(--parsable -J "$name" -n "$ntasks" --mem 64GB --time=10-00:00:00
                -o "$LOG_DIR/%x-%j.out" --export=ALL)
    [ -n "$deps" ] && args+=(--dependency=afterok:${deps//,/:})
    if [ $DRY_RUN -eq 1 ]; then
        [ $LOCAL -eq 1 ] && echo "bash -c \"$wrapped\" > $LOG_DIR/$name.out" \
                         || echo "sbatch ${args[*]} --wrap \"$wrapped\""
        next_placeholder
    elif [ $LOCAL -eq 1 ]; then
        echo "=== $name ($env) $(date)"
        bash -c "$wrapped" > "$LOG_DIR/$name.out" 2>&1 \
            || { echo "FAILED: $name (log: $LOG_DIR/$name.out)"; exit 1; }
        next_placeholder
    else
        JOB_ID=$(sbatch "${args[@]}" --wrap "$wrapped")
    fi
}
# submit_script DIR DEPS SCRIPT: run a batch script from DIR (its #SBATCH lines hold the resources).
submit_script() {
    local dir=$1 deps=$2 script=$3
    local args=(--parsable --chdir "$dir" --export=ALL)
    [ -n "$deps" ] && args+=(--dependency=afterok:${deps//,/:})
    if [ $DRY_RUN -eq 1 ]; then
        [ $LOCAL -eq 1 ] && echo "(cd $dir && bash $script)" || echo "sbatch ${args[*]} $script"
        next_placeholder
    elif [ $LOCAL -eq 1 ]; then
        echo "=== $script $(date)"
        (cd "$dir" && bash "$script") || { echo "FAILED: $script"; exit 1; }
        next_placeholder
    else
        JOB_ID=$(sbatch "${args[@]}" "$script")
    fi
}
join() { local IFS=,; echo "$*"; }

C=$PIPE/camp2ex
S=$PIPE/synthetic

# ---------------------------------------------------------------- pre
J_PRE=; J_RTG=; J_MIX=
if has_stage pre; then
    if [ -n "$(ls -A $OUT_ROOT/data/V11 2>/dev/null)" ]; then
        echo "$OUT_ROOT/data/V11 is not empty; use a fresh --out-root"; exit 1
    fi
    mkdir -p $OUT_ROOT/data/interim $OUT_ROOT/data/V11
    submit s00_mie_table at3d_pure_k9 "" 4 "python $C/s00_mie_table.py"; J_MIE=$JOB_ID
    submit s01_acp_mixture pyhdf "" 4 "python $C/s01_acp_mixture.py"; J_ACP=$JOB_ID
    submit s02_misr_preprocess misr "" 4 "python $C/s02_misr_preprocess.py"; J_MISR=$JOB_ID
    submit s02b_misr_obs_default misr "" 4 "python $C/s02b_misr_obs_default.py"; J_MOBS=$JOB_ID
    submit s03_rte_grid at3d_k9 "$J_MOBS" 4 "python $C/s03_rte_grid.py"; J_RTG=$JOB_ID
    submit s04_era5_atmosphere at3d_pure_k9 "$J_RTG" 4 "python $C/s04_era5_atmosphere.py"; J_ERA=$JOB_ID
    submit s05_misr_aerosol at3d_pure_k9 "$J_RTG,$J_ACP" 4 \
        "python $C/s05_misr_aerosol.py 0.150 && python $C/s05_misr_aerosol.py 0.200 && python $C/s05_misr_aerosol.py 0.250"
    J_AER=$JOB_ID
    submit s06_mix_background at3d_pure_k9 "$J_ERA,$J_AER" 4 \
        "python $C/s06_mix_background.py 0p200 '' && python $C/s06_mix_background.py 0p150 _0p150 && python $C/s06_mix_background.py 0p250 _0p250"
    J_MIX=$JOB_ID
    # Track winds: saved output of notebooks/investigation/pre_retrieval/MISR_CloudMotionVectors.ipynb
    submit s07_obs at3d_pure_k9 "$J_MISR" 4 \
        "python $C/s07_obs.py 1.3 2.4 && python $C/s07_obs.py 1.9 5.1 ATM && python $C/s07_obs.py 0.7 -0.3 ATP && python $C/s07_obs.py -0.3 2.7 CTM && python $C/s07_obs.py 2.9 2.1 CTP"
    J_OBS=$JOB_ID
    submit s08_cvm at3d_pure_k9 "$J_OBS,$J_RTG,$J_MISR" 4 \
        "python $C/s08_cvm.py 7 && python $C/s08_cvm.py 0 1 2 3 4 5 6 7 && python $C/s09_cvm_unc_mod.py"
    J_CVM=$JOB_ID
    J_PRE=$(join $J_MIE $J_MIX $J_CVM)
fi

# ---------------------------------------------------------------- retrievals
J_RET=()
if has_stage retrievals; then
    if [ $DRY_RUN -eq 1 ]; then
        echo "python $C/s10_make_configs.py  (skipped in dry run)"
    else
        (source $CONDA_BASE/bin/activate at3d_pure_k9 && python $C/s10_make_configs.py)
    fi
    declare -A RET_ID
    while IFS=, read -r out_path restart_iter _; do
        [ "$out_path" = out_path ] && continue
        deps=$J_PRE
        if [ "$restart_iter" != none ]; then
            stage1=$(dirname "$(dirname "$restart_iter")")/
            deps=$(join $deps ${RET_ID[$stage1]})
            deps=${deps#,}
        fi
        submit_script "$OUT_ROOT/$out_path" "$deps" "$OUT_ROOT/${out_path}run_at3d.sh"
        RET_ID[$out_path]=$JOB_ID
        J_RET+=($JOB_ID)
    done < $C/job_list_V11.csv
fi

# ---------------------------------------------------------------- vc
J_VC=
if has_stage vc; then
    submit min_optical_path vis2_clone "$(join ${J_RET[@]})" 12 \
        "python $PROJECT_ROOT/src/veiledCore.py $OUT_ROOT/experiments/CAMP2Ex_RF17/V11/"
    J_VC=$JOB_ID
fi

# ---------------------------------------------------------------- synthetic
J_SYN=()
if has_stage synthetic; then
    SYN=$OUT_ROOT/data/synthetic
    OPEN=$SYN/thesis/TradeCumulus
    PER=$SYN/thesis_periodic_V2/TradeCumulus
    LENS=(005 007 009 011 015 019)
    submit syn_mie_table at3d_pure_k9 "" 4 "python $S/s00_mie_table.py"; J_SMIE=$JOB_ID
    # Domain subsets and ymls. The periodic ymls are copies of the open ones (identical in Synthetic/IO).
    copy_ymls=""
    for l in ${LENS[@]}; do
        copy_ymls+=" && mkdir -p $PER/len$l && cp $OPEN/len$l/ex00.yml $OPEN/len$l/ex00em.yml $PER/len$l/"
    done
    submit syn_prep at3d_pure_k9 "" 4 \
        "python $S/s01_subset.py && python $S/ex00_ymlWriter.py && python $S/ex00em_ymlWriter.py$copy_ymls"
    J_PREP=$JOB_ID
    # Open boundaries (Synthetic/IO/thesis/batch_writer.ipynb; env at3d_pure, now broken: at3d_pure_k9 is used)
    declare -A J_GEN
    for l in ${LENS[@]} 149; do
        submit shdom${l}cu at3d_pure_k9 "$J_SMIE,$J_PREP" 4 \
            "python $S/gen_synthetic_obs_stochastic.py $OPEN/len$l/ex00.yml > $OPEN/len$l/ex00.gen_obs.txt"
        J_GEN[$l]=$JOB_ID
    done
    for l in ${LENS[@]}; do
        submit emu${l}cu at3d_pure_k9 "${J_GEN[$l]},${J_GEN[149]}" 4 \
            "python $S/emulate_obs_stochastic.py $OPEN/len$l/ex00 $OPEN/len149/ex00 && cp $OPEN/len$l/ex00em_syntheticObs.nc $PER/len$l/"
        j_emu=$JOB_ID
        submit at3d${l}cu_ at3d_pure_k9 "${J_GEN[$l]}" 4 \
            "python $S/botany_at3d.py $OPEN/len$l/ex00.yml > $OPEN/len$l/ex00.at3d.txt"
        J_SYN+=($JOB_ID)
        submit at3d${l}cu_em at3d_pure_k9 "$j_emu" 4 \
            "python $S/botany_at3d.py $OPEN/len$l/ex00em.yml > $OPEN/len$l/ex00em.at3d.txt"
        J_SYN+=($JOB_ID)
        # Periodic boundaries (Synthetic/IO/thesis_periodic_V2/batch_writer.ipynb; env at3d_pure_k9).
        # The emulated obs come from the open run, as in Synthetic/IO/thesis_periodic_V2.
        submit pshdom${l}cu at3d_pure_k9 "$J_SMIE,$J_PREP" 4 \
            "python $S/gen_synthetic_obs_stochastic_periodic.py $PER/len$l/ex00.yml > $PER/len$l/ex00.gen_obs.txt"
        j_pgen=$JOB_ID
        submit pat3d${l}cu_ at3d_pure_k9 "$j_pgen" 4 \
            "python $S/botany_at3d_V2.py $PER/len$l/ex00.yml > $PER/len$l/ex00.at3d.txt"
        J_SYN+=($JOB_ID)
        submit pat3d${l}cu_em at3d_pure_k9 "$j_emu" 4 \
            "python $S/botany_at3d_V2.py $PER/len$l/ex00em.yml > $PER/len$l/ex00em.at3d.txt"
        J_SYN+=($JOB_ID)
    done
fi

# ---------------------------------------------------------------- b1
J_B1=
if has_stage b1; then
    submit figB1_shdom1d vis2_clone "$(join $J_RTG $J_MIX)" 4 "python $PIPE/surface1D/figB1_shdom1d.py"
    J_B1=$JOB_ID
fi

# ---------------------------------------------------------------- figures
if has_stage figures; then
    if [ "$OUT_ROOT" != "$PROJECT_ROOT" ]; then
        echo "Skipping figures: scripts/figures reads from the repo root, not $OUT_ROOT"
    else
        submit_script "$PROJECT_ROOT" "$(join $J_VC ${J_SYN[@]} $J_B1)" "$PROJECT_ROOT/scripts/figures/run_figures.sh"
    fi
fi
