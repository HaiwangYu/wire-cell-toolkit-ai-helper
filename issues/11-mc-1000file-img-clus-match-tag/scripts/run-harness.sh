#!/bin/bash
# 1-step img -> clus -> QL matching -> taggers over a list of MC reco1 files.
#
#   ./run-harness.sh <file-list> <outdir> [nworkers] [cores-per-worker]
#
# Descended from issue-8's run_harness.sh (prabhjot-10file-Aug5) with three
# changes forced by the 100x larger scale:
#
#  1. CORE BUDGET.  Issue 8 ran 10 unbounded jobs: WCT runs TbbFlow, whose TBB
#     pool defaults to *hardware concurrency* (64 here), and OMP_NUM_THREADS
#     does not bound it.  Fine for a 9-minute run, not for a multi-hour one on
#     a shared build box.  Every worker is pinned with taskset to its own
#     disjoint core set, so the ceiling is NWORK * CORES_PER exactly.
#  2. WORK STEALING.  Issue 8 gave one worker per file with the event count
#     known up front.  Here the counts are not known (pre-counting 1000 dCache
#     files would be a slow serial pass), so workers pull the next file index
#     from a lock-guarded cursor and count events themselves on open.
#  3. SUMMARY.  One CSV row per event (rc, wall, zip size) so the run can be
#     audited without unpacking 13k zips.
#
# Per-event isolation is kept verbatim from issue 8, and for the same reason:
# concurrent lar jobs collide on art's MemoryTracker/TFileService sqlite files
# ("SQLExecutionError: disk I/O error") unless each has its own cwd.
LIST="$1"; OUT="$2"; NWORK="${3:-10}"; CORESPER="${4:-2}"

source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-ap.sh >/dev/null 2>&1
# set -e AFTER the sources: ups setup scripts return non-zero.
set -uo pipefail
export FHICL_FILE_PATH=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd:$FHICL_FILE_PATH
# Bound the per-process math libs too; the TBB pool is bounded by taskset.
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

FCL=wcls-img-clus-matching-xin.fcl
NFILES=$(wc -l < "$LIST")
CURSOR="$OUT/.cursor"; LOCK="$OUT/.cursor.lock"
mkdir -p "$OUT"/{work,logs,zips}
echo 0 > "$CURSOR"
SUMMARY="$OUT/summary.csv"
echo "file_idx,event_idx,run,subrun,event,rc,wall_s,zip_bytes,file" > "$SUMMARY"

next_index () {                       # atomic file-index handout
    local i
    exec 9>"$LOCK"; flock 9
    i=$(cat "$CURSOR"); echo $((i+1)) > "$CURSOR"
    flock -u 9; exec 9>&-
    echo "$i"
}

count_events () {                     # entries in the art Events tree
    python3 -c "
import ROOT, sys
f = ROOT.TFile.Open('$1')
if not f or f.IsZombie(): print(-1); sys.exit()
t = f.Get('Events')
print(t.GetEntries() if t else -1)
" 2>/dev/null | tail -1
}

worker () {
    local wid="$1" cores="$2" fi nev fpath ed rc t0 t1 z
    while :; do
        fi=$(next_index)
        [ "$fi" -ge "$NFILES" ] && break
        fpath=$(sed -n "$((fi+1))p" "$LIST")
        [ -z "$fpath" ] && continue
        nev=$(count_events "$fpath")
        if [ "$nev" -le 0 ] 2>/dev/null; then
            echo "file$fi UNREADABLE $fpath" >> "$OUT/logs/w$wid.log"
            echo "$fi,,,,,-1,0,0,$fpath" >> "$SUMMARY"
            continue
        fi
        echo "file$fi START nev=$nev $(date +%H:%M:%S) $fpath" >> "$OUT/logs/w$wid.log"
        for k in $(seq 0 $((nev-1))); do
            ed="$OUT/work/e_${fi}_${k}"; mkdir -p "$ed"; cd "$ed" || continue
            t0=$(date +%s)
            taskset -c "$cores" timeout 1800 lar -n 1 --nskip "$k" -c "$FCL" \
                    -s "$fpath" --no-output > lar.log 2>&1
            rc=$?
            t1=$(date +%s)
            # issue-8 cleanup: keep only mabc.zip
            rm -f nugraph.h5 trash-all-apa.tar.gz *.db tf-default.root mabc-pr.zip 2>/dev/null
            local rse
            rse=$(grep -m1 -oE "run: [0-9]+ subRun: [0-9]+ event: [0-9]+" lar.log 2>/dev/null \
                  | awk '{printf "%s,%s,%s",$2,$4,$6}')
            [ -z "$rse" ] && rse=",,"
            if [ $rc -eq 0 ] && [ -f mabc.zip ]; then
                z=$(stat -c %s mabc.zip)
                mv mabc.zip "$OUT/zips/z_$(printf '%04d_%03d' "$fi" "$k").zip"
            else
                z=0
                cp lar.log "$OUT/logs/fail_${fi}_${k}.log" 2>/dev/null
            fi
            echo "$fi,$k,$rse,$rc,$((t1-t0)),$z,$fpath" >> "$SUMMARY"
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
echo "harness done $(date) : ok=$ok fail=$bad  zips=$(ls "$OUT/zips" 2>/dev/null | wc -l)"
