#!/bin/bash
# Run dqdx_dump_art.py in the SL7 container with the sbndcode env of the YZ kit (issue 46).
# Usage: run-dqdx-dump.sh <art.root> <outdir> [dqdx_dump_art.py options]
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
KIT=$HERE/../yz-sim-kit
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    APPT=$(command -v apptainer || echo /cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer)
    exec "$APPT" exec -B /cvmfs,/exp,/pnfs,/tmp,/opt "$IMG" /bin/bash "$HERE/run-dqdx-dump.sh" "$@"
fi
source "$KIT/setup-yz-env.sh" >/dev/null || exit 1
exec python3 "$HERE/dqdx_dump_art.py" "$@"
