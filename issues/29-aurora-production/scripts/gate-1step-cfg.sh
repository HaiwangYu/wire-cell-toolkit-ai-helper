#!/bin/bash
# Config gates for the split of the SBND 1-step job into
#   wcls-img-clus-matching-xin-lib.jsonnet (function) + two top-level jobs
# (issue 32, doc sbnd_xin/123 sec 16).  Run INSIDE SL7 with setup-aurora-ap.sh sourced:
#   SL7_SETUP=$S/setup-aurora-ap.sh $S/in-aurora-sl7.sh $S/gate-1step-cfg.sh <outdir> [<git ref of the pre-split tree, default origin/master>]
#
#  G-A  the reco1-flash job compiles BYTE-IDENTICAL to the pre-split monolithic file
#       (the pre-split file is taken from <ref> with `git show` into a scratch cfg dir
#       that is put FIRST on WIRECELL_PATH), for the sim and the data extVar sets;
#  G-B  the hit-flash job compiles, and differs from the reco1 job ONLY in the light
#       nodes (wclsOpHitSource/SBNDOpFlashFinder in, wclsOpFlashSource out), the
#       QLMatching xtpc_sc1_* keys and the plugin list.
set -u
OUT=${1:?outdir}; REF=${2:-origin/master}
Y=/lus/flare/projects/neutrinoGPU/yuhw
WCT_SRC=${WCT_SRC:-$Y/wire-cell-toolkit}
mkdir -p "$OUT/pre/pgrapher/experiment/sbnd"
J=cfg/pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet
(cd $WCT_SRC && git show "$REF:$J") > "$OUT/pre/pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet" || { echo "cannot git show $REF:$J"; exit 2; }
echo "pre-split file from $REF: $(md5sum < $OUT/pre/pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet | cut -c1-8), $(wc -l < $OUT/pre/pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet) lines; new tree $(cd $WCT_SRC && git rev-parse --short HEAD)"

# The fcl's extVar sets (wcls-img-clus-matching-xin.fcl / -data.fcl), as compile-both does.
common=(--ext-str enable_tracking_root=true --ext-str enable_nugraph_h5=true --ext-str pr_operating_point=sync
        --ext-code 'trace_tags=["gauss", "wiener"]' --ext-code 'output_mask_tags=["bad"]'
        --ext-str opflash0_input_label=opflashtpc0: --ext-str opflash1_input_label=opflashtpc1:
        --ext-str ophit0_input_label=ophitpmt --ext-str ophit1_input_label=ophitpmt)
sim=(--ext-str reality=sim --ext-code 'recobwire_tags=["simtpc2d:dnnsp", "simtpc2d:dnnsp"]'
     --ext-code 'summary_tags=["", "simtpc2d:wienersummary"]' --ext-code 'input_mask_tags=["simtpc2d:badmasks"]')
data=(--ext-str reality=data --ext-code 'recobwire_tags=["sptpc2d:dnnsp", "sptpc2d:dnnsp"]'
      --ext-code 'summary_tags=["", "sptpc2d:wienersummary"]' --ext-code 'input_mask_tags=["sptpc2d:badmasks"]')

rc=0
for real in sim data; do
  if [ $real = sim ]; then ev=("${sim[@]}"); else ev=("${data[@]}"); fi
  WIRECELL_PATH=$OUT/pre:$WIRECELL_PATH wcsonnet "${common[@]}" "${ev[@]}" pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet > $OUT/pre-$real.json 2> $OUT/pre-$real.err || { echo "G-A $real: pre-split compile FAILED"; tail -3 $OUT/pre-$real.err; rc=1; continue; }
  wcsonnet "${common[@]}" "${ev[@]}" pgrapher/experiment/sbnd/wcls-img-clus-matching-xin.jsonnet > $OUT/new-$real.json 2> $OUT/new-$real.err || { echo "G-A $real: new reco1 compile FAILED"; tail -3 $OUT/new-$real.err; rc=1; continue; }
  if cmp -s $OUT/pre-$real.json $OUT/new-$real.json; then echo "G-A $real: PASS byte-identical ($(md5sum < $OUT/new-$real.json | cut -c1-12), $(wc -c < $OUT/new-$real.json) bytes)"; else echo "G-A $real: FAIL differs"; diff <(python3 -m json.tool $OUT/pre-$real.json) <(python3 -m json.tool $OUT/new-$real.json) | head -20; rc=1; fi
  wcsonnet "${common[@]}" "${ev[@]}" pgrapher/experiment/sbnd/wcls-img-clus-matching-xin-hits.jsonnet > $OUT/hits-$real.json 2> $OUT/hits-$real.err || { echo "G-B $real: hits compile FAILED"; tail -3 $OUT/hits-$real.err; rc=1; continue; }
  python3 - $OUT/new-$real.json $OUT/hits-$real.json $real <<'PY'
import json, sys
a, b, real = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
def idx(c): return {(x.get('type'), x.get('name')): x for x in c}
ia, ib = idx(a), idx(b)
only_a = sorted(k for k in ia if k not in ib); only_b = sorted(k for k in ib if k not in ia)
diffs = []
for k in sorted(set(ia) & set(ib)):
    if ia[k] != ib[k]:
        da, db = ia[k].get('data', {}), ib[k].get('data', {})
        keys = sorted(kk for kk in set(da) | set(db) if da.get(kk) != db.get(kk))
        diffs.append((k, keys))
print(f"G-B {real}: reco1 {len(a)} vs hits {len(b)} components; only reco1: {only_a}; only hits: {only_b}")
for k, keys in diffs: print(f"   {k[0]}:{k[1]} differs in {keys}")
exp_only_a = {('wclsOpFlashSource', 'tpc0'), ('wclsOpFlashSource', 'tpc1')}
exp_only_b = {('wclsOpHitSource', 'tpc0'), ('wclsOpHitSource', 'tpc1'), ('SBNDOpFlashFinder', 'tpc0'), ('SBNDOpFlashFinder', 'tpc1')}
ok = set(only_a) == exp_only_a and set(only_b) == exp_only_b
for k, keys in diffs:
    if k == ('QLMatching', 'matching_joint') and set(keys) == {'xtpc_sc1_light_gate', 'xtpc_sc1_overpred_max'}: continue
    if k == ('wire-cell', None) and keys == ['plugins']: continue
    if k == ('Pgrapher', None) and keys == ['edges']: continue
    ok = False; print(f"   UNEXPECTED difference: {k} {keys}")
ql = ib[('QLMatching', 'matching_joint')]['data']
print(f"   hits QLMatching: xtpc_sc1_light_gate={ql.get('xtpc_sc1_light_gate')} xtpc_sc1_overpred_max={ql.get('xtpc_sc1_overpred_max')}")
print(f"G-B {real}: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
  [ $? -eq 0 ] || rc=1
done
echo "GATE_1STEP_CFG_RC=$rc"; exit $rc
