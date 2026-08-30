#!/bin/bash
# 1-step img -> clus -> QL match -> tagger -> PR over a per-EVENT manifest.
#
#   ./run-harness.sh <manifest> <outdir> [nworkers] [cores-per-worker] [fcl]
#
# Data sibling of the issue-16 MC harness.  Two changes:
#
#  1. WORK IS DISTRIBUTED BY EVENT, NOT BY FILE.  The data samples are one
#     merged artROOT file of 1000 events, so a file cursor would give all the
#     work to one worker.  The manifest (make-manifest.sh) carries one line per
#     event with its RSE already resolved from EventAuxiliary, so workers just
#     pull line numbers and every output is named for its own event.
#  2. DATA FCL by default: wcls-img-clus-matching-xin-data.fcl, which sets
#     reality="data" and the sptpc2d product tags.  In data mode the labeler
#     emits an INPUT-ONLY nugraph (no truth labels) and no truth Bee layers.
#
# Everything else is deliberately identical to issue 16: one lar process per
# event in its own cwd (concurrent lar jobs otherwise collide on art's
# MemoryTracker/TFileService sqlite files), /usr/bin/time -v for peak RSS,
# per-event check-pr-run.sh audit, three deliverables named by RSE.
MANIFEST="$1"; OUT="$2"; NWORK="${3:-32}"; CORESPER="${4:-1}"
FCL="${5:-wcls-img-clus-matching-xin-data.fcl}"

source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
# DL (SCN) neutrino vertex.  Without it TaggerCheckNeutrino silently falls back
# to the geometric vertex; check-pr-run.sh audits for exactly that.
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-dlvtx.sh >/dev/null 2>&1
set -uo pipefail
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

NTASK=$(wc -l < "$MANIFEST")
CURSOR="$OUT/.cursor"; LOCK="$OUT/.cursor.lock"
mkdir -p "$OUT"/{work,logs,bee,tracking-pr,nugraph}
echo 1 > "$CURSOR"
SUMMARY="$OUT/summary.csv"
echo "task,event_idx,run,subrun,event,rc,wall_s,peak_rss_kb,bee_bytes,trackpr_bytes,nugraph_bytes,audit,rse_check,file" > "$SUMMARY"

next_task () {                        # atomic manifest-line handout
    local i
    exec 9>"$LOCK"; flock 9
    i=$(cat "$CURSOR"); echo $((i+1)) > "$CURSOR"
    flock -u 9; exec 9>&-
    echo "$i"
}

worker () {
    local wid="$1" cores="$2" ti line fpath k run sub evt tag ed rc t0 t1
    while :; do
        ti=$(next_task)
        [ "$ti" -gt "$NTASK" ] && break
        line=$(sed -n "${ti}p" "$MANIFEST")
        [ -z "$line" ] && continue
        IFS=$'\t' read -r fpath k run sub evt <<< "$line"
        tag="r${run}_s${sub}_e${evt}"
        ed="$OUT/work/t_${ti}"; mkdir -p "$ed"; cd "$ed" || continue
        t0=$(date +%s)
        taskset -c "$cores" /usr/bin/time -v -o time.txt \
            timeout -k 60 3600 lar -n 1 --nskip "$k" -c "$FCL" \
                -s "$fpath" --no-output > lar.log 2>&1
        rc=$?
        t1=$(date +%s)
        local rss bz tz nz audit
        audit=$(CHK=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/check-pr-run.sh; \
                if [ -x "$CHK" ] && "$CHK" lar.log >audit.txt 2>&1; then echo ok; else echo FAIL; fi)
        [ "$audit" = FAIL ] && cp audit.txt "$OUT/logs/audit_${ti}_${tag}.txt" 2>/dev/null
        # AUTHORITATIVE RSE: read it back from the job's own tracking-pr.root
        # Trun, and use THAT for the filenames.  The manifest RSE is only a
        # prediction of what --nskip k lands on; if the two ever disagree the
        # prediction is wrong (art's logical order is FileIndex/RSE-sorted, not
        # Events-tree order -- see make-manifest.sh).  Naming from the output
        # makes a wrong prediction loud instead of silently mislabelling
        # every file.
        local rse_true=""
        if [ -f tracking-pr.root ]; then
            rse_true=$(python3 -c "
import ROOT, sys
ROOT.gErrorIgnoreLevel = ROOT.kFatal
f = ROOT.TFile.Open('tracking-pr.root')
t = f.Get('Trun') if f and not f.IsZombie() else None
if t and t.GetEntries():
    t.GetEntry(0); print('%d %d %d' % (t.runNo, t.subRunNo, t.eventNo))
" 2>/dev/null | tail -1)
        fi
        local rse_ok=ok
        if [ -n "$rse_true" ]; then
            read -r trun tsub tevt <<< "$rse_true"
            if [ "$trun" != "$run" ] || [ "$tsub" != "$sub" ] || [ "$tevt" != "$evt" ]; then
                rse_ok="MISMATCH(manifest=${run}/${sub}/${evt})"
                run="$trun"; sub="$tsub"; evt="$tevt"; tag="r${run}_s${sub}_e${evt}"
                echo "task $ti: manifest RSE != Trun RSE; used Trun $tag" >> "$OUT/logs/rse-mismatch.log"
            fi
        fi
        rss=$(awk '/Maximum resident set size/ {print $NF}' time.txt 2>/dev/null); [ -z "$rss" ] && rss=0
        bz=0; tz=0; nz=0
        if [ $rc -eq 0 ]; then
            [ -f mabc.zip ]         && { bz=$(stat -c %s mabc.zip);         mv mabc.zip         "$OUT/bee/bee_${tag}.zip"; }
            [ -f tracking-pr.root ] && { tz=$(stat -c %s tracking-pr.root); mv tracking-pr.root "$OUT/tracking-pr/tracking-pr_${tag}.root"; }
            [ -f nugraph.h5 ]       && { nz=$(stat -c %s nugraph.h5);       mv nugraph.h5       "$OUT/nugraph/nugraph_${tag}.h5"; }
            if [ "$bz" -eq 0 ] || [ "$tz" -eq 0 ] || [ "$nz" -eq 0 ]; then
                cp lar.log "$OUT/logs/missing_${ti}_${tag}.log" 2>/dev/null
            fi
        else
            cp lar.log "$OUT/logs/fail_${ti}_${tag}.log" 2>/dev/null
        fi
        echo "$ti,$k,$run,$sub,$evt,$rc,$((t1-t0)),$rss,$bz,$tz,$nz,$audit,$rse_ok,$fpath" >> "$SUMMARY"
        cd "$OUT" || true; rm -rf "$ed"
    done
    echo "worker$wid done $(date +%H:%M:%S)" >> "$OUT/logs/w$wid.log"
}

echo "harness start $(date) : $NTASK events, $NWORK workers x $CORESPER cores = $((NWORK*CORESPER)) cores, fcl=$FCL"
for w in $(seq 0 $((NWORK-1))); do
    lo=$((w*CORESPER)); hi=$((lo+CORESPER-1))
    worker "$w" "$lo-$hi" &
done
wait
ok=$(awk -F, 'NR>1 && $6==0' "$SUMMARY" | wc -l)
bad=$(awk -F, 'NR>1 && $6!=0' "$SUMMARY" | wc -l)
echo "harness done $(date) : ok=$ok fail=$bad  bee=$(ls "$OUT/bee" 2>/dev/null | wc -l) trackpr=$(ls "$OUT/tracking-pr" 2>/dev/null | wc -l) nugraph=$(ls "$OUT/nugraph" 2>/dev/null | wc -l)"
