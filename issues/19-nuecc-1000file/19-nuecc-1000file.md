# Issue 19 — nueCC exclusive sample, 1000 files, on the SYNCHRONISED operating point

First campaign run with the PR operating point synchronised to Xin's 2-step
chain ([issue 17](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/17)),
and the first on a **signal** sample, so it is the first that can measure
**efficiency** rather than just yield.

Output: `/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-nuecc-1000file-2026-08-29/`

## Headline

| | value |
|---|---|
| **nueCC signal efficiency** | **8,269 / 8,866 = 93.3%** |
| `nue_score > 0` among reconstructed | **56.8%** |
| `nue_score` floored at −15.00 | **28.1%** (was **75%** on the CV sample) |
| events | 8,866 / 8,877 = **99.88%** |
| wall | 12 h 06 m, 26 workers, 200.8 core-h |
| disk | **71.4 GB** |

**The `nue_score` column is alive on this sample.** On the issue-16 CV sample it
was pinned at exactly −15.00 for 75% of candidates and was effectively unusable;
here the median is **+2.821**, p90 **+4.301**, and only 28% sit on the floor.
That is the combination of a signal sample and the synchronised operating point;
this campaign cannot separate the two contributions.

## Sample

`aurora_..._EX_nuecc_v10_14_02_05_reco1_sbnd`, definition of 14,231 files;
**first 1000 in samweb list order** (owner's choice).

- Path `Gen2_Exclusive_2026/nuecc/` — a **filtered nueCC sample**: `mc.generated_event_count`
  12,500 against an Event Count of ~9, i.e. a ~1400:1 filter. Every event
  contains a true nueCC interaction, which is what makes efficiency measurable.
- **8,877 events from 999 files.** One file resolved and opened cleanly with
  **0 events** (380 kB against the usual 259 MB) — the filter kept nothing from
  that job. Not corruption; expected in a filtered sample.
- 8–18 events/file (mean 8.9), 19 runs. Products identical to issue 16's MC
  (`simtpc2d:dnnsp`, `simtpc2d:wienersummary`, `simtpc2d:badmasks`), so the
  chain ran unmodified despite the version bump to v10_14_02_05.

## Configuration

`wcls-img-clus-matching-xin.fcl` with `pr_operating_point: "sync"` — the
generated `pr-operating-point.jsonnet` carrying 151 knobs, gate at 0 differences
against Xin's 2-step. **This is the first campaign not subject to the issue-17
gap**, so its numbers are not comparable to issues 16 and 18, which were run
pre-flip and remain so by owner decision.

## Results

`2026-08-29 22:11:30 → 2026-08-30 10:17:26 CDT`, **12 h 06 m**, 26 workers × 1 core.

| | |
|---|---|
| events | **8,866 ok / 8,877 = 99.88%** |
| deliverables | 8,866 × 3, zero-size or missing: **0** |
| RSE | 8,866 unique, `rse_check` != ok: **0** |
| `audit` FAIL among successes | **0** |
| wall/event | mean 81.5 s, median 71, p90 120, p99 240, max 1682 |
| memory | mean 44.6 GB, **max 51.0 GB** |
| disk | 8.05 MB/event → **71.4 GB** (Bee 53 GB, nugraph 13 GB, tracking-pr 2.4 GB) |

26 workers rather than 32: peak RSS is 2.38 GB on this sample, so 32 would need
~76 GB against the 64 GB budget.

### Efficiency and scores

```
usable reconstruction (kine_reco_Enu > 0) : 8269/8866 = 93.3%
kine_reco_Enu   median 1001   p10  399   p90 2244   max 5712 MeV
nue_score       median  2.821 p10 -15.000 p90 4.301   floored 28.1%
numu_score      median -0.021 p10  -1.295 p90 1.384
nue_score > 0                             : 4696/8269 = 56.8%
```

93.3% is the fraction of true nueCC events reaching a reconstructed main vertex.
It is **not** a selection efficiency — no cut on `nue_score` has been applied,
and no containment or fiducial requirement beyond what the chain itself imposes.

## The 11 failures (0.12%)

| mode | n | detail |
|---|---|---|
| `vector::_M_range_check`, `__n == size()` | 6 | the same one-past-the-end `.at()` seen in issues 16 and 18 |
| SIGSEGV (`dumped core`) | 3 | |
| **hung in `TaggerCheckNeutrino`** | **2** | killed at 8.6 h and 6.6 h |

### The two hangs — same place, and the timeout did not stop them

`299/77/91` and `291/72/4327` both stopped producing output at the **identical**
point:

```
TaggerCheckNeutrino nue_tagger volume: apa=0 face=0   TaggerCheckNeutrino.cxx:2431
```

immediately after `shower_clustering_with_nv`, having logged 76 MABC stages and
reached `CreateSteinerGraph`. Neither produced another line for 8.6 h / 6.6 h.
Logs preserved as `t_4164-lar.log.gz`, `t_6196-lar.log.gz`.

Because this is a nueCC sample on the newly synchronised operating point (which
turns on 39 `shower_*` knobs), the hang may be pre-existing and rarely reached on
CV, or exposed by the sync. **This campaign cannot distinguish those**; the two
events are reproducible test cases either way.

### Harness bug: `timeout` without `-k` is not a bound

`timeout 3600` was in the process tree the whole time — still alive at 8h34m,
with its `lar` child running. Plain `timeout` sends only **SIGTERM**, and
lar/art did not take it. The job never died and the worker never moved on, so
two workers were parked for the last ~8 h of a 12 h campaign.

Fixed to `timeout -k 60 3600` in this harness **and retro-fixed in the issue-16
and issue-18 harnesses**, which carried the same defect. Issues 16 and 18 were
not affected in practice (their longest events completed at 2988 s and 2199 s),
but the bound they advertised was never real.

## Bee (10-event pilot)

- chain: <https://www.phy.bnl.gov/twister/bee/set/0acc7d6a-80bd-44f8-8a0b-23c394f55656/event/list/>
- nugraph: <https://www.phy.bnl.gov/twister/bee/set/bb564577-0fe7-4560-93cc-7911b0322ec2/event/list/>

The pilot showed 10/10 usable, against 93.3% over the full sample — a reminder
that a 10-event pilot bounds nothing.

## Caveats

- **Not comparable to issues 16/18**, which are pre-flip. Making the three
  homogeneous means regenerating those two (~8 h); deferred by owner decision.
- 93.3% is reconstruction reach, not selection efficiency.
- nugraph remains **unvalidated** (issue 16 §6); the truth labels here are
  richer than on CV (nu/cosmic/ghost all populated) but nobody has checked them.
