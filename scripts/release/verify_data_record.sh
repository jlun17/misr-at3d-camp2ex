#!/bin/bash
# Check the unpacked data record against its checksum list.
#
#   tar -xzf LundstromPub2025_data_record.tar.gz -C <repository root>
#   scripts/release/verify_data_record.sh
#
# The archive unpacks DATA_RECORD.sha256 into the repository root next to the data files.

set -e
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$PROJECT_ROOT"
[ -f DATA_RECORD.sha256 ] || { echo "DATA_RECORD.sha256 not found in $PROJECT_ROOT; unpack the data record there first"; exit 1; }
sha256sum --quiet -c DATA_RECORD.sha256
echo "All $(wc -l < DATA_RECORD.sha256) data record files verified"
