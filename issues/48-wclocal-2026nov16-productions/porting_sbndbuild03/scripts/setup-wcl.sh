# Issue 48 (WCLocal2026Nov16-FermiGrid): the production run environment on sbndbuild03 with the
# release swapped in.  Source INSIDE SL7, in the shell that then runs the steps.
#   WCT 0.38.0 (c935e30d)  -> $R/opt (wcb install of the worktree $R/wct)
#   larwirecell ad5d942    -> $R/opt/larwirecell (copies of the deployed .so, RPATH -> $R/opt/lib)
#   cfg                    -> $R/wct/cfg
#   wire-cell-data         -> the usual /exp/sbnd/app/users/yuhw/wire-cell-data (master 99c6497, has aurora_space)
#   DV2 python             -> torch/numpy from the scn product (setup-dlvtx.sh), lightgbm 4.6.0 + scipy 1.13.1 from $R/pydv2
# Every path entry equal to /exp/sbnd/app/users/yuhw/opt or under it is moved to $R/opt.
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh
WCL_R=${WCL_R:-/exp/sbnd/data/users/yuhw/wclocal-nov16}
_Y=/exp/sbnd/app/users/yuhw
_wcl_move() {  # _wcl_move VAR old-prefix new-prefix
  local v=$1 o=$2 n=$3
  export $v="$(echo "${!v}" | tr ':' '\n' | awk -v o="$o" -v n="$n" '$0==o {print n; next} index($0, o"/")==1 {print n substr($0, length(o)+1); next} {print}' | paste -sd:)"
}
for v in PATH LD_LIBRARY_PATH CET_PLUGIN_PATH PYTHONPATH WIRECELL_PATH FHICL_FILE_PATH CMAKE_PREFIX_PATH PRODUCTS; do
  _wcl_move $v $_Y/opt $WCL_R/opt
  _wcl_move $v $_Y/wire-cell-toolkit/cfg $WCL_R/wct/cfg
done
export LARWIRECELL_DIR=$WCL_R/opt/larwirecell/v10_01_28 LARWIRECELL_FQ_DIR=$WCL_R/opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof
export LARWIRECELL_INC=$LARWIRECELL_DIR/include LARWIRECELL_LIB=$LARWIRECELL_FQ_DIR/lib LARWIRECELL_FCL=$LARWIRECELL_DIR/fcl
export PYTHONPATH=$WCL_R/pydv2:$PYTHONPATH   # lightgbm 4.6.0 + threadpoolctl (pyenv-dv2) + scipy 1.13.1 (wire-cell-python venv): the grid has no venv
export GODEBUG=asyncpreemptoff=1
unset _Y
