#!/bin/bash
# Run a command inside the Fermilab SL7 image on Polaris, with CVMFS provided
# by an unprivileged cvmfsexec (Recipe B of docs/polaris-img-clus-match-pr-production-plan.md).
#
#   in-polaris-sl7.sh <cmd> [args...]        # e.g.  in-polaris-sl7.sh bash -c 'source $SBND/setup-polaris-opt.sh; lar ...'
#
# Env knobs:
#   SL7_SETUP   setup script to source first (default: setup-polaris-opt.sh next to
#               this file; "none" for a bare container)
#   CVMFSEXEC   cvmfsexec dist to use. Default: the login-node copy. Job scripts
#               MUST point this at a private per-node copy (rsync the template to
#               /local/scratch) -- cache and locks live inside dist/ and two
#               instances sharing one dist crash each other.
#   BINDS       extra apptainer -B args
#
# Facts baked in (measured 2026-09-10, see the plan doc):
#  - no setuid apptainer: --userns is required; the spack "base" 1.3.2 build lacks
#    unsquashfs, so use the "testing" 1.3.6 build;
#  - compute nodes have no network except http://proxy.alcf.anl.gov:3128;
#  - PBS injects an XALT LD_PRELOAD that SL7 cannot load -> unset it;
#  - do not mount sbn.osgstorage.org (stalls); sbn.opensciencegrid.org IS needed
#    by setup_sbnd.sh.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
: "${CVMFSEXEC:=/lus/eagle/projects/neutrinoGPU/yuhw/cvmfsexec-login}"
: "${SL7_SETUP:=$HERE/setup-polaris-opt.sh}"
: "${BINDS:=}"
APP=/soft/spack/testing/0.8.1/apptainer/install/linux-sles15-zen3/gcc-12.3.0/apptainer-1.3.6-7czfylw7oeizgfklnroabhww7kygmtjt/bin/apptainer
# fnal-dev-sl7 (not -wn-): the worker-node image lacks -devel headers (bzlib.h) and wcb configure fails at BZIP2.
IMG=${SL7_IMAGE:-/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest}
# uboone: the scn v01_00_00 product (torch + sparseconvnet venv) for the DL neutrino vertex.
REPOS="sbnd.opensciencegrid.org sbn.opensciencegrid.org larsoft.opensciencegrid.org fermilab.opensciencegrid.org singularity.opensciencegrid.org uboone.opensciencegrid.org"

unset LD_PRELOAD
ulimit -c 0   # an uncaught WireCell exception in wcsonnet otherwise leaves a 170 MB core in the cwd (seen 2026-09-15)
export HTTP_PROXY=http://proxy.alcf.anl.gov:3128 HTTPS_PROXY=http://proxy.alcf.anl.gov:3128
export http_proxy=$HTTP_PROXY https_proxy=$HTTPS_PROXY
export APPTAINER_CACHEDIR=${APPTAINER_CACHEDIR:-/tmp/apptainer-cache-$USER}
export APPTAINER_TMPDIR=${APPTAINER_TMPDIR:-/tmp/apptainer-tmp-$USER}
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

# Pass the user command through as a single quoted string.
CMD=$(printf '%q ' "$@")
if [ "$SL7_SETUP" != "none" ]; then
    INNER="source $(printf '%q' "$SL7_SETUP") >/dev/null 2>&1; $CMD"
else
    INNER="$CMD"
fi
# --cleanenv: the Polaris PrgEnv modules export CXX=nvc++, CC=nvc, plus Cray
# CPATH/LIBRARY_PATH/LD_LIBRARY_PATH; passed through, they made wcb pick nvc++
# ("could not configure a C++ compiler", 2026-09-15).  Only pass what we need.
export APPTAINERENV_SL7_SETUP="$SL7_SETUP"
export APPTAINERENV_USER="$USER" APPTAINERENV_TERM="${TERM:-xterm}"
export APPTAINERENV_HTTP_PROXY=$HTTP_PROXY APPTAINERENV_HTTPS_PROXY=$HTTPS_PROXY
export APPTAINERENV_http_proxy=$HTTP_PROXY APPTAINERENV_https_proxy=$HTTPS_PROXY
for v in ${PASS_ENV:-}; do export "APPTAINERENV_$v=${!v}"; done   # PASS_ENV="A B" to forward more

cd "$CVMFSEXEC" || exit 2
exec ./cvmfsexec $REPOS -- \
    "$APP" exec --userns --cleanenv -B /cvmfs -B /lus/eagle -B /tmp $BINDS \
      ${PWD_BIND:-} "$IMG" bash -c "cd $(printf '%q' "$OLDPWD") && $INNER" 2> >(grep -v -E '^ln: failed to create symbolic link|CernVM-FS: (loading|mounted)' >&2)
