# wire-cell-toolkit-ai-helper

Working notes, scripts and per-issue records for SBND Wire-Cell development,
kept so that Claude Code sessions (and people) can pick up where the last one
stopped. Data, logs and figures are gitignored; only documents and scripts are
tracked.

## Start here

- **[`docs/sbnd-1step-build-run-validate.md`](docs/sbnd-1step-build-run-validate.md)**
  — the procedure: build WCT + larwirecell on sbndbuild/sbndgpvm (SL7), sync the PR
  operating point, run the 1-step, run Xin's 2-step here, and compare. Every step
  names its gate and the trap it guards against (RPATH into the build tree, the
  stale operating point, the reco1 reader race, the dictionary segfault, …).
- `wcp-porting-img/sbnd/CLAUDE.md` and `sbnd/docs/8-build-and-run-both-chains.md`
  in the experiment repo — the narrative behind the procedure.

## Layout

- `issues/<n>-<slug>/` — one folder per GitHub issue: the doc plus its scripts.
  Notable: `17-…` (operating-point resync tooling), `20-…` (chain comparison
  tools), `23-…` / `24-…` (the two validation rounds against Xin's production).
- `docs/` — procedures that outlive any single issue.
