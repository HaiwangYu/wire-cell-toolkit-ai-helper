#!/bin/bash
# Issue 48 P0: md5 of the compiled step-2 configuration (wct-pr.jsonnet) of the two production passes.
#   config-md5.sh <wct source tree>          (needs wcsonnet + python3 on PATH: run inside the release setup)
# WIRECELL_PATH = the tree's cfg only, so the md5 does not depend on the machine.  The JSON is normalised
# (sort_keys, separators (',', ':')) before the md5.  TLAs as aurora/bin/step2.sh passes them in production:
#   input qlpctree.tar.gz, evt_subdir 'pr_evt{run}_{subrun}_{event}', dl_vtx_dump true, flat_tree true,
#   truth_match = (reality == sim), dv2_bundle dv2max/sbnd/aurora_space/bundle.json, and
#   split  : vertex_method dv2_split_move, dl_vtx_dump_space true
#   snap   : vertex_method dv2_snap,       dl_vtx_dump_space false
#   default: no vertex_method / dv2_bundle TLA (master's default), dl_vtx_dump_space true -- must equal split
SRC=${1:?wct source tree}; T=$(mktemp)
md5() { python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")).encode()).hexdigest())' "$1"; }
for R in sim data; do
  TM=false; [ $R = sim ] && TM=true
  for M in split snap default; do
    case $M in
      split)   X=(-A vertex_method=dv2_split_move -A dv2_bundle=dv2max/sbnd/aurora_space/bundle.json -S dl_vtx_dump_space=true) ;;
      snap)    X=(-A vertex_method=dv2_snap       -A dv2_bundle=dv2max/sbnd/aurora_space/bundle.json -S dl_vtx_dump_space=false) ;;
      default) X=(-S dl_vtx_dump_space=true) ;;
    esac
    WIRECELL_PATH=$SRC/cfg wcsonnet -P $SRC/cfg -A input=qlpctree.tar.gz -A reality=$R -A 'evt_subdir=pr_evt{run}_{subrun}_{event}' \
      "${X[@]}" -S dl_vtx_dump=true -S flat_tree=true -S truth_match=$TM \
      $SRC/cfg/pgrapher/experiment/sbnd/wct-pr.jsonnet > $T || { echo "$R $M: wcsonnet failed"; continue; }
    echo "$R $M $(md5 $T) $(grep -oE '"(vertex_method|dv2_bundle|dl_vtx_dump_space)": *[^,}]*' $T | sort -u | tr '\n' ' ')"
  done
done
rm -f $T
