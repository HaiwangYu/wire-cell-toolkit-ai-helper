# PR #543 RE-review (v2 = PR head f3767016, bundle from wire-cell-data) (ai-helper issue): the production run setup, with the toolkit swapped for the
# PR build.  Source INSIDE SL7.  Whole path entries are replaced (opt/larwirecell is untouched).
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh
_swap() {  # _swap VAR old new: replace the path entry 'old' by 'new' in $VAR
  local v=$1 o=$2 n=$3
  export $v="$(echo "${!v}" | tr ':' '\n' | awk -v o="$o" -v n="$n" '$0==o {print n; next} {print}' | paste -sd:)"
}
Y=/exp/sbnd/app/users/yuhw
_swap PATH            $Y/opt/bin              $Y/opt-pr543v2/bin
_swap LD_LIBRARY_PATH $Y/opt/lib              $Y/opt-pr543v2/lib
_swap PYTHONPATH      $Y/opt/python           $Y/opt-pr543v2/python
_swap WIRECELL_PATH   $Y/wire-cell-toolkit/cfg $Y/wct-pr543/cfg
_swap WIRECELL_PATH   $Y/opt/share/wirecell   $Y/opt-pr543v2/share/wirecell
export PYTHONPATH=$Y/pyenv-dv2:$PYTHONPATH      # lightgbm 4.6.0 + threadpoolctl (glibc-2.17 wheels)
