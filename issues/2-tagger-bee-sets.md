# Issue #2 — Add STM/TGM/FC tagger BEE sets to `TensorSetLabeler.cxx`

Status: **done & validated** (2026-07-29).

Add three BEE point sets — `tagger_stm`, `tagger_tgm`, `tagger_fc` — to
`wclsTensorSetLabeler` (larwirecell `aiml/`), each sharing `clustering_global`'s
coordinates and charge, colored by the tagged flag.

## What the sets contain

| field | value |
|---|---|
| `x,y,z` | **same points as `clustering_global`** (the all-APA MABC blob dump) |
| `q` | **same as `clustering_global`** (`point_charge`) |
| `cluster_id` | **1 = tagged, 0 = not tagged** — from the cluster's `flag_STM` / `flag_TGM` / `flag_FC` |
| `real_cluster_id` | written as `0` everywhere (see note) |

Note on "no real_cluster_id": `Bee::Points::append()` always emits a
`real_cluster_id` array, so it is present but **all-zero**. Because BEE colors by
`real_cluster_id` only when it is `> 0` (`sst.js:150-154`, see
`questions/cluster_id-vs-real_cluster_id.md`), an all-zero array makes BEE fall
back to coloring by **`cluster_id`** — i.e. exactly the tagged/not-tagged split
we want. So functionally there is "no real_cluster_id" coloring; the tag flag
drives the color.

Unlike the truth sets (`mc`, `truth_*`, `sed-*`, sim-only), the tagger sets are
written in **both realities** (MC and data).

## Changes

### 1. `larwirecell/aiml/TensorSetLabeler.cxx` (the labeler)
- Declare three `Bee::Points` (`tagger_stm/tgm/fc`) with the event RSE, next to
  the existing `bpts_unlab`.
- In the per-cluster loop, read the tag flags from the cluster's
  `cluster_scalar` local PC: `flag_STM` / `flag_TGM` / `flag_FC` (int scalars set
  by the taggers; `set_flag(name)` → `flag_<name> = 1`). A helper returns `1`
  iff the scalar exists and is non-zero, else `0`.
- In the blob dump, append every point to all three tagger sets with
  `append(p, q, tag, 0)` (`tag` = the cluster's flag, `0` = real_cluster_id).
- Gate: the blob-dump / write blocks that were `if (is_sim && m_bee_sink)` are
  split — the **truth** sets stay inside `if (is_sim)`, the **tagger** sets are
  written whenever `m_bee_sink` exists (both realities).

### 2. `cfg/pgrapher/experiment/sbnd/clus.jsonnet` (WCT, wiring)
The tag flags are produced by the STM/TGM/FC **PR tagger pass** (the same
pipeline the standalone nusel step runs). The labeler only reads flags, so the
PR pass must run **before** it. Added a `run_taggers` path:
- `clus_maker.all_apa(..., run_taggers=false)`: when `true`, build a `pr_node`
  from `clus_pr(...)` (pipeline
  `switch_scope, unmerge_bundle, unmerge_assoc, steiner, fiducialutils,
  tagger_check_tgm, tagger_check_stm, tagger_check_fc`, `dump=false`,
  `particle_dataset`/`extra_uses` from `particle_dataset.jsonnet`) and pass it
  into `clus_all_apa` as `pr_node`.
- `clus_all_apa(..., pr_node=null)`: splices `pr_node` between the all-APA MABC
  and the labeler — `pipeline([mabc, pr_node, labeler, sink])`.

This is **functionally equivalent** to "move the labeler to the entry jsonnet
and wire `pr()` before it": the graph is `MABC → PR(taggers) → labeler → sink`
either way. It is kept inside `clus.jsonnet` (gated by the flag) because jsonnet
top-level `local`s are not mutually recursive — `clus_all_apa` (defined early)
cannot reference `clus_pr` (defined later); building `pr_node` inside the maker
method (the final expression, which *can* see `clus_pr`) sidesteps that.

### 3. `sbnd/wcls-img-clus-matching-xin.jsonnet` (entry, wcp-porting-img)
`clus_maker.all_apa(..., run_taggers=true)`.

## ⚠ Operational finding — taggers must run **per-event**

Running the PR tagger chain **inline over a multi-event `lar` job crashes**
(SIGSEGV inside the tagger/steiner patrec — the known data-dependent patrec
instability, *not* an issue-#2 bug): a 10-event MC batch died on the 3rd event,
a 10-event data batch on the 6th. This is why the standalone nusel tagger step
runs one event per process. **Bulk tagger production must be per-event**
(one `lar -n 1 --nskip K` per event), then merge the per-event BEE zips.

## Local edits (not yet pushed)

| repo | branch | file | state |
|---|---|---|---|
| larwirecell (MRB `srcs/larwirecell`) | `dev-v10_14_02_02` | `aiml/TensorSetLabeler.cxx` | modified, built, `libWireCellAIML.so` hand-copied to `opt` |
| wire-cell-toolkit | `master` | `cfg/pgrapher/experiment/sbnd/clus.jsonnet` | modified (jsonnet, no build) |
| wcp-porting-img | — | `sbnd/wcls-img-clus-matching-xin.jsonnet` | modified |

## Validation

See `runs/2026-07-29-tagger-bee-sets.md`. Summary:
- Smoke (1 MC + 1 data, evt 269774): both `RC=0`, sets present; data evt 269774
  → `FC=true` on cluster 13 → `tagger_fc` `cluster_id=1` for 9689 pts.
- 10 MC + 10 data, **per-event**: all 20 `RC=0`, no segfaults. Taggers fired
  across all three types; spot-checks confirm each flag maps independently to
  `cluster_id=1` in its own set (MC evt9 STM=2545 pts; data evt1 TGM=2332 +
  FC=3546 pts).

BEE (10 events each, full `.../event/list/` URLs):
- MC: https://www.phy.bnl.gov/twister/bee/set/2d09d17e-0696-45da-872b-91b7a7b9340f/event/list/
- data: https://www.phy.bnl.gov/twister/bee/set/7937d2e8-5d4a-4f8a-9dda-cab7a2d166fb/event/list/
