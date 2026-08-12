#!/bin/bash
# Decode the data leg's 10 events (see decode-data.fcl).  -> <campaign>/data/decoded.root
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
C="$D/data/validation-20260812"
RAW=/pnfs/sbnd/archive/sbn/sbn_nd/data/raw/bnblight/v1_10_04/sbnd_daq_v1_10_04/daq/00/01/82/59/data_EventBuilder6_art2_run18259_14_strmBNBLight_20250219T075652.root
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$C/data/decode"; cd "$C/data/decode"
lar -c "$HERE/decode-data.fcl" -s "$RAW" -n 10 > "$C/logs/decode.log" 2>&1
echo "decode rc=$?"
ls -la decoded.root 2>/dev/null | awk '{printf "  %.1f MB %s\n",$5/1048576,$NF}'
