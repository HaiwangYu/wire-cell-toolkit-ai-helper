#!/bin/bash
# One SBND DetSim job (standard_detsim_sbnd.fcl = WCT sim + NF + SP + DNN-ROI, TbbFlow)
# on a Gen-2 g4 file, with either the cvmfs wirecell v0_32_1 libraries (control)
# or the patched 0.32.x build in $WCT_PREFIX.
# Usage (inside SL7, SL7_SETUP=none):
#   bash run-detsim.sh <cvmfs|patched> <g4.root> <nevents> <outdir> [extra lar args]
# Writes <outdir>/detsim.root, lar.log, ldlibs.txt (which libWireCell*.so were loaded).
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mode=$1; g4=$2; nev=$3; out=$4; shift 4
source "$here/env-0.32.sh"
mkdir -p "$out"; cd "$out"
if [[ $mode == patched ]]; then
  export LD_LIBRARY_PATH="$WCT_PREFIX/lib:$LD_LIBRARY_PATH"
  export PATH="$WCT_PREFIX/bin:$PATH"
  # cfg (share/wirecell) is unchanged by the cherry-picks; keep the production WIRECELL_PATH.
elif [[ $mode != cvmfs ]]; then
  echo "mode must be cvmfs or patched" >&2; exit 2
fi
echo "mode=$mode host=$(hostname) start=$(date -Is) g4=$g4 nev=$nev" > run.txt
echo "WCT_PREFIX=$WCT_PREFIX" >> run.txt
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH" >> run.txt
# LD_DEBUG=libs records every library the loader resolved -> proves which WCT libs ran.
LD_DEBUG=libs LD_DEBUG_OUTPUT="$out/lddebug" \
  /usr/bin/time -v lar -c standard_detsim_sbnd.fcl -s "$g4" -n "$nev" -o detsim.root -T hist.root "$@" > lar.log 2>&1
rc=$?
cat "$out"/lddebug.* 2>/dev/null | grep -o "calling init: .*libWireCell[A-Za-z]*\.so" | sed 's/calling init: //' | sort -u > ldlibs.txt
rm -f "$out"/lddebug.*
echo "rc=$rc end=$(date -Is)" >> run.txt
echo "LAR_RC=$rc mode=$mode out=$out"
exit $rc
