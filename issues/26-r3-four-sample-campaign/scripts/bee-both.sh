#!/bin/bash
# bee-both.sh <spotdir> <tag> : build + upload both chains' Bee sets for a spot check, same event order
P=$1; TAG=$2; U=$P/bee-upload; rm -rf $U; mkdir -p $U/evtdirs; S=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues
: > $U/bee-order.txt; k=0; DIRS=""; CZ=""
for e in $(ls -d $P/work-Bpr/pr_evt* | sed 's/.*pr_evt//' | sort -n); do
  d=$U/evtdirs/evt$e; mkdir -p $d
  ln -s $P/work-B/ql_evt$e/mabc-apa0-face0.zip $P/work-B/ql_evt$e/mabc-apa1-face0.zip $P/work-B/ql_evt$e/mabc-all-apa.zip $P/work-Bpr/pr_evt$e/mabc-pr.zip $d/
  cz=$(ls $P/run-C/bee/bee_r*_e$e.zip); rse=$(basename $cz .zip | sed 's/bee_//')
  echo "$k $e $rse" >> $U/bee-order.txt; DIRS="$DIRS $d"; CZ="$CZ $cz"; k=$((k+1))
done
python3 $S/20-campaign-summary/scripts/merge_twostep_bee.py $U/bee-xin2step-$TAG.zip $DIRS | tail -1
python3 $S/18-data-1000evt-beamon-beamoff/scripts/merge_bee.py $U/bee-ours-chainC-$TAG.zip $CZ | tail -1
cd $U; for z in bee-xin2step-$TAG.zip bee-ours-chainC-$TAG.zip; do echo "$z $(bash /exp/sbnd/app/users/yuhw/wcp-porting-img/upload-to-bee.sh $z 2>&1 | tail -1)"; done
