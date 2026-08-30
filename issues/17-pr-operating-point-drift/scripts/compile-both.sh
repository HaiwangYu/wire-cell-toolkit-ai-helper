#!/bin/bash
# Compile our 1-step chain and Xin's two 2-step steps to JSON, then diff the PR
# operating point.  This is the verification gate for issue 17: after the fix,
# the clus_pr / TaggerCheckNeutrino / Tagger* / Clustering* diff must be ZERO.
#
#   ./compile-both.sh [outdir]
#
# METHOD TRAP, do not remove: the 2-step MUST be compiled with the production
# pipeline_names TLA that run_pr_chain_batch*.sh passes.  Its in-signature
# default (wct-pr-perevt.jsonnet:101) is the 10-stage pre-adoption list, so
# compiling bare defaults reports a phantom 10-vs-15 stage difference that does
# not exist in either real chain.  The first pass of this audit fell into it.
OUT="${1:-./compiled}"
mkdir -p "$OUT"
# Sources FIRST, and `set -u` only afterwards: the ups/mrb setup scripts read
# unset variables and return non-zero, so `set -u` before them kills the script
# silently (empty output, no error) -- which is exactly what happened the first
# time this was run.
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
set -o pipefail
cd /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd || exit 1

PIPELINE="switch_scope,unmerge_bundle,unmerge_assoc,steiner,fiducialutils,tagger_check_tgm,tagger_check_stm,tagger_check_fc,protect_bundle,steiner_refresh,tagger_check_neutrino,numu_bdt_scorer,nue_bdt_scorer,tracking_visitor,tagger_output"
PIPE_TLA="pipeline_names=[$(echo "$PIPELINE" | sed "s/[^,]\+/'&'/g")]"

# --- our 1-step.  extVars mirror wcls-img-clus-matching-xin.fcl's params/structs.
wcsonnet \
  --ext-str reality=sim \
  --ext-str enable_tracking_root=true \
  --ext-str "pr_operating_point=${PR_OP:-sync}" \
  --ext-code 'recobwire_tags=["simtpc2d:dnnsp", "simtpc2d:dnnsp"]' \
  --ext-code 'trace_tags=["gauss", "wiener"]' \
  --ext-code 'summary_tags=["", "simtpc2d:wienersummary"]' \
  --ext-code 'input_mask_tags=["simtpc2d:badmasks"]' \
  --ext-code 'output_mask_tags=["bad"]' \
  --ext-str opflash0_input_label=opflashtpc0: \
  --ext-str opflash1_input_label=opflashtpc1: \
  wcls-img-clus-matching-xin.jsonnet > "$OUT/onestep.json" || { echo "1-step compile FAILED"; exit 1; }

# --- Xin's 2-step, step 1 (img/clus/match) and step 2 (PR), production pipeline.
wcsonnet pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet \
    > "$OUT/xin-step1.json" || { echo "step1 compile FAILED"; exit 1; }
wcsonnet --tla-code "$PIPE_TLA" pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet \
    > "$OUT/xin-step2.json" || { echo "step2 compile FAILED"; exit 1; }

# Xin's two steps are one operating point split across two jobs; merge for the diff.
python3 - "$OUT" <<'PY'
import json, sys
o = sys.argv[1]
merged = json.load(open(o + '/xin-step1.json')) + json.load(open(o + '/xin-step2.json'))
json.dump(merged, open(o + '/xin-both.json', 'w'))
print("wrote xin-both.json (%d components)" % len(merged))
PY

# Pgrapher edges and the wire-cell plugin list differ by construction (different
# graphs); they are not operating-point knobs.
# Deliberate 1-step design differences (issue 13), NOT operating-point knobs:
#   bee_sink / save_deadarea / bee_points_sets / bee_pf -- one shared Bee zip
#     (G4/G5): the PR node writes into the same zip under renamed sets, and only
#     one node may write dead area or the entries duplicate.
#   rse_from_ident / rse_from_metadata -- run/subrun/event plumbing (G3), which
#     the standalone 2-step gets from its own TLAs instead.
#   dump_mode -- the 1-step has no pctree handoff to dump; the 2-step needs one.
# Everything else must be identical, so the exit status is a real gate.
exec python3 "$(dirname "$0")/audit-config-diff.py" \
    "$OUT/onestep.json" "$OUT/xin-both.json" \
    --label-a 1-step --label-b Xin \
    --skip-type Pgrapher --skip-type wire-cell \
    --expected-key bee_sink --expected-key rse_from_ident \
    --expected-key rse_from_metadata --expected-key save_deadarea \
    --expected-key bee_points_sets --expected-key bee_pf \
    --expected-key dump_mode
