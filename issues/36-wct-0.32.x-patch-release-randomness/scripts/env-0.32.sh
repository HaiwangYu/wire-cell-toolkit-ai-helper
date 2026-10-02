# Environment for building/running WCT 0.32.x against the SAME UPS products as
# the cvmfs `wirecell v0_32_1 -q e26:prof` that SBND production uses.
# `setup sbndcode v10_14_02_03 -q e26:prof` pulls in wirecell v0_32_1 and all its
# dependencies (gcc v12_1_0, root v6_28_12, boost v1_82_0, spdlog v1_9_2,
# jsoncpp v1_9_5a, gojsonnet v0_18_0, tbb v2021_9_0, hdf5 v1_12_2a, libtorch
# v2_1_1b, eigen v23_08_01, fftw v3_3_10) and larwirecell v10_01_26_01.
# Source inside the SL7 container (claude-utilities/in-gpvm-sl7.sh, SL7_SETUP=none).
source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh >/dev/null 2>&1
UPS_PATCHES=/exp/sbnd/app/users/yuhw/opt/ups-patches   # larcv2/root version-conflict workaround, see wcp-porting-img/sbnd/setup-local-opt.sh
[[ -d "$UPS_PATCHES" ]] && export PRODUCTS="$UPS_PATCHES:$PRODUCTS"
setup sbndcode v10_14_02_03 -q e26:prof || return 1
export WCT_SRC=/exp/sbnd/app/users/yuhw/wire-cell-toolkit-0.32.x      # git worktree, branch 0.32.x
export WCT_PREFIX=/exp/sbnd/app/users/yuhw/opt-0.32.x                 # install prefix for the patched build
