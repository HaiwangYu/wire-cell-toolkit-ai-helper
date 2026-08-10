#!/bin/bash
# Bokeh waveform viewer for issue 10 (dashed W track, run 270/6/46).
# Same setup as standalone-sample/w-gap/serve_compare_wires.sh, but defaults to
# this issue's extracted single-event file.
#
#   ./serve-viewer.sh [port] [fileA fileB [tagA [tagB]]]
# defaults: port 5010, A=B=data/evt-270-6-46.root, tagA=dnnsp, tagB=simchannel
#
# Tunnel from a laptop:
#   ssh -L 5010:localhost:5010 <user>@sbndbuild03.fnal.gov
# then open http://localhost:5010/compare_wires_viewer
set -e
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
PORT=${1:-5010}; shift || true
if [ $# -eq 0 ]; then
  set -- "$D/data/evt-270-6-46.root" "$D/data/evt-270-6-46.root" dnnsp simchannel
fi
exec /cvmfs/oasis.opensciencegrid.org/mis/apptainer/current/bin/apptainer exec \
    -B /cvmfs,/exp,/nashome,/pnfs \
    /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest \
    bash -c "
source /nashome/y/yuhw/.bashrc
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh
cd $HERE
bokeh serve --port $PORT \
    --allow-websocket-origin=localhost:$PORT \
    --allow-websocket-origin=127.0.0.1:$PORT \
    compare_wires_viewer.py --args $*
"
