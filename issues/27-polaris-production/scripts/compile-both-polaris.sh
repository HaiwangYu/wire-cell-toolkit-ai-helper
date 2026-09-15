#!/bin/bash
# Polaris port of issues/17-pr-operating-point-drift/scripts/compile-both.sh:
# compile our 1-step chain and Xin's two 2-step steps to JSON and diff the PR
# operating point (gate: zero unexpected differences).  Only the environment
# lines differ from the FNAL original; the method trap (production
# pipeline_names TLA for step 2) is kept verbatim.
#
#   in-polaris-sl7.sh ... : run this INSIDE SL7 with setup-polaris-ap.sh sourced, e.g.
#   SL7_SETUP=$S/setup-polaris-ap.sh $S/in-polaris-sl7.sh $S/compile-both-polaris.sh <outdir>
OUT="${1:-./compiled}"
mkdir -p "$OUT"
HERE="$(cd "$(dirname "$0")" && pwd)"
I17=$HERE/../../17-pr-operating-point-drift/scripts
set -o pipefail
cd "${WCP_SBND:-/lus/eagle/projects/neutrinoGPU/yuhw/wcp-porting-validation/sbnd}" || exit 1

PIPELINE="switch_scope,unmerge_bundle,unmerge_assoc,steiner,fiducialutils,tagger_check_tgm,tagger_check_stm,tagger_check_fc,protect_bundle,steiner_refresh,tagger_check_neutrino,numu_bdt_scorer,nue_bdt_scorer,tracking_visitor,tagger_output"
PIPE_TLA="pipeline_names=[$(echo "$PIPELINE" | sed "s/[^,]\+/'&'/g")]"

wcsonnet \
  --ext-str reality=sim \
  --ext-str enable_tracking_root=true \
  --ext-str enable_nugraph_h5=true \
  --ext-str "pr_operating_point=${PR_OP:-sync}" \
  --ext-code 'recobwire_tags=["simtpc2d:dnnsp", "simtpc2d:dnnsp"]' \
  --ext-code 'trace_tags=["gauss", "wiener"]' \
  --ext-code 'summary_tags=["", "simtpc2d:wienersummary"]' \
  --ext-code 'input_mask_tags=["simtpc2d:badmasks"]' \
  --ext-code 'output_mask_tags=["bad"]' \
  --ext-str opflash0_input_label=opflashtpc0: \
  --ext-str opflash1_input_label=opflashtpc1: \
  wcls-img-clus-matching-xin.jsonnet > "$OUT/onestep.json" || { echo "1-step compile FAILED"; exit 1; }

wcsonnet pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet \
    > "$OUT/xin-step1.json" || { echo "step1 compile FAILED"; exit 1; }
wcsonnet --tla-code "$PIPE_TLA" pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet \
    > "$OUT/xin-step2.json" || { echo "step2 compile FAILED"; exit 1; }

python3 - "$OUT" <<'PY'
import json, sys
o = sys.argv[1]
merged = json.load(open(o + '/xin-step1.json')) + json.load(open(o + '/xin-step2.json'))
json.dump(merged, open(o + '/xin-both.json', 'w'))
print("wrote xin-both.json (%d components)" % len(merged))
PY

exec python3 "$I17/audit-config-diff.py" \
    "$OUT/onestep.json" "$OUT/xin-both.json" \
    --label-a 1-step --label-b Xin \
    --skip-type Pgrapher --skip-type wire-cell \
    --expected-key bee_sink --expected-key rse_from_ident \
    --expected-key rse_from_metadata --expected-key save_deadarea \
    --expected-key bee_points_sets --expected-key bee_pf \
    --expected-key dump_mode
