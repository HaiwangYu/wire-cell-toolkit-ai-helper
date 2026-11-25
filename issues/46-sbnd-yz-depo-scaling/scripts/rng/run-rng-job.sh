#!/bin/bash
# One detsim job of the RNG study (issue 46), using the study copy of the kit.
# Usage: run-rng-job.sh <outdir> <yz on|off> <app TbbFlow|Pgrapher> <streams shared|separate> <nskip> <nev> [norandomize] [seed]
#   norandomize: "aslr-off" runs lar under `setarch -R` (no address-space randomization)
# Always also writes the sim RawDigits (wclsFrameSaver:simdigits) so noise can be compared.
KIT=${RNG_KIT:-/exp/sbnd/data/users/yuhw/YZ-non-uniformity/rng-study/kit-copy}
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
SELF=$(readlink -f "${BASH_SOURCE[0]}")
if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    APPT=$(command -v apptainer || echo /cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer)
    exec "$APPT" exec -B /cvmfs,/exp,/pnfs,/tmp,/opt "$IMG" /bin/bash "$SELF" "$@"
fi
OUT=$1 YZ=$2 APP=$3 STREAMS=$4 NSKIP=$5 NEV=$6 ASLR=${7:-aslr-on} SEED=${8:-0}
G4=${G4:-/exp/sbnd/data/users/yuhw/YZ-non-uniformity/mu-test/g4.root}
D=$OUT/detsim; mkdir -p "$D" && cd "$D" || exit 1
[[ -e detsim.root ]] && { echo "$D/detsim.root exists" >&2; exit 1; }
source "$KIT/setup-yz-env.sh" >/dev/null || exit 1
cat > job.fcl <<FCL
#include "detsim_sbnd_yz_$YZ.fcl"
physics.producers.simtpc2d.wcls_main.apps: ["$APP"]
physics.producers.simtpc2d.wcls_main.params.wct_app: "$APP"
physics.producers.simtpc2d.wcls_main.params.rng_streams: "$STREAMS"
physics.producers.simtpc2d.wcls_main.params.rng_seed: "$SEED"
physics.producers.simtpc2d.wcls_main.outputers: ["wclsDepoFluxWriter:postdrift", "wclsFrameSaver:spsaver", "wclsFrameSaver:dnnsaver", "wclsFrameSaver:simdigits"]
FCL
PRE=(); [[ $ASLR == aslr-off ]] && PRE=(setarch x86_64 -R)
echo "$(date '+%F %T') start yz=$YZ app=$APP streams=$STREAMS nskip=$NSKIP nev=$NEV $ASLR seed=$SEED g4=$G4" | tee detsim.cmd
/usr/bin/time -v -o detsim.time "${PRE[@]}" env LD_PRELOAD="$WCT_YZ_PRELOAD" lar -c job.fcl -s "$G4" -o detsim.root -n "$NEV" --nskip "$NSKIP" \
    --timing-db timing.db --memcheck-db memory.db > detsim.log 2>&1
rc=$?
{ grep -E 'Elapsed \(wall|Maximum resident|Exit status|Percent of CPU' detsim.time; sed -n '/^TimeTracker printout/,/^MemReport  VmPeak/p' detsim.log; } > summary.txt
echo "$(date '+%F %T') rc $rc $(grep -E 'Elapsed' detsim.time | awk '{print $NF}') wall; simtpc2d: $(grep 'simtpc2d:WireCell' summary.txt | head -1)" | tee -a detsim.cmd
exit $rc
