# ai-helper #45: the PR #543 run setup on a grid worker (relocated twin of
# production-prep/pr543-review/v2/setup-pr543v2.sh).  Needs WC_TOP.  Source inside SL7.
source "${WC_TOP:?}/sbnd-wirecell-production/aurora/env/fnal/setup-fnal-run.sh"
_swap() { local v=$1 o=$2 n=$3; export $v="$(echo "${!v}" | tr ':' '\n' | awk -v o="$o" -v n="$n" '$0==o {print n; next} {print}' | paste -sd:)"; }
_swap PATH            $WC_TOP/opt/bin               $WC_TOP/opt-pr543v2/bin
_swap LD_LIBRARY_PATH $WC_TOP/opt/lib               $WC_TOP/opt-pr543v2/lib
_swap PYTHONPATH      $WC_TOP/opt/python            $WC_TOP/opt-pr543v2/python
_swap WIRECELL_PATH   $WC_TOP/wire-cell-toolkit/cfg $WC_TOP/wct-pr543/cfg
_swap WIRECELL_PATH   $WC_TOP/opt/share/wirecell    $WC_TOP/opt-pr543v2/share/wirecell
export PYTHONPATH=$WC_TOP/pyenv-dv2:$PYTHONPATH
