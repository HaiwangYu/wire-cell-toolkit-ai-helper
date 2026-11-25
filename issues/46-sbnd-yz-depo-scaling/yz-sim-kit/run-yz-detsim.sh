#!/bin/bash
# Run the standard SBND detsim with the Wire-Cell YZ scaling on or off
# (ai-helper issue 46), and optionally the standard reco1 on its output.
#
# Usage:
#   run-yz-detsim.sh --yz on|off [--reco1] [--nskip N] [--map FILE] <g4.root> <outdir> [nevents=-1]
#
#   --yz on|off  the toggle (detsim_sbnd_yz_on.fcl / detsim_sbnd_yz_off.fcl)
#   --reco1      also run standard_reco1_sbnd.fcl on the detsim output
#   --nskip N    skip the first N input events
#   --map FILE   (with --yz on) use this YZ map file instead of the default
#                sbnd/sbnd-yzmap-run2-gen2-bnblight-v1.json.bz2; same binning
#                (100 z x 80 y bins of 5 cm, z from 0, y from -200 cm)
#
# Output, one directory per art job (art's MemoryTracker keeps an SQLite file in
# the working directory, and two jobs sharing one on CephFS fail with
# "disk I/O error"):
#   <outdir>/detsim/detsim.root   + detsim.log, detsim.time (/usr/bin/time -v),
#                                   timing.db, memory.db, summary.txt
#   <outdir>/reco1/reco1.root     (with --reco1) + the same files
# Use a different <outdir> for "on" and "off".
#
# Runs anywhere on an SBND gpvm or build node: outside SL7 it re-starts itself
# in the fnal-dev-sl7 container.  It sources setup-yz-env.sh itself.
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest

if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    APPT=$(command -v apptainer || echo /cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer)
    exec "$APPT" exec -B /cvmfs,/exp,/pnfs,/tmp,/opt "$IMG" /bin/bash "$KIT/run-yz-detsim.sh" "$@"
fi

usage() { sed -n '5,14p' "$KIT/run-yz-detsim.sh" >&2; exit 2; }
YZ= RECO1=0 NSKIP=0 MAP=
while [[ $# -gt 0 ]]; do
    case "$1" in
        --yz) YZ=$2; shift 2 ;;
        --reco1) RECO1=1; shift ;;
        --nskip) NSKIP=$2; shift 2 ;;
        --map) MAP=$(readlink -f "$2"); shift 2 ;;
        -h|--help) usage ;;
        --*) echo "unknown option $1" >&2; usage ;;
        *) break ;;
    esac
done
[[ "$YZ" == on || "$YZ" == off ]] || usage
[[ $# -ge 2 ]] || usage
if [[ -n "$MAP" ]]; then
    [[ "$YZ" == on ]] || { echo "--map needs --yz on" >&2; exit 2; }
    [[ -r "$MAP" ]] || { echo "cannot read map $MAP" >&2; exit 1; }
fi
G4=$(readlink -f "$1"); OUT=$2; NEV=${3:--1}
[[ -r "$G4" ]] || { echo "cannot read $G4" >&2; exit 1; }
mkdir -p "$OUT" && OUT=$(cd "$OUT" && pwd) || exit 1

source "$KIT/setup-yz-env.sh" >/dev/null || exit 1

# Per-job summary: wall time, peak RSS, and art's per-module TimeTracker /
# MemoryTracker tables from the log.
summarize() {  # <dir> <name>
    local d=$1 n=$2
    {
        grep -E 'Elapsed \(wall|Maximum resident|Exit status' "$d/$n.time" | sed 's/^\s*/== /'
        sed -n '/^TimeTracker printout/,/^MemReport  VmPeak/p' "$d/$n.log"
    } > "$d/summary.txt"
}

run_lar() {  # <dir> <name> <fcl> <input> <nevents> <nskip> [command prefix, e.g. env VAR=x]
    local d=$1 n=$2 fcl=$3 in=$4 nev=$5 nskip=$6; shift 6
    mkdir -p "$d" && cd "$d" || return 1
    if [[ -e "$n.root" ]]; then echo "$d/$n.root exists; not overwriting" >&2; return 1; fi
    echo "$(date '+%F %T') $n: $* lar -c $fcl -s $in -o $n.root -n $nev --nskip $nskip" | tee "$n.cmd"
    /usr/bin/time -v -o "$n.time" "$@" lar -c "$fcl" -s "$in" -o "$n.root" -n "$nev" --nskip "$nskip" \
        --timing-db timing.db --memcheck-db memory.db > "$n.log" 2>&1
    local rc=$?
    summarize "$d" "$n"
    echo "$(date '+%F %T') $n: rc $rc, $(grep -E 'Elapsed \(wall' "$n.time" | awk '{print $NF}') wall, $(grep -E 'Maximum resident' "$n.time" | awk '{print $NF}') kB max RSS"
    return $rc
}

# detsim: the WCT libraries of the branch are preloaded for this job only.
FCL=detsim_sbnd_yz_$YZ.fcl
if [[ -n "$MAP" ]]; then   # a one-line fcl on top of the "on" wrapper
    mkdir -p "$OUT/detsim"
    FCL=$OUT/detsim/detsim_sbnd_yz_on_custom_map.fcl
    printf '#include "detsim_sbnd_yz_on.fcl"\nphysics.producers.simtpc2d.wcls_main.params.yz_map: "%s"\n' "$MAP" > "$FCL"
fi
run_lar "$OUT/detsim" detsim "$FCL" "$G4" "$NEV" "$NSKIP" env LD_PRELOAD="$WCT_YZ_PRELOAD" || exit 1
# The reco1 job reads the detsim output; it runs no Wire-Cell code.
if [[ $RECO1 == 1 ]]; then
    run_lar "$OUT/reco1" reco1 standard_reco1_sbnd.fcl "$OUT/detsim/detsim.root" -1 0 || exit 1
fi
