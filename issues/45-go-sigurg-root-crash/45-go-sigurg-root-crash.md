# Issue 45: intermittent wire-cell crashes — ROOT's SIGURG handler vs the go-jsonnet Go runtime

Found while re-reviewing WCT PR #543 (ai-helper #43). Step-2 `wire-cell` jobs crash now and then (segfault, rc 139; once glibc abort, rc 6), and the same job passes when rerun. It was first taken for a PR #543 heap-corruption problem. It is not: master crashes the same way.

## Summary

- **Who dies:** in every crash with a stack dump (18 of 19), the faulting thread is a **Go runtime thread**, not Wire-Cell code. The main thread was in a different place each time (clustering, track fitting, malloc, Python I/O, torch).
- **Where Go comes from:** the toolkit is built against **go-jsonnet** (`gojsonnet v0_18_0`, `libjsonnet.so`, a Go c-shared library). Loading it starts a Go runtime inside `wire-cell`, 20–90 threads, idle after configure except for its garbage collector (forced every 2 minutes).
- **The clash:** ROOT (`TUnixSystem::Init`) installs its own handler for **SIGURG** (and SIGCHLD, SIGSEGV, SIGALRM, …) **without `SA_ONSTACK`**, replacing the handler Go installed. Go uses SIGURG to preempt its own goroutines. When Go preempts one, ROOT's handler runs on the goroutine's stack (a few KB) and overflows it, writing mostly zeros into the neighbouring goroutine's stack.
- **The two crash forms that follow:**
  - Go's GC scans the damaged stack: `runtime: g 48: unexpected return pc for runtime.gopark called from 0x0` / `fatal error: unknown caller pc`;
  - a Go thread resumes the damaged stack and returns to address 0: `#7 0x0000000000000000 in ?? ()`.
- **Secondary:** the one glibc `corrupted double-linked list` (PR `dv2_split`, `acd2`) came after a Go thread had jumped to 0: ROOT's crash handler ran `system("gdb …")` while the main thread was inside malloc.
- **Why a rerun passes:** it depends on when the signal lands relative to which goroutine is running — thread timing, not event data.
- **Not PR #543:** master crashed identically (`runs/master/s40-2`: `g 53: unexpected return pc … fatal error: unknown caller pc`, main thread in the same torch call as two PR crashes).

## Evidence

### The installed handlers (gdb, live processes)

`scripts/local/sigprobe.sh` starts `wire-cell` on a small input inside SL7, attaches gdb after configure (90 s) and calls `__sigaction(sig, NULL, buf)` for each signal (`scripts/local/sig.gdb`). Output: `scripts/local/sigprobe-{master,pr}.out`. Master and PR builds are the same:

| signal | handler | flags | `SA_ONSTACK` |
|---|---|---|---|
| SIGURG (23) | ROOT `sighandler(int)`, `libCore.so.6.28` | `0x14000000` (`SA_RESTORER\|SA_RESTART`) | **no** |
| SIGCHLD, SIGSEGV, SIGBUS, SIGFPE, SIGABRT, SIGALRM, SIGUSR2, SIGWINCH | the same ROOT handler | the same | no |
| SIGINT, SIGPIPE | ignored | | |

Go's runtime requires every handler for a signal it can receive on a goroutine stack to use `SA_ONSTACK`, and it relies on its own SIGURG handler for preemption.

### The crashes (PR #543 review area, `production-prep/pr543-review`)

| run | mode | rc | Go fatal / jump to 0 | faulting thread | main thread at |
|---|---|---|---|---|---|
| v1 `nuecc48-s32-40` | PR `dv2_snap` | 139 | jump to 0 | Go (T44) | `form_point_association` |
| v1 `7a1b` | PR `dv2_snap` | 139 | jump to 0 | Go (T2) | `PointCloud::Tree::ScopedBase::fill_cache` |
| v1 `dffa` | PR `dv2_snap` | 11 | — (no stack dump) | | |
| v1 `nuecc48-s40-48` | PR `original` | 139 | Go fatal | Go GC | torch `FunctionSignature::parse` |
| v1 rerun `nuecc48-s40-48` try2 | PR `original` | 139 | Go fatal | Go GC | torch `FunctionSignature::parse` |
| v2 `3750` | PR `dv2_split` | 139 | jump to 0 | Go (T11) | nanoflann, `recompute_shower_kine_charge` |
| v2 `acd2` | PR `dv2_split` | 6 | jump to 0, then glibc abort | Go (T18) | `Cluster::hough_transform` |
| v2 `ncpi0-s13-19` | PR `dv2_split_move` | 139 | jump to 0 | Go (T23) | Python `_io_FileIO_readall` (DV2 import) |
| v2 `7a1b` | PR `dv2_split_move` | 139 | jump to 0 | Go (T26) | numpy `_int_malloc` (DV2 call) |
| v2 `nuecc48-s40-48` | PR `original` | 139 | Go fatal | Go GC | `_int_malloc` |
| v2 `2af0` | PR `original` | 139 | jump to 0 | Go (T2) | `TrackFitting::form_map_graph` |
| crashrate `7a1b` ×2 | PR `dv2_split_move` | 139 | jump to 0 | Go | torch `sgemm`; `_int_malloc` |
| crashrate `acd2` ×2 | PR `original` | 139 | jump to 0; Go fatal | Go | `_Rb_tree`; Eigen `realloc` |
| crash-study `s40-2` | **master** | 139 | **Go fatal** | Go GC | torch `FunctionSignature::parse` |
| crash-study `s40-2`, `s40-9` | PR `original` | 139 | jump to 0 | Go | `form_point_association`; … |

In every dump, all threads other than main are Go runtime threads (`runtime.futexsleep`, `runtime.mPark`, `runtime.sysmon`, …). With `OMP_NUM_THREADS=1` there are no torch / TBB worker threads.

### The earlier "PR only" impression

Before the crash study, master had 0 crashes in 41 runs and the PR builds ~6 %. That was luck plus easier inputs: many PR runs were repeats on the crash-prone `nuecc48-s40-48`.

### Repeat test on the crash-prone input (sbndbuild03, 2026-11-12)

`data--nuecc48-s40-48` (8 data nueCC events), 10 repeats per mode, `scripts/local/run-one.sh` (the review's `run-step2.sh` + an optional env var):

| mode | crashes |
|---|---|
| master | 1/10 |
| PR `original` | 2/10 |
| PR `original` + `GODEBUG=asyncpreemptoff=1` | 0/10 |

`GODEBUG=asyncpreemptoff=1` stops Go from sending SIGURG at all (Go 1.19: no async preemption, and the GC's `suspendG` falls back to cooperative preemption). 0/10 against 3/20 is suggestive, not proof. A 30-run confirmation was cut off by the sbndbuild03 reboot of 2026-11-12 08:51 (none finished).

### All runs so far, by mode (each run counted once)

| mode | runs | crashes |
|---|---|---|
| master | 52 | 1 |
| PR `original` (uboone SCN) | 83 | 8 |
| PR DV2 methods | 190 | 9 |
| PR `original`, Go preemption off | 10 | 0 |

The inputs differ between modes, so these totals cannot be compared directly. On `nuecc48-s40-48` alone: master 1/11, PR `original` 5/15 (p ≈ 0.2).

## Grid test: the same events, 4 modes, 3 passes (FermiGrid)

The owner asked for the same ~100 events in each mode, the hard event included. sbndbuild03 is down, so it runs on FermiGrid.

- **Inputs (10 qlpctrees, 103 events):** every input that crashed at least once (`nuecc48-s40-48`, `nuecc48-s32-40`, `ncpi0-s13-19`, `7a1b`, `acd2`, `2af0`, `3750`, `dffa`), plus `1dca` and `ncpi0-s0-7`. Staged at `/pnfs/sbnd/scratch/users/yuhw/pr543-crash-study/inputs/`.
- **Modes:** master; PR `original` (old model); PR `dv2_split_move` (new model, the PR's default); PR `original` + `GODEBUG=asyncpreemptoff=1` (the candidate fix).
- **Jobs:** 10 inputs × 4 modes × 3 passes = 120, one `wire-cell` per job (`scripts/tasks.txt`).
- **Code:** `scripts/make-tarball-crash.sh` = the production tarball (`fermigrid/bin/make-tarball.sh`: master = local `opt/`, toolkit cfg `4b6853d4`) + the PR build overlay (`opt-pr543v2`, `wct-pr543/cfg` `4291a668`, `pyenv-dv2`, the DV2 bundle) and `scripts/setup-pr543v2.sh` (relocated).
- **Job:** `scripts/crash-job.sh` runs exactly the local review command (`-L debug`, `dl_vtx_dump`, `flat_tree`, truth match on MC, 1 thread). It writes `<mode>/<input>-p<pass>.<cluster>.<index>.tar.gz` (`summary.txt` with rc, crash signature, host, CPU; `time.txt`; `wct.log.gz`). A crash is a result, not a job failure.
- **Submit:** `scripts/submit-crash.sh <tarball> tasks.txt <tag>`; 4500 MB (a crash's gdb dump reaches 4.4 GB), 3 h.
- **scipy:** DV2 needs scipy (lightgbm imports it), which the CVMFS stack does not have. Locally it comes from the `wire-cell-python` venv: the venv's `python3` is first on PATH, so the embedded interpreter takes the venv prefix, and the venv's site-packages follow PYTHONPATH. The first tarball lacked it (emulated DV2 job: rc 1 at configure, `No module named 'scipy'`). Tarball v2 ships the venv modules the embedded Python imports locally (`scipy`, `pandas`, `matplotlib` and their small dependencies; found by importing `DV2_Vertex` and loading the bundle, then listing modules loaded from `/exp`) as `venv-site/`, appended to PYTHONPATH in every mode. This is a deployment point for PR #543 too: DV2 needs lightgbm and scipy, neither in the standard stack.
- **Emulated worker** (`scripts/emulate-crash.sh`, only `/cvmfs` and `/pnfs` mounted), tarball v2: master MC nueCC `2af0` rc 0 (6 events), PR `dv2_split_move` data `ncpi0-s13-19` rc 0 (6 events), its 6 DV2 call records identical to the local v2 run (inputs, predictions, scores; only the timing differs). Tarball v1: master and PR + `asyncpreemptoff` rc 0 (`GODEBUG` reaches the job).
- **Submitted 2026-11-12 12:33:** cluster `30747544@jobsub04`, 120 jobs, tarball `production-prep/pr543-crash-grid/tar/wccrash-v2.tar.gz` (323 MB), results in `/pnfs/sbnd/scratch/users/yuhw/pr543-crash-study/grid-v2/<mode>/`. Tabulate with `scripts/collect.py`.

### Grid run 1 (cluster 30747544): no crash in any mode — the grid pins jobs to one CPU

All 120 jobs finished (12:33–13:00), 309 events per mode, **0 crashes in every mode**, on every input including `nuecc48-s40-48` (0/12):

| mode | jobs | crashes |
|---|---|---|
| master | 30 | 0 |
| PR `original` | 30 | 0 |
| PR `dv2_split_move` | 30 | 0 |
| PR `original` + `asyncpreemptoff` | 30 | 0 |

At the sbndbuild03 rate (~5 % per job; 1–3 in 10 on `nuecc48-s40-48`) about 6 crashes were expected (P(0) ≈ 0.002). The difference: **every grid job saw `nproc` = 1** (HTCondor CPU affinity; the nodes have 40–128 CPUs online), so Go ran with GOMAXPROCS = 1. On sbndbuild03 the jobs saw all 64 CPUs, so Go ran with GOMAXPROCS = 64: up to 16 parallel GC mark workers, the 20–90 Go threads seen in the crash dumps, and far more preemption signals.

- Consequence for production: one-CPU FermiGrid jobs are effectively protected; sbndbuild03 jobs without CPU pinning are exposed.
- `GOMAXPROCS=1` (or pinning the job to one CPU) is a second candidate fix.
- This run cannot compare the modes. Grid run 2 forces `GOMAXPROCS=64` in every job (the job script's new optional 4th argument; `CRASH_XENV=GOMAXPROCS=64 submit-crash.sh …`), to recreate Go's sbndbuild03 behaviour on a one-CPU slot.

### Grid run 2 (cluster 30747639, `GOMAXPROCS=64`)

Submitted 2026-11-12 ~13:05, same 120 tasks, results in `grid-v2-gmp64/`.

**Again 0/120 crashes in every mode**, 309 events per mode. `GOMAXPROCS=64` reached all 120 jobs (`xenv` in `summary.txt`), but each still had one CPU (`nproc` = 1, 98 % CPU), so Go's 64 Ps time-share one core instead of running beside the main thread. The sbndbuild03 crashes (89–114 % CPU) apparently need Go threads running truly in parallel with the main thread.

**What the grid runs show (240 jobs, 618 events per mode):**
- On one-CPU slots no mode crashes: master 0/60, PR `original` 0/60, PR `dv2_split_move` 0/60, PR + `asyncpreemptoff` 0/60. Nothing PR-specific appears.
- The crash needs real multi-core execution, as on sbndbuild03 (64 CPUs, no pinning).
- To compare the modes where the bug shows: run the same test on multi-core grid slots (e.g. `--cpu=8`, so Go sees 8 CPUs), or on sbndbuild03 once it is back.

## Status and conclusions (2026-11-12)

| where | master | PR `original` | PR `dv2_split_move` | PR `original` + `asyncpreemptoff` |
|---|---|---|---|---|
| sbndbuild03, all local runs (64 CPUs, unpinned) | 1/52 | 8/83 | 9/190 | 0/10 |
| sbndbuild03, `nuecc48-s40-48` only | 1/11 | 5/15 (PR modes together) | | 0/10 |
| FermiGrid run 1 + 2 (1 CPU per job), 103 events × 6 | 0/60 | 0/60 | 0/60 | 0/60 |

- **Cause:** ROOT's SIGURG handler (no `SA_ONSTACK`) runs on go-jsonnet goroutine stacks and overflows them. It is in master; PR #543 neither causes nor fixes it.
- **PR #543:** on the same events the PR in either model behaves like master on the grid (0/120 vs 0/60). On sbndbuild03 master and the PR crash with the same Go signature, and the per-input rates are not statistically distinguishable (`nuecc48-s40-48`: 1/11 vs 5/15, p ≈ 0.2). Nothing blocks the merge on this account.
- **Exposure:** only when Go threads truly run in parallel with the main thread: multi-core hosts without CPU pinning (sbndbuild03, `run-pairs.sh` pools). One-CPU FermiGrid jobs saw no crash in 240 jobs, even with `GOMAXPROCS=64`.
- **The fg1 grid step-2 crashes** (`TrackFitting::update_association`, `SteinerGrapher`, RSS runaway to ~4.5 GB; `sbnd-wirecell-production` `aurora/docs/aurora-r8-chain.md` §8) ran on one-CPU slots, so they are most likely a different bug, as are the two saved r7 master crashes (ROOT `TStyle::GetHistLineColor`).
- **Open:** the mode comparison where the bug fires (multi-core: sbndbuild03 once back, or `--cpu=8` grid slots), and confirmation of `asyncpreemptoff` beyond 0/10.

## Open items (parked 2026-11-12)

1. **Compare the modes where the bug fires.** Rerun the same 4 modes × 3 passes on a multi-core machine: sbndbuild03 once it is back (within the load rule), or grid jobs with `--cpu=8` (`submit-crash.sh` needs a `--cpu` option, ~240 core-hours). This also tests `GODEBUG=asyncpreemptoff=1` beyond 0/10.
2. **Put the workaround into the sbndbuild03 run setup.** `export GODEBUG=asyncpreemptoff=1` (or `GOMAXPROCS=1`) in `sbnd-wirecell-production` `aurora/env/fnal/setup-fnal-run.sh`, or `taskset` one CPU per `wire-cell` in the pool. Only documented so far (5d9480b).
3. **Toolkit fix.** After ROOT initializes, drop ROOT's SIGURG handler (`gSystem->ResetSignal(kSigUrgent)`) or restore Go's; longer term, build against the C++ jsonnet library instead of go-jsonnet. Then open a toolkit issue/PR.

## Fix options

1. **Workaround (no rebuild):** `export GODEBUG=asyncpreemptoff=1` in the job setup (`aurora/env/fnal/setup-fnal-run.sh`), or `GOMAXPROCS=1`, or pin each `wire-cell` to one CPU (`taskset`). `asyncpreemptoff`: 0/10 on the crash-prone input on sbndbuild03 (master 1/10, PR 2/10 in the same test); the grid could not test it (no crash in any mode there). Documented in `sbnd-wirecell-production` (`aurora/AGENTS.md`, `aurora/docs/aurora-r8-chain.md` §8); not yet set in the setup scripts.
2. **Fix in the toolkit:** after ROOT initializes, remove ROOT's SIGURG handler (`gSystem->ResetSignal(kSigUrgent)`), or save Go's handler before ROOT starts and put it back.
3. **Remove the Go runtime:** build against the C++ jsonnet library instead of go-jsonnet.

Production uses the same ROOT and go-jsonnet (sbndbuild03 and FermiGrid), so some intermittent production failures may be this bug. The two r7 master production crashes saved in `production-prep/r7-r26-master-b7bd2a1a/crash-*-wct.log.gz` are a different one (main thread in ROOT `TStyle::GetHistLineColor`).

## Log

- 2026-11-12:
  - Crash logs re-read: all faulting threads are Go threads; two forms (Go fatal, jump to 0).
  - gdb on live master and PR processes: SIGURG → ROOT `sighandler`, no `SA_ONSTACK`.
  - Repeat test on `nuecc48-s40-48`: master 1/10, PR `original` 2/10, PR `original` + `asyncpreemptoff` 0/10. Master's crash has the Go signature.
  - sbndbuild03 rebooted at 08:51; the 30-run confirmation was lost.
  - Grid test (sbndbuild03 down): tarball, job, 120 tasks; scipy missing on the worker, fixed in tarball v2; emulation OK; submitted cluster 30747544@jobsub04.
  - Grid run 1: 0/120 crashes, every mode; every job had nproc = 1 (GOMAXPROCS = 1). Grid run 2 with GOMAXPROCS=64: cluster 30747639@jobsub04, also 0/120 (still one CPU per job).
  - Status section; sbnd-wirecell-production docs updated (trap + known-problems row); WCT PR #543 merged with a pointer to this issue.
  - Parked; three open items listed.
