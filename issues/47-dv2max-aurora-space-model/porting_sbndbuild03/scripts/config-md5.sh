#!/bin/bash
# Issue 47 P1: md5 of the compiled SBND step-2 config (wct-pr.jsonnet) of the test branch, r7_cloud vs aurora_space.
#   config-md5.sh <wct source tree at dv2max-aurora-space-test>     (needs wcsonnet + python3 on PATH)
# WIRECELL_PATH = the tree's cfg only (machine-independent); the step-2 TLAs of aurora/bin/step2.sh for MC
# (input qlpctree.tar.gz, reality sim, evt_subdir '', dl_vtx_dump true, dl_vtx_dump_space true, flat_tree true,
# truth_match true), vertex_method dv2_split_move and dv2_bundle explicit.  The JSON is normalised before the md5
# (json.dumps sort_keys, separators (',', ':')), so go-jsonnet vs C++ jsonnet formatting does not matter.
SRC=${1:?wct source tree}
for B in r7_cloud aurora_space; do
  WIRECELL_PATH=$SRC/cfg wcsonnet -P $SRC/cfg \
    -A input=qlpctree.tar.gz -A reality=sim -A evt_subdir= -A vertex_method=dv2_split_move \
    -A dv2_bundle=dv2max/sbnd/$B/bundle.json \
    -S dl_vtx_dump=true -S dl_vtx_dump_space=true -S flat_tree=true -S truth_match=true \
    $SRC/cfg/pgrapher/experiment/sbnd/wct-pr.jsonnet > /tmp/cfgmd5.$$.json || { echo "$B: wcsonnet failed"; exit 1; }
  echo "$B $(python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")).encode()).hexdigest())' /tmp/cfgmd5.$$.json) $(grep -o '"dv2_bundle[^,]*' /tmp/cfgmd5.$$.json | tr '\n' ' ')"
done
rm -f /tmp/cfgmd5.$$.json
