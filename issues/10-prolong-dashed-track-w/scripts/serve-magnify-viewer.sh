#!/bin/bash
# Serve the Magnify browser (2D per SP stage + 1D all-stage overlay).
#
#   ./serve-magnify-viewer.sh [port] [magnify.root]
# defaults: port 5012, data/magnify-270-6-46.root
#
# Tunnel from a laptop:
#   ssh -L 5012:localhost:5012 <user>@sbndbuild03.fnal.gov
# then open http://localhost:5012/magnify_viewer
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
PORT=${1:-5012}
FILE=${2:-$D/data/magnify-270-6-46.root}
exec /cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer exec \
    -B /cvmfs,/exp,/nashome,/pnfs \
    /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest \
    bash -c "
source /nashome/y/yuhw/.bashrc
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh
export MAGNIFY_FILE='$FILE'
cd $HERE
bokeh serve --port $PORT \
    --allow-websocket-origin=localhost:$PORT \
    --allow-websocket-origin=127.0.0.1:$PORT \
    magnify_viewer.py
"
