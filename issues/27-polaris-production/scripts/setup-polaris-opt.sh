# Polaris port of wcp-porting-img/sbnd/setup-local-opt.sh: local WCT + larwirecell
# install under $OPT on top of sbndcode from CVMFS.  Source INSIDE the SL7
# container (in-polaris-sl7.sh does that for you).
#
# Layout (Eagle):
#   $OPT                = WCT install (lib/, include/, share/wirecell/, bin/)
#   $OPT/larwirecell/$LWC_VER/slf7.x86_64.e26.prof/lib = hand-copied larwirecell .so
#   $WCT_SRC            = wire-cell-toolkit checkout (its cfg/ is prepended in setup-polaris-ap.sh)
#   $WCD                = wire-cell-data checkout
Y=/lus/eagle/projects/neutrinoGPU/yuhw
export OPT=$Y/opt
export WCT_SRC=$Y/wire-cell-toolkit
export WCD=$Y/wire-cell-data
export WCP_SBND=$Y/wcp-porting-validation/sbnd
export LWC_VER=${LWC_VER:-v10_01_28}

source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh >/dev/null 2>&1
# sbndcode v10_14_02_03 -> larsoft v10_14_02_02, the pairing of the FNAL MRB area.
setup sbndcode v10_14_02_03 -q e26:prof
setup cetmodules v3_24_00
setup cmake v3_27_4
setup patchelf 0.13.1
setup gdb 2>/dev/null

path-remove ()  { local IFS=':'; local NEWPATH; local DIR; local PATHVARIABLE=${2:-PATH}
  for DIR in ${!PATHVARIABLE}; do [ "$DIR" != "$1" ] && NEWPATH=${NEWPATH:+$NEWPATH:}$DIR; done
  export $PATHVARIABLE="$NEWPATH"; }
path-prepend () { path-remove "$1" "$2"; local PATHVARIABLE="${2:-PATH}"
  export $PATHVARIABLE="$1${!PATHVARIABLE:+:${!PATHVARIABLE}}"; }
path-append ()  { path-remove "$1" "$2"; local PATHVARIABLE="${2:-PATH}"
  export $PATHVARIABLE="${!PATHVARIABLE:+${!PATHVARIABLE}:}$1"; }

# Drop the cvmfs larwirecell/wirecell that sbndcode pulled in so their plugins
# and cfg cannot shadow ours.  (UPS-level unsetup; the paths below then win.)
unsetup larwirecell 2>/dev/null
unsetup wirecell 2>/dev/null
# The ambient spdlog is v1_9_2 (bundled fmt).  WCT's headers were built against
# spdlog v1_14_1 + external fmt v11_0_2 (configure-wct-polaris.sh); anything that
# includes them (larwirecell) must see the same pair, else
# "spdlog/fmt/fmt.h: fatal error: fmt/core.h: No such file" (2026-09-15).
unsetup spdlog 2>/dev/null
setup spdlog v1_14_1 -q e26:prof
setup fmt v11_0_2 -q e26:prof 2>/dev/null

LWC_FQ="$OPT/larwirecell/$LWC_VER/slf7.x86_64.e26.prof"
export LARWIRECELL_DIR="$OPT/larwirecell/$LWC_VER"
export LARWIRECELL_VERSION=$LWC_VER
export LARWIRECELL_FQ_DIR="$LWC_FQ"
export LARWIRECELL_INC="$OPT/larwirecell/$LWC_VER/include"
export LARWIRECELL_LIB="$LWC_FQ/lib"
export LARWIRECELL_FCL="$OPT/larwirecell/$LWC_VER/fcl"
export WIRECELL_FQ_DIR=$OPT
export WIRECELL_DIR=$OPT
export WIRECELL_INC=$OPT/include
export WIRECELL_LIB=$OPT/lib

path-prepend "$LWC_FQ/lib"        CET_PLUGIN_PATH
path-prepend "$LWC_FQ/lib"        LD_LIBRARY_PATH
path-prepend "$LARWIRECELL_FCL"   FHICL_FILE_PATH
path-prepend "$OPT"               CMAKE_PREFIX_PATH
path-prepend "$OPT/lib"           LD_LIBRARY_PATH
path-prepend "$OPT/bin"           PATH
path-prepend "$OPT/lib/python3.9/site-packages" PYTHONPATH 2>/dev/null

# WIRECELL_PATH layering as at FNAL: sbndcode cfg wins over opt/share/wirecell,
# wire-cell-data at the back.  setup-polaris-ap.sh re-layers for the AP chain.
# (UPS already put $SBNDCODE_DIR/wire-cell-cfg and sbnd_data/.../WireCell on
# WIRECELL_PATH; sbndcode cfg therefore wins over opt/share/wirecell here.)
path-prepend "$WCD"                                  WIRECELL_PATH
path-prepend "$OPT/share/wirecell"                   WIRECELL_PATH
path-prepend "$SBNDCODE_DIR/wire-cell-cfg"           WIRECELL_PATH
path-prepend . FHICL_FILE_PATH
path-prepend "$WCP_SBND" FHICL_FILE_PATH
export CXXFLAGS="-DSPDLOG_FMT_EXTERNAL"

# waf's preforked subprocess pool breaks inside the userns container ("Could not
# determine the compiler version" on the g++ probe, 2026-09-15); run subprocesses directly.
export WAF_NO_PREFORK=1

# in-polaris-sl7.sh sources this file and then execs the user's command; when
# that command is itself `bash -c ...`, shell FUNCTIONS (UPS setup/unsetup, the
# path helpers) would be lost in the child ("setup: command not found").  Export them.
for f in setup unsetup path-prepend path-append path-remove; do
    declare -F "$f" >/dev/null 2>&1 && export -f "$f"
done
