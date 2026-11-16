#!/bin/bash
# Issue 48 P2 (+ the P3 two-pass test): step 1 + both step-2 passes + the two-tree merge + validation, with the
# 0.38.0 release, on the P2 pairs (pick-p2-pairs.py).  WC_KEEP=all (the step-1 tars are compared afterwards).
#   run-p2.sh <pairs.tsv> <workdir>
export WC_DAY_MAXPAR=${WC_DAY_MAXPAR:-12}
# the pool waits for a valid Kerberos ticket (WC_KRB_WAIT): use the newest cache
export KRB5CCNAME=${KRB5CCNAME_P2:-$KRB5CCNAME}
source /exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/porting_sbndbuild03/scripts/site-wcl-sbndbuild03.sh
export WC_KEEP=all WC_STAMP_INPUT_FILE=1
export WC_STEP2_PASSES="pr:dv2_split_move:space:/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/schema/recTreeWireCell-dlvtx-space.schema.json pr-dv2snap:dv2_snap:nospace:/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/schema/recTreeWireCell.schema.json"
exec /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/bin/run-pairs.sh /exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/porting_sbndbuild03/scripts/site-wcl-sbndbuild03.sh "$1" "$2" /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/schema/recTreeWireCell-dlvtx-space.schema.json
