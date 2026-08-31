#!/bin/bash
# Run Xin's canonical 2-step chain on one event, from a reco1 artROOT file.
#
#   ./run-twostep.sh <file> <nskip> <run> <subrun> <event> <outdir>
#
# Three stages, because "2-step" is really imaging + (clus/QL) + PR:
#   A  LArSoft dumps this event's imaging clusters and opflash into WCT-native
#      files (wcls-img-dump.fcl -> icluster-apa*.npz,
#      wcls-flash-dump.fcl -> opflash_apa*.tar.gz)
#   B  wct-clus-matching-perevt.jsonnet: clustering + Q/L matching + all-APA,
#      writing the pctree tarball
#   C  wct-pr-perevt.jsonnet: the PR chain, writing tracking-pr.root
#
# Stages B and C are the IN-TREE canonical jsonnets -- the same files compiled
# for the issue-17 audit -- not sbnd_xin's shell drivers, which hardcode
# /nfs/data/1/xqian/toolkit-dev and expect pre-made dumps in Xin's layout.
# Nothing under sbnd_xin is read or modified.
FILE="$1"; NSKIP="$2"; RUN="$3"; SUB="$4"; EVT="$5"; OUT="$6"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-dlvtx.sh >/dev/null 2>&1
set -o pipefail
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/standalone-sample:/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p "$OUT"; cd "$OUT" || exit 1

PIPE="switch_scope,unmerge_bundle,unmerge_assoc,steiner,fiducialutils,tagger_check_tgm,tagger_check_stm,tagger_check_fc,protect_bundle,steiner_refresh,tagger_check_neutrino,numu_bdt_scorer,nue_bdt_scorer,tracking_visitor,tagger_output"
PIPE_TLA="pipeline_names=[$(echo "$PIPE" | sed "s/[^,]\+/'&'/g")]"

echo "== A1 img dump"
timeout -k 60 1800 lar -n 1 --nskip "$NSKIP" -c wcls-img-dump.fcl -s "$FILE" --no-output > A1-img-dump.log 2>&1 \
  || { echo "  A1 FAILED rc=$?"; tail -5 A1-img-dump.log; exit 11; }
echo "== A2 flash dump"
timeout -k 60 1800 lar -n 1 --nskip "$NSKIP" -c wcls-flash-dump.fcl -s "$FILE" --no-output > A2-flash-dump.log 2>&1 \
  || { echo "  A2 FAILED rc=$?"; tail -5 A2-flash-dump.log; exit 12; }
for f in icluster-apa0-active.npz icluster-apa0-masked.npz icluster-apa1-active.npz icluster-apa1-masked.npz \
         opflash_apa0.tar.gz opflash_apa1.tar.gz; do
    [ -s "$f" ] || { echo "  stage A did not produce $f"; exit 13; }
done

echo "== B clus + Q/L matching"
timeout -k 60 3600 wire-cell -c pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet \
    --tla-str input="$OUT" --tla-code anode_indices='[0,1]' \
    --tla-str output_dir="$OUT" \
    --tla-code run="$RUN" --tla-code subrun="$SUB" --tla-code event="$EVT" \
    --tla-str reality=sim \
    --tla-str save_tensors="$OUT/pctree.tar.gz" > B-clus-ql.log 2>&1 \
  || { echo "  B FAILED rc=$?"; tail -8 B-clus-ql.log; exit 21; }
[ -s pctree.tar.gz ] || { echo "  B produced no pctree.tar.gz"; exit 22; }

echo "== C pattern recognition"
timeout -k 60 3600 wire-cell -c pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet \
    --tla-str input="$OUT/pctree.tar.gz" --tla-code anode_indices='[0,1]' \
    --tla-str output_dir="$OUT" \
    --tla-code run="$RUN" --tla-code subrun="$SUB" --tla-code event="$EVT" \
    --tla-str reality=sim \
    --tla-code "$PIPE_TLA" > C-pr.log 2>&1 \
  || { echo "  C FAILED rc=$?"; tail -8 C-pr.log; exit 31; }
[ -s tracking-pr.root ] && echo "  OK tracking-pr.root $(stat -c %s tracking-pr.root) bytes" \
                        || { echo "  C produced no tracking-pr.root"; exit 32; }
