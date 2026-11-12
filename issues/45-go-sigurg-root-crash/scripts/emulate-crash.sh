#!/bin/bash
# ai-helper #45: run crash-job.sh as a FermiGrid worker would, here: the tarball unpacked in a fresh dir,
# the SL7 image, ONLY /cvmfs and /pnfs mounted.   emulate-crash.sh <tarball> <tasks.txt> <index> <work dir>
set -euo pipefail
TAR=$(realpath "${1:?tarball}"); T=$(realpath "${2:?tasks}"); P=${3:?index}; W=${4:?work dir}
mkdir -p "$W"/{tar,input,scratch,out}; W=$(realpath "$W")
[ -d "$W/tar/wc" ] || tar -C "$W/tar" -xzf "$TAR"; cp "$T" "$W/input/"
/cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer exec --contain --cleanenv -B /cvmfs,/pnfs,"$W" --pwd "$W/scratch" \
  --env INPUT_TAR_DIR_LOCAL="$W/tar",CONDOR_DIR_INPUT="$W/input",_CONDOR_SCRATCH_DIR="$W/scratch",PROCESS="$P",CRASH_EMULATE=1 \
  /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest \
  bash "$W/tar/wc/crash-job.sh" "$(basename "$T")" /pnfs/sbnd/scratch/users/yuhw/pr543-crash-study/inputs "$W/out"
