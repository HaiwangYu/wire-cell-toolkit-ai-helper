#!/bin/bash
# Issue 37: light-only detsim rerun of one regenerated event with a chosen duneopdet build and knob setting, then the
# official OpHit finder, the light-truth dump and the bug metrics.
#   run-rerun.sh <config> <mix|sol> <idx>          (self re-execs into SL7 via in-sl7.sh)
# config:  stock    cvmfs duneopdet v10_26_00d00 (control: the rerun mechanism reproduces the stored waveforms)
#          legacy   local build, MergeOverlappingRanges false, LateLightReference "Event" (must equal stock)
#          default  local build with its defaults (merge on, "Event")                      (bug 1 fixed)
#          track    local build, merge on, LateLightReference "Track" on sipmAr10ppm{,Ext}   (bugs 1 and 2 fixed)
# Seed: the event's own detsim masterSeed (job_detsim.fcl), NuRandomService policy "random" as in the original job,
# so the stock rerun must reproduce the stored raw::OpDetWaveforms and OpDetDivRecs bit for bit.
# Reads $WA/fdvd02/<s>/evt<i>/reco.root; writes $WA/rerun/<config>/<s>/evt<i>/{metrics.json,lt.npz,*.log,cfg.txt}.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WA=${WA:-/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37}
CFG=$1; S=$2; I=$3
case $CFG in stock) ;; legacy|default|track) export OPDEV=${OPDEV:-$WA/opdev} ;; *) echo "bad config $CFG"; exit 2 ;; esac
[ -n "${APPTAINER_NAME:-}" ] || exec $HERE/in-sl7.sh /bin/bash "$0" "$@"
STAGEA=${STAGEA:-/exp/dune/data/users/yuhw/wcp-porting-validation/fdvd_sim/stageA}
IN=$WA/fdvd02/$S/evt$I
W=$WA/rerun/$CFG/$S/evt$I
[ -f $W/metrics.json ] && [ -z "${FORCE:-}" ] && { echo "$CFG $S $I skip"; exit 0; }
grep -q DONE $IN/status.txt 2>/dev/null || { echo "$CFG $S $I: no input"; exit 3; }
rm -rf $W; mkdir -p $W && cd $W || exit 3
echo "config $CFG; duneopdet $(ups active | awk '$1=="duneopdet"{print $2, $NF}')" > build.txt
[ -n "${OPDEV:-}" ] && cat $OPDEV/build-source.txt >> build.txt
export FHICL_FILE_PATH="$STAGEA:$FHICL_FILE_PATH"
SEED=$(awk '/masterSeed/{print $2}' $IN/job_detsim.fcl)
{ cat $STAGEA/detsim_light_rerun.fcl
  echo "services.NuRandomService.masterSeed: $SEED"
  case $CFG in
    legacy) echo "physics.producers.opdigi10ppm.MergeOverlappingRanges: false" ;;
    track)  echo "physics.producers.sipmAr10ppm.LateLightReference: \"Track\""
            echo "physics.producers.sipmAr10ppmExt.LateLightReference: \"Track\"" ;;
  esac
} > detsim.fcl
lar -c detsim.fcl --debug-config cfg.txt > /dev/null 2>&1
lar -c detsim.fcl -s $IN/reco.root -n 1 > detsim.log 2>&1 || { echo "$CFG $S $I detsim FAILED"; exit 4; }
lar -c $STAGEA/reco_ophit_variant.fcl -s detsim_rerun.root -n 1 -o ophit.root > ophit.log 2>&1 || { echo "$CFG $S $I ophit FAILED"; exit 5; }
python3 $STAGEA/dump_light_truth.py detsim_rerun.root lt.npz > lt.log 2>&1 || { echo "$CFG $S $I lt FAILED"; exit 6; }
python3 $HERE/light_bugs_metrics.py detsim_rerun.root ophit.root lt.npz $IN/reco.root metrics.json > metrics.log 2>&1 || { echo "$CFG $S $I metrics FAILED"; exit 7; }
[ "${KEEP:-0}" = 1 ] || rm -f detsim_rerun.root ophit.root
echo "$CFG $S $I ok $(date +%T)"
