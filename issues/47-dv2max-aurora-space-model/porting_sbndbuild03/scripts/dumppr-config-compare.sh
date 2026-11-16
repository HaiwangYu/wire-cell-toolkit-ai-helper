#!/bin/bash
# Issue 47 task B gate 1: compiled configs of the dump-PR branch (sbnd-dlvtx-space-pr) vs master, knob OFF.
#   dumppr-config-compare.sh <branch cfg dir> <master cfg dir> <outdir>     (wcsonnet + python3 on PATH)
# Step 2 (wct-pr.jsonnet, production arguments, sim and data, vertex_method default / original), and step 1
# (wcls-img-clus-matching.jsonnet, sim and data): branch must equal master.  Then knob ON (dl_vtx_dump_space=true):
# lists the keys that differ from knob off (expected: only the SbndPrMagnifyTrackingVisitor space_* keys).
# JSON normalised (sort_keys) before comparing.
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
  for VM in dv2_split_move original; do
    c s2_${R}_${VM}_new $NEW wct-pr.jsonnet "${S2[@]}" -A vertex_method=$VM
    c s2_${R}_${VM}_old $OLD wct-pr.jsonnet "${S2[@]}" -A vertex_method=$VM
    a=$(norm $O/s2_${R}_${VM}_new.json); b=$(norm $O/s2_${R}_${VM}_old.json)
    echo "off s2 $R $VM branch $a master $b $([ "$a" = "$b" ] && echo EQUAL || echo DIFFER)"
  done
  c s1_${R}_new $NEW wcls-img-clus-matching.jsonnet -V reality=$R "${WCLS[@]}"
  c s1_${R}_old $OLD wcls-img-clus-matching.jsonnet -V reality=$R "${WCLS[@]}"
  a=$(norm $O/s1_${R}_new.json); b=$(norm $O/s1_${R}_old.json)
  echo "off s1 $R branch $a master $b $([ "$a" = "$b" ] && echo EQUAL || echo DIFFER)"
  c s2_${R}_on $NEW wct-pr.jsonnet "${S2[@]}" -S dl_vtx_dump_space=true
  python3 - $O/s2_${R}_dv2_split_move_new.json $O/s2_${R}_on.json $R <<'EOF'
import json, sys
off, on = (json.load(open(f)) for f in sys.argv[1:3])
def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from flat(v, f"{p}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from flat(v, f"{p}[{i}]")
    else: yield p, o
a, b = dict(flat(off)), dict(flat(on))
d = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
print(f"on  s2 {sys.argv[3]}: {len(d)} leaf keys differ from off:", ", ".join(k.split("/")[-1] if "[" not in k.split("/")[-1] else k.split("/")[-2] + "/" + k.split("/")[-1] for k in d))
EOF
done
