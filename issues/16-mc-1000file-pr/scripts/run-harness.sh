#!/bin/bash
# 1-step img -> clus -> QL match -> tagger -> PATTERN RECOGNITION over a list of
# MC reco1 files, one lar process per event.
#
#   ./run-harness.sh <file-list> <outdir> [nworkers] [cores-per-worker]
#
# Descended from the 2026-08-14 img-clus-match-tag harness.  Four changes:
#
#  1. THE PR CHAIN IS ON.  clus_pr runs the 15-name pipeline including
#     tagger_check_neutrino and both BDT scorers, so setup-dlvtx.sh is sourced
#     (see below) and enable_tracking_root stays "true".
#  2. THREE DELIVERABLES KEPT, NOT ONE.  The 08-14 harness deleted nugraph.h5
#     and never produced tracking-pr.root.  Here all three are archived per
#     event: the Bee zip, tracking-pr.root and nugraph.h5.
#  3. RSE IN THE FILENAME, READ FROM EventAuxiliary.  The 08-14 harness grepped
#     run/subRun/event out of the lar log; that regex matched 2 of 13217 rows,
#     i.e. it silently never worked.  Each file's RSE list is now read once up
#     front with PyROOT (rse_list.py) -- the same open that counts the events --
#     so every archived file is named for the event it holds and nothing depends
#     on log formatting.
#  4. PEAK RSS PER EVENT.  /usr/bin/time -v around lar, recorded in the CSV, so
#     the concurrency ceiling is measured rather than assumed.
#
# Per-event isolation is kept verbatim from the ancestor harness, and for the
# same reason: concurrent lar jobs collide on art's MemoryTracker/TFileService
# sqlite files ("SQLExecutionError: disk I/O error") unless each has its own cwd.
LIST="$1"; OUT="$2"; NWORK="${3:-32}"; CORESPER="${4:-1}"
# MAXEV>0 caps how many events are taken from EACH file.  The pilot sets
# MAXEV=1 so its 10 events come from 10 different files: that keeps a realistic
# dCache open in every measurement and gives 10 distinct events to hand-scan,
# which 10 events out of one file would not.  0 = every event (the bulk run).
MAXEV="${MAXEV:-0}"

source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
# DL (SCN) neutrino vertex.  MUST be after setup-ap.sh.  Without it
# TaggerCheckNeutrino catches the torch ImportError, logs it at WARN and
# silently uses the geometric vertex -- a complete, plausible result computed
# the wrong way.  check-pr-run.sh audits for exactly that.
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-dlvtx.sh >/dev/null 2>&1
# set -e stays OFF after the sources: ups setup scripts return non-zero.
set -uo pipefail
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
# Bound the per-process math libs too; the TBB pool is bounded by taskset.
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

FCL=wcls-img-clus-matching-xin.fcl
RSEPY="$(cd "$(dirname "$0")" && pwd)/rse_list.py"
NFILES=$(wc -l < "$LIST")
CURSOR="$OUT/.cursor"; LOCK="$OUT/.cursor.lock"
mkdir -p "$OUT"/{work,logs,bee,tracking-pr,nugraph}
echo 0 > "$CURSOR"
SUMMARY="$OUT/summary.csv"
echo "file_idx,event_idx,run,subrun,event,rc,wall_s,peak_rss_kb,bee_bytes,trackpr_bytes,nugraph_bytes,audit,file" > "$SUMMARY"

next_index () {                       # atomic file-index handout
    local i
    exec 9>"$LOCK"; flock 9
    i=$(cat "$CURSOR"); echo $((i+1)) > "$CURSOR"
    flock -u 9; exec 9>&-
    echo "$i"
}

worker () {
    local wid="$1" cores="$2" fi fpath ed rc t0 t1 k tag rse run sub evt nev
    local -a RSE
    while :; do
        fi=$(next_index)
        [ "$fi" -ge "$NFILES" ] && break
        fpath=$(sed -n "$((fi+1))p" "$LIST")
        [ -z "$fpath" ] && continue
        # One PyROOT open: event count AND the per-event RSE, together.
        mapfile -t RSE < <(python3 "$RSEPY" "$fpath" 2>/dev/null)
        nev=${#RSE[@]}
        if [ "$nev" -eq 0 ]; then
            echo "file$fi UNREADABLE $fpath" >> "$OUT/logs/w$wid.log"
            echo "$fi,,,,,-1,0,0,0,0,0,$fpath" >> "$SUMMARY"
            continue
        fi
        [ "$MAXEV" -gt 0 ] && [ "$nev" -gt "$MAXEV" ] && nev=$MAXEV
        echo "file$fi START nev=$nev $(date +%H:%M:%S) $fpath" >> "$OUT/logs/w$wid.log"
        for k in $(seq 0 $((nev-1))); do
            read -r run sub evt <<< "${RSE[$k]}"
            tag="r${run}_s${sub}_e${evt}"
            ed="$OUT/work/e_${fi}_${k}"; mkdir -p "$ed"; cd "$ed" || continue
            t0=$(date +%s)
            taskset -c "$cores" /usr/bin/time -v -o time.txt \
                timeout 3600 lar -n 1 --nskip "$k" -c "$FCL" \
                    -s "$fpath" --no-output > lar.log 2>&1
            rc=$?
            t1=$(date +%s)
            local rss bz tz nz audit
            audit=$(CHK=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/check-pr-run.sh; \
                    if [ -x "$CHK" ] && "$CHK" lar.log >audit.txt 2>&1; then echo ok; else echo FAIL; fi)
            [ "$audit" = FAIL ] && cp audit.txt "$OUT/logs/audit_${fi}_${k}_${tag}.txt" 2>/dev/null
            rss=$(awk '/Maximum resident set size/ {print $NF}' time.txt 2>/dev/null); [ -z "$rss" ] && rss=0
            bz=0; tz=0; nz=0
            if [ $rc -eq 0 ]; then
                # Archive the three deliverables under the event's own RSE.
                [ -f mabc.zip ]         && { bz=$(stat -c %s mabc.zip);         mv mabc.zip         "$OUT/bee/bee_${tag}.zip"; }
                [ -f tracking-pr.root ] && { tz=$(stat -c %s tracking-pr.root); mv tracking-pr.root "$OUT/tracking-pr/tracking-pr_${tag}.root"; }
                [ -f nugraph.h5 ]       && { nz=$(stat -c %s nugraph.h5);       mv nugraph.h5       "$OUT/nugraph/nugraph_${tag}.h5"; }
                # A zero here is a real failure mode, not an accounting gap:
                # the job "succeeded" but produced nothing.  Keep the log.
                if [ "$bz" -eq 0 ] || [ "$tz" -eq 0 ] || [ "$nz" -eq 0 ]; then
                    cp lar.log "$OUT/logs/missing_${fi}_${k}_${tag}.log" 2>/dev/null
                fi
            else
                cp lar.log "$OUT/logs/fail_${fi}_${k}_${tag}.log" 2>/dev/null
            fi
            echo "$fi,$k,$run,$sub,$evt,$rc,$((t1-t0)),$rss,$bz,$tz,$nz,$audit,$fpath" >> "$SUMMARY"
            cd "$OUT" || true; rm -rf "$ed"
        done
        echo "file$fi DONE $(date +%H:%M:%S)" >> "$OUT/logs/w$wid.log"
    done
}

# Disjoint core sets: worker w gets cores [w*CORESPER, w*CORESPER+CORESPER-1].
echo "harness start $(date) : $NFILES files, $NWORK workers x $CORESPER cores = $((NWORK*CORESPER)) cores"
for w in $(seq 0 $((NWORK-1))); do
    lo=$((w*CORESPER)); hi=$((lo+CORESPER-1))
    worker "$w" "$lo-$hi" &
done
wait
ok=$(awk -F, 'NR>1 && $6==0' "$SUMMARY" | wc -l)
bad=$(awk -F, 'NR>1 && $6!=0' "$SUMMARY" | wc -l)
echo "harness done $(date) : ok=$ok fail=$bad  bee=$(ls "$OUT/bee" 2>/dev/null | wc -l) trackpr=$(ls "$OUT/tracking-pr" 2>/dev/null | wc -l) nugraph=$(ls "$OUT/nugraph" 2>/dev/null | wc -l)"
