# Issue #2 — Add STM/TGM/FC tagger BEE sets to `TensorSetLabeler.cxx`

Status: **done & validated** (2026-07-29).

Add three BEE point sets — `tagger_stm`, `tagger_tgm`, `tagger_fc` — to
`wclsTensorSetLabeler` (larwirecell `aiml/`). Each set contains **only the
clusters the corresponding tagger actually evaluates** — the beam-window
candidates — sharing `clustering_global`'s coordinates and charge, colored by the
tagger verdict.

## What the sets contain

| field | value |
|---|---|
| points | **only beam-window candidate clusters** (`main_cluster` with `cluster_t0 ∈ [0.2,2.2) µs`); out-of-window mains and non-mains are omitted |
| `x,y,z` | **same corrected coords as `clustering_global`** — data `x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce` (see "coordinates" below) |
| `q` | **same as `clustering_global`** (`point_charge`) |
| `cluster_id` | **0 = not tagged, 1 = tagged** (`flag_STM/TGM/FC` set) |
| `real_cluster_id` | written as `0` everywhere (see note) |

Note on "no real_cluster_id": `Bee::Points::append()` always emits a
`real_cluster_id` array, so it is present but **all-zero**. Because BEE colors by
`real_cluster_id` only when it is `> 0` (`sst.js:150-154`, see
`questions/cluster_id-vs-real_cluster_id.md`), an all-zero array makes BEE fall
back to coloring by **`cluster_id`** — i.e. exactly the tagged/not-tagged split
we want. So functionally there is "no real_cluster_id" coloring; the verdict
drives the color.

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

## Candidate-only + verdict coloring (`cluster_id`)

To keep the display focused, the tagger sets contain **only the beam-window
candidates** — a cluster is dumped iff it is a `flag_main_cluster` (QLMatching
flags the main of every matched flash bundle) **and** its `cluster_t0` is in the
beam gate `[0.2, 2.2) µs`. Out-of-window mains and non-main (associated /
unmatched) clusters are dropped entirely. The surviving points are colored:

| `cluster_id` | meaning |
|---|---|
| 0 | candidate evaluated, **not tagged** |
| 1 | candidate **tagged** (`flag_STM/TGM/FC` set) |

The labeler gates on `flag_main_cluster` + `cluster_t0` vs the beam gate, then
colors by `flag_STM/TGM/FC`. (An earlier revision kept all clusters with a 4-case
code 0/1/2/3 = not-main / out-of-window / in-window-untagged / in-window-tagged;
this was narrowed to candidate-only 0/1 for a cleaner display.)

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
  `flag_main_cluster`, `cluster_t0` (double), and `flag_STM/TGM/FC`. A cluster is
  a tagger **candidate** iff `flag_main_cluster && cluster_t0 ∈ [low,high)`; only
  candidates are appended, with `cluster_id = flag_STM/TGM/FC ? 1 : 0`.
- New config params:
  - `tagger_coords` (3 strings): the corrected coord array names for the tagger
    sets (data `x_t0cor/y_cor/z_cor`, sim `x_sce/y_sce/z_sce`); empty → raw
    `x,y,z`. Read from the blob's `"3d"` PC.
  - `beam_window` (2 doubles, internal units, default `[0.2, 2.2] µs`): the
    in-window test; MUST match the tagger's `beam_window`. (`Units.h` added to
    the header for the default.)
- In the blob dump, append points to the three tagger sets **only for candidate
  clusters**, with corrected coords + the 0/1 verdict: `append(pt, q, tag_xxx, 0)`.
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

## ⚠ Operational findings — bulk running

- **Taggers must run per-event.** Running the PR tagger chain **inline over a
  multi-event `lar` job crashes** (SIGSEGV inside the tagger/steiner patrec — the
  known data-dependent patrec instability, *not* an issue-#2 bug): a 10-event MC
  batch died on the 3rd event, a 10-event data batch on the 6th. This is why the
  standalone nusel tagger step runs one event per process. **Bulk tagger
  production must be per-event** (one `lar -n 1 --nskip K` per event), then merge
  the per-event BEE zips.
- **Cap each event with a timeout.** Rare data events hang in *imaging*
  (`MaskSlice`, before clustering) — the 48-event data run had one (evt29) freeze
  for >10 min. Wrap each per-event `lar` in `timeout 300` so a hang can't stall a
  batch; the retried evt29 then completed cleanly in < 5 min.
- **Watch the cephfs quota.** The per-event `nugraph.h5` + `trash-all-apa.tar.gz`
  are byproducts not needed for the tagger BEE; on a tight user quota (`yuhw` is
  60 GiB) they exhaust it mid-run (HDF5 `truncate ... Disk quota exceeded`,
  errno 122 → the run's tail fails). Delete `nugraph.h5`/`trash-all-apa.tar.gz`
  per event (keep only `mabc.zip`).

## Local edits (pushed 2026-07-30)

| repo | branch | file | commit |
|---|---|---|---|
| larwirecell | `dev-v10_14_02_02` (`HaiwangYu/larwirecell`) | `aiml/TensorSetLabeler.{cxx,h}` | `4143d3e` (built, `libWireCellAIML.so` hand-copied to `opt`) |
| wire-cell-toolkit | `master` (`WireCell/wire-cell-toolkit`) | `cfg/pgrapher/experiment/sbnd/clus.jsonnet` | `cdca41c0` — labeler/PR tail removed, primitives exposed |
| wcp-porting-validation | `main` | `sbnd/wcls-img-clus-matching-xin.jsonnet` | `6402808` — assembles MABC→pr→labeler→dump |

## Validation

See `runs/2026-07-29-tagger-bee-sets.md`. Summary:
- Smoke (1 MC + 1 data, evt 269774): both `RC=0`. Candidate-only confirmed — MC
  tagger sets 1818 pts (vs 22009 in `clustering-global`), all `cluster_id=0`;
  data `tagger_fc` = `{0: 16, 1: 9689}` (cluster 13 FC-tagged). Coordinate fix
  confirmed — coords track `clustering_global`, not raw truth.
- 10 MC + 10 data, **per-event**: all 20 `RC=0`, no segfaults. 0/1 aggregate
  (per-set point total = the candidate count, same across the three taggers):

  | set | MC (0/1) | data (0/1) |
  |---|---|---|
  | `tagger_stm` | 30307 / **2545** | 90272 / — |
  | `tagger_tgm` | 13879 / **18973** | 75568 / **14704** |
  | `tagger_fc`  | 32852 / — | 51891 / **38381** |

  (Fired: STM 1 MC evt; TGM 2 MC + 2 data; FC 5 data.)
- **All 48 data events** (the full evt-269774 file), per-event, all `RC=0`
  (evt29 needed a retry after an imaging hang; evt30 after a quota-exhaustion
  crash — both then clean):

  | set | data 48-evt (0/1) | tagged in |
  |---|---|---|
  | `tagger_stm` | 421465 / — | 0/48 |
  | `tagger_tgm` | 378688 / **42777** | 5/48 |
  | `tagger_fc`  | 228115 / **193350** | 22/48 |

BEE (full `.../event/list/` URLs, candidate-only 0/1):
- MC 10-evt:   https://www.phy.bnl.gov/twister/bee/set/169bdddf-0f71-44ab-aab1-47a896316040/event/list/
- data 10-evt: https://www.phy.bnl.gov/twister/bee/set/98263fdf-53ac-491d-84cf-c4dca3522606/event/list/
- **data 48-evt**: https://www.phy.bnl.gov/twister/bee/set/7d081fbf-b08f-4dbd-9c47-cd73a7c98472/event/list/
