#!/bin/bash
# PR #543 re-review: does a broken DV2 setup fail the job now?  One small data input (7 events), dv2_split_move.
#   T1 lightgbm missing         -> configure error, rc != 0
#   T2 bundle.json edited       -> sha256 mismatch at configure, rc != 0
#   T3 dv2_bundle not found     -> configure error, rc != 0
#   T4 Python error in an event, default DV2_STRICT  -> job fails, rc != 0
#   T5 the same with DV2_STRICT=0                    -> job finishes, WARN, traditional vertex for that call
#   T6 original without lightgbm -> runs (the dv2 model is not loaded)
D=/exp/sbnd/data/users/yuhw/production-prep/pr543-review; V=$D/v2; T=$V/failtests; IN=$D/inputs/data--ncpi0-s0-7.qlpctree.tar.gz
rm -rf $T; mkdir -p $T/badbundle/dv2max/sbnd/r7_cloud
B=/exp/sbnd/app/users/yuhw/wire-cell-data/dv2max/sbnd/r7_cloud
for f in pass1.pt pass2.pt ranker_fold0.txt isotonic_fold0.json; do ln -s $B/$f $T/badbundle/dv2max/sbnd/r7_cloud/$f; done
cp $B/bundle.json $T/badbundle/dv2max/sbnd/r7_cloud/bundle.json; echo >> $T/badbundle/dv2max/sbnd/r7_cloud/bundle.json
run() {  # run <name> <vertex_method> <extra shell setup>
  local n=$1 vm=$2 extra=$3 XTLA=$4; mkdir -p $T/$n
  SL7_SETUP=$V/setup-pr543v2.sh /exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh bash -c "
    cd $T/$n; export OMP_NUM_THREADS=1 DV2_THREADS=1 DV2_HOOK_LOG=$T/$n/dv2-hook.jsonl; $extra
    timeout 3600 wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet --tla-str input=$IN --tla-str reality=data \
      --tla-str vertex_method=$vm $XTLA --tla-code dl_vtx_dump=true --tla-code flat_tree=true > wct.log 2>&1; echo \$? > rc" > $T/$n/run.out 2>&1
  echo "$n rc=$(cat $T/$n/rc) events=$(ls -d $T/$n/pr_evt* 2>/dev/null | wc -l) hook_calls=$(cat $T/$n/dv2-hook.jsonl 2>/dev/null | wc -l)"
  grep -m3 -E "cannot load DV2-MAX|sha256|not found on WIRECELL_PATH|DV2-MAX inference failed|no DV2-MAX prediction|DV2_Vertex: RuntimeError|injected|Error|FATAL" $T/$n/wct.log | cut -c1-400
}
NOLGBM='export PYTHONPATH=$(echo $PYTHONPATH | tr ":" "\n" | grep -v pyenv-dv2 | paste -sd:)'
run T1-nolightgbm dv2_split_move "$NOLGBM" &
run T2-badsha     dv2_split_move "export WIRECELL_PATH=$T/badbundle:\$WIRECELL_PATH" &
run T3-nobundle   dv2_split_move "" "--tla-str dv2_bundle=dv2max/sbnd/nope/bundle.json" &
run T4-fault-strict  dv2_split_move "export PYTHONPATH=$V/fault:\$PYTHONPATH DV2_FAULT_CALL=1" &
run T5-fault-strict0 dv2_split_move "export PYTHONPATH=$V/fault:\$PYTHONPATH DV2_FAULT_CALL=1 DV2_STRICT=0" &
run T6-original-nolgbm original "$NOLGBM" &
wait
