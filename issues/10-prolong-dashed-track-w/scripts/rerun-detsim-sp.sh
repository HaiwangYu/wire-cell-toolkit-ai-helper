#!/bin/bash
# Re-run detsim + SP for run 270/6/46 to obtain gauss / wiener / dnnsp (+ RawDigit)
# in ONE file, so the SP stages can be compared against the SimChannel truth.
#
# Why a re-run: the MCP2025C production stage is a single chained
# gen_g4_detsim_reco1_reco2_caf job -- no intermediate g4/detsim file was saved,
# and reco1 keeps NO raw::RawDigit, only recob::Wires_simtpc2d_dnnsp_DetSim.
# But reco1 DOES keep sim::SimEnergyDeposits_ionandscint_priorSCE_G4, which is
# exactly the input this job wants (params.inputTag = "ionandscint:priorSCE"),
# so we can re-drift + re-digitize + re-SP from the same true depositions.
#
# CAVEAT: drift/electronics/noise are re-simulated, so the re-run dnnsp is NOT
# bit-identical to the production dnnsp (different noise realization).  The
# point is the SELF-CONSISTENT gauss vs wiener vs dnnsp vs truth comparison on
# the same track; the production dnnsp stays available in data/evt-270-6-46.root.
#
# Cost (from the w-gap study): ~137 s and ~5.9 GB peak RSS per event.
# NOTE: source the setup scripts BEFORE `set -e` -- they return non-zero on
# their last command, which would abort the script silently.
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -e
# GOTCHA 1 (memory: sim jobs WIRECELL_PATH): setup-local-opt.sh puts
# opt/share/wirecell ahead of sbndcode's cfg; opt's pgrapher/common/params.jsonnet
# dropped elec.gain, so the sbndcode sim stack dies with
# "Field does not exist: gain".  sbndcode's cfg must win for SIM jobs.
#
# GOTCHA 2 (found here, 2026-08-10): setup-local-opt.sh already puts the LOCAL
# sbndcode checkout (/exp/.../sbndcode/sbndcode/WireCell/cfg) on the path, and
# it is STALE -- its params.jsonnet asks for "sbnd-wires-geometry-v0202.json.bz2",
# which exists nowhere, so WireSchemaFile gets an empty filename and the job dies
# with  Persist.cxx: "no such file: ."  at module construction.
# Prepend the CVMFS sbndcode cfg of the version we actually run (v10_14_02_03):
# it carries the sim entry jsonnet AND wires v0206, which does exist.
path-prepend /cvmfs/sbnd.opensciencegrid.org/products/sbnd/sbndcode/v10_14_02_03/wire-cell-cfg WIRECELL_PATH

HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
cd "$D/data"
/usr/bin/time -v lar -c "$HERE/detsim-sp-rerun.fcl" \
    -s "$D/data/evt-270-6-46.root" -n 1 \
    > "$D/data/detsim-sp-rerun.log" 2>&1
echo "lar rc=$?"
ls -la evt-270-6-46_sp.root 2>/dev/null | awk '{printf "  %.1f MB  %s\n",$5/1048576,$NF}'
