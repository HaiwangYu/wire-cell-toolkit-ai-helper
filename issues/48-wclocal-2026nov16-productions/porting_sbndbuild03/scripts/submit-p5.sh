#!/bin/bash
# Issue 48 P5: submit the WCLocal2026Nov16 FermiGrid production (porting_sbndbuild03).
#   submit-p5.sh <step2|full|recover> [--dry-run]
#   step2    the full step-2-only lists (lists/pairs-<s>-step2.tsv); pairs already at the destination
#            (the P4 pilot) are skipped by job.sh
#   full     the 93 pairs that run from reco1 (lists/pairs-<s>-full.tsv), one pair per job
#   recover  lists/recover-<s>.tsv (pairs whose status is not OK, e.g. step 2 killed at the 4 GB limit),
#            8000 MB, written to <s>-mem8g/ so the first try's outputs stay as they are
#   recover-full  the same for from-reco1 pairs (lists/recover-full-<s>.tsv), full mode
#   recover-slow  step-2 timeouts (lists/recover-slow-<s>.tsv): 8000 MB, step-2 limit 4 h + 300 s/event
#            (WC_TIMEOUT_STEP2_BASE=14400; needs workflow submit.sh forwarding it), 12 h, into <s>-mem8g/
# Tarball: wclocal-nov16/tar/wcgrid-wcl1116-53a90eb.tar.gz (workflow wclocal-nov16 53a90eb).
# Needs KRB5CCNAME pointing at a valid ticket (htgettoken -a htvaultprod.fnal.gov -i sbnd --nooidc).
set -u
WHAT=${1:?step2|full|recover|recover-full|recover-slow}; DRY=${2:-}
R=/exp/sbnd/data/users/yuhw/wclocal-nov16
TARBALL=${TARBALL:-$R/tar/wcgrid-wcl1116-53a90eb.tar.gz}
cd /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/fermigrid || exit 1
export WC_STEP2_PASSES="pr:dv2_split_move:space:recTreeWireCell-dlvtx-space.schema.json pr-dv2snap:dv2_snap:nospace:recTreeWireCell.schema.json"
export WC_DV2_BUNDLE=dv2max/sbnd/aurora_space/bundle.json
export WC_GRID_LINES='+FERMIHTC_AutoRelease=True;+FERMIHTC_GraceMemory=2048;+FERMIHTC_GraceLifetime=3600'
case $WHAT in
  step2)   export WC_GRID_MODE=step2 WC_GRID_MEMORY=4000MB WC_GRID_LIFETIME=6h WC_GRID_DISK=10GB
           SPECS=("mc-cv 12" "mc-nuecc 4" "beam-off 3" "run3bnb 2" "opendata 2"); LIST=pairs-%s-step2.tsv; SUF= ;;
  full)    export WC_GRID_MODE=full WC_GRID_MEMORY=4000MB WC_GRID_LIFETIME=8h WC_GRID_DISK=15GB
           SPECS=("mc-cv 1" "mc-nuecc 1" "beam-off 1" "run3bnb 1" "opendata 1"); LIST=pairs-%s-full.tsv; SUF= ;;
  recover) export WC_GRID_MODE=${WC_GRID_MODE:-step2} WC_GRID_MEMORY=8000MB WC_GRID_LIFETIME=6h WC_GRID_DISK=10GB
           SPECS=("mc-cv 1" "mc-nuecc 1" "beam-off 1" "run3bnb 1" "opendata 1"); LIST=recover-%s.tsv; SUF=-mem8g ;;
  recover-full) export WC_GRID_MODE=full WC_GRID_MEMORY=8000MB WC_GRID_LIFETIME=8h WC_GRID_DISK=15GB
           SPECS=("mc-cv 1" "mc-nuecc 1" "beam-off 1" "run3bnb 1" "opendata 1"); LIST=recover-full-%s.tsv; SUF=-mem8g ;;
  recover-slow) export WC_GRID_MODE=step2 WC_GRID_MEMORY=8000MB WC_GRID_LIFETIME=12h WC_GRID_DISK=10GB WC_TIMEOUT_STEP2_BASE=14400
           SPECS=("mc-cv 1" "mc-nuecc 1" "beam-off 1" "run3bnb 1" "opendata 1"); LIST=recover-slow-%s.tsv; SUF=-mem8g ;;
  *) echo "unknown $WHAT" >&2; exit 2 ;;
esac
for s in "${SPECS[@]}"; do
  set -- $s; f=$R/lists/$(printf "$LIST" "$1")
  [ -f "$f" ] && [ "$(grep -vc '^#' "$f")" -gt 0 ] || { echo "== $1$SUF: no pairs ($f)"; continue; }
  echo "== $1$SUF ($WHAT, $(grep -vc '^#' "$f") pairs, $2 per job, $WC_GRID_MEMORY)"
  bin/submit.sh "$TARBALL" "$f" "$2" "$1$SUF" WCLocal2026Nov16 $DRY 2>&1 | grep -E "submitted to cluster|Use job id|^20|rror"
done
