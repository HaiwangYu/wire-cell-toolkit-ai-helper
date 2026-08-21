#!/bin/bash
# Beam-off sample prep: file list -> merged+frameshifted artROOT -> manifest.
#   ./prep-beam-off.sh <files.lst> <outdir> [target_events]
#
# Mirrors the beam-on recipe (add-frameshift-data-2nd-2k-2026-08-15): one
# `lar -c run_frameshift.fcl -S <list> -n <N> -o <out.root>` pass that merges the
# input reco1 files AND adds the FrameShift product in the same job.
#
# WHY FRAMESHIFT IS NOT OPTIONAL: every Gen2 real-data reco1 file must have
# run_frameshift.fcl applied before the imaging chain, or the TPC/PMT time
# alignment is wrong and Q/L matching is meaningless.  See
# sbnd-gen2-data/docs (reference_gen2_frameshift).
#
# GOTCHA kept from run-frameshift.sh: capture positional params BEFORE sourcing;
# sourcing ups/bashrc clobbers $1/$2.
LIST="$1"; OUT="$2"; TARGET="${3:-1000}"
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
set -o pipefail
mkdir -p "$OUT"/logs
MERGED="$OUT/data_beamoff_reco1_frameshift_1k.root"
# Own cwd: concurrent lar jobs collide on art's sqlite files.
WD="$OUT/logs/wd_frameshift"; mkdir -p "$WD"; cd "$WD" || exit 1
echo "frameshift+merge: $(wc -l < "$LIST") input file(s) -> $MERGED (target $TARGET events)"
lar -c run_frameshift.fcl -S "$LIST" -n "$TARGET" -o "$MERGED" \
    > "$OUT/logs/frameshift.log" 2>&1
rc=$?
echo "  rc=$rc  $(ls -la "$MERGED" 2>/dev/null | awk '{printf "%.2f GB", $5/1073741824}')"
[ $rc -ne 0 ] && { echo "FRAMESHIFT FAILED -- see $OUT/logs/frameshift.log"; tail -20 "$OUT/logs/frameshift.log"; exit $rc; }
# Verify the FrameShift product actually landed; a merge that silently produced
# no FrameShift would still give a plausible-looking file.
python3 -c "
import ROOT, sys
ROOT.gErrorIgnoreLevel = ROOT.kError
f = ROOT.TFile.Open('$MERGED'); t = f.Get('Events')
n = t.GetEntries()
fs = [b.GetName() for b in t.GetListOfBranches() if 'FrameShift' in b.GetName()]
print('  events=%d  FrameShift product: %s' % (n, fs if fs else 'MISSING !!'))
sys.exit(0 if fs else 1)
" || { echo "FrameShift product MISSING in the merged file"; exit 1; }
echo "$MERGED" > "$OUT/beam-off-files.lst"
exec "$(dirname "$0")/make-manifest.sh" "$OUT/beam-off-files.lst" "$OUT/beam-off.manifest" 0
