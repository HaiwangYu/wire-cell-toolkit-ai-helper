# Issue #2 — Add STM/TGM/FC tagger BEE sets to `TensorSetLabeler.cxx`

Status: **done & validated** (2026-07-29).

Add three BEE point sets — `tagger_stm`, `tagger_tgm`, `tagger_fc` — to
`wclsTensorSetLabeler` (larwirecell `aiml/`), each sharing `clustering_global`'s
coordinates and charge, colored by a 4-case tagger state.

## What the sets contain

| field | value |
|---|---|
| `x,y,z` | **same points AND same corrected coords as `clustering_global`** — data `x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce` (see "coordinates" below) |
| `q` | **same as `clustering_global`** (`point_charge`) |
| `cluster_id` | **4-case tagger state 0/1/2/3** (see "4-case encoding" below) |
| `real_cluster_id` | written as `0` everywhere (see note) |

Note on "no real_cluster_id": `Bee::Points::append()` always emits a
`real_cluster_id` array, so it is present but **all-zero**. Because BEE colors by
`real_cluster_id` only when it is `> 0` (`sst.js:150-154`, see
`questions/cluster_id-vs-real_cluster_id.md`), an all-zero array makes BEE fall
back to coloring by **`cluster_id`** — i.e. exactly the tagger-state split we
want. So functionally there is "no real_cluster_id" coloring; the state drives
the color.

Unlike the truth sets (`mc`, `truth_*`, `sed-*`, sim-only), the tagger sets are
written in **both realities** (MC and data).

## How the taggers work (what the encoding reflects)

`TaggerCheckSTM/TGM/FC` (`clus/src/`) only ever act on `Flags::main_cluster`
clusters (`if (!cluster->get_flag(Flags::main_cluster)) continue;`) — and of
those, with `beam_window_only=true` they only *evaluate* the ones whose matched
flash time `cluster_t0` is in the beam gate `[0.2, 2.2) µs` ("beam-window
candidates"); a flag (`flag_STM/TGM/FC`) is set only on a tagged candidate.
`associated_cluster`s are companions in the same flash bundle (grouped by
`matched_flash_gid`) — passed into `check_*_conditions` as *context* only, never
tagged; non-main/non-associated clusters are ignored entirely.

`flag_main_cluster` itself is set by **QLMatching** (`flag_matched_mains`): it
flags the main of **every** matched flash bundle. In SBND essentially every
cluster matches a flash, so almost every cluster is a main — which is why the
"not-main" case (code 0 below) is rare in practice.

## 4-case encoding (`cluster_id`)

Two axes — is it a main_cluster (QLMatching), and if so is it an in-beam-window
candidate the tagger evaluated / tagged:

| code | meaning |
|---|---|
| 0 | not a `main_cluster` (associated / unmatched) — rare in SBND |
| 1 | main, **out of beam window** — never evaluated by the tagger |
| 2 | main, **in beam window**, evaluated but **not tagged** |
| 3 | main, **in beam window**, **tagged** (`flag_STM/TGM/FC` set) |

The labeler derives this per cluster from `flag_main_cluster`, `cluster_t0` vs
the beam gate, and `flag_STM/TGM/FC`.

## Coordinates

The tagger sets overlay `clustering_global`, so they use the **same corrected
coordinate scope** the all-APA MABC bee uses — data `['x_t0cor','y_cor','z_cor']`,
sim `['x_sce','y_sce','z_sce']` (`common_corr_coords`). The labeler reads these
named arrays from each blob's `"3d"` PC (falling back to raw `x,y,z` if unset).
The **truth** sets (`mc`, `truth_*`) keep raw/true coords — those represent true
deposit positions, not reco clusters.

## Changes

### 1. `larwirecell/aiml/TensorSetLabeler.{cxx,h}` (the labeler)
- Declare three `Bee::Points` (`tagger_stm/tgm/fc`) with the event RSE, next to
  the existing `bpts_unlab`.
- In the per-cluster loop, read from the cluster's `cluster_scalar` local PC:
  `flag_main_cluster`, `cluster_t0` (double), and `flag_STM/TGM/FC`, and compute
  the 4-case `cluster_id` code (0/1/2/3) using the beam gate.
- New config params:
  - `tagger_coords` (3 strings): the corrected coord array names for the tagger
    sets (data `x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce`); empty → raw
    `x,y,z`. Read from the blob's `"3d"` PC.
  - `beam_window` (2 doubles, internal units, default `[0.2, 2.2] µs`): the
    in-window test; MUST match the tagger's `beam_window`. (`Units.h` added to
    the header for the default.)
- In the blob dump, append every point to all three tagger sets with the
  corrected coords + the 4-case code: `append(pt, q, code_xxx, 0)`.
- Gate: the blob-dump / write blocks that were `if (is_sim && m_bee_sink)` are
  split — the **truth** sets stay inside `if (is_sim)` (raw coords), the
  **tagger** sets are written whenever `m_bee_sink` exists (both realities).

### 2. `cfg/pgrapher/experiment/sbnd/clus.jsonnet` (WCT) — clustering+matching ONLY
The follow-up tail (PR taggers + labeler + dump) was **removed** from
`clus.jsonnet` so the toolkit maker does only clustering + matching:
- `clus_all_apa` no longer takes `run_labeler`/`pr_node`, no longer defines the
  `wclsTensorSetLabeler` node, and returns just the all-APA MABC
  (`pipeline([mabc])`, or `[mabc, sink]` when `dump=true`).
- The maker `all_apa()` method dropped `run_taggers`/`pr_node`.
- New maker primitives are exposed so the **entry** can build the labeler node
  with the exact same config: `pc_transforms(dv)`, `sce_field_fwd`,
  `drift_speed`, `time_offset`, `fiducial_box()`, `bee_coords` (the corrected
  coord names `clustering_global` uses) (and the existing
  `detector_volumes(anodes, face)`). The `pr()` method (SBND production tagger
  operating point) was already exposed.

### 3. `sbnd/wcls-img-clus-matching-xin.jsonnet` (entry, wcp-porting-img) — assembles the tail
The tagger PR pass, the `wclsTensorSetLabeler`, and the terminal `TensorFileSink`
are now built **here** and wired in `g.intern`:
```
matching_joint → clus_all_apa(MABC, dump=false) → pr_node → labeler → tail_dump
```
- `clus_all_apa = clus_maker.all_apa(..., dump=false)` — clustering+matching, no sink.
- `pr_node = clus_maker.pr(..., pipeline_names=[switch_scope, unmerge_bundle,
  unmerge_assoc, steiner, fiducialutils, tagger_check_tgm/stm/fc],
  particle_dataset/extra_uses from particle_dataset.jsonnet)` — the STM/TGM/FC pass.
- `labeler` = the `wclsTensorSetLabeler` `g.pnode`, built from the exposed
  `clus_maker` primitives, plus `tagger_coords: clus_maker.bee_coords` and
  `beam_window`. **Node name kept `clus_all_apa`** so the fcl inputer
  `wclsTensorSetLabeler:clus_all_apa` still resolves (no fcl change).
- `tail_dump` = `TensorFileSink` (`dump_mode=false`, the labeled-pctree tarball).
- A single `local beam_window = [0.2*wc.us, 2.2*wc.us]` feeds **both**
  `clus_maker.pr(...)` and the labeler `beam_window`, so the tagger's evaluation
  gate and the labeler's in-window test can never drift.

Benefit: `clus.jsonnet` is clustering+matching only; the entry config owns the
larwirecell labeler + PR follow-up. Validated byte-for-byte equivalent to the
previous in-`clus.jsonnet` wiring (same mabc.zip sizes, same tagged counts).

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
| larwirecell (MRB `srcs/larwirecell`) | `dev-v10_14_02_02` | `aiml/TensorSetLabeler.{cxx,h}` | modified, built, `libWireCellAIML.so` hand-copied to `opt` |
| wire-cell-toolkit | `master` | `cfg/pgrapher/experiment/sbnd/clus.jsonnet` | modified — labeler/PR tail removed, primitives exposed (jsonnet, no build) |
| wcp-porting-img | — | `sbnd/wcls-img-clus-matching-xin.jsonnet` | modified — assembles MABC→pr→labeler→dump |

## Validation

See `runs/2026-07-29-tagger-bee-sets.md`. Summary:
- Smoke (1 MC + 1 data, evt 269774): both `RC=0`. Coordinate fix confirmed —
  `tagger_fc` x-mean tracks `clustering_global` (data −12.8 vs −13.0; sim
  likewise), not the raw truth coords (−91). 4-case confirmed — data evt 269774
  `tagger_fc` = `{1: 11843, 2: 16, 3: 9689}` (cluster 13 FC-tagged → code 3).
- 10 MC + 10 data, **per-event**: all 20 `RC=0`, no segfaults. 4-case aggregate:

  | set | MC (0/1/2/3) | data (0/1/2/3) |
  |---|---|---|
  | `tagger_stm` | 1:254013, 2:30307, **3:2545** | 1:278702, 2:90272 |
  | `tagger_tgm` | 1:254013, 2:13879, **3:18973** | 1:278702, 2:75568, **3:14704** |
  | `tagger_fc`  | 1:254013, 2:32852 | 1:278702, 2:51891, **3:38381** |

  (No code 0 — QLMatching flags every matched cluster a main. The large code-1
  bucket is out-of-window cosmic mains, cleanly separated from the in-window
  candidates in codes 2/3.)

BEE (full `.../event/list/` URLs):
- MC 1-evt smoke: https://www.phy.bnl.gov/twister/bee/set/3b6ccf2b-a99a-4795-a031-3cef27bea31d/event/list/
- data 1-evt smoke: https://www.phy.bnl.gov/twister/bee/set/5e4a6fa2-6547-4c2d-af9d-a3a0303eafcc/event/list/
- MC 10-evt: https://www.phy.bnl.gov/twister/bee/set/32520625-3ffe-4804-8eda-0e72b906f5b7/event/list/
- data 10-evt: https://www.phy.bnl.gov/twister/bee/set/01532c4a-b363-45ab-9374-247da14819b6/event/list/
