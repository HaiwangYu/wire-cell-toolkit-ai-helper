#!/bin/bash
# Compile the WCT config of the study variants and compare against the kit's (stock-identical) config.
IMG=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest
SELF=$(readlink -f "${BASH_SOURCE[0]}")
if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    exec apptainer exec -B /cvmfs,/exp,/pnfs,/tmp,/opt "$IMG" /bin/bash "$SELF" "$@"
fi
R=/exp/sbnd/data/users/yuhw/YZ-non-uniformity/rng-study
source $R/kit-copy/setup-yz-env.sh >/dev/null
cd $R/config-check
for yz in off on; do for app in TbbFlow Pgrapher; do for st in shared separate; do
  n=${yz}_${app}_${st}
  printf '#include "detsim_sbnd_yz_%s.fcl"\nphysics.producers.simtpc2d.wcls_main.apps: ["%s"]\nphysics.producers.simtpc2d.wcls_main.params.wct_app: "%s"\nphysics.producers.simtpc2d.wcls_main.params.rng_streams: "%s"\n' $yz $app $app $st > $n.in.fcl
  lar -c $n.in.fcl --debug-config $n.fcl > $n.lar.log 2>&1 || { echo "lar $n failed"; continue; }
  mapfile -t ARGS < <(python3 $YZ_KIT/scripts/fcl_wcls_args.py $n.fcl)
  $YZ_WCT_LIB/../bin/wcsonnet "${ARGS[@]}" -o $n.raw.json > $n.wcs.log 2>&1 || { echo "wcsonnet $n failed"; tail -5 $n.wcs.log; continue; }
  python3 -c 'import json,sys; json.dump(json.load(open(sys.argv[1])), open(sys.argv[2],"w"), indent=1, sort_keys=True)' $n.raw.json $n.json
done; done; done
