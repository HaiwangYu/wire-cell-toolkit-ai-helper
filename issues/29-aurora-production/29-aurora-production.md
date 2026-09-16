# Issue 29: Aurora production of img-clus-match-pr (port of issue 27)

Tracking: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/29
Plan: `docs/aurora-img-clus-match-pr-production-plan.md`.

## scripts/
- `probe-aurora.pbs` -- phase A1 probe (node facts, filesystems incl. Eagle, cgroup, userns/fuse, proxy, apptainer modes, Recipe A' via twester's Flare UPS tree, Recipe B via cvmfsexec + fnal-dev-sl7 + eventdump of the nc-sideband file). Submit with `-A neutrinoGPU::debug2 -q debug -l filesystems=flare:home` after copying the cvmfsexec template and the nc-sideband file to Flare.

## log
- 2026-09-16: plan v1 written from ALCF docs + sbank + colleagues' Aurora tooling (nothing run on Aurora yet); issue opened.
