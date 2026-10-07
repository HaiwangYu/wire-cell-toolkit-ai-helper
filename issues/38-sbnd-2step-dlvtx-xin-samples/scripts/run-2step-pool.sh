#!/bin/bash
# Our larwirecell 2-step chain (issue 33) with the DL-vertex dump (issue 35) over many work units on
# sbndbuild03 (issue 38).  One work unit = one `lar` step-1 process (a whole reco1 file, or an
# --nskip/-n chunk of one) followed by one standalone `wire-cell` step 2 on its tar.
#
#   run-2step-pool.sh <units.tsv> <run dir> <sim|data> [MAXPAR]
#
# units.tsv: unit_id <TAB> reco1 file <TAB> nskip <TAB> nevents (nevents "all" = the whole file)
#
# Half-machine cap (owner's rule: <= half of the 64 cores / 125 GB):
#   * EVERY process runs under `taskset -c $CPUSET` (default 32-63, 32 cores), so even thread-happy
#     libraries (torch in the DL vertex) cannot use more than half the cores in total;
#   * at most MAXPAR units at once (default 28), and no new unit starts while the RSS summed over
#     this user's lar/wire-cell processes exceeds MEM_GUARD_GB (default 50).
#   OMP/MKL/torch thread counts are set to 1 per process.
#
# Layout:  <run>/<unit>/ql/{qlpctree.tar.gz, mabc.zip, nugraph.h5, lar.log.gz, time.txt, rc}
#          <run>/<unit>/pr/{pr_evt<E>/tracking-pr.root, mabc-pr.zip, wct.log.gz, time.txt, rc}
#          <run>/units.tsv (copy), <run>/RUN-RECORD.txt (pins), <run>/pool.log
# Re-running skips units whose pr/rc is 0 (resume after an interruption).
set -u
UNITS=${1:?units.tsv}; RUN=${2:?run dir}; REALITY=${3:?sim|data}; MAXPAR=${4:-28}
CPUSET=${CPUSET:-32-63}; MEM_GUARD_GB=${MEM_GUARD_GB:-50}; WCT_TLAS=${WCT_TLAS:---tla-code dl_vtx_dump=true}
case $REALITY in sim) FCL=wcls-img-clus-matching.fcl ;; data) FCL=wcls-img-clus-matching-data.fcl ;; *) echo "reality sim|data"; exit 2 ;; esac
SBND=/exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd
WRAP=/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh
mkdir -p $RUN; cp -f $UNITS $RUN/units.tsv
WCT=/exp/sbnd/app/users/yuhw/wire-cell-toolkit; LWC=/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell
{
  echo "start      $(/bin/date '+%F %T %Z') on $(hostname)"
  echo "reality    $REALITY  fcl $FCL  step-2 TLAs: $WCT_TLAS"
  echo "toolkit    $(git -C $WCT rev-parse --short HEAD) ($(git -C $WCT branch --show-current)); cfg changes: $(git -C $WCT status --short cfg | wc -l)"
  echo "larwirecell $(git -C $LWC rev-parse --short HEAD) ($(git -C $LWC branch --show-current))"
  echo "wcp        $(git -C $SBND rev-parse --short HEAD) ($(git -C $SBND branch --show-current)); sbnd changes: $(git -C $SBND status --short . | wc -l)"
  echo "wire-cell-data $(git -C /exp/sbnd/app/users/yuhw/wire-cell-data rev-parse --short HEAD)"
  echo "units      $(wc -l < $UNITS); MAXPAR $MAXPAR; CPUSET $CPUSET; MEM_GUARD_GB $MEM_GUARD_GB"
} >> $RUN/RUN-RECORD.txt

# one unit, executed INSIDE SL7 with setup-ap.sh sourced
cat > $RUN/unit.sh <<EOF
#!/bin/bash
# unit.sh <unit_id> <file> <nskip> <nevents>
u=\$1; f=\$2; k=\$3; n=\$4
D=$RUN/\$u; mkdir -p \$D/ql \$D/pr
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TORCH_NUM_THREADS=1
export FHICL_FILE_PATH=$SBND:\$FHICL_FILE_PATH   # the step-1 fcls and their #includes live in wcp sbnd/
NARG=""; [ "\$n" = all ] || NARG="-n \$n"
cd \$D/ql
if [ "\$(cat rc 2>/dev/null)" != 0 ]; then
  /usr/bin/time -v -o time.txt taskset -c $CPUSET lar \$NARG --nskip \$k -c $FCL -s \$f --no-output > lar.log 2>&1
  echo \$? > rc
  grep -E "frame_apply_at_caf|Exception|ERROR|FATAL" lar.log | sort | uniq -c | sort -rn | head -20 > lar-digest.txt
  gzip -f lar.log
fi
[ "\$(cat rc)" = 0 ] && [ -f qlpctree.tar.gz ] || { echo 98 > \$D/pr/rc; exit 1; }
cd \$D/pr
python3 -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('SCN_Vertex') and u.find_spec('torch') and u.find_spec('sparseconvnet') else 1)" \\
  || { echo "SCN_Vertex/torch/sparseconvnet not importable: PYTHONPATH=\$PYTHONPATH" > scn-env-error.txt; echo 97 > rc; exit 1; }
/usr/bin/time -v -o time.txt taskset -c $CPUSET wire-cell -l stdout -L debug -c pgrapher/experiment/sbnd/wct-pr.jsonnet \\
    --tla-str input=\$D/ql/qlpctree.tar.gz --tla-str reality=$REALITY $WCT_TLAS > wct.log 2>&1
echo \$? > rc
grep -E "Exception|ERROR|FATAL|error" wct.log | sort | uniq -c | sort -rn | head -20 > wct-digest.txt
grep -c "DL vertex failed" wct.log > dl_fail          # must be 0 (T1 gate)
grep -c "SCN_Vertex" wct.log > scn_lines
gzip -f wct.log
EOF
chmod +x $RUN/unit.sh

ourmem_gb() { ps -u $USER -o rss=,comm= | awk '$2 ~ /^(lar|wire-cell)$/ {s+=$1} END {printf "%d", s/1048576}'; }

echo "$(/bin/date '+%F %T') pool start: $(wc -l < $UNITS) units" >> $RUN/pool.log
nrun=0
while IFS=$'\t' read -r u f k n; do
  [ -z "$u" ] && continue; [[ $u == \#* ]] && continue
  [ "$(cat $RUN/$u/pr/rc 2>/dev/null)" = 0 ] && continue
  while [ $nrun -ge $MAXPAR ]; do wait -n; nrun=$((nrun-1)); done
  while [ "$(ourmem_gb)" -ge $MEM_GUARD_GB ]; do sleep 20; done
  # setup-dlvtx.sh: the uBooNE scn product (torch, sparseconvnet) + opt/python (SCN_Vertex.py).  WITHOUT
  # IT THE DL VERTEX FAILS SILENTLY ("DL vertex failed: ... No module named 'SCN_Vertex'"), the job still
  # exits 0 and every candidate falls back to the traditional vertex (found in the issue-38 smoke).
  # setup-dlvtx.sh calls path-prepend, a FUNCTION defined by setup-local-opt.sh that the wrapper's
  # `bash -c` does not inherit -> "command not found", PYTHONPATH unchanged, and `source` still
  # returns 0.  So setup-ap.sh is re-sourced (idempotent) in the same shell first, and unit.sh
  # refuses to run step 2 unless SCN_Vertex is importable.
  ( SL7_SETUP=$SBND/setup-ap.sh $WRAP bash -c "cd $SBND && source $SBND/setup-ap.sh >/dev/null 2>&1; source $SBND/setup-dlvtx.sh && $RUN/unit.sh $u $f $k $n" > /dev/null 2>&1
    echo "$(/bin/date '+%F %T') $u ql_rc=$(cat $RUN/$u/ql/rc 2>/dev/null) pr_rc=$(cat $RUN/$u/pr/rc 2>/dev/null) dl_fail=$(cat $RUN/$u/pr/dl_fail 2>/dev/null)" >> $RUN/pool.log ) &
  nrun=$((nrun+1))
  sleep 2
done < $UNITS
wait
echo "$(/bin/date '+%F %T') pool done" >> $RUN/pool.log
echo "end        $(/bin/date '+%F %T %Z')" >> $RUN/RUN-RECORD.txt
