#!/bin/bash
# Phase-2 comparison of a Polaris smoke run against a FNAL run-harness output dir.
#   compare-to-fnal.sh <polaris-run-dir (has evtK/ + rse-by-nskip.tsv)> <fnal-run-dir (has run/tracking-pr/, run/bee/, bee-upload/bee-order.txt)>
# Builds <polaris>/cmp-fnal/{polaris-evt,fnal-arm,polaris-bee}, runs deep_compare.py
# (exact T_kine/T_tagger hash + every T_rec_charge point) and the branch-level
# census, merges the Polaris Bee zips in the FNAL bee-order, and uploads both
# sets.  ROOT parts run inside SL7 via in-polaris-sl7.sh; the upload runs on the host.
set -u
P=$1; F=$2
S=$(cd "$(dirname "$0")" && pwd)
AI=$S/../../..
[ -f $P/rse-by-nskip.tsv ] || $S/in-polaris-sl7.sh python3 $S/rse-by-nskip.py $P 2>&1 | grep -v CernVM-FS | tail -3
C=$P/cmp-fnal; rm -rf $C; mkdir -p $C/polaris-evt $C/fnal-arm $C/polaris-bee $P/bee-upload
while IFS=$'\t' read -r k run sub evt trees bytes; do
  [ "$k" = nskip ] && continue
  mkdir -p $C/polaris-evt/evt_$evt
  ln -sf $P/evt$k/tracking-pr.root $C/polaris-evt/evt_$evt/tracking-pr.root
  ln -sf $F/run/tracking-pr/tracking-pr_r${run}_s${sub}_e${evt}.root $C/fnal-arm/tracking-pr_$evt.root
  ln -sf $P/evt$k/mabc.zip $C/polaris-bee/bee_r${run}_s${sub}_e${evt}.zip
done < $P/rse-by-nskip.tsv
echo "events: $(ls $C/polaris-evt | wc -l); FNAL files resolving: $(find -L $C/fnal-arm -type f | wc -l)"
$S/in-polaris-sl7.sh bash -c "
  python3 $AI/issues/20-campaign-summary/scripts/deep_compare.py $C/polaris-evt $C/fnal-arm 'Polaris (W) vs FNAL (arm)' | tee $C/deep_compare.txt
  python3 $S/branch-diff-tracking-pr.py $C/polaris-evt $C/fnal-arm T_tagger T_kine T_cluster T_rec_charge Trun T_bad_ch T_proj T_proj_data | tee $C/branch_diff.txt
" 2>&1 | grep -v CernVM-FS
Z=""; while read -r i rse; do Z="$Z $C/polaris-bee/bee_$rse.zip"; done < $F/bee-upload/bee-order.txt
cp $F/bee-upload/bee-order.txt $P/bee-upload/
python3 $AI/issues/18-data-1000evt-beamon-beamoff/scripts/merge_bee.py $P/bee-upload/bee-polaris.zip $Z | tail -1
U=/lus/eagle/projects/neutrinoGPU/yuhw/wcp-porting-validation/upload-to-bee.sh
[ "$(ls $C/polaris-evt | wc -l)" -gt 0 ] || { echo "no events; not uploading"; exit 1; }
ZIPS="$P/bee-upload/bee-polaris.zip"; [ "${UPLOAD_FNAL:-0}" = 1 ] && ZIPS="$F/bee-upload/bee-*.zip $ZIPS"   # UPLOAD_FNAL=1 to (re)upload the FNAL set too
cd $P/bee-upload && for z in $ZIPS; do echo "$(basename $z) $(bash $U $z 2>&1 | tail -1)"; done | tee $P/bee-upload/bee-links.txt
