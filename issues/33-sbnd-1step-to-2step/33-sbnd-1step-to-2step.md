# Issue 33: split the SBND LArSoft 1-step chain into Q/L (LArSoft) + PR (standalone) with truth pass-through

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/33.

Builds on:
- #32: toolkit `polaris-build-fixes` `58b958f1`; the hit-flash 1-step validated against Xin's `m0925pr` run.
- #29: the Aurora setup and scripts in `issues/29-aurora-production/scripts/`.

The component graph of today's chain is in toolkit `cfg/pgrapher/experiment/sbnd/docs/wcls-img-clus-matching-xin-chain.md`.

**Ask (Haiwang, 2026-09-29).** Split the 1-step chain `wcls-img-clus-matching-xin-lib.jsonnet` into two steps:

1. `wcls-img-clus-matching.jsonnet` (LArSoft).
   - After charge-light matching, write the matched bundles to disk as an ITensorSet tar. The tar carries the clustering, the light information and the metadata.
   - This lets the PR part be re-run many times, so it can be iterated faster. The PR part is the taggers, track/shower, trajectory fitting, vertexing, PID, particle flow, energy reconstruction and the nue/numu/NC scores.
   - CTPC must survive, because 2D and trajectory fitting need it.
2. `wct-pr.jsonnet`, which runs that PR part.

A new larwirecell module, `TruthInformationAttacher`, attaches truth and the RSE to the step-1 ITensorSet before serialization. It **replaces `wclsTensorSetMetadataAttacher`**, since what it attaches is a superset. It writes two tensors:
- **Neutrino level**: a 2D tensor with one truth neutrino per row. Columns: true energy, vertex, deposited energy, interaction time, flavour (nue/numu) and interaction type (CC/NC/...).
- **Particle-flow level**: a 2D tensor with one particle per row. Columns: row index into the neutrino tensor, PID, energy, start position and end position.

When truth is present, `SbndPrMagnifyTrackingVisitor` writes two new trees, one for each tensor.

Validation: re-run the nueCC-48 and NCpi0-19 samples and compare with our own previous results, the way #32 did.

## Decisions (Haiwang, 2026-09-29, answers to the scoping questions)

| question | decision |
|---|---|
| where step 1 ends | **After `clus_all_apa`**, the same cut Xin's Q/L job makes. Step 1 is `... QLMatching -> clus_all_apa -> labeler_truth -> TruthInformationAttacher -> TensorFileSink`. `labeler_truth` (blob `trackid`, truth/sed Bee sets, nugraph HDF5) stays in step 1. |
| what step 2 is | **A new thin standalone job** (`wire-cell -c wct-pr.jsonnet`): `TensorFileSource -> clus_maker.pr()` with its production defaults, the exact PR node the 1-step runs. It does not wrap the 3,927-line `wct-pr-perevt.jsonnet`, and it has no knob mirror. |
| tar layout | **One tar per `lar` job**, holding every event of that job. `wct-pr.jsonnet` loops over the tensor sets. |
| `labeler_tagger` (the tagger_stm/tgm/fc Bee sets, art-only) | **Port to a toolkit visitor** so that step 2 writes them standalone. |

## What already exists (surveyed 2026-09-29, toolkit `58b958f1`, larwirecell `f8177c7`)

- **Xin's standalone 2-step:**
  - `cfg/pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet` writes the all-APA MABC tensor output with `clus_maker.all_apa(..., tensor_outname=...)`. The output is `pctree-evt<E>.tar.gz` with the `clustering_` prefix.
  - `wct-pr-perevt.jsonnet` reads it back with `TensorFileSource{prefix: 'clustering_'}`.
  - So the dump and read-back mechanism works: Xin's PR runs from that tar. His tar is written straight from the MABC, though, with no art-side truth.
- **The 1-step already ends in a tar:** `TensorFileSink:clus_all_apa` writes `trash-all-apa.tar.gz` after `labeler_tagger`. Step 1 moves that sink to just after `clus_all_apa`/`labeler_truth`.
- **CTPC:**
  - Built by `PointTreeBuilding::add_ctpc` as grouping-level local point clouds `ctpc_a<A>f<F>p<P>`, which `Facade_Grouping` reads.
  - Dead-wind PCs (`dead_winds_a*`) sit alongside them.
  - Xin's PR works from the tar, so these are expected to survive serialization. M1 checks this explicitly, per dataset, before we rely on it.
- **`wclsTensorSetMetadataAttacher`:**
  - An O(1) filter: `IArtEventVisitor` plus `ITensorSetFilter`, adding `runNo`/`subRunNo`/`eventNo` to the set metadata.
  - Three instances: `rse_apa0`, `rse_apa1` and `rse_all_apa`.
- **`wclsTensorSetLabeler` already reads most of the requested truth** (from `generator` MCTruth, `largeant` MCParticle, `ionandscint:priorSCE` SimEnergyDeposit):
  - The per-neutrino fields are set metadata written as parallel arrays: `n_nu`, `nu_idx`, `nu_pdg`, `nu_ccnc`, `nu_int_type`, `nu_energy`, `nu_vtx_{x,y,z}`, `nu_flavor`, `nu_edep`.
  - A `truth_per_track` 2D tensor has one MCParticle per row, with `nu_idx` and `process` columns. Its default is beam-neutrino primaries only.
  - **Missing: the interaction time.** It will be taken from the MCTruth neutrino's `Nu().T()`.
- **RSE and multi-event output:**
  - `SbndPrMagnifyTrackingVisitor` takes the RSE from the ensemble (`ensemble.rse_valid()`, published by the MABC from set metadata).
  - Its `output_filename` already accepts a printf template (`tracking-pr-%d.root`, ident-substituted) so that a multi-event process writes one file per event. Without `%`, a multi-event run keeps only the last event, the #29 caveat. `UbooneTaggerOutputVisitor` opens the same file with UPDATE.
- **How metadata reaches the visitors:**
  - The MABC keeps the input set metadata (`m_in_metadata`), and `bee_pf` already merges a metadata key (`bee_pf_truth`) from `labeler_truth` into the `mc` tree.
  - **No path exists yet for an extra tensor to reach an `IEnsembleVisitor`**, which is what the new truth trees need.

## Design

### Step 1: `wcls-img-clus-matching.jsonnet` (LArSoft, art input)

```
sigs -> FrameFanout -> img[n] -> PointTreeBuilding[n] -> TIA:rse_apa<n> -> MABC apa<n>
light[n] (hits | reco1) -----------------------------------------> flash_attach[n]
flash_attach[0,1] -> QLMatching:matching_joint -> TIA:rse_all_apa -> MABC clus_all_apa
  -> wclsTensorSetLabeler:labeler_truth -> wclsTruthInformationAttacher:truth -> TensorFileSink (qlpctree.tar)
```

(TIA = `wclsTruthInformationAttacher`.)

- **Shared code:** the imaging, clustering and light section is lifted from `wcls-img-clus-matching-xin-lib.jsonnet` into a shared lib, so the 1-step job and step 1 cannot drift apart. The 1-step job stays available: `wcls-img-clus-matching-xin{,-hits}.jsonnet` are unchanged, and a compile gate checks their byte-identity.
- **Flash options:** `flash_source` (`reco1`/`hits`) and the light gate stay arguments, as today. The production pair is the `-hits` pair.
- **Output name:** `outname` is an extVar, with fcl default `qlpctree.tar.gz`. The prefix stays `clustering_`, which Xin's reader expects.
- **`TensorFileSink` format:** `dump_mode: false` gives real tensors. Every event of the `lar` job goes into one file, keyed by set ident. **Open item:** we need a set ident unique within the file. Today it is the art event number, and a file spanning subruns could repeat it. M1 checks this, and the RSE is in the metadata regardless.

### `wclsTruthInformationAttacher` (larwirecell, new)

- **Interfaces:** `IArtEventVisitor` + `ITensorSetFilter` + `IConfigurable`, the same as `TensorSetMetadataAttacher`. It is O(1) in the point cloud: it appends tensors and metadata and never deserializes the tree.
- **Always:** it stamps `runNo`/`subRunNo`/`eventNo`. So the three `rse_*` nodes become instances with `truth: false`, and `wclsTensorSetMetadataAttacher` is retired. The retirement lands only after the gate shows identical output.
- **When `truth: true` and the event has MCTruth (sim)**, it appends two tensors.
  - `truth_nu`, shape `[n_nu, K]`. Its columns are named in the tensor metadata `columns`, and units are LArSoft native (cm, ns, GeV):

    | column | meaning |
    |---|---|
    | `nu_idx` | the MCTruth index |
    | `pdg` | neutrino PDG code |
    | `ccnc` | CC or NC |
    | `int_type` | interaction type |
    | `mode` | interaction mode |
    | `flavor` | 0 none / 1 nue / 2 numu / 3 NC |
    | `E` | true neutrino energy |
    | `vtx_x`, `vtx_y`, `vtx_z` | interaction vertex |
    | `t` | interaction time, new |
    | `edep` | deposited energy |
  - `truth_pf`, shape `[n_particle, K]`. One MCParticle per row, with columns `nu_row` (row in `truth_nu`, or -1), `trackid`, `mother`, `pdg`, `process`, `E`, `KE`, `start_{x,y,z,t}` and `end_{x,y,z,t}`.
    - The selection follows `labeler_truth`: `truth_tracks_nu_only`, and `pf_ke_min` as the labeler's pf tree applies it.
    - The truth extraction is factored out of `TensorSetLabeler` into a shared helper. The two outputs then agree by construction, and a unit check compares them on MC.
- **On data** it writes the RSE only. No empty truth tensors are written, so "truth present" means the tensors exist.
- **Tensor names** inside the set are `truth/nu` and `truth/pf`, next to the `pointtrees/<N>` datapath. The MABC and PR readers skip what they do not know. M1 checks that assumption.

### Step 2: `wct-pr.jsonnet` (standalone `wire-cell`, no art)

```
TensorFileSource(qlpctree.tar.gz, prefix clustering_) -> MABC clus_pr (clus_maker.pr() defaults, 15 visitors) -> sinks
```

- **Visitors and knobs:** the same `pipeline_names`, `particle_dataset`, `beam_window` and `bee_sink` as the 1-step's `pr_node`. The two PR-stage members of `clus_all_apa` stay in step 1. Gate: the compiled `clus_pr` block of step 2 must equal the 1-step's `clus_pr` block, with only the file names allowed to differ.
- **Per-event output:**
  - `tracking-pr-%d.root`, one file per event through the existing printf template. A later option could write one multi-event file instead.
  - Bee goes to `mabc-pr.zip`, with every event in one zip.
- **Tagger Bee sets:** a new toolkit visitor (e.g. `TaggerBeeVisitor`) ports the tagger_stm/tgm/fc/lm Bee sets from `labeler_tagger`'s tagger branch. It needs the same 4-case cluster-id encoding and beam window, and `tagger_coords` = `clus_maker.bee_coords`. It is appended after `UbooneTaggerOutputVisitor`. This only matters if the labeler's tagger code is art-free, which it should be because it reads only PR flags.
- **The MC truth `mc` merge:** `labeler_truth`'s `bee_pf_truth` metadata travels in the tar, so `bee_pf.merge_metadata_key` keeps working. M1 checks that `TensorFileSource` restores the set metadata.

### Truth trees in `SbndPrMagnifyTrackingVisitor`

- **Carrying the truth:** the MABC must hand the truth tensors to its visitors. Planned route:
  - The MABC keeps the non-pointtree tensors of its input set and exposes them on the `Ensemble`. Proposed accessors: `ensemble.aux_tensor(name)`, or truth-specific getters.
  - The MABC forwards them to its output, so the pass-through also covers a chain of MABCs.
  - This is a toolkit `clus` change, reviewed separately.
- **Writing the trees:** when `truth/nu` is present, the visitor writes `T_truth_nu` (one entry per event, vector branches over neutrinos) and `T_truth_pf` (one entry per event, vector branches over particles). The branch names are the tensor column names, plus `run`, `subrun`, `event`. When the truth is absent, no trees are written, so data files are unchanged.

## Plan

| milestone | content | gate |
|---|---|---|
| M0 | this doc + issue | -- |
| M1 | Feasibility checks, on 1 MC + 1 data event, from the existing `trash-all-apa.tar.gz`. Checks: (a) `ctpc_*` and `dead_winds_*` PCs and `save_real/assoc_cluster_id` provenance survive the sink/source round trip; (b) the set metadata (RSE, `bee_pf_truth`, `frame_apply_at_caf`) is restored; (c) an extra tensor in the set is ignored by the MABC; (d) the set ident is unique across a multi-event file. | a written finding per item |
| M2 | Toolkit cfg: shared lib, `wcls-img-clus-matching.jsonnet` (step 1), `wct-pr.jsonnet` (step 2); the 1-step jobs untouched. | compile gate: 1-step byte-identical; step-2 `clus_pr` equals the 1-step `clus_pr` |
| M3 | larwirecell `wclsTruthInformationAttacher` + shared truth helper; retire `wclsTensorSetMetadataAttacher` from the jsonnet. | MC: `truth/nu`, `truth/pf` equal the labeler's metadata and `truth_per_track`; data: RSE only |
| M4 | Toolkit: truth tensors carried to the Ensemble and forwarded by the MABC; `T_truth_nu`/`T_truth_pf` in `SbndPrMagnifyTrackingVisitor`; the tagger Bee visitor. | unit/doctest + MC smoke |
| M5 | Validation (below) | tables in this doc + Bee links |

## Validation

- **Samples:** nueCC-48 and NCpi0-19 (data, hit-flash), plus the MC smoke of #32 (`mc50-hits`, 9 events) for the truth trees.
- **Reference:** our own #32 hit-flash 1-step runs `production-prep/nuecc48-hits-20260926-0535`, `ncsb-hits-20260926-0535` and `mc50-hits-20260926-0608`, built the same way (toolkit merge + `c7e7775e`).
- **Expectation: identical**, because the split only adds a serialization round trip between `clus_all_apa` and PR.
- **Tools:** the #32 tools (`compare-xin.pbs` style layout, `deep_compare.py`, `compare-bee-content.py`, `evt-branch-diff.py`, the census) and an event-by-event table. Bee uploads cover both arms.
- **Any difference is a finding:** a float residual from the round trip, or a PC that the serializer drops. Each gets traced to its cause.
- **What is new** (`T_truth_*`, the `truth/*` tensors) is checked against `labeler_truth`'s outputs on MC.

## Open items

- A set ident unique within a multi-subrun tar (M1 d).
- Whether step 2 should also write one multi-event `tracking-pr.root` instead of a file per event (later).
- Upstreaming the toolkit and larwirecell pieces: Haiwang's call, as in #32.

## Log

- 2026-09-29: scope agreed (the Decisions table above); survey of the existing pieces (section "What already exists").

### (a) 2026-09-29: M1 findings, M2 implemented, M3/M4 written (not yet built)

**M1: the tar round trip (from existing tars, no job needed).**
- **(a) What PR needs is serialized.** The 1-step's `trash-all-apa.tar.gz` (NCpi0 evt0) has these under `pointtrees/<ident>/live`:
  - CTPC: `ctpc_a{0,1}f0p{U,V,W}`, with `charge`, `charge_err`, `cident`, `slice_index`, `wind`, `x`, `y`;
  - dead wires: `dead_winds_a*` and `dead_gap_a*W`;
  - light: `flash`, `light`, `flashlight`, `opflash` (with `gid`);
  - provenance: `perblob` (`real_cluster_id/main/was_main`, `assoc_cluster_id/main`);
  - the flags and `matched_flash_gid` in `cluster_scalar`, and the blob `trackid`;
  - the `dead` grouping.
- **(a) The round trip is not new.** Between `clus_all_apa` and PR, the 1-step already passes a serialized ITensorSet (`labeler_truth` re-serializes the tree). Writing that set to disk and reading it back is expected to be lossless (`.npy` binary), which is what M5 tests.
- **(b) The set metadata carries** `runNo/subRunNo/eventNo` and the labeler's `nu_*` arrays, plus `bee_pf_truth` (the truth particle tree the PR MABC merges into Bee `mc`) on MC.
- **(c) An extra tensor does no harm.** On MC the labeler already appends a `truthtracks/<ident>` tensor, and the 1-step PR MABC ignores it.
- **(d) The set ident is the art event number.** It is unique within one filtered file. A multi-subrun file could repeat it, but the RSE in the metadata still distinguishes the events; still open.

**M2: toolkit cfg (working tree on `polaris-build-fixes`, not yet committed).**
- `sbnd-pr-stage.jsonnet`: the PR stage (beam gate, 15-visitor pipeline, the `pr()` call) as ONE definition, imported by both the 1-step lib and step 2.
- `wcls-img-clus-matching-xin-lib.jsonnet(stage='1step'|'ql')`. With `'ql'`, the graph ends `labeler_truth -> TensorFileSink:ql_pctree` (`qlpctree.tar.gz`, prefix `clustering_`, real tensors, all events of the `lar` job).
- `wcls-img-clus-matching.jsonnet` (step 1) = lib(hits, light gate, `stage='ql'`).
- `wct-pr.jsonnet` (step 2, standalone): `TensorFileSource -> sbnd-pr-stage node -> sink`, with its own `BeeSink:mabc_pr`.
  - Per-event outputs go to `pr_evt%1%/` (the ident).
  - `rse_from_metadata`, with `event_from_ident` as `evt_subdir`'s required partner.
- wcp-porting-validation: `sbnd/wcls-img-clus-matching{,-data}.fcl` (step 1, MC/data), with the re-export `sbnd/wcls-img-clus-matching.jsonnet`.
- **Gates** (`scripts/gate-2step-cfg.sh` + `gate-2step-compare.py`), checked with go-jsonnet on the UAN for data and sim. The `wcsonnet` run is part of `run-2step.pbs`.
  - **G-A:** both 1-step jobs (reco1, hits) compile byte-identical to HEAD `58b958f1`.
  - **G-B:** step 1 is the hits 1-step minus the 34 PR-tail components, plus `TensorFileSink:ql_pctree`. All 195 shared components are identical.
  - **G-C:** step 2's PR closure (38 components) equals the 1-step's. The only differences are output names (`output_filename`, `bee_zip`), the Bee sink, `event_from_ident`, and `reset_shower_ids_per_event`.
  - `reset_shower_ids_per_event` restarts the static shower-id counter per event in a multi-event process. Identity with the one-event-per-process 1-step reference requires it.
- **go-jsonnet:** a go-jsonnet v0.20 binary is at `$Y/tools/go-jsonnet/jsonnet`, for config work on the UAN. Remember that the right-most `-J` wins.

**M3 (written, pending build):**
- larwirecell `Components/TruthInformationAttacher.{h,cxx}`, factory `wclsTruthInformationAttacher`.
  - **Always:** stamps the RSE.
  - **`truth: true` on MC:** appends
    - `truth/<ident>/nu` (`datatype` `truth_nu`), one row per neutrino MCTruth: `nu_idx, pdg, ccnc, mode, int_type, flavor, E, vtx_x/y/z, t, edep`;
    - `truth/<ident>/pf` (`truth_pf`), one row per particle of the labeler's Bee `mc` particle-flow selection (beam-nu-derived, KE > 10 MeV): `nu_row, trackid, parent_trackid, mother_trackid, pdg, process, E, KE, start_x/y/z/t, end_x/y/z/t, start_px/py/pz`.
- The G4 process-code table moved to the header-only `aiml/G4ProcessCode.h`, shared with the labeler (no behaviour change there).
- **jsonnet (staged):** `rse_apa0/1`, `rse_all_apa` become `wclsTruthInformationAttacher{truth:false}`, and a `truth` instance goes after `labeler_truth` in both stages. The fcls' inputers are updated.
- **G-A fallback:** `gate-1step-attacher.py` accepts exactly this attacher swap.
- **Check:** `check-truth.py` compares the tables with the labeler's own `nu_*` metadata and Bee tree.

**M4 (written, pending build):**
- `Facade::Ensemble::{set_,}aux_tensor(datatype)`.
- MABC `aux_datatypes` (default `truth_nu`, `truth_pf`): publishes those input tensors on the Ensemble and forwards them to its output. Nothing changes without them.
- `SbndPrMagnifyTrackingVisitor` writes `T_truth_nu` / `T_truth_pf`: one entry per row, plus `runNo/subRunNo/eventNo`, identifier columns as `Int_t`.
- `clus/src/TaggerBeeVisitor.cxx`: the toolkit port of `labeler_tagger`'s tagger Bee sets. It is `pr()`'s `tagger_bee` entry, appended in step 2 only.

**Runs (M2 config) queued at 2026-09-29 05:10:** `run-2step.pbs` NCpi0-19 (job 8877054, with the gates) and MC-9 (8877055), against the #32 hit-flash 1-step runs. At 06:00 no job was running on any Aurora queue, a machine-wide stall, so both are still queued.

### (b) 2026-09-29: M2-M5 done -- the 2-step chain is identical to the 1-step on all three samples

**Fixes found by the first runs:**
- **Step 2 aborted at configure:** `NamedFactory: Failed to find instance "mabc_pr" of class "BeeSink"`. `pr()` names its `bee_sink` but does not list it in its uses; in the 1-step, the per-APA MABCs bring the shared sink in. Fixed in `wct-pr.jsonnet` only, by configuring the sink explicitly, so the 1-step config is untouched.
- **The labeler's `sed-*` Bee sets differed in events 2+ of a multi-event `lar` job.** Its depo-smear RNG (`m_rng`, fixed seed) was seeded once per process. It is now re-seeded at every `visit()`, so every event gives what a one-event process gives, and one-event processes are unchanged (larwirecell `189ad26`).
- **`evt-branch-diff.py` reported NaN == NaN as a difference** (`T_rec_charge.reduced_chi2`). It now compares with NaN equal to NaN.

**Commits (local, not pushed):**
- toolkit `5a51329e`: cfg split, aux tensors, truth trees, `TaggerBeeVisitor`;
- larwirecell `4961f76`: `wclsTruthInformationAttacher`, `G4ProcessCode.h`;
- larwirecell `189ad26`: the RNG re-seed;
- wcp-porting-validation `0d3dec4f`: step-1 fcls, inputers.

The build is `build-wct-lwc.pbs` job 8877108, with `tree_wirecell_refs=0`.

**Config gates** (`wcsonnet`, in-job, sim and data): G-A (1-step byte-identical to HEAD, or exactly the attacher swap), G-B and G-C all PASS. Step 2's PR closure is the 1-step's 38 components plus `TaggerBeeVisitor:pr`.

**Validation.** Each row is compared against our #32 hit-flash 1-step run of the same events. Step 1 runs as `lar` jobs of 10 events; step 2 is one standalone `wire-cell` per tar.

| sample | run | step 1 wall | step 2 wall | `deep_compare` | every branch, every tree (exact) | census pairs | Bee, every layer | truth |
|---|---|---|---|---|---|---|---|---|
| MC-9 (gen2 CV) | `mc50-2step-m34-20260929-0550` | 5.2 min, 1 job | 49 s, 1 job | 9/9 | 9/9 | 0 | 9/9 | `check-truth` PASS; `T_truth_*` in 9/9 |
| NCpi0-19 (data) | `ncsb-2step-m34-20260929-0550` | 6.0 min, 2 jobs | 3.4 min, 2 jobs | 19/19 | 19/19 | 0 | 19/19 | -- |
| nueCC-48 (data) | `nuecc48-2step-m34-20260929-0601` | 3.5 min, 5 jobs | 6.4 min, 5 jobs | 48/48 | 48/48 | 0 | 48/48 | -- |
| 1-step MC-9, new build | `mc50-1step-m34-20260929-0607` | -- | -- | 9/9 | 9/9 | 0 | 9/9 | `T_truth_*` in 9/9, same rows as step 2 |

- **Bee:** "every layer" includes the tagger sets, now written by `TaggerBeeVisitor` in step 2, and the MC `sed-*` sets.
- **The earlier M2 runs** (`mc50-2step-20260929-0513`, `ncsb-2step-20260929-0519`) were already exact in `tracking-pr.root`. They differed only in the not-yet-ported tagger Bee sets and in the RNG-dependent `sed-*` sets, both fixed above.
- **`check-truth.py` (MC, per event):**
  - `truth_nu` equals the labeler's `nu_*` metadata exactly: 1 or 2 neutrinos per event (the gen2 CV sample carries rockbox interactions).
  - `truth_pf` holds the same particle ids as the labeler's Bee `mc` tree: 3 to 86 per event, split over neutrinos by `nu_row`. Each particle's parent equals `parent_trackid`, KE agrees to 0.1 MeV, and start/end agree.

**Usage:**
```
# step 1 (LArSoft; all events of the job in one tar)
lar -n <N> --nskip <k> -c wcls-img-clus-matching[-data].fcl -s <reco1.root> --no-output     # -> qlpctree.tar.gz, mabc.zip
# step 2 (standalone; create pr_evt<E>/ for each event of the tar first)
wire-cell -c pgrapher/experiment/sbnd/wct-pr.jsonnet --tla-str input=qlpctree.tar.gz --tla-str reality=data|sim
#   -> pr_evt<E>/tracking-pr.root (+ T_truth_nu/T_truth_pf on MC), mabc-pr.zip
```
`scripts/run-2step.pbs` does both steps plus the comparison. `SKIP1=1,RUN_DIR=` re-runs only PR on existing tars, which is the iteration loop this refactor is for.

**Open:**
- the set ident is the art event number (unique per filtered file; a multi-subrun file could repeat it);
- pushing the commits;
- upstreaming.
