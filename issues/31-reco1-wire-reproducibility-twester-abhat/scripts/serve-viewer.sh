#!/bin/bash
# Bokeh server for compare_wires_rse_viewer.py on an Aurora UAN (no container
# needed: uproot decodes the wires).
#
#   ./serve-viewer.sh [port] [viewer args...]
#   e.g. ./serve-viewer.sh 5031 --rse 1/16/6 --product dnnsp_reco1
#
# Default event list: ../rse-manifest.tsv (from compare_wires_hash.py).
# From the laptop, tunnel to the SAME UAN this runs on (it prints its name):
#   ssh -L 5031:localhost:5031 <user>@<uan>.alcf.anl.gov      # e.g. aurora-uan-0010
# then open http://localhost:5031/compare_wires_rse_viewer
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
PORT=${1:-5031}; shift || true
VENV=${VENV:-/lus/flare/projects/neutrinoGPU/yuhw/tools/venv-wire-viewer}
# venv made with: module load python/3.12.12; python3 -m venv $VENV;
#                 $VENV/bin/pip install uproot awkward bokeh numpy matplotlib
echo "serving on $(hostname) port $PORT -> tunnel: ssh -L $PORT:localhost:$PORT $USER@$(hostname -s).alcf.anl.gov"
exec "$VENV/bin/bokeh" serve --port "$PORT" \
    --allow-websocket-origin="localhost:${PORT}" \
    --allow-websocket-origin="127.0.0.1:${PORT}" \
    "$HERE/compare_wires_rse_viewer.py" --args "$@"
