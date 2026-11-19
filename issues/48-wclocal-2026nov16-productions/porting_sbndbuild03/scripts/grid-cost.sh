#!/bin/bash
# Issue 48: CPU and wall cost of the WCLocal2026Nov16-FermiGrid clusters, from condor_history
# on each jobsub schedd (porting_sbndbuild03, 2026-11-19).  jobsub_history ignores --constraint and
# always answers from jobsub01, so condor_history is queried per schedd with the bearer token.
#   grid-cost.sh <out.tsv>   (cluster ids from wclocal-nov16/lists/*submit*.log)
# out.tsv: schedd ClusterId ProcId RemoteUserCpu RemoteSysCpu RemoteWallClockTime CumulativeSlotTime
#          JobStartDate CompletionDate RequestCpus NumJobStarts QDate JobStatus
set -u
OUT=${1:?out.tsv}; L=/exp/sbnd/data/users/yuhw/wclocal-nov16/lists
export BEARER_TOKEN_FILE=${BEARER_TOKEN_FILE:-/run/user/$(id -u)/bt_u$(id -u)} _condor_SEC_CLIENT_AUTHENTICATION_METHODS=SCITOKENS
A="ClusterId ProcId RemoteUserCpu RemoteSysCpu RemoteWallClockTime CumulativeSlotTime JobStartDate CompletionDate RequestCpus NumJobStarts QDate JobStatus"
C=$(grep -h -o -E 'Use job id [0-9]+\.0@jobsub0[0-9]' $L/*submit*.log | awk '{split($4,a,"[.@]"); print a[3], a[1]}' | sort -u)
: > "$OUT"
for s in $(echo "$C" | cut -d' ' -f1 | sort -u); do
  c=$(echo "$C" | awk -v s=$s '$1==s {printf "%sClusterId==%s", (n++?" || ":""), $2}')
  condor_history -name $s.fnal.gov -pool gpcollector04.fnal.gov -constraint "$c" -af $A | sed "s/^/$s /" >> "$OUT"
done
echo "$(wc -l < "$OUT") jobs in $(echo "$C" | wc -l) clusters" >&2
