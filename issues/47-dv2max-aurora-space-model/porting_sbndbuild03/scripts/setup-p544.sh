# Issue 47: the production step-2 setup with the toolkit swapped for the test build
# (P5: PR 544 updated on master, local branch p544-on-master 5aa05cf1).  Source INSIDE SL7.
# Whole path entries are replaced (opt/larwirecell is untouched).  The aurora_space bundle is found through
# WIRECELL_PATH: issue47/wcdata/dv2max/sbnd/aurora_space -> the copy of Sne's bundle (not in wire-cell-data).
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh
_swap() {  # _swap VAR old new: replace the path entry 'old' by 'new' in $VAR
  local v=$1 o=$2 n=$3
  export $v="$(echo "${!v}" | tr ':' '\n' | awk -v o="$o" -v n="$n" '$0==o {print n; next} {print}' | paste -sd:)"
}
Y=/exp/sbnd/app/users/yuhw; T=/exp/sbnd/data/users/yuhw
_swap PATH            $Y/opt/bin              $T/opt-p544/bin
_swap LD_LIBRARY_PATH $Y/opt/lib              $T/opt-p544/lib
_swap PYTHONPATH      $Y/opt/python           $T/opt-p544/python
_swap WIRECELL_PATH   $Y/wire-cell-toolkit/cfg $T/wct-p544/cfg
_swap WIRECELL_PATH   $Y/opt/share/wirecell   $T/opt-p544/share/wirecell
export WIRECELL_PATH=$WIRECELL_PATH:$T/production-prep/issue47/wcdata
export PYTHONPATH=$Y/pyenv-dv2:$PYTHONPATH      # lightgbm 4.6.0 + threadpoolctl (glibc-2.17 wheels)
