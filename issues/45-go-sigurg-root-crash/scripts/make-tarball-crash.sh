#!/bin/bash
# ai-helper #45: the code tarball for the crash-rate grid test.
#   make-tarball-crash.sh <out.tar.gz>
# = the production tarball (sbnd-wirecell-production/fermigrid/bin/make-tarball.sh: master = the local
#   opt/ + wire-cell-toolkit/cfg, exactly as the 11-11 local runs) + the PR #543 build as an overlay:
#   opt-pr543v2/{bin/wire-cell, lib/libWireCell*.so *.rootmap *.pcm, python, share/wirecell} (debug info
#   stripped, like the master libs), wct-pr543/cfg, pyenv-dv2 (lightgbm), wire-cell-data/dv2max/sbnd/r7_cloud,
#   the relocated PR setup (setup-pr543v2.sh), the job script (crash-job.sh), and venv-site/ (see below).
set -euo pipefail
OUT=$(realpath -m "${1:?out.tar.gz}"); Y=/exp/sbnd/app/users/yuhw; H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ST=$(mktemp -d "${TMPDIR:-/tmp}/wccrash.XXXXXX"); trap 'rm -rf "$ST"' EXIT
$Y/sbnd-wirecell-production/fermigrid/bin/make-tarball.sh "$ST/base.tar.gz"
tar -C "$ST" -xzf "$ST/base.tar.gz"; rm "$ST/base.tar.gz"; W=$ST/wc
cp_rel() { for r in "$@"; do mkdir -p "$W/$(dirname "$r")"; cp -a "$Y/$r" "$W/$r"; done; }
cd $Y
cp_rel opt-pr543v2/bin/wire-cell
for f in opt-pr543v2/lib/libWireCell*.so opt-pr543v2/lib/libWCP*.so opt-pr543v2/lib/*.rootmap opt-pr543v2/lib/*.pcm; do [ -e "$f" ] && cp_rel "$f"; done
cp_rel opt-pr543v2/python opt-pr543v2/share/wirecell wct-pr543/cfg pyenv-dv2 wire-cell-data/dv2max/sbnd/r7_cloud
find "$W/opt-pr543v2" -type f \( -name '*.so' -o -path '*/bin/wire-cell' \) -exec strip --strip-debug {} +
find "$W/opt-pr543v2/python" "$W/pyenv-dv2" -name __pycache__ -prune -exec rm -rf {} +
# the wire-cell-python venv modules the embedded Python imports locally (DV2 -> lightgbm -> scipy; lightgbm also
# imports pandas / matplotlib when present).  Locally they come from the venv because its python3 is first on PATH.
V=wire-cell-python/venv/lib/python3.9/site-packages
mkdir -p "$W/venv-site"
for m in scipy scipy.libs pandas matplotlib dateutil pytz cycler kiwisolver pyparsing packaging six.py; do cp -a "$Y/$V/$m" "$W/venv-site/"; done
find "$W/venv-site" -name __pycache__ -prune -exec rm -rf {} +
cp "$H/setup-pr543v2.sh" "$H/crash-job.sh" "$W/"
{ echo "--- ai-helper #45 overlay"
  echo "wct-pr543 $(git -C $Y/wct-pr543 rev-parse --short HEAD) (pr543-review2 = sbnd-wc-flatcaf + PR #543 head f3767016) $(git -C $Y/wct-pr543 status --short cfg | wc -l) dirty cfg files"
  echo "opt-pr543v2/lib/libWireCellClus.so md5 (unstripped) $(md5sum < $Y/opt-pr543v2/lib/libWireCellClus.so | cut -c1-12)"
  echo "opt/bin/wire-cell md5 $(md5sum < $Y/opt/bin/wire-cell | cut -c1-12), opt-pr543v2/bin/wire-cell md5 $(md5sum < $Y/opt-pr543v2/bin/wire-cell | cut -c1-12) (unstripped)"
} >> "$W/TARBALL-PROVENANCE.txt"
tar -C "$ST" -czf "$OUT" wc
echo "$OUT: $(du -h "$OUT" | cut -f1)"; cat "$W/TARBALL-PROVENANCE.txt"
