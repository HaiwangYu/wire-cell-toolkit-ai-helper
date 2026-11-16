#!/bin/bash
# ai-helper #48 P0: md5 of the compiled SBND step-2 config (wct-pr.jsonnet) for both modes, porting's #47 recipe
# (WIRECELL_PATH = the tree's cfg only; JSON normalised: sort_keys, separators (',',':')).
#   config-md5.sh <wct source tree>      (wcsonnet + python3 on PATH)
SRC=${1:?wct source tree}; T=$(mktemp)
run() { local name=$1; shift
  WIRECELL_PATH=$SRC/cfg wcsonnet -P $SRC/cfg -A input=qlpctree.tar.gz -A reality=sim -A evt_subdir= \
    -S dl_vtx_dump=true -S flat_tree=true -S truth_match=true "$@" \
    $SRC/cfg/pgrapher/experiment/sbnd/wct-pr.jsonnet > $T || { echo "$name: wcsonnet failed"; return; }
  echo "$name $(python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")).encode()).hexdigest())' $T)"
}
B=dv2max/sbnd/aurora_space/bundle.json
run split_move_space   -A vertex_method=dv2_split_move -A dv2_bundle=$B -S dl_vtx_dump_space=true
run snap_nospace       -A vertex_method=dv2_snap       -A dv2_bundle=$B -S dl_vtx_dump_space=false
run snap_space         -A vertex_method=dv2_snap       -A dv2_bundle=$B -S dl_vtx_dump_space=true
run default_space      -S dl_vtx_dump_space=true
rm -f $T
