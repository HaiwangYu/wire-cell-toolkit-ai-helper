#!/bin/bash
# ai-helper #45: submit the crash-rate test, one job per tasks.txt line.
#   submit-crash.sh <tarball> <tasks.txt> <tag> [--dry-run]
# Inputs from /pnfs/sbnd/scratch/users/$USER/pr543-crash-study/inputs, results to .../<tag>/<mode>/.
# Memory 4500MB: a normal step 2 peaks at ~2 GB, but a crash runs ROOT's gdb stack dump (seen at 4.4 GB).
set -euo pipefail
TAR=$(realpath "${1:?tarball}"); TASKS=$(realpath "${2:?tasks}"); TAG=${3:?tag}; DRY=${4:-}
B=/pnfs/sbnd/scratch/users/$USER/pr543-crash-study; H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
N=$(grep -vc '^#' "$TASKS")
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
REQ='(TARGET.HAS_SINGULARITY=?=true)&&(TARGET.HAS_CVMFS_sbnd_opensciencegrid_org==true)&&(TARGET.HAS_CVMFS_larsoft_opensciencegrid_org==true)&&(TARGET.HAS_CVMFS_uboone_opensciencegrid_org==true)'
cmd=(jobsub_submit -G sbnd --role=Analysis -N "$N" --memory=4500MB --disk=4GB --expected-lifetime=3h --cpu=1
     --resource-provides=usage_model=DEDICATED,OPPORTUNISTIC --singularity-image "$IMG" --append_condor_requirements="$REQ"
     --tar_file_name "dropbox://$TAR" -f "dropbox://$TASKS" --mail_never
     "file://$H/crash-job.sh" "$(basename "$TASKS")" "$B/inputs" "$B/$TAG")
echo "$(date '+%F %T') $N jobs -> $B/$TAG"; printf '%q ' "${cmd[@]}"; echo
[ "$DRY" = --dry-run ] && exit 0
"${cmd[@]}"
