#!/bin/bash
# Run a command in the SL7 container with the study kit environment (no LD_PRELOAD).
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
SELF=$(readlink -f "${BASH_SOURCE[0]}")
if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    exec apptainer exec -B /cvmfs,/exp,/pnfs,/tmp,/opt "$IMG" /bin/bash "$SELF" "$@"
fi
source /exp/sbnd/data/users/yuhw/YZ-non-uniformity/rng-study/kit-copy/setup-yz-env.sh >/dev/null || exit 1
exec "$@"
