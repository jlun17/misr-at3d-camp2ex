#!/bin/bash
# Download the CAMP2Ex P-3B in situ files Fig 7 reads (PIPELINE.md, "Pipeline inputs") from the NASA
# Langley airborne science data archive, and check them against CAMP2Ex.sha256.
#
#   scripts/download/download_camp2ex.sh [OUT_DIR]     (default: <repo>/data/raw/CAMP2Ex_SPEC)
#
# Files (research flight 17, 2019-10-01 UTC date; about 28 MB in total), at the paths
# scripts/figures/fig07_insitu.py reads:
#   CAMP2EX-MetNav_P3B_20191001_R0.ict             P-3B navigation and meteorology (PI: M. Yang)
#   PaulLawson/CAMP2Ex-FCDP_P3B_20191001_R1.ict    FCDP cloud droplet spectra (PI: P. Lawson)
#   PaulLawson/CAMP2Ex-2DS10_P3B_20191001_R0.ict   2D-S (10 um) particle spectra (PI: P. Lawson)
#
# The archive serves the files through enzFile links; the hex string in each link encodes the archive
# path, /pub-air/XFS/CAMP2EX/2019/P3B_AIRCRAFT/<PI>/<file>, given next to each URL below. No login is
# needed. Requires curl and sha256sum.
#
# Files already in OUT_DIR with the expected checksum are skipped. The checksums were computed from the
# files used for the manuscript; a mismatch means the archive now serves a different file.

set -e
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CHECKSUMS=$SCRIPT_DIR/CAMP2Ex.sha256
OUT_DIR=${1:-$SCRIPT_DIR/../../data/raw/CAMP2Ex_SPEC}
ENZ=https://www-air.larc.nasa.gov/cgi-bin/enzFile

# local path | download URL
FILES=(
    # /pub-air/XFS/CAMP2EX/2019/P3B_AIRCRAFT/YANG.MELISSA/CAMP2EX-MetNav_P3B_20191001_R0.ict
    "CAMP2EX-MetNav_P3B_20191001_R0.ict|$ENZ?bA0841B08DF7F1ACFBAD5C83F9313E20C792f7075622d6169722f5846532f43414d503245582f323031392f5033425f41495243524146542f59414e472e4d454c495353412f43414d503245582d4d65744e61765f5033425f32303139313030315f52302e696374"
    # /pub-air/XFS/CAMP2EX/2019/P3B_AIRCRAFT/LAWSON.PAUL/CAMP2Ex-FCDP_P3B_20191001_R1.ict
    "PaulLawson/CAMP2Ex-FCDP_P3B_20191001_R1.ict|$ENZ?cc3041B08DF7F1ACFBAD5C83F9313E20C792f7075622d6169722f5846532f43414d503245582f323031392f5033425f41495243524146542f4c4157534f4e2e5041554c2f43414d503245782d464344505f5033425f32303139313030315f52312e696374"
    # /pub-air/XFS/CAMP2EX/2019/P3B_AIRCRAFT/LAWSON.PAUL/CAMP2Ex-2DS10_P3B_20191001_R0.ict
    "PaulLawson/CAMP2Ex-2DS10_P3B_20191001_R0.ict|$ENZ?cc3041B08DF7F1ACFBAD5C83F9313E20C792f7075622d6169722f5846532f43414d503245582f323031392f5033425f41495243524146542f4c4157534f4e2e5041554c2f43414d503245782d32445331305f5033425f32303139313030315f52302e696374"
)

for cmd in curl sha256sum; do
    command -v $cmd > /dev/null || { echo "$cmd is required"; exit 1; }
done
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

expected_sum() { grep " $1\$" "$CHECKSUMS" | cut -d' ' -f1; }
has_expected_sum() { [ -f "$1" ] && [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$(expected_sum "$1")" ]; }

for entry in "${FILES[@]}"; do
    file=${entry%%|*}
    url=${entry#*|}
    if has_expected_sum "$file"; then
        echo "present: $file"
        continue
    fi
    echo "downloading: $file"
    mkdir -p "$(dirname "$file")"
    if ! curl -f -L -sS -o "$file.part" -- "$url"; then
        rm -f "$file.part"
        echo "Download failed: $url"
        echo "If the link no longer works, find the file under the archive path in the comment above it."
        exit 1
    fi
    mv "$file.part" "$file"
done

echo "Checking files against $CHECKSUMS"
sha256sum -c "$CHECKSUMS"
