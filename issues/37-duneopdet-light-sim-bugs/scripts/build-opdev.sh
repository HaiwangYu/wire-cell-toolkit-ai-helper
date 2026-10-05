#!/bin/bash
# Issue 37: build the proposed duneopdet change against dunesw v10_26_00d00 e26:prof (SL7 apptainer, mrb).
#   build-opdev.sh [test]        (self re-execs into SL7 via in-sl7.sh; "test" also runs the cet tests)
# The proposal lives on the uncommitted branch fix-light-sim-pileup (off develop) of $SRC.  develop and the
# v10_26_00d00 tag differ only in version strings (top-level CMakeLists.txt, ups/product_deps), so the build tree is a
# git worktree of $SRC at the tag, and the proposal's duneopdet/ subdirectory is rsynced over it before each build.
# A second worktree ($OPDEV0, the tag unchanged) is the stock-code control build when STOCK=1.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${APPTAINER_NAME:-}" ] || SL7_SETUP=none exec $HERE/in-sl7.sh /bin/bash "$0" "$@"
SRC=${SRC:-/exp/dune/data/users/yuhw/duneopdet}
WA=${WA:-/exp/dune/data/users/yuhw/wire-cell-toolkit-ai-helper-workarea/issue-37}
DEV=${OPDEV:-$WA/opdev}
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
setup dunesw v10_26_00d00 -q e26:prof > /dev/null 2>&1 || { echo "dunesw setup failed"; exit 3; }
setup mrb > /dev/null 2>&1
export MRB_PROJECT=larsoft
mkdir -p $DEV && cd $DEV || exit 3
[ -d srcs ] || { mrb newDev -v v10_26_00d00 -q e26:prof -f > newdev.log 2>&1 || { echo "newDev failed"; exit 4; }; }
source localProducts*/setup > /dev/null 2>&1
if [ ! -d srcs/duneopdet ]; then
  git -C $SRC worktree add --detach $DEV/srcs/duneopdet v10_26_00d00 > /dev/null 2>&1 || { echo "worktree failed"; exit 5; }
  (cd srcs && mrb uc > ../uc.log 2>&1) || { echo "mrb uc failed"; exit 6; }
fi
if [ "${STOCK:-0}" != 1 ]; then
  rsync -a --delete --exclude .git $SRC/duneopdet/ srcs/duneopdet/duneopdet/ || exit 7
fi
{ echo "proposal $(git -C $SRC rev-parse --abbrev-ref HEAD) @ $(git -C $SRC rev-parse --short HEAD) + uncommitted:"
  git -C $SRC status --porcelain; echo "build tree diff vs v10_26_00d00:"; git -C srcs/duneopdet status --porcelain; } > build-source.txt
mrbsetenv > setenv.log 2>&1 || { echo "mrbsetenv failed"; exit 8; }
mrb i -j16 > build.log 2>&1; rc=$?
echo "build rc=$rc ($DEV/build.log)"
[ $rc = 0 ] || exit $rc
if [ "${1:-}" = test ]; then
  (cd $MRB_BUILDDIR/duneopdet && ctest --output-on-failure > $DEV/test.log 2>&1); trc=$?
  echo "test rc=$trc ($DEV/test.log)"; exit $trc
fi
