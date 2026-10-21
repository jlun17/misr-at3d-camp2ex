#!/bin/bash
# Download the MISR granules the pipeline reads (PIPELINE.md, "Pipeline inputs") from the NASA Langley
# ASDC, and check them against MISR.sha256.
#
#   scripts/download/download_misr.sh [OUT_DIR]        (default: <repo>/data/raw/MISR)
#
# Granules (path 117, orbit 105254, 2019-10-02; about 2.2 GB in total):
#   MI1B2E.003   L1B2 ellipsoid-projected radiances, 9 cameras  MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_*_F03_0024.hdf
#   MIB2GEOP.002 geometric parameters                           MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf
#   MIL2TCSP.001 level 2 cloud (stereo cloud-top heights, motion) MISR_AM1_TC_CLOUD_P117_O105254_F01_0001.hdf
#   MIANACP.001  aerosol climatology product, mixtures           MISR_AM1_ACP_MIXTURE_F06_0022.hdf
#
# Requires curl, sha256sum and a NASA Earthdata Login (https://urs.earthdata.nasa.gov). Credentials are
# read from a "machine urs.earthdata.nasa.gov" entry in ~/.netrc if there is one; otherwise they are
# prompted for once and kept only in a temporary file that is deleted on exit.
#
# Files already in OUT_DIR with the expected checksum are skipped. The checksums were computed from the
# files used for the manuscript; a mismatch means ASDC now serves a different file (e.g. a reprocessed
# version) and the pipeline outputs are not expected to match.
#
# Replaces the four Earthdata Search scripts that were in data/raw/ (archive/data/raw/download_MISR_*.sh).

set -e
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CHECKSUMS=$SCRIPT_DIR/MISR.sha256
OUT_DIR=${1:-$SCRIPT_DIR/../../data/raw/MISR}
ASDC=https://data.asdc.earthdata.nasa.gov/asdc-prod-protected/MISR

URLS=(
    $ASDC/MI1B2E.003/2019.10.02/MISR_AM1_GRP_ELLIPSOID_GM_P117_O105254_{DF,CF,BF,AF,AN,AA,BA,CA,DA}_F03_0024.hdf
    $ASDC/MIB2GEOP.002/2019.10.02/MISR_AM1_GP_GMP_P117_O105254_F03_0013.hdf
    $ASDC/MIL2TCSP.001/2019.10.02/MISR_AM1_TC_CLOUD_P117_O105254_F01_0001.hdf
    $ASDC/MIANACP.001/1999.12.01/MISR_AM1_ACP_MIXTURE_F06_0022.hdf
)

for cmd in curl sha256sum; do
    command -v $cmd > /dev/null || { echo "$cmd is required"; exit 1; }
done
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"

expected_sum() { grep " $1\$" "$CHECKSUMS" | cut -d' ' -f1; }
has_expected_sum() { [ -f "$1" ] && [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$(expected_sum "$1")" ]; }

cookiejar=$(mktemp)
netrc=
cleanup() { rm -f "$cookiejar" ${netrc:+"$netrc"}; }
trap cleanup EXIT

netrc_file=
# Set netrc_file, asking for credentials only once and only if something needs downloading.
get_credentials() {
    [ -n "$netrc_file" ] && return
    if grep -qs "machine urs.earthdata.nasa.gov" ~/.netrc; then
        netrc_file=~/.netrc
        echo "Using Earthdata credentials from ~/.netrc"
    else
        netrc=$(mktemp)
        chmod 0600 "$netrc"
        echo "Enter your NASA Earthdata Login (https://urs.earthdata.nasa.gov)"
        read -p "Username: " username
        read -s -p "Password: " password
        echo
        echo "machine urs.earthdata.nasa.gov login $username password $password" > "$netrc"
        unset password
        netrc_file=$netrc
    fi
}

for url in "${URLS[@]}"; do
    file=${url##*/}
    if has_expected_sum "$file"; then
        echo "present: $file"
        continue
    fi
    get_credentials
    echo "downloading: $file"
    if ! curl -f -L -g -b "$cookiejar" -c "$cookiejar" --netrc-file "$netrc_file" -o "$file.part" -- "$url"; then
        rm -f "$file.part"
        echo "Download failed: $url"
        echo "Check the Earthdata username and password, and that you can open the URL above in a browser"
        echo "after logging in (the first ASDC download may ask you to authorize the application)."
        exit 1
    fi
    mv "$file.part" "$file"
done

echo "Checking files against $CHECKSUMS"
sha256sum -c "$CHECKSUMS"
