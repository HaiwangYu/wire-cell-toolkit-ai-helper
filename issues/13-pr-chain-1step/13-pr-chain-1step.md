# Issue 13 — porting the PR chain into the 1-step wcls workflow

Goal: run Xin's full pattern-recognition (PR) chain inside our single-process
`wcls-img-clus-matching-xin` job, instead of the 2-step
`run_ql_evt.sh` → `run_pr_chain_batch.sh` handoff through files.

**Primary document (component map, gaps, routes, all measurements):**
`wcp-porting-img/sbnd/docs/5-pr-chain-in-1step.html`
— an HTML doc in the working repo, iterated on across this whole investigation.
This issue is the tracking record and the narrative of how each gap fell.

## The headline

The 1-step job **already instantiates the PR node** — the same
`MultiAlgBlobClustering` instance (`clus_pr`) the 2-step chain runs — and already
executed 8 of its 15 production stages. Every C++ component the remaining 7 need
was already compiled into our installed libs. Turning the full chain on is a
**5-name edit to `pipeline_names`**, and that edit has now been run end-to-end.

## Component inventory

- **Graph nodes**: `wclsCookedFrameSource` → `FrameFanout` → 2× imaging pipe →
  `PointTreeBuilding` → per-APA `MABC` → `FlashTensorToOpticalPCs` → joint
  `QLMatching` → all-APA `MABC` → **`clus_pr` MABC** → `wclsTensorSetLabeler` →
  `TensorFileSink`.
- **CM modules inside the MABCs**: 16 per-APA (`ClusteringPointed` …
  `ClusteringExamineBundles`), 10 all-APA (flash-T0 gated, plus
  `ClusteringCathodeConnect` / `CathodeBundleRescue`), and the 15-stage PR list
  (`switch_scope`, `unmerge_bundle`, `unmerge_assoc`, `steiner`, `fiducialutils`,
  `tagger_check_tgm/stm/fc`, `protect_bundle`, `steiner_refresh`,
  `tagger_check_neutrino`, `numu_bdt_scorer`, `nue_bdt_scorer`,
  `tracking_visitor`, `tagger_output`).

Full tables — jsonnet name → component type → SBND operating point — are in the
HTML doc §2, §3.

## Does the PR chain discard out-of-beam-window clusters?

**No.** Investigated because it determines whether the PR stage is safe to add.

- The `beam_window_only` gates are `continue;` statements over work lists.
  `TaggerCheckNeutrino.cxx` contains no `separate(` / `remove` / `erase` at all —
  it is a pure annotator.
- `CreateSteinerGraph` filters a local `std::vector<Cluster*>`; the grouping is
  untouched.
- `unmerge_bundle` / `unmerge_assoc` / `protect_bundle` all use
  `separate(..., remove=false)` with explicit `BLOB LOSS` assertions.
- `switch_scope` splits by **active volume**, not time, and keeps both halves.
- Things disappear only from the **Bee display**, and only by volume
  (`bee_points_sets` `filter` defaults to 1 = in-scope only). The tensor output
  is unfiltered.

Consequence to remember: an out-of-window cluster comes out **un-evaluated**,
which is not "evaluated and found not a cosmic".

## Gap ledger

| | gap | status |
|---|---|---|
| G0 | C++ components present | never a problem — all already built |
| G1 | `XGB_nue_seed2_0923.xml` missing | **resolved** (owner added it) |
| G2 | DL (SCN) vertex unavailable | **resolved** — uboone `scn` UPS product |
| G3 | RSE = 0/0/0 in everything WCT writes | **resolved** — new attacher component |
| G4 | PR Bee layers land in a separate zip | **resolved*** — one caveat, see below |
| G5 | `PrDisplayDump` absent | **resolved** by the upstream merge |
| G6 | no pctree written before the PR node | open (one `tensor_outname` argument) |
| G7 | cost of the full chain | partially measured, see below |
| G8 | stale docs (`enable_downstream_pr`, `x_sce` comment) | open, cosmetic |

## How each gap fell

### Toolkit merge (prerequisite)
`ap-yuhw` was 5 ahead / 143 behind `origin/apply-pointcloud`. Four of the five
commits were already published on `fork/ap-yuhw`, so this was integrated by
**merge, not rebase** — zero conflicts, merge commit `598d2195`, safety tag
`pre-merge-20260817`. WCT rebuilt (7m18s) and larwirecell rebuilt + hand-copied.
The merge also delivered **G5**: `PrDisplayDump` and the `pr_display` stage.

Gotcha found: `standalone-sample/2025f-mc.root` and `2025f-data.root` are broken
symlinks (their target dir was cleaned). Use a file from the issue-11 list.

### G2 — the DL vertex
The missing torch/sparseconvnet come from the **uBooNE UPS product
`scn v01_00_00`**, flavor `Linux64bit+3.10-2.17`, under
`/cvmfs/uboone.opensciencegrid.org/products`. It works *only because* its venv is
python **3.9.15 — the same as our container python**; `WCPPyUtil` embeds
libpython, so any other version would not load. (The sibling `SparseConvNet`
product is flavor `NULL`; `scn` is the right one.)

Wired by the new opt-in `sbnd/setup-dlvtx.sh`. Kept out of `setup-ap.sh` because
it shadows numpy 1.24.3 with 2.0.2 for every python in the shell.

**`LD_PRELOAD` is NOT needed on our build**, unlike sbnd_xin's runner.

A/B on one MC event, full 15-stage pipeline:

| | with `scn` | without |
|---|---|---|
| `"DL vertex failed"` | **0** | 1 (`No module named 'torch'`) |
| `overall main vertex` | **6523 ms** | 29 ms |
| full event | 21.63 s | 14.86 s |

Scores came out bit-identical between the two arms on this event — but the
selected main cluster was 1.6 cm long in a cosmic-dominated event, so that is
**not** a general statement. Cost and physics effect both need a real
multi-event sample (this is the open half of G7).

### Labeler ordering (prerequisite for G3)
The labeler sat *downstream* of the PR node, so truth was attached to the
PR-split, PR-renumbered clustering — i.e. truth labels depended on PR
configuration. Split into two instances:

```
clus_all_apa -> labeler_truth -> pr_node -> labeler_tagger -> sink
```

Reused the existing component rather than forking it; two new knobs
(`label_blobs`, `bee_sets`), both defaulting to historical behaviour.
`label_blobs=false` is required, not an optimisation: the `trackid` write-back is
not reality-gated, so a second pass would stamp `trackid=-1` over the first
instance's labels.

Verified: instance B reported `projected 0/120293 depos, labeled 2889/3044
blobs` — it read back what A wrote, proving the labels survive `switch_scope`,
`unmerge_bundle`, `unmerge_assoc` and `protect_bundle`. (They ride on the
*blob node's* `"scalar"` PC; `switch_scope` erases only the *cluster-level*
`"perblob"`.) 15 of 17 Bee layers byte-identical; the two that moved were
exactly the ones carrying cluster identity. Cost +0.13%.

### G3 — RSE
Root cause: `IEnsembleVisitor::visit()` receives **only** the `Ensemble` — no
`ITensorSet`, no ident, no RSE. And `rse_from_ident` recovers the *event number
only* (`MultiAlgBlobClustering.cxx`: *"run/subrun are not available in this
chain"*), because the ident traces to `SimpleFrame(event.event(), ...)`.

Measured symptom: one `mabc.zip` carrying **two different run numbers** — 7 MABC
layers at 0/0/3, 10 labeler layers at 713/74/3 — and `Trun = (0,0,0)` in
`tracking-pr.root`.

Fix, seven pieces (item 8, RSE branches on `T_tagger`, deferred):

1. **New** `wclsTensorSetMetadataAttacher` in `larwirecell/Components/` —
   `IArtEventVisitor` + `ITensorSetFilter`, stamps RSE into set metadata, shares
   `in->tensors()` by pointer (O(1), no pctree round trip). Warns instead of
   stamping 0/0/0 if it was never registered as an inputer.
2. `MultiAlgBlobClustering::rse_from_metadata`, precedence
   **metadata > ident > config**.
3. MABC metadata passthrough — it previously dropped input metadata entirely.
4. MABC publishes the resolved RSE on the ensemble scalar PC.
5. Both Magnify tracking visitors read it from the ensemble, config as fallback.
6. `clus.jsonnet`: `rse_from_metadata` threaded, plus a new `pre_mabc` splice
   hook (the per-APA `PTB → MABC` pipeline was otherwise opaque).
7. Three attacher instances wired in the entry jsonnet + both fcls.

Result: **all 17 Bee layers at 713/74/3**, `Trun` (0,0,0) → (713,74,3),
**payload identical in 17/17 layers** with RSE excluded, cost +0.2%.

Two traps hit: assigning the new RSE before `flush()` (which writes the
*previous* event) would have stamped each event with its successor's RSE; and
jsonnet top-level `local`s are not forward-visible.

## Full PR chain, end to end

With G1/G2/G5 closed, the 15-stage pipeline ran **first try, rc=0**, no code
change beyond the stage names:

- `tracking-pr.root` 211 KB — `T_tagger` (1 entry, **1216 branches**,
  `numu_score = -1.7148`, `nue_score = -15.0`), `T_kine`
  (`kine_reco_Enu = 107.46`), `Trun`, plus the Magnify trees.
- DL vertex healthy (0 failures).

### G4 — PR Bee layers
`clus_pr` was the only MABC maker without a `bee_sink`, so its layers went to
`mabc-pr.zip`, which the issue-11 harness deletes — throwing away the three
layers that exist nowhere else (`track_fit`, `shower_track`, `vertices`: the
fitted trajectory, per-particle shower/track colouring, reconstructed vertices).

Fixed with three jsonnet changes, no C++: `bee_sink` pass-through; the two
colliding set names renamed **only when a sink is shared**
(`clustering`→`clustering-pr`, `mc`→`mc-pr`) so sbnd_xin's `nusel_extract.py`,
which requires `-clustering-global.json` inside `mabc-pr.zip`, keeps working;
and `save_deadarea: bee_sink == null` — the first attempt produced 24 entries
with `channel-deadarea-apa0/1` **duplicated**, because `clus_pr` wrote dead area
on top of `clus_all_apa`'s (`clus_per_face` already guarded this).

Result: one zip, 22 entries, zero duplicates, no `mabc-pr.zip`.

**Bee check** (uploaded, set `8374939d`): 19 layers registered, DAQ ID shown as
`713-74-3` (the G3 fix, visible). But *registered != rendered*, and the two
families differ, read off `bee.js`:
- **point sets are generic** — `${event_url}${eventId}/${this.name}/`, so
  `clustering-pr-global`, `track_fit-global`, `shower_track-global`,
  `vertices-global` are all viewable;
- **the particle tree is hardcoded** — `this.url = base_url + "mc/"`, feeding one
  `<div id="mc">`. Bee renders **exactly one** particle tree per event, named `mc`.

So `mc-pr.json` is stored and listed but **never displayed**. The collision is
real (two different trees, one name), so something must give: current state keeps
the labeler's TRUTH tree as the rendered `mc` and parks the PR RECO particle flow
at `mc-pr`. Swapping is one line in each of `clus_pr` and the labeler. Which
deserves the panel is a physics call — left open.

## Open

- **G6** — no post-Q/L pctree; blocks `nusel_extract.py` and the
  run-the-2-step-on-1-step-output cross-check. One `tensor_outname` argument.
- **G7** — cost and physics of the full chain on a real multi-event sample.
  DL vertex is +6.8 s/event on the one event measured.
- **Route B cross-check** — run the canonical
  `cfg/pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet` on a 1-step-written
  pctree and compare `T_tagger` leaf-by-leaf against Route A. This is the real
  validation and it is not done.
- **Item 8** — RSE branches on `T_tagger`/`T_kine` (they carry none today).
- Single-instance labeler config not re-verified byte-identical after the
  two-knob change (defaults are historical; reasoning, not measurement).

## Repos touched (all uncommitted, for review)

| repo | files |
|---|---|
| `wire-cell-toolkit` (`ap-yuhw`) | merge `598d2195`; `MultiAlgBlobClustering.{h,cxx}`, `Sbnd{Pr,}MagnifyTrackingVisitor.{h,cxx}`, `cfg/…/sbnd/clus.jsonnet` |
| `larwirecell` (MRB tree) | **new** `Components/TensorSetMetadataAttacher.{h,cxx}` + CMakeLists; `aiml/TensorSetLabeler.{h,cxx}` |
| `wcp-porting-img` | `sbnd/docs/5-pr-chain-in-1step.html`, `sbnd/setup-dlvtx.sh`, `sbnd/wcls-img-clus-matching-xin.{jsonnet,fcl}`, `…-data.fcl` |
