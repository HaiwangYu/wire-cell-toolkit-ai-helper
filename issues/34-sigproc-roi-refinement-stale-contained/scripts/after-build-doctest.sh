#!/bin/bash
# Issue 34: wait for build job $1, then run doctest-sigproc.pbs (the debug queue allows 1 queued job per user,
# so it cannot be chained with -W depend).  Summary in /lus/flare/projects/neutrinoGPU/yuhw/aurora-build-logs/i34b-summary.out.
cd /lus/flare/projects/neutrinoGPU/yuhw/aurora-build-logs
while qstat $1 >/dev/null 2>&1; do sleep 60; done; echo "build $1 done $(date)"
awk "/job $1/{f=1} f" build-wct-lwc.out | grep -E "version:|WCB_RC|nlibs|single_threaded|fmt_needed|rpath_stripped|ldd_not_found|error"
awk "/job $1/{f=1} f" build-wct-lwc.out | grep -q "WCB_RC=0" || { echo "BUILD FAILED"; exit 1; }
T=$(qsub -o /lus/flare/projects/neutrinoGPU/yuhw/aurora-build-logs/doctest-sigproc-i34b.out /lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit-ai-helper/issues/34-sigproc-roi-refinement-stale-contained/scripts/doctest-sigproc.pbs); echo doctest=$T
while qstat ${T%%.*} >/dev/null 2>&1; do sleep 60; done; grep -v bashrc doctest-sigproc-i34b.out; echo "ALL DONE $(date)"
