# Issue 11 — 1-step img/clus/match/tag over 1000 MC files (~13k events)

Large-scale run of the **1-step chain** (imaging → clustering → Q/L matching →
TGM/STM/FC taggers) over the first 1000 files of the Gen2 v10_14_02_03 MC list,
as a scaled-up repeat of [issue 8](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/8)
(which did the same thing over 10 files / 118 events).

Output tree: `/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-mc-1000file-2026-08-14/`

## Scope caveat, stated up front

The input files carry **production (pre-fix) `dnnsp` and no `raw::RawDigit`**:

```
recob::Wires_simtpc2d_dnnsp_DetSim          <- production SP output
sim::SimChannels_simtpc2d_simpleSC_DetSim   <- truth
recob::OpFlashs_opflashtpc0__Reco1          <- flashes for Q/L matching
recob::OpFlashs_opflashtpc1__Reco1
recob::Hit...gaushit__Reco1
```

With no RawDigits there is nothing to re-run NF+SP from, so **this run cannot
and does not exercise the four signal-processing fixes from issue 10**
(`partial_enable`, W `max_rms_cut`, `roi_mad_rms`, `r_break_roi_loop_planes`).
It measures the clustering + matching + tagger chain on production signal
processing. Any conclusion about the SP fixes must come from issue 10's
campaign, not from here.

## Input

- List: `/exp/sbnd/app/users/yuhw/sbnd-gen2-data/round2-patrec/mc_paths-v10_14_02_03-full.lst`
  (749,339 files total), **first 1000 lines** → `files-1000.lst`.
- Sample: `aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/reco1`.
- 13 events/file, ~315 MB/file → **~13,000 events**, ~315 GB read from dCache.
- The 1000 files span only **16 dCache directories**, so read locality is good.

## Local repository state (this is the configuration being run)

Captured 2026-08-14. Everything the chain loads comes from these trees.

| repo | path | branch | HEAD | clean? |
|---|---|---|---|---|
| wire-cell-toolkit | `/exp/sbnd/app/users/yuhw/wire-cell-toolkit` | `ap-yuhw` | `06a02ccb` | clean |
| wcp-porting-img | `/exp/sbnd/app/users/yuhw/wcp-porting-img` | `main` | `b3efbd3` | clean |
| larwirecell | `/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell` | `dev-v10_14_02_02` | `3b07b85` | clean |
| wire-cell-data | `/exp/sbnd/app/users/yuhw/wire-cell-data` | `master` | `421d2cd` | clean |
| sbndcode | `/exp/sbnd/app/users/yuhw/sbndcode` | `wcp-porting` | `e140cca76` | **5 files dirty** |
| sbnd_xin | `/exp/sbnd/app/users/yuhw/sbnd_xin` | — | not a git repo | — |

**The dirty sbndcode files do not affect this run.** They are the issue-10
fixes staged for review (`sp.jsonnet`, `nf.jsonnet`, `nf-data.jsonnet`,
`chndb-base.jsonnet`, `wcls-nf-sp.jsonnet`) — all NF/SP config, and this chain
runs no NF or SP. `setup-ap.sh` additionally *prepends the toolkit cfg* ahead
of sbndcode's, so the imaging/clustering jsonnet resolves from
wire-cell-toolkit regardless.

### Installed libraries vs source

The chain loads `.so` files from `/exp/sbnd/app/users/yuhw/opt/lib`, which is a
separate install from the source trees above — they can drift.

| library | built | matches source? |
|---|---|---|
| `libWireCellClus.so` | 2026-08-06 12:25 | **yes** — no commit since Aug 6 touches `clus/src` or `clus/inc` |
| `libWireCellSigProc.so` | 2026-08-11 14:45 | yes (carries the issue-10 fixes; unused here) |

Verified with `git log --since=2026-08-06 -- clus/ cfg/`: the only commits are
`b8086bd6`, `13ed5167`, `06a02ccb`, all sigproc/SP-config. So the Aug 6 clus
build is current for everything this run touches.

### Config changes carried relative to upstream

Nothing in the imaging/clustering/matching/tagger path was changed for this
run. The toolkit `ap-yuhw` branch is a fork of `apply-pointcloud`; its
clustering and tagger knobs (including the TGM fiducial volume — one
`BoxFiducial` spanning both TPCs, `sbnd_pr_fv`, with `fv_tolerance`
`[-2.5,-2.5,-3,-3,-5,-3]` cm) are as committed on that branch. The three
commits on top of it are the issue-10 SP work and are inert here.

## Chain

One `lar` job per event, `wcls-img-clus-matching-xin.fcl` — the **1-step**
chain, identical to issue 8. It produces `mabc.zip` carrying the clustering,
truth, and `tagger_fc` / `tagger_stm` / `tagger_tgm` layers in a single pass;
there is no separate PR/tagger stage.

```
lar -n 1 --nskip <k> -c wcls-img-clus-matching-xin.fcl -s <file> --no-output
```

Environment: `setup-ap.sh` (which sources `setup-local-opt.sh`, then prepends
the toolkit cfg and `wire-cell-data/sbnd/photodet` to `WIRECELL_PATH`), plus
`FHICL_FILE_PATH` ← `wcp-porting-img/sbnd`. Run inside the SL7 apptainer via
`claude-utilities/in-gpvm-sl7.sh`.

Per-event cleanup, verbatim from issue 8 — keep `mabc.zip`, drop
`nugraph.h5`, `trash-all-apa.tar.gz`, `*.db`, `tf-default.root`, `mabc-pr.zip`.

## Harness — how it differs from issue 8

`scripts/run-harness.sh`. Three changes, all forced by the 100× scale:

1. **Core budget.** Issue 8 ran 10 jobs with *no* pinning. WCT runs `TbbFlow`,
   whose pool defaults to hardware concurrency (64 on sbndbuild03), and
   `OMP_NUM_THREADS` does **not** bound it — so that run took as much of the
   machine as it wanted. Acceptable for 9 minutes, not for a multi-hour run on
   a shared build box. Every worker is now pinned with `taskset` to a disjoint
   core set, making the ceiling exactly `NWORK × CORES_PER`.
2. **Work stealing.** Issue 8 assigned one worker per file with event counts
   known up front (`manifest.txt`). Pre-counting 1000 dCache files would be a
   slow serial pass, so workers instead pull the next file index from a
   `flock`-guarded cursor and count events themselves on open. This also
   self-balances when files differ in event count.
3. **Summary CSV.** One row per event (`rc`, wall seconds, zip bytes, RSE) so
   a 13k-event run can be audited without unpacking anything.

Per-event isolation (own cwd) is kept from issue 8 for the original reason:
concurrent `lar` jobs collide on art's MemoryTracker/TFileService sqlite files
(`SQLExecutionError: disk I/O error`) unless each has its own directory.

## Pilot (10 events)

One event from each of the first 10 files — one event per file rather than 10
from one file, so the measurement includes a realistic dCache open per file and
the BEE set shows 10 distinct events.

**10/10 succeeded, zero failures.** Each event pinned to its own 2-core set,
run serially (so these numbers carry no contention).

| idx | wall s | mabc.zip MB | intermediates MB |
|---|---|---|---|
| 0 | 40 | 3.51 | 2.16 |
| 1 | 31 | 5.17 | 3.02 |
| 2 | 40 | 5.76 | 3.44 |
| 3 | 29 | 4.19 | 2.41 |
| 4 | 25 | 3.41 | 2.12 |
| 5 | 38 | 3.53 | 2.72 |
| 6 | 33 | 4.77 | 2.84 |
| 7 | 24 | 2.83 | 1.82 |
| 8 | 44 | 7.38 | 4.83 |
| 9 | 20 | 1.46 | 1.00 |
| **mean** | **32.4** (sd 7.6, range 20–44) | **4.20** | **2.64** |

Peak memory per event (art `MemReport`): **VmHWM 1.72 GB**, VmPeak 3.45 GB.

Layers in each `mabc.zip` — confirming the taggers ran in the same pass, as in
issue 8:

```
channel  clustering  face  img  mc  op  sed
tagger_fc  tagger_lm  tagger_stm  tagger_tgm
truth_trackid_labeled  truth_unlabeled
```

The discarded intermediates, per event: `trash-all-apa.tar.gz` 1.14 MB,
`nugraph.h5` 0.87 MB, `mabc-pr.zip` 0.13 MB, `tf-default.root` 0.01 MB.
Keeping the pctree tarball would have added only ~11 GB over the full run —
cheap if a later re-clustering is ever wanted, but per the issue-8 convention
it is dropped.

**Pilot BEE (10 events):**
<https://www.phy.bnl.gov/twister/bee/set/bd8bc010-17c3-4f67-a80d-c76c7e12c1d6/event/list/>
(idx 0–9 = event 0 of files 1–10 of `files-1000.lst`.)

## Full run — projections

### Event count

Sampling the first 8 files gives **10.1 events/file** (13, 6, 11, 5, 10, 11,
13, 12 — they vary a lot), so 1000 files ≈ **10,100 events**, not the 13,000 a
naive "13 per file" from the first file alone would suggest.

### Time

At the pilot's 32.4 s/event on 2 cores, with **10 workers × 2 cores = 20 cores**:

```
10,100 events x 32.4 s / 10 workers = 32,700 s = 9.1 hours
```

That is a floor: the pilot ran one event at a time, so it saw no contention for
memory bandwidth, shared L3, or dCache. With ten concurrent workers, budget
**10–13 hours**. The work-stealing cursor means stragglers do not idle workers,
so the tail should be short.

Configuration caveat: 32.4 s/event was measured at **2 cores per worker only**.
20 workers × 1 core might give better aggregate throughput, since TBB scaling
within one event is sublinear — but it is unmeasured, and it would triple
resident memory (see below). Not recommended without its own pilot.

### Disk

| item | per event | full run |
|---|---|---|
| `mabc.zip` (kept) | 4.20 MB | **~42 GB** |
| intermediates (deleted) | 2.64 MB | ~27 GB, never retained |
| per-event logs | — | only failures are kept |

`/exp/sbnd/data` has **94 TB available**, so 42 GB is not a constraint.

### Load on sbndbuild03

The box has **64 cores / 125 GB RAM**. Baseline at planning time: load average
24.5, but almost entirely `rpc.gssd` and NFS `kworker` threads — no competing
user jobs.

| | |
|---|---|
| cores used | 20 of 64 (31 %), hard-capped by `taskset` |
| projected load average | ~44 of 64 (69 %), leaving ~20 cores free |
| resident memory | 10 × 1.72 GB = **~17 GB** of 114 GB available (15 %) |
| dCache read | 1000 × 315 MB = **~315 GB** over 10–13 h ≈ 7 MB/s average |

The memory and I/O footprints are both modest; cores are the binding
constraint, and they are capped by construction. This should be unobtrusive to
other users — unlike issue 8's harness, which had no pinning and would have
taken all 64.

## Full run — execution

Launched 2026-08-14 after the pilot was reviewed and approved.

```bash
CAMPAIGN=/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-mc-1000file-2026-08-14
bash scripts/run-harness.sh $CAMPAIGN/files-1000.lst $CAMPAIGN 10 2
#                            <list>                  <out>     ^NWORK ^CORES_PER
```

Run on sbndbuild03 directly (not submitted to the grid), inside the SL7
apptainer. It is started detached rather than tied to a terminal — a 10–13 hour
job cannot survive an interactive session — with a watcher reporting per-file
completions and any non-zero `rc`. The core cap is enforced by `taskset` inside
the harness, not by the launch method, so it holds either way.

Restartability: the harness is **not** resumable as written. The cursor starts
at 0 and `zips/` is additive, so re-running would redo completed files (their
zips would simply be overwritten). If it dies partway, the cheap fix is to
build a new list from the files absent in `summary.csv` and run that.

### The 100-event BEE set

Sampled as **every 100th event** across the run in completion order, rather
than the first 100, so the set spans many files and both the easy and hard tails
of the event-size distribution. Built with the same `merge_bee.py` as the pilot.

## Full run — results

2026-08-14 21:25:23 → 2026-08-15 11:04:33, **13 h 39 min**.

| | |
|---|---|
| files | 1000 / 1000 |
| events | **13,217** (13,211 ok, **6 failed = 0.045 %**) |
| events/file | mean **13.2** (min 5, max 23) |
| wall/event | mean 35.6 s, median 32, p90 49, p99 93, **max 950** |
| CPU | **261.5 core-hours** |
| disk | **64 GB** of `mabc.zip` |

**100-event BEE set:**
<https://www.phy.bnl.gov/twister/bee/set/3fa24feb-fbb3-4a9e-a27b-0aa2bb540003/event/list/>
— 101 events, every 132nd zip in completion order so the set spans files 0–999.
`bee/sample-100-index.txt` maps BEE index → (file, event).

### Where the pre-run estimates were wrong

| quantity | projected | actual | why |
|---|---|---|---|
| events/file | 10.1 | **13.2** | the 8-file sample caught several short files; the distribution is wide (5–23) |
| total events | ~10,100 | **13,217** | follows from the above |
| wall | 10–13 h | **13.6 h** | right at the top of the range: +31 % more events than projected, partly offset by the per-event rate holding at 35.6 s |
| disk | ~42 GB | **64 GB** | more events, and the pilot's 10 events under-sampled the large-event tail (4.20 → 4.85 MB/event) |

The per-event *rate* held almost exactly (pilot 32.4 s uncontended → 35.6 s
under 10-way contention, a 10 % penalty). Everything that missed came from
under-sampling the input, not from mismodelling the machine — a 10-event pilot
is enough to calibrate cost per event and nothing about the population.

### Load — and why load average misled here

At 81 % through, load average read 57 and later 73, which looked alarming.
It was not us:

- our 10 workers stayed pinned to cores 0–19 throughout (verified with
  `taskset -cp`), and their **aggregate CPU was 885 % ≈ 8.9 cores** — under
  half the 20-core allowance;
- machine-wide only **10 processes were runnable** against a load average of
  57, with the rest of the number coming from `D`-state I/O wait.

This run is **I/O-bound, not CPU-bound**: 315 GB read from dCache, and workers
sat at 70–95 % of a single core rather than saturating their pairs. Load
average counts uninterruptible I/O wait, so on an NFS/dCache-heavy box it is a
poor proxy for "am I crowding other users". The honest measure is per-user CPU:
`yuhw` 875 %, `root` 341 %, others < 35 % — about 12.7 of 64 cores busy.

Consequence for future runs: **more workers would not have helped**. The
binding constraint was dCache, so the 20-core cap cost nothing.

### Failure census — 6 events, three distinct causes

| file | event | rc | wall | cause |
|---|---|---|---|---|
| 196 | 11 | 1 | 27 s | `sig2img` range check |
| 224 | 1 | 1 | 27 s | `sig2img` range check |
| 684 | 7 | 139 | 30 s | **segfault** in `MultiAlgBlobClustering` |
| 364 | 16 | 124 | 2369 s | timeout |
| 470 | 4 | 124 | 2698 s | timeout |
| 955 | 3 | 124 | 2499 s | timeout |

**1. `sig2img` off-by-one (2 events) — a real toolkit bug.**

```
vector::_M_range_check: __n (which is 353) >= this->size() (which is 353)
vector::_M_range_check: __n (which is 383) >= this->size() (which is 383)
```

In both, the index is *exactly* `size()` — one past the end, never further.
That is the signature of an off-by-one at an upper bound (`<=` for `<`, or a
bin lookup returning `nbins` for a value on the top edge). Reproducers:

- run 719 / subRun 77 / event 35 —
  `.../000041/000418/reco1-detsim-g4-gen-Gen2_2026-d53d-206a-31c4-9dbe.root`
- run 714 / subRun 44 / event 10 —
  `.../000041/000413/reco1-detsim-g4-gen-Gen2_2026-24c6-2937-92b2-cc2c.root`

**2. Segfault in clustering (1 event).** Died in
`MultiAlgBlobClustering:apa0-0` shortly after `ClusteringSeparate`, 30 s in.
A separate defect from (1) — different component. The core file did not
survive (the harness deletes the per-event work directory), so a stack trace
needs a re-run under `gdb` on
`.../000017/000170/reco1-detsim-g4-gen-Gen2_2026-67a3-4e42-52e3-19f7.root`.

**3. Timeouts (3 events) — not bugs.** Each exceeded `timeout 1800`; all three
consumed 2350–2700 s. Note art reported these as `passed = 1` and the log shows
`closed shared Bee zip mabc.zip` **before** the SIGTERM, so their output was
probably complete — but the harness keys on `rc == 0` and discarded it. That is
the conservative choice, and at 3 events in 13,217 the loss is negligible;
worth knowing before anyone reuses this harness where such events matter. The
p99 is 93 s and the slowest *successful* event took 950 s, so these three are
far out in the tail, not near the cut.

## Status

- [x] Pilot 10 events + BEE (`bd8bc010-17c3-4f67-a80d-c76c7e12c1d6`)
- [x] Full run, 1000 files / 13,217 events, 13 h 39 min
- [x] 100-event BEE set (`3fa24feb-fbb3-4a9e-a27b-0aa2bb540003`)
- [x] Failure census + wall-time distribution
- [ ] File the `sig2img` off-by-one upstream (2 reproducers above)
- [ ] Get a stack trace for the clustering segfault
- [ ] Tagger-rate summary across the 13,211 zips (not yet built — see below)

## Not done

No **physics** summary exists. `summary.csv` carries `rc` and wall time per
event, but nothing about what was reconstructed: no per-event TGM/STM/FC
verdicts, cluster counts, or kinematics. Extracting those from the 13,211 zips
into one table is what would make this run analyzable rather than merely
completed. Deliberately left out of scope here.

## Files in this folder

```
11-mc-1000file-img-clus-match-tag.md   this document
scripts/run-harness.sh                 the full-run harness (work-stealing, taskset)
scripts/run-pilot.sh                   10-event pilot
scripts/merge_bee.py                   from issue 8: merge per-event zips, re-index
```

Data (gitignored) lives under
`/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-mc-1000file-2026-08-14/`:
`files-1000.lst`, `pilot/`, `zips/`, `logs/`, `summary.csv`, `bee/`.
