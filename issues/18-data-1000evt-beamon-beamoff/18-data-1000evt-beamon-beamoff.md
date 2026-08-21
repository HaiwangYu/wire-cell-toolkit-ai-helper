# Issue 18 — real-data production: 1000 beam-on + 1000 beam-off events

Data counterpart of [issue #16](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/16)
(13,213 MC events). Same chain (img → clus → Q/L match → tagger → PR), same
computing setup (32 workers × 1 core, one `lar` process per event), **same
configuration** — which means the same `#17` operating-point gap; see Caveats.

Work/output: `/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-data-1000evt-2026-08-21/`

| sample | status |
|---|---|
| **beam-on**, 1000 events | **complete** — 1000/1000, 25 min |
| **beam-off**, 1000 events | **blocked** on the SAM file list (see below) |

## Data mode differs from MC in four ways

Config is `sbnd/wcls-img-clus-matching-xin-data.fcl`, which already existed:
`reality="data"` plus the `sptpc2d` product tags (`sptpc2d:dnnsp` ×2,
`sptpc2d:wienersummary`, `sptpc2d:badmasks`). Consequences, all verified:

1. **No truth Bee layers.** 16 layers instead of 20 — no `truth_trackid_labeled`,
   no `truth_unlabeled`, no three `sed-*`. Bee zips are ~4× smaller
   (1.01 MB vs 4.61 MB).
2. **`mc.json` is reco-only, and still present.** e.g. `gamma 86 MeV`,
   `gamma 5 MeV`, `proton 111 MeV` at top level with no "reco nu" wrapper —
   `merge_metadata_key` finds no truth tree, so the reco nodes are published
   directly. Not empty, not missing. **This verifies issue 13's T4** (exercise
   the empty PF branch on data).
3. **nugraph is input-only.** `y_semantic` and `y_instance` are **all −1**, so
   the graph carries features and edges but **no training target**. Still
   produced; do not expect to train on it.
4. **Frameshift is mandatory upstream.** Every Gen2 real-data reco1 file must
   have `run_frameshift.fcl` applied before this chain or the TPC/PMT time
   alignment is wrong and Q/L matching is meaningless. The beam-on input was
   already frameshifted; `prep-beam-off.sh` does it for beam-off and then
   *verifies the FrameShift product actually landed* rather than assuming.

## The `--nskip` ordering bug (found and fixed here)

Worth reading before reusing any of this.

The first smoke wrote a file named `r18259_s1_e171099` whose `Trun` said
**18255/1/49415**. Cause:

> **`lar --nskip k` counts in art's logical `FileIndex` order — sorted by
> (run, subrun, event) — not the Events-tree write order that `EventAuxiliary`
> is read in.**

For a single-run-per-file input (every MC reco1 file) the two orders coincide,
so the issue-16 harness was correct **by luck**. This merged data file (1000
events from 20 reco1 files) starts its Events tree with run 18259 while art
starts with 18255, so `--nskip 0` processed tree entry **300**.

Why it is dangerous: every output file is internally self-consistent — the Bee
JSON, `Trun` and the nugraph key all carry the RSE the job really saw. Only the
*filename* is wrong. Nothing fails and nothing warns. Unsorted, all 1000
outputs would have been mislabelled invisibly.

Two fixes, both in place:

- `make-manifest.sh` sorts the RSE triplets into art's order before assigning
  the `--nskip` index. Verified at indices **0, 1, 499, 999** — index 0 agreeing
  proves nothing on its own.
- `run-harness.sh` reads the RSE back from each job's own `tracking-pr.root:Trun`,
  **names the files from that**, and records an `rse_check` column. A wrong
  prediction is now loud instead of silent.

**Issue 16's MC dataset is unaffected**: single-run inputs, and `Trun` was
independently verified there.

## Beam-on results (complete)

Input: `add-frameshift-data-2nd-2k-2026-08-15/data_MCP2025C_reco1_frameshift_2nd1k_part1.root`
— exactly 1000 events, runs 18255 (850) and 18259 (150), subrun 1.

`2026-08-21 15:08:26 → 15:33:34 CDT`, **25 min 08 s**, 12.4 core-hours.

| | result |
|---|---|
| events | **1000 / 1000 (100%)** |
| deliverables | 1000 × 3, **0** zero-size or missing |
| RSE | 1000 unique, and **identical to the manifest prediction** (0 differences) |
| `audit` FAIL | **0** |
| `rse_check` != ok | **0** |
| wall | mean **44.5 s**, median 42, p90 58, p99 104, **max 192** |
| memory | mean 48.0 GB, **max 57.8 GB** at 32 jobs |
| disk | **2.4 GB** — Bee 968 MB, nugraph 1.3 GB, tracking-pr 114 MB |
| candidates | **434 / 1000 = 43.4%** |

Two things differ from the MC run in a useful way:

- **No tail.** Zero events over 300 s, max 192 s. MC had 25 events over 300 s
  and a 2988 s maximum. Real events are far more uniform than
  `prodgenie_corsika` MC.
- **The 10-event pilot over-estimated cost by 2×** (95.9 s vs 44.5 s). The pilot
  took the *first* ten manifest entries, which are systematically heavier;
  sampling the head of a sorted manifest is a biased estimator. Sample randomly
  next time.

Disk is 2.45 MB/event against MC's 5.78, almost all of it the absent truth
layers.

### Bee (first 10 events)

- full chain: <https://www.phy.bnl.gov/twister/bee/set/39fad5b1-bbb4-47ad-92c3-f1c95e1a6cea/event/list/>
- nugraph space points: <https://www.phy.bnl.gov/twister/bee/set/ab1514e6-ba9a-4c7f-bfac-dae731417d05/event/list/>

## Beam-off — blocked, and on exactly one thing

`samweb` cannot be reached from this build node: **no DNS for any `*.fnal.gov`
SAM host**, inside or outside the SL7 container (`www.phy.bnl.gov` resolves, so
it is selective, not a general network outage). The definition is
`data_MCP2025C_FallValidationII_RollingDev_offbeamlight_v10_14_00_reco1_sbnd`.

`scripts/make-beamoff-list.sh` must therefore be **run by the owner**. It
describes the definition, lists its files, resolves each to a `/pnfs` path and
stops at 60 (beam-on reached 1000 events from 20 files, and the merge caps at
`lar -n 1000`, so surplus files are never read). Everything after that is
automated: `prep-beam-off.sh` → merge+frameshift+verify → manifest, then the
same harness.

### Open question: the two samples are different processings

| | beam-on | beam-off definition |
|---|---|---|
| campaign | `Fall25-Run1_BNB_Dev_bnblight` | `FallValidationII_RollingDev_offbeamlight` |
| version | **v10_14_02** | **v10_14_00** |

Beam-on/beam-off is normally a subtraction, so a version and campaign mismatch
is worth a decision before spending the cycles. Awaiting owner input on whether
a v10_14_02 off-beam definition should be used instead.

## Caveats

- **The `#17` operating-point gap applies here too.** This ran the same
  pre-flip PR configuration as issue 16: 160 knobs that Xin's 2-step chain sets
  are at default, 139 of them on `TaggerCheckNeutrino`. So the 43.4% candidate
  rate, `T_tagger`, `T_kine` and `kine_reco_Enu` are **this configuration's**,
  not SBND production's. Requested explicitly as "same configuration as
  issue-16".
- Validation output, not production. No stability guarantee.
- `nue_score` is a floor at −15.00 for most candidates (measured on MC); expect
  the same here.
