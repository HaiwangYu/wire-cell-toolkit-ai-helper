#!/bin/bash
# Run a command inside an SL7 image on an Aurora COMPUTE node (Recipe A' of
# docs/aurora-img-clus-match-pr-production-plan.md): the UPS products come from
# twester's Flare tree + our $Y/products overlay; no CVMFS, no network needed.
#
#   in-aurora-sl7.sh <cmd> [args...]     # e.g. in-aurora-sl7.sh bash -c 'lar ...'
#
# Env knobs:
#   SL7_SETUP   setup script to source first (default: setup-aurora-opt.sh next to
#               this file; setup-aurora-ap.sh for config work, setup-aurora-run.sh
#               for lar runs; "none" for a bare container)
#   SL7_IMAGE   image; default: $Y/images/fnal-dev-sl7.sif if present (has the
#               -devel headers wcb configure needs), else the bare slf7.sif
#   APPTAINER_MODE  "" (default; user namespaces are on for compute nodes),
#               "--fakeroot" or "--userns" if the probe says so
#   BINDS       extra apptainer -B args
#   PASS_ENV    "A B" host variables to forward besides the proxies and USER
#
# Facts (plan v2, measured 2026-09-16): login nodes cannot run containers at all
# (user.max_user_namespaces=0, non-setuid apptainer) -> this script is for jobs;
# compute nodes have no network except http://proxy.alcf.anl.gov:3128; PBS may
# inject an LD_PRELOAD SL7 cannot load; the host oneAPI/Cray env (CC, CXX, CPATH,
# LD_LIBRARY_PATH) must not leak into the container (--cleanenv, as on Polaris).
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
Y=${Y:-/lus/flare/projects/neutrinoGPU/yuhw}
: "${SL7_SETUP:=$HERE/setup-aurora-opt.sh}"
: "${BINDS:=}"
: "${APPTAINER_MODE:=}"
if [ -z "${SL7_IMAGE:-}" ]; then
    SL7_IMAGE=$Y/images/fnal-dev-sl7.sif
    [ -f "$SL7_IMAGE" ] || SL7_IMAGE=/lus/flare/projects/neutrinoGPU/containers/slf7.sif
fi

if ! command -v apptainer >/dev/null 2>&1; then
    module load apptainer >/dev/null 2>&1
    module load fuse-overlayfs >/dev/null 2>&1
fi
command -v apptainer >/dev/null 2>&1 || { echo "in-aurora-sl7.sh: no apptainer (are you on a login node? containers only work in jobs)" >&2; exit 2; }

unset LD_PRELOAD
ulimit -c 0
export HTTP_PROXY=http://proxy.alcf.anl.gov:3128 HTTPS_PROXY=http://proxy.alcf.anl.gov:3128
export http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY
export no_proxy="admin,*.hostmgmt.cm.aurora.alcf.anl.gov,*.alcf.anl.gov,localhost"
export APPTAINER_CACHEDIR=${APPTAINER_CACHEDIR:-/tmp/apptainer-cache-$USER}
export APPTAINER_TMPDIR=${APPTAINER_TMPDIR:-/tmp/apptainer-tmp-$USER}
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

CMD=$(printf '%q ' "$@")
if [ "$SL7_SETUP" != "none" ]; then
    INNER="source $(printf '%q' "$SL7_SETUP") >/dev/null 2>&1; $CMD"
else
    INNER="$CMD"
fi
export APPTAINERENV_SL7_SETUP="$SL7_SETUP" APPTAINERENV_Y="$Y"
export APPTAINERENV_USER="$USER" APPTAINERENV_TERM="${TERM:-xterm}"
export APPTAINERENV_HTTP_PROXY=$HTTP_PROXY APPTAINERENV_HTTPS_PROXY=$HTTPS_PROXY
export APPTAINERENV_http_proxy=$HTTP_PROXY APPTAINERENV_https_proxy=$HTTPS_PROXY APPTAINERENV_no_proxy=$no_proxy
for v in ${PASS_ENV:-}; do export "APPTAINERENV_$v=${!v}"; done

exec apptainer exec $APPTAINER_MODE --cleanenv -B /lus/flare -B /tmp $BINDS "$SL7_IMAGE" \
    bash -c "cd $(printf '%q' "$PWD") && $INNER"
