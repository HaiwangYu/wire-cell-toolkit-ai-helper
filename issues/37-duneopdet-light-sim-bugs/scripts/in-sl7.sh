#!/bin/bash
# Run a command inside the FNAL SL7 dev apptainer on a dunegpvm/dunebuild node, with dunesw v10_26_00d00 e26:prof set up.
#   in-sl7.sh <cmd ...>                    (SL7_SETUP=none: bare container, no dunesw setup)
# The dunesw/mrb setup is done by the inner shell; OPDEV=<mrb dev dir> additionally sources its localProducts + mrbslp.
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
if [ -z "${APPTAINER_NAME:-}" ]; then
  exec /usr/bin/apptainer exec -B /cvmfs -B /exp -B /nashome ${KRB5CCNAME:+--env KRB5CCNAME=$KRB5CCNAME} $IMG /bin/bash "$0" "$@"
fi
if [ "${SL7_SETUP:-dunesw}" != none ]; then
  source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
  setup dunesw v10_26_00d00 -q e26:prof > /dev/null 2>&1 || { echo "dunesw setup failed" >&2; exit 90; }
  if [ -n "${OPDEV:-}" ]; then
    source $OPDEV/localProducts*/setup > /dev/null 2>&1; mrbslp > /dev/null 2>&1
  fi
fi
exec "$@"
