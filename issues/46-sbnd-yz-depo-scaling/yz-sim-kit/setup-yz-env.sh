# Environment for the SBND YZ-scaled detsim kit (ai-helper issue 46).
# Source it INSIDE the SL7 container:
#   apptainer exec -B /cvmfs,/exp,/pnfs,/tmp,/opt \
#       /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:latest bash
#   source <kit>/setup-yz-env.sh
#
# What it sets up:
#   - sbndcode v10_14_02_03 (e26:prof) from CVMFS: fcl, services, cfg, data.
#   - larwirecell built against the newer WCT (YZ_LWC_DIR), instead of the
#     CVMFS larwirecell.
#   - the WCT libraries of branch sbnd-yz-depo-scaling (YZ_WCT_LIB).  Only that
#     branch has DepoTransformYZ.  They are loaded with LD_PRELOAD, because
#     larwirecell carries an RPATH to the WCT it was built against, and an RPATH
#     wins over LD_LIBRARY_PATH.  The preload list is in WCT_YZ_PRELOAD; the run
#     script sets LD_PRELOAD=$WCT_YZ_PRELOAD for the detsim job only.  To run
#     lar by hand:  LD_PRELOAD=$WCT_YZ_PRELOAD lar -c ...
#   - WIRECELL_PATH = <kit>/cfg : (sbndcode's own path) : YZ_MAP_PATH
#     The kit cfg only ADDS files with new names (…-yz.jsonnet), so it shadows
#     nothing of sbndcode.  YZ_MAP_PATH is a directory that holds
#     sbnd/sbnd-yzmap-*.json.bz2 (a wire-cell-data clone); it goes last, so it
#     cannot shadow sbndcode files either.
#   - FHICL_FILE_PATH starts with <kit>/fcl.
#
# Override any of these before sourcing to use your own build or map:
#   YZ_WCT_LIB   WCT libraries of branch sbnd-yz-depo-scaling
#   YZ_LWC_DIR   larwirecell product dir (holds fcl/ and slf7.x86_64.e26.prof/lib)
#   YZ_MAP_PATH  directory that contains sbnd/<map>.json.bz2

YZ_KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export YZ_KIT
: "${YZ_WCT_LIB:=/exp/sbnd/app/users/yuhw/opt-yz/lib}"
: "${YZ_LWC_DIR:=/exp/sbnd/app/users/yuhw/opt/larwirecell/v10_01_28}"
: "${YZ_MAP_PATH:=/exp/sbnd/app/users/yuhw/wire-cell-data}"
export YZ_WCT_LIB YZ_LWC_DIR YZ_MAP_PATH

if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    echo "setup-yz-env.sh: not in SL7; start the fnal-dev-sl7 container first" >&2
    return 1 2>/dev/null || exit 1
fi

source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh >/dev/null 2>&1
setup sbndcode v10_14_02_03 -q e26:prof || { echo "setup-yz-env.sh: setup sbndcode failed" >&2; return 1 2>/dev/null || exit 1; }

# larwirecell: replace the CVMFS one (-j: leave its dependencies set up).
unsetup -j larwirecell
_lwc_lib=$YZ_LWC_DIR/slf7.x86_64.e26.prof/lib
for _d in "$YZ_WCT_LIB" "$_lwc_lib" "$YZ_MAP_PATH/sbnd"; do
    [[ -d "$_d" ]] || echo "setup-yz-env.sh: WARNING: missing directory $_d" >&2
done
export CET_PLUGIN_PATH=$_lwc_lib:$CET_PLUGIN_PATH
export LD_LIBRARY_PATH=$YZ_WCT_LIB:$_lwc_lib:$LD_LIBRARY_PATH
export FHICL_FILE_PATH=$YZ_KIT/fcl:$YZ_LWC_DIR/fcl:$FHICL_FILE_PATH
export WIRECELL_PATH=$YZ_KIT/cfg:$WIRECELL_PATH:$YZ_MAP_PATH

# Every WCT library a detsim job loads (larwirecell's NEEDED + the plugins in
# the fcl + their dependencies), all from the branch build, dependencies first.
# They are given by BARE NAME, not by path: ld.so then finds them through
# LD_LIBRARY_PATH (YZ_WCT_LIB is first) and records the bare name, so every
# later "NEEDED libWireCellX.so" matches the preloaded copy and no RPATH
# (larwirecell's to its own WCT, the branch libraries' to their build tree)
# can load a second copy.  The WCT libraries carry no SONAME, so a full-path
# preload does not have this effect.
WCT_YZ_PRELOAD=
for _l in libWCPPyUtil libWCPQuickhull libWireCellUtil libWireCellIface libWireCellAux \
          libWireCellApps libWireCellMcs libWireCellClus libWireCellGen libWireCellSigProc \
          libWireCellRoot libWireCellPgraph libWireCellTbb libWireCellPytorch; do
    if [[ -f "$YZ_WCT_LIB/$_l.so" ]]; then
        WCT_YZ_PRELOAD=${WCT_YZ_PRELOAD:+$WCT_YZ_PRELOAD:}$_l.so
    else
        echo "setup-yz-env.sh: WARNING: missing $YZ_WCT_LIB/$_l.so" >&2
    fi
done
export WCT_YZ_PRELOAD
unset _l _d _lwc_lib

echo "YZ kit env: sbndcode $SBNDCODE_VERSION, WCT libs $YZ_WCT_LIB, larwirecell $YZ_LWC_DIR"
