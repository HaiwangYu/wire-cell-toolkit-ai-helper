#!/bin/bash
# Config gates for the SBND 2-step split (issue 33, M2).  Run INSIDE SL7 with setup-aurora-ap.sh sourced:
#   SL7_SETUP=$S29/setup-aurora-ap.sh $S29/in-aurora-sl7.sh $S33/gate-2step-cfg.sh <outdir> [<git ref of the pre-split cfg, default HEAD>]
#
#  G-A  the 1-step jobs (obsolete/wcls-img-clus-matching-pr-{flash,hits}.jsonnet; before 2026-09-30
#       wcls-img-clus-matching-xin{,-hits}.jsonnet -- the pre tree is compiled under whichever name it has) compile
#       BYTE-IDENTICAL to <ref> (its whole cfg/ tree extracted and put FIRST on WIRECELL_PATH),
#       sim and data extVar sets -- or, against a <ref> from before M3, differ ONLY by the
#       attacher swap (gate-1step-attacher.py);
#  G-B  step 1 (wcls-img-clus-matching.jsonnet) = the hits 1-step minus the PR tail: every shared
#       component identical; only-in-1step = the PR-side components; only-in-step1 = TensorFileSink:ql_pctree;
#  G-C  step 2 (wct-pr.jsonnet, --tla-str reality=sim|data) builds the PR MABC and every component it
#       reaches identically to the 1-step's, up to output file names and the Bee sink.
set -u
OUT=${1:?outdir}; REF=${2:-HEAD}
Y=/lus/flare/projects/neutrinoGPU/yuhw
WCT_SRC=${WCT_SRC:-$Y/wire-cell-toolkit}
rm -rf "$OUT"; mkdir -p "$OUT/pre"
(cd $WCT_SRC && git archive "$REF" cfg) | tar -x -C "$OUT/pre" || { echo "cannot extract $REF:cfg"; exit 2; }
echo "pre cfg from $REF ($(cd $WCT_SRC && git rev-parse --short $REF)); work tree $(cd $WCT_SRC && git status --short cfg | wc -l) changed/new cfg files"
common=(--ext-str enable_tracking_root=true --ext-str enable_nugraph_h5=true --ext-str pr_operating_point=sync
        --ext-code 'trace_tags=["gauss", "wiener"]' --ext-code 'output_mask_tags=["bad"]'
        --ext-str opflash0_input_label=opflashtpc0: --ext-str opflash1_input_label=opflashtpc1:
        --ext-str ophit0_input_label=ophitpmt --ext-str ophit1_input_label=ophitpmt)
sim=(--ext-str reality=sim --ext-code 'recobwire_tags=["simtpc2d:dnnsp", "simtpc2d:dnnsp"]'
     --ext-code 'summary_tags=["", "simtpc2d:wienersummary"]' --ext-code 'input_mask_tags=["simtpc2d:badmasks"]')
data=(--ext-str reality=data --ext-code 'recobwire_tags=["sptpc2d:dnnsp", "sptpc2d:dnnsp"]'
      --ext-code 'summary_tags=["", "sptpc2d:wienersummary"]' --ext-code 'input_mask_tags=["sptpc2d:badmasks"]')
J=pgrapher/experiment/sbnd
rc=0
for real in sim data; do
  if [ $real = sim ]; then ev=("${sim[@]}"); else ev=("${data[@]}"); fi
  for job in flash hits; do
    new=$J/obsolete/wcls-img-clus-matching-pr-$job.jsonnet
    old=$J/wcls-img-clus-matching-xin$([ $job = hits ] && echo -hits).jsonnet
    pre=$new; [ -f $OUT/pre/cfg/$new ] || pre=$old     # a <ref> from before the 2026-09-30 rename
    WIRECELL_PATH=$OUT/pre/cfg:$WIRECELL_PATH wcsonnet "${common[@]}" "${ev[@]}" $pre > $OUT/pre-$job-$real.json 2> $OUT/pre-$job-$real.err || { echo "G-A $real $job: pre compile FAILED"; tail -3 $OUT/pre-$job-$real.err; rc=1; continue; }
    WIRECELL_PATH=$WCT_SRC/cfg:$WIRECELL_PATH wcsonnet "${common[@]}" "${ev[@]}" $new > $OUT/new-$job-$real.json 2> $OUT/new-$job-$real.err || { echo "G-A $real $job: new compile FAILED"; tail -3 $OUT/new-$job-$real.err; rc=1; continue; }
    if cmp -s $OUT/pre-$job-$real.json $OUT/new-$job-$real.json; then echo "G-A $real $job: PASS byte-identical ($(md5sum < $OUT/new-$job-$real.json | cut -c1-12), $(wc -c < $OUT/new-$job-$real.json) bytes)"
    else python3 $(dirname $0)/gate-1step-attacher.py $OUT/pre-$job-$real.json $OUT/new-$job-$real.json "$real $job" || { diff <(python3 -m json.tool $OUT/pre-$job-$real.json) <(python3 -m json.tool $OUT/new-$job-$real.json) | head -20; rc=1; }; fi
  done
  WIRECELL_PATH=$WCT_SRC/cfg:$WIRECELL_PATH wcsonnet "${common[@]}" "${ev[@]}" $J/wcls-img-clus-matching.jsonnet > $OUT/step1-$real.json 2> $OUT/step1-$real.err || { echo "G-B $real: step-1 compile FAILED"; tail -3 $OUT/step1-$real.err; rc=1; }
  WIRECELL_PATH=$WCT_SRC/cfg:$WIRECELL_PATH wcsonnet --tla-str reality=$real $J/wct-pr.jsonnet > $OUT/step2-$real.json 2> $OUT/step2-$real.err || { echo "G-C $real: step-2 compile FAILED"; tail -3 $OUT/step2-$real.err; rc=1; }
  python3 $(dirname $0)/gate-2step-compare.py $OUT/new-hits-$real.json $OUT/step1-$real.json $OUT/step2-$real.json $real || rc=1
done
echo "GATE_2STEP_CFG_RC=$rc"; exit $rc
