#!/bin/bash
# Drive the validation campaign event-by-event with a bounded core budget.
#   ./campaign-driver.sh <worklist>
# worklist lines:  <label> <input.root> <entry>
# Per event: campaign-sp.sh (SP roi:both -> sp.root, magnify roi:trad ->
# magnify.root) then campaign-img.sh (-> mabc.zip).
#
# CORE BUDGET: WCT runs TbbFlow, whose TBB pool defaults to hardware
# concurrency (64 here), so OMP/MKL vars alone do NOT bound it.  Each worker is
# pinned with taskset to a 2-core pair => 4 workers = 8 cores, under the 10 asked
# for.  Do not raise NWORK without shrinking the core pairs.
WORKLIST="$1"
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
C="$D/data/validation-20260812"
SL7=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
NWORK=4
CORES=("0,1" "2,3" "4,5" "6,7")
# $SUB selects the leg (and so the pair of per-event scripts): mc runs the
# sim+SP chain from SimEnergyDeposits, data runs NF+SP from decoded RawDigits.
case "$SUB" in
  mc)   SPSH=campaign-sp.sh;      IMGSH=campaign-img.sh ;;
  data) SPSH=campaign-sp-data.sh; IMGSH=campaign-img-data.sh ;;
  *)    echo "set SUB=mc|data" >&2; exit 2 ;;
esac
run_one () {                      # $1=label $2=input $3=entry $4=coreset
    local lbl="$1" in="$2" ent="$3" cs="$4" out="$C/$SUB/$1"
    mkdir -p "$out"
    taskset -c "$cs" bash $SL7 bash "$HERE/$SPSH"  "$in" "$ent" "$out" >> "$C/logs/$lbl.out" 2>&1
    taskset -c "$cs" bash $SL7 bash "$HERE/$IMGSH" "$out"              >> "$C/logs/$lbl.out" 2>&1
    echo "  done $lbl  $(ls -la "$out"/mabc.zip 2>/dev/null | awk '{printf "%.1f MB mabc",$5/1048576}')"
}
i=0
while read -r lbl in ent; do
    [ -z "$lbl" ] && continue
    slot=$(( i % NWORK ))
    run_one "$lbl" "$in" "$ent" "${CORES[$slot]}" &
    i=$(( i + 1 ))
    (( i % NWORK == 0 )) && wait     # keep at most NWORK in flight
done < "$WORKLIST"
wait
echo "campaign leg '$SUB' complete: $i events"
