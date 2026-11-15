#!/bin/bash
# Issue 47 P5: compiled configs of PR #544 updated on master (5aa05cf1) vs the PR head before the update (b6278234).
#   p5-config-compare.sh <new cfg dir> <old cfg dir> <outdir>     (wcsonnet + python3 on PATH)
# Step 2 (wct-pr.jsonnet, production arguments, sim and data): new with vertex_method=original must equal old.
# Step 1 (wcls-img-clus-matching.jsonnet, sim and data): new must equal old.  JSON normalised before comparing.
NEW=${1:?}; OLD=${2:?}; O=${3:?}; mkdir -p $O
norm() { python3 -c 'import json,sys,hashlib; print(hashlib.md5(json.dumps(json.load(open(sys.argv[1])),sort_keys=True,separators=(",",":")).encode()).hexdigest())' $1; }
c() { local n=$1 d=$2 j=$3; shift 3; WIRECELL_PATH=$d wcsonnet -P $d "$@" $d/pgrapher/experiment/sbnd/$j > $O/$n.json 2> $O/$n.err || echo "$n FAILED"; }
WCLS=(-V recobwire_tags='["sptpc2d:gauss"]' -V trace_tags='["gauss"]' -V summary_tags='["wiener"]'
      -V input_mask_tags='["sptpc2d:badmasks"]' -V output_mask_tags='["bad"]' -V opflash0_input_label=opflashtpc0
      -V opflash1_input_label=opflashtpc1 -V enable_tracking_root=true)
for i in $(seq 0 9); do WCLS+=(-V ophit${i}_input_label=ophit$i); done
for R in sim data; do
  TM=false; [ $R = sim ] && TM=true
  S2=(-A input=qlpctree.tar.gz -A reality=$R -A evt_subdir= -S dl_vtx_dump=true -S flat_tree=true -S truth_match=$TM)
  c s2_${R}_new $NEW wct-pr.jsonnet "${S2[@]}" -A vertex_method=original
  c s2_${R}_old $OLD wct-pr.jsonnet "${S2[@]}"
  c s1_${R}_new $NEW wcls-img-clus-matching.jsonnet -V reality=$R "${WCLS[@]}"
  c s1_${R}_old $OLD wcls-img-clus-matching.jsonnet -V reality=$R "${WCLS[@]}"
  for s in s2 s1; do a=$(norm $O/${s}_${R}_new.json); b=$(norm $O/${s}_${R}_old.json); echo "$s $R new $a old $b $([ "$a" = "$b" ] && echo EQUAL || echo DIFFER)"; done
done
