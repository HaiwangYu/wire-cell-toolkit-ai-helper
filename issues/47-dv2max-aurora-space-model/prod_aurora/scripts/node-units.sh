#!/bin/bash
# ai-helper #47 (prod_aurora): step 2 (test build, aurora_space) on hold-out units, NPAR at a time.
#   node-units.sh UNITS_TSV RUNDIR [NPAR]    UNITS_TSV = sample<TAB>unit<TAB>dlspace-relative unit dir or tar path[<TAB>sim|data]
set -u
Y=/lus/flare/projects/neutrinoGPU/yuhw
P=$Y/production-prep/dv2max-aurora-space
E=$Y/sbnd-wirecell-production/aurora
export UNITS=$1 RUN=$2 NPAR=${3:-64} P E Y
export SL7_SETUP=$P/setup-dv2test.sh
one() {
  s=$1; u=$2; d=$3; real=${4:-sim}
  O=$RUN/$s/$u; [ -f $O/DONE ] && return 0
  rm -rf $O; mkdir -p $O
  case $d in /*) T=$d;; *) T=$Y/production-prep/dlspace/$d/ql/all/qlpctree.tar.gz;; esac
  [ -f "$T" ] || { echo "$s $u rc 2 no tar $T" >> $RUN/units.log; return 0; }
  n=$(cat $Y/production-prep/dlspace/$d/reco1_events 2>/dev/null || echo 50)
  t0=$(/bin/date +%s)
  PASS_ENV='DV2_HOOK_LOG DLVTX_SPACE WC_EVT_SUBDIR' DV2_HOOK_LOG=$O/dv2hook.jsonl DLVTX_SPACE=true WC_EVT_SUBDIR='pr_evt{run}_{subrun}_{event}' \
    $E/env/aurora/in-aurora-sl7.sh /usr/bin/time -v -o $O/time.txt /usr/bin/timeout -k 60 $((600 + 300 * n)) \
    $E/bin/step2.sh $T $O/pr $real > $O/step2.out 2>&1
  rc=$?
  echo "$s $u rc $rc wall $(( $(/bin/date +%s) - t0 )) calls $(cat $O/dv2hook.jsonl 2>/dev/null | wc -l)" >> $RUN/units.log
  echo $rc > $O/rc; [ $rc = 0 ] && touch $O/DONE
}
export -f one
mkdir -p $RUN
echo "start $(hostname) $(/bin/date -u) units $(wc -l < $UNITS) npar $NPAR" >> $RUN/units.log
tr '\t' ' ' < $UNITS | xargs -P $NPAR -L 1 bash -c 'one $0 $1 $2 $3'
echo "end $(hostname) $(/bin/date -u)" >> $RUN/units.log
