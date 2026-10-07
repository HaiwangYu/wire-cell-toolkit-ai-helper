# Issue 35: SBND DL vertexing -- streamline training and inference

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/35.

Builds on:
- #33: the 2-step chain. Step 2, `wct-pr.jsonnet`, re-runs PR from the step-1 tar. On MC the tar carries the `truth_nu` / `truth_pf` tables, and `tracking-pr.root` has `T_truth_nu` / `T_truth_pf`.
- WireCell PR 535.

**Ask (Haiwang, 2026-10-01):**
1. Analyse the algorithms around the DL-vertex inference and draw them as a mermaid diagram in `cfg/pgrapher/experiment/sbnd/docs/`. Is "(traditional vertexing) -> (trajectory fitting, ...) -> (DL vertexing) -> (trajectory fitting, ...) -> (final PR)" right?
2. Dump the actual DL-vertex input (the trajectory-fit points as the network sees them) and the truth vertex, for training.
   - `tracking-pr.root` holds the FINAL fit points, which are not the network input. Training on them is a domain mismatch.
   - Add debug options to dump the inference output, and build a standalone inference on the dumped input that must give the same output.
3. Afterwards, propose a more streamlined iterative PR that gives the same results.

## Decisions (Haiwang, 2026-10-01)

| question | decision |
|---|---|
| which network calls to dump | **Both**, tagged by pass (the exclusion-free OFF pass and the production pass) and by candidate (`nu_index`) |
| truth vertex | **MC truth.** The in-detector interaction of the #33 `truth_nu` table, transformed into the frame of the fit points |
| format | **New trees in `tracking-pr.root`** behind a knob, default off, so production files are unchanged unless asked |
| Xin's `sbnd_xin/dl_vtx_training` | **Own tools.** The standalone inference imports the same Python module production's `SCN_Vertex` calls, and Xin's area stays untouched. His scripts can read our dump. |
| training-format export (Haiwang, 2026-10-07) | **Not from us.** The `T_dlvtx_call` / `T_dlvtx_cloud` trees are the deliverable; the training side reads them (PyROOT or uproot). No npz export. |

## What the code does today (survey 2026-10-01, toolkit `c3cce7f3`)

The SBND production operating point (compiled step 2) sets:
- `nu_per_bundle = true`, so PR runs once per beam-window flash-bundle candidate;
- `fit_exclusion = true`;
- `dl_weights = uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`;
- `dl_vtx_rerank = true` with `dl_vtx_top_k = 5`, `dl_vtx_min_accept_score = 10`, `dl_vtx_score_scale = 1000`;
- `dl_vtx_dual_chain = true` with `dual_chain_mode = snap`, `dual_chain_transfer = true`, `dual_chain_transfer_max = 2` cm.

Per candidate, `TaggerCheckNeutrino::visit()` runs:

0. **The dual-chain OFF pass** (`run_dual_chain_off_pass`, doc pr/112 sec 11). It is a deliberate copy of steps 1–4 below on its own fitter and graph, with `fit_exclusion = false`. In `snap` mode it runs the full vertex determination and refinement, including its own DL inference, and hands production a hint vertex (`DualChainHint`).
1. **Main-cluster traditional PR:** `find_proto_vertex`, which runs the trajectory fits internally (`do_multi_tracking`); `clustering_points`; `separate_track_shower`; `determine_direction`; `shower_determining_in_main_cluster`; `determine_main_vertex`; `reassociate_cluster_orphans`.
2. **The same for every other cluster of the bundle** (clusters ≤ 6 cm take a shorter path), then `deghosting` across all of them.
3. **DL vertex** (`determine_overall_main_vertex_DL`, `NeutrinoVertexFinder.cxx:4703`).
   - **The network input** (`:4780-4804`) is every PR-graph vertex (its fit point if valid, else its wcpt) plus every segment's interior fit points, from every cluster of the bundle. The values are x, y, z in cm and q = dQ * `dQdx_scale` + `dQdx_offset`.
   - **The call** is `WCPPyUtil::SCN_Vertex("SCN_Vertex", "SCN_Vertex", weights, xyzq, "float32", false, top_k)`, which goes to `pyutil/python/SCN_Vertex.py` and `SCN/DeepVtx.py`.
   - **Selection:** the top-5 voxels are reranked against the graph's vertex candidates. Then, in `snap` mode (`:5271`), the OFF pass's final vertex is snapped to the nearest production candidate the cluster gate admits; if that candidate is within 2 cm it replaces the rerank's choice, otherwise production keeps its own pick. If the DL doesn't change the vertex, the traditional `determine_overall_main_vertex` is used.
4. **Vertex refinement:** `snap_main_vertex_to_kink`, `snap_main_vertex_to_junction`, then `improve_vertex` (a refit), `main_vertex_graph_audit` and `stitch_disconnected_main_cluster`.
5. **Final PR:** `clustering_points`, `examine_direction`, `demote_cross_cluster_straight_stems`, `orphan_dup_audit`, `shower_clustering_with_nv`, `reconcile_particle_flags`, the shower kinematics, the taggers (cosmic, numu, ssm, nue, singlephoton) and `fill_kine_tree`. The BDT scorers and the ROOT writers then run as later MABC visitors.

So the outline in the ask is roughly right, with three refinements:
- **Fitting is inside the traditional vertexing.** The DL input is the fit state after step 2 (with fit exclusion); it is not a separate fitting stage.
- **There are two chains.** The OFF pass is a full duplicate, so each candidate makes two network calls on two different clouds.
- **The final points are refit.** The points `tracking-pr.root` writes come after step 4's refit and step 5.

**What exists for the input/output today:**
- The pr/79 sec 10 harvest (`dl_vtx_harvest` + `vertex_scoreboard`, both default off) copies the exact live `vec_xyzq` into the vertex scoreboard. `PrDisplayDump` writes it to the calib JSON as `hv_cloud`. It covers the production pass only, because the OFF pass sets `m_vtx_harvest = false`, and `PrDisplayDump` is not in the production pipeline.
- Xin's `sbnd_xin/dl_vtx_training/build_dataset.py` rebuilds the cloud from the calib JSON's FINAL vertices and segments. His `parity_check.py` reproduces production's recorded top-1 voxel exactly on 39 of 66 events, which is this issue's domain mismatch, measured.

## Goal, revised 2026-10-02

Xin's finding: the current DL-vertex model does better on **exclusion-off** trajectory-fit points, while the other PR tasks do better on **exclusion-on** fits. That is why production runs the dual chain: an exclusion-off copy of the whole vertexing (the OFF pass) only to produce a vertex hint for the exclusion-on production pass.

Haiwang's aim: dump **both** clouds for the next training round, train on each, and test whether a model trained on the exclusion-on cloud matches or beats the current one. If it does, the OFF pass can be dropped.

### The three questions, from the code (toolkit `sbnd-dlvtx-35`)

1. **How is the hint used? Does the model see it?** No. The OFF pass hands production one point, its final main vertex (`DualChainHint::vertex`). Production runs its own network call on its own exclusion-on cloud (`NeutrinoVertexFinder.cxx:4870`) and reranks its top-5; only then, in `snap` mode (`:5271`), the production candidate nearest the hint replaces the rerank pick if within 2 cm. The hint touches the selection after inference, never the input or the inference. (`voxels` / `union` modes would pool the OFF payload into the selection; production runs `snap`.)
2. **Does the OFF vertex change the 2nd-round fit?** Before step C, no, by construction: the OFF pass has its own `TrackFitting` and `PR::Graph`, and the one Facade residue (`Flags::main_cluster`) is snapshotted and restored. So the production cloud and payload in `T_dlvtx_*` are independent of the OFF pass, and so is the OFF cloud. After step C, yes: the winning vertex (possibly the snapped one) drives `improve_vertex` and everything downstream, so the final fit, `T_rec_charge`, `final_*` and Bee depend on the hint. For training this is harmless: inputs are the step-C clouds, labels are MC truth. **Empirical check:** `dlvtx-decouple.py` compares the production clouds of a dual-chain-ON and a dual-chain-OFF run bit for bit (result below when the job runs).
3. **Is the model called in round C, and used?** Called always. Used only when the snap is not accepted (no admissible candidate within 2 cm of the hint, or no hint). `dual_transferred` records this per call; `dlvtx-stats.py` gives the fractions.

**Fact from the dual-chain-OFF run (NCpi0-19, `ncsb-dlvtx-nodual-20261002`):** dropping the OFF pass today changes the final result in 7 of 19 events (12 identical to the reference, step 2 3.4 min instead of 4.0). That is the size of what a model trained on the exclusion-on cloud has to recover.

### The clouds the dump provides

| `T_dlvtx_call.pass` | cloud | fit exclusion | graph | status |
|---|---|---|---|---|
| 1 (`off`) | the OFF pass's network input | off, from step A onward | the OFF pass's own graph and candidates | dumped |
| 0 (`prod`) | the production network input | on | the production graph | dumped |
| 0 with `cloud_no_exclusion = 1` | an exclusion-free refit of the production graph, built just for the cloud, then restored (`dl_vtx_cloud_no_exclusion`) | off, cloud only | the production graph's topology | dumpable via `pr_knobs` |

Both `off` and `prod` rows carry MC truth; `hint_*` on the `prod` row is the OFF pass's final vertex.

## Plan

| milestone | content | gate |
|---|---|---|
| M0 | this doc and issue | done |
| M1 | `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md` | done (`9979a13f`) |
| M2 | `dl_vtx_dump`: `T_dlvtx_call` / `T_dlvtx_cloud`, both passes, exact input, payload, decision, hint, MC truth | done (`17b2b468`, `78ba593c`, hint/cloud flag commit); recording-only verified on MC-9, NCpi0-19, nueCC-48 |
| M3 | standalone replay `dlvtx-replay.py` | done: 140 + 20 calls, 0 mismatch (bit-identical or 1–3 ulps in scores) |
| M3b | decoupling: production cloud independent of the OFF pass | done: 20/20 clouds and payloads bit-identical with the dual chain off (log c) |
| M4 | **training set, both clouds:** a large MC sample through step 1 + step 2 with `dl_vtx_dump=true`; the selection (truth vertex in the active volume, candidate = the true interaction's bundle) as `dlvtx-truth-eval.py`; no export from us (the trees are read directly) | done for gen2 CV: 1006 events dumped, replayed 960/960, 373 training events (log e, validation summary below); a nueCC-enriched sample is optional for yield |
| M5 | **model on the exclusion-on cloud:** train on `prod` (and `cloud_no_exclusion`) clouds, evaluate against the current model on `off` clouds with the same labels | vertex accuracy at 1 cm comparable or better |
| M6 (task 3) | **skip the OFF pass:** run production with the new weights and `dl_vtx_dual_chain=false`; compare with production | identical or better on the hand-scan and MC truth; step 2 ~15 % faster |

## Validation summary (2026-10-07, toolkit `sbnd-dlvtx-35` = master `0319ea67` + the dump, on the fork)

What the dump is and how it was checked, in one place; details in the log entries.

| check | sample | result |
|---|---|---|
| knob off changes nothing | all 8 compiled SBND configs | byte-identical; no tree written (b) |
| knob on changes only the dump | MC-9, NCpi0-19, nueCC-48, gen2 CV 1006 | `tracking-pr.root` identical to the #32 reference apart from the two new trees; Bee identical (b, d) |
| production cloud independent of the OFF pass | NCpi0-19, dual chain off | 20/20 clouds and payloads bit-identical (c) |
| OFF pass recorded with its hint | NCpi0-19 | `pass=off` rows, `hint_valid=1` on the production row (d) |
| standalone inference == in-chain inference | 1200 calls (MC-9, NCpi0-19 x3, nueCC-48, gen2 CV 1006) | 0 mismatches: same voxels and ranking; scores bit-identical or within 1.8e-6 float32 noise (b, d, e) |
| truth frame | gen2 CV, 373 selected candidates | SCE-shifted truth vertex within 1 cm of the final vertex in 65 %, median 0.54 cm (e) |
| raw model output on the two clouds | same | top-1 42 % < 1 cm on both the exclusion-off and the exclusion-on cloud, median 1.53 vs 1.41 cm (e) |
| PR 536 review fixes (log g, toolkit `21562551`) | MC-10, NCpi0-19, bulk 1006 | knob off: configs 8/8 byte-identical, `tracking-pr.root` + Bee identical to master 9/9 + 19/19; dump on: only the two trees added, replay 46 + 960 calls 0 mismatch, 0 failed; doctests clus 473/473, root 10/10 (g) |
| merge of master `0319ea67` (PR 535 merged + 22 commits) | MC-10, NCpi0-19 | compiled configs byte-identical (8/8); step-1 tars, `tracking-pr.root` every branch and Bee every layer identical to a master build, 9/9 + 19/19; dump on: only the two trees added; replay 46 calls 0 mismatch; doctests clus 471/471, root 9/9 (f) |

The dump is ready to be read for training: `T_dlvtx_call` (one row per network call, both passes, with the exact float32 input and output, the decision, the hint, and the raw and SCE-shifted MC truth vertex) and `T_dlvtx_cloud` (one row per input point). Branch documentation: log (b) and `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md`.

## Open items

- **Truth frame.** The fit points live in the reco frame: drift x with the cluster t0 correction, and data y/z position offsets. The MC truth vertex needs SCE true->reco plus the same t0/drift convention. `wclsTensorSetLabeler` already shifts the depos true->reco (`sce_field_fwd`), so M2 should reuse that convention, then check it against the hand-scan labels on MC.
- **The OFF pass's call is captured** (done): it records with `pass = off`, result unchanged.

## Log

- 2026-10-01: scope and decisions; survey of the current flow (above).
- 2026-10-01: M1 -- `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md` (toolkit branch `sbnd-dlvtx-35`, local; kept off PR 535's branch): per-event and DL-step mermaid diagrams, the stage/anchor table, the `do_multi_tracking` census by function, planned dump points.
- 2026-10-01: M2 + M3 implemented (toolkit `sbnd-dlvtx-35` `17b2b468`, local; ai-helper scripts):
  - **knob:** `dl_vtx_dump` (default false), a `pr()` parameter, passed through `sbnd-pr-stage.node()` and a `wct-pr.jsonnet` TLA.
  - **recording:** `determine_overall_main_vertex_DL` records each network call as `PR::DlVtxCall` (`clus/inc/WireCellClus/PRDlVtxDump.h`):
    - the exact float32 `vec_xyzq` copy (vertex block first), q scale/offset, top_k, the raw payload;
    - the decision: traditional vertex, accepted DL vertex, dual-chain transfer.
  - **OFF pass:** it records too (pass `off`) and hands its calls to production through `DualChainHint::dump_calls`, using a scope guard that covers every return.
  - **carrier:** the candidate's calls ride on `TrackFitting::dlvtx_calls`, which is cleared at the event reset.
  - **writer:** `SbndPrMagnifyTrackingVisitor::write_dlvtx` writes `T_dlvtx_call` (one row per call, with the candidate's final vertex) and `T_dlvtx_cloud` (one row per point). On MC, the truth vertex is the max-edep `truth_nu` row, given raw and shifted by the TrueFwd SCE map (`sce_field` = `sbnd_dualmap_fwd`, configured only with the knob on). SBND apa = sign of x.
  - **knob off:** all eight compiled SBND configs (1-step flash/hits, step 1, step 2; sim and data) are byte-identical, and no tree is written.
  - **knob on:** exactly three config changes (`TaggerCheckNeutrino.dl_vtx_dump`, `SbndPrMagnifyTrackingVisitor.sce_field`, `SCEFieldTH3:sbnd_dualmap_fwd`).
  - **M3:** `scripts/dlvtx-replay.py` re-runs `SCN_Vertex.SCN_Vertex` (the module production imports) on each recorded cloud with its top_k and the same resolved weights, compares with the payload (bit-exact), and summarises the truth distances.
  - **harness:** `run-2step.pbs` gains `WCT_TLAS` and `DLVTX_REPLAY=1`.
  - **not recorded:** the dual-chain `voxels` / `union` modes' separate OFF inference (`dual_chain_scn_voxels`). Production runs `snap`, where the OFF pass's call goes through `determine_overall_main_vertex_DL` and is recorded.

### (b) 2026-10-01: M2 + M3 validated


**Build:** toolkit `sbnd-dlvtx-35` `17b2b468`, local. clus doctests 452/452 (1 skipped), root 8/8. The config gates pass, and with the knob off the hashes equal the PR 535 build's.

**Runs:** step 2 with `--tla-code dl_vtx_dump=true`, on the existing PR 535 step-1 tars, compared with the #32 1-step references. Then `dlvtx-replay.py` re-runs `SCN_Vertex.SCN_Vertex` on every recorded call.

| sample | `tracking-pr.root` (every shared tree) | Bee | network calls (OFF + prod) | replay: bit-identical / equivalent / MISMATCH | DL accepted (OFF, prod) |
|---|---|---|---|---|---|
| MC-9 (`mc50-dlvtx-20261001`) | 9/9 identical | 9/9 | 4 (2 + 2); only 2 events reach the DL step | 2 / 2 / 0 | 1/2, 1/2 |
| NCpi0-19 (`ncsb-dlvtx-20261001`) | 19/19 | 19/19 | 40 (20 + 20) | 38 / 2 / 0 | 19/20, 18/20 |
| nueCC-48 (`nuecc48-dlvtx-20261001`) | 48/48 | 48/48 | 96 (48 + 48) | 94 / 2 / 0 | 46/48, 48/48 |

- **Recording only:** with the knob on, the reconstruction output is unchanged in every event. The arm gains exactly `T_dlvtx_call` / `T_dlvtx_cloud`; MC also has `T_truth_*`.
- **"Equivalent":** identical voxel coordinates and order (the same ranking), with every score within 1e-6. Worst observed: 3.6e-7 on MC, 1.2e-7 on data, which is 1–3 float32 ulps.
  - `dlvtx-call-diff.py` on MC event 16 shows the coordinates bit-identical and the replay repeating bit-identically within one process. So the residual is the network's float non-determinism between the production process and a fresh one, not an input difference.
  - Scores enter the decision only as score × 1000 against the cut of 10, so a 1e-7 shift could matter only for a candidate sitting exactly on the cut.
- **MC truth frame check, first look (2 events):** the accepted DL vertices are 1.2 / 1.3 cm from the SCE-shifted truth vertex. The traditional vertices are a median 12–14 cm away. That is consistent with the cloud frame being the t0-corrected reco frame. A larger MC sample is needed (M4).

**Scripts:**
- `dlvtx-replay.py` (gate: exact or equivalent);
- `dlvtx-call-diff.py` (per-call detail);
- `run-2step.pbs` with `WCT_TLAS` and `DLVTX_REPLAY=1`.

**Next (M4):** a training-data note and an MC sample large enough to measure the truth-frame residual, plus Haiwang's choices on which pass and which cuts to train on.

### (c) 2026-10-02: M3b decoupling and the hint statistics


Run on the login node with the UPS ROOT (`setup-uan-root.sh`), since Aurora's scheduler is down.

**Decoupling (NCpi0-19, production pass, dual chain ON vs OFF, `dlvtx-decouple.py`):** all 20 production clouds (x, y, z, q, float32) and all 20 payloads are **bit-identical** with and without the OFF pass. Only the decision differs, in 7 of 20 events:
- 3 events (21073, 56982, 259542): with the dual chain off the DL is **not accepted** (`accepted` 1 → 0). Production's own rerank failed the score cut; only the snap had supplied a DL vertex.
- 4 events (285567, 463565, 506114, 506746): a **different candidate** is accepted, 0.5–55 cm away; the final vertex follows.

So the answer to question 2 is measured: nothing the OFF pass does reaches the production fit or inference. A model trained on `pass=prod` clouds has no hidden dependence on the OFF pass. The coupling starts only at the selection, which is what a retrained model has to replace.

**How often the hint decides (`dlvtx-stats.py`, dual chain ON, MC-9 + NCpi0-19 + nueCC-48, 70 candidates):**

| | OFF pass | production pass |
|---|---|---|
| network calls | 70 | 70 |
| DL accepted | 66 | 67 |
| snap overrode production's own pick (`dual_transferred`) | – | **19 (27 %)** |
| production's own top-1 voxel → accepted vertex | – | median 0.69 cm; 42 within 1 cm, 14 beyond 5 cm |
| traditional vertex → accepted DL vertex | – | median 7.0 cm; 31 within 1 cm, 34 beyond 5 cm |

With the dual chain OFF (NCpi0-19): accepted 15/20 (vs 18/20 ON); production's own top-1 → accepted vertex median 0.27 cm, none beyond 5 cm (no snap, so the accepted vertex is always production's own choice).

Reading: in about 27 % of candidates the OFF pass's answer wins over the exclusion-on model's own answer, and the 14 cases where production's top-1 voxel is more than 5 cm from the accepted vertex are these transfers. That 27 % is the gap a model trained on the exclusion-on cloud has to close for the OFF pass to be dropped.

**Dump additions (toolkit `sbnd-dlvtx-35` `9781e43c`, to be built):** `T_dlvtx_call` gains `hint_valid`, `hint_x/y/z` (the OFF vertex given to the production call) and `cloud_no_exclusion`.

### (d) 2026-10-06: the rebuilt dump verified; the exclusion-free-refit variant exercised

Both on the NCpi0-19 step-1 tars, step 2 only, compared with the #32 reference and replayed:
- `ncsb-dlvtx-hint-20261005` (dump on): output identical 19/19, Bee 19/19; replay 40 calls, 38 bit-identical, 2 equivalent, 0 mismatch; the production row now carries `hint_valid=1` and the OFF pass's vertex in `hint_x/y/z`.
- `ncsb-dlvtx-noexcl-20261005` (dump on + `pr_knobs={dl_vtx_cloud_no_exclusion:true}`): the production cloud is the exclusion-free refit (`cloud_no_exclusion=1`, e.g. 409 vs 399 points in event 114446; the log shows the refits), the replay passes 40/40, and the final output is still identical 19/19: the rerank landed on the same candidate in every event. This variant is NOT part of the current chain (the knob is off in production); it is an option for training only.

Replay totals so far: 240 recorded network calls re-run standalone, 0 mismatches.

### (e) 2026-10-06/07: M4 bulk run -- 1006 gen2 CV MC events through step 1 + step 2 with the dump

Run `$Y/production-prep/mc1k-dlvtx-20261006` (combined job 8907313, `scripts/step12-bulk.pbs`, one debug node): 74 reco1 files (first 74 of `twester/sbnd_gen2_prod1/Gen2_2026/reco1/000000/000000/`, `manifest.tsv` / `inputs.tsv` = the input list as run) -> 1006 events, every file rc=0 in both steps. Toolkit `sbnd-dlvtx-35` (local), larwirecell `dev-v10_14_02_02`, step 1 `wcls-img-clus-matching.fcl`, step 2 `wct-pr.jsonnet --tla-code dl_vtx_dump=true`.

**Resources** (`resources.md`, `resources-pr.md`; one `lar` / `wire-cell` process per file, 74 concurrent, 2 cores each):

| | queue wait | node wall | per process wall median / max | CPU median | max RSS median / max | CPU per event | output per event |
|---|---|---|---|---|---|---|---|
| step 1 | 332 s | 790 s (13.2 min) | 583 / 790 s | 402 s | 1531 / 1809 MB | 29.0 s | qlpctree.tar.gz 1.79 MB, mabc.zip 5.24 MB, nugraph.h5 1.27 MB |
| step 2 + dump | (same job) | 186 s (3.1 min) | 133 / 186 s | 68 s | 1201 / 1481 MB | 4.9 s | tracking-pr.root 0.17 MB, mabc-pr.zip 0.27 MB |

Totals: tars 1.80 GB, step-1 Bee 5.27 GB, h5 1.27 GB, tracking-pr.root 0.17 GB, step-2 Bee 0.27 GB; `du` 8.5 GB. Node-seconds per event 0.79 (step 1) + 0.18 (step 2), so 1000 events cost ~16 node-minutes end to end on one node, dominated by step 1's wall, which is the longest single file (17 events), not CPU. The Bee zips are kept (Haiwang, 2026-10-06).

**Replay** (`dlvtx-replay.txt/.json`): 960 recorded network calls (480 candidates x 2 passes) re-run standalone. In the job (SL7, CPU): 714 bit-identical, 245 equivalent, 1 call at |dscore| 1.19e-6, just over the 1e-6 tolerance -> `SCORE_TOL` raised to 1e-5 (the mismatch class means a different voxel or ranking, a score difference at 1e-6 is float32 process-to-process noise). Re-run on the UAN (`setup-uan-root.sh` now adds torch / sparseconvnet / `SCN_Vertex` to PYTHONPATH, so the replay runs on the login node too, 26 s for 960 calls): 618 bit-identical, 342 equivalent, 0 mismatch, worst |diff| 1.79e-6. The bit-identical fraction depends on the host (74 % in the job, 64 % on the UAN), the voxels and ranking never. Totals: 1200 calls replayed, 0 mismatches.

**Decisions** (`dlvtx-stats.py`, 480 candidates): OFF pass DL accepted 241/480; production DL accepted 463/480, of which 247 `dual_transferred` (the snap to the OFF vertex replaced production's own rerank pick), 238 both. Production's own top-1 voxel is >5 cm from the accepted DL vertex in 188/463 calls: the OFF-pass hint decides in a large share of events. Traditional vertex == accepted DL vertex in 383/459 (<1 cm): the DL step mostly confirms.

**Truth, all candidates** (`dlvtx-stats.txt`, truth = max-edep `truth_nu` row shifted by the TrueFwd SCE map, no selection): final vertex median 0.93 cm, 51 % < 1 cm; raw own top-1 median 9.8 cm (off) / 7.9 cm (prod), 32-33 % < 1 cm. These mix in candidates that are not the neutrino bundle and events with the truth vertex outside the active volume, so they understate the model.

**Truth, training selection** (`dlvtx-truth-eval.py`, `dlvtx-truth-eval.{txt,tsv}`): per event, truth inside |x|,|y| < 200, 0 < z < 500 cm, and the candidate whose production cloud has a point within 3 cm of the truth vertex (= the true interaction's bundle). Of 1006 events: 373 selected (6 with more than one candidate), 82 truth outside, 19 inside but no candidate's cloud contains it, the rest have no DL call (no in-window candidate). On the 373 selected candidates, distance to the SCE-shifted truth vertex (cm):

| vertex | n | median | < 1 cm | < 2 cm | > 5 cm |
|---|---|---|---|---|---|
| final (production) | 373 | 0.54 | 65 % | 73 % | 18 % |
| OFF-pass final (hint) | 373 | 0.55 | 66 % | 75 % | 18 % |
| off: accepted DL | 225 | 0.55 | 72 % | 83 % | 12 % |
| off: own top-1 voxel (raw) | 373 | 1.53 | 42 % | 55 % | 41 % |
| off: traditional | 373 | 0.67 | 59 % | 70 % | 20 % |
| prod: accepted DL | 360 | 0.66 | 63 % | 74 % | 17 % |
| prod: own top-1 voxel (raw) | 373 | 1.41 | 42 % | 57 % | 39 % |
| prod: traditional | 372 | 0.71 | 58 % | 68 % | 20 % |

Reading: (1) the raw network output is at 42 % < 1 cm on BOTH clouds with the current (exclusion-off-trained) weights -- on the exclusion-on production cloud it is no worse than on the exclusion-off cloud it was trained on (median 1.41 vs 1.53 cm, > 5 cm 39 vs 41 %), so the domain shift between the two clouds is small for this model; (2) what lifts 42 % to 65 % is the rerank / snap / traditional-vertex logic around the model, not the model's top-1 (58 events have a raw prod top-1 > 5 cm off but a final vertex < 1 cm; 4 the reverse); (3) the 18 % > 5 cm tail of the final vertex is the target for M5. These are the baseline numbers a model trained on the exclusion-on cloud has to match (M5 gate: raw top-1 and accepted-DL at 1 cm on held-out events).

**Note on the selection counts.** 82/1006 truth-outside and ~530 events without any DL call: the gen2 CV sample is a full-spill mix, so many events have no in-window candidate or the interaction in the dirt / cryostat wall. For the training set only the 373 count; a nueCC-enriched sample (M4, still to run) will have a far higher yield per event.

**Decision (Haiwang, 2026-10-07):** no npz export from us; the trees are read directly by the training side.

**Scripts** (ai-helper): `step1-bulk.pbs` / `step2-bulk.pbs` (resource summary argv fix: PBS timestamps contain spaces), `dlvtx-stats.py` (+ truth distances per pass), `dlvtx-truth-eval.py` (new), `dlvtx-replay.py` (tolerance), `setup-uan-root.sh` (torch on the UAN). Toolkit `sbnd-dlvtx-35` unchanged.
- 2026-10-07: toolkit branch `sbnd-dlvtx-35` (4 commits, head `9781e43c`) pushed to the fork `HaiwangYu/wire-cell-toolkit`; the stray 574 MB core file under issue 31 deleted.

### (f) 2026-10-07: master merged into `sbnd-dlvtx-35`; output identical to master

**Merge.** `origin/master` `0319ea67` (PR 535 merged on 2026-09-30 as `51b5a1fc`, then the 22 commits of master's `cfg/pgrapher/experiment/sbnd/docs/deploy-validation-2026-10-01.md`) merged into `sbnd-dlvtx-35` as `f6d49e53`, no conflicts (6 files touched by both sides, all hunks disjoint). Local `master` tracks `origin/master`; the pre-merge head is tagged `sbnd-dlvtx-35-pre-master-merge` (`9781e43c`). Pushed to the fork after the gates below, with a re-check note in `sbnd-dl-vertex-flow.md`.

**Code reading.** With `dl_vtx_dump` off every branch addition is inert: `NeutrinoVertexFinder` records nothing (`dump_i = -1`), `TaggerCheckNeutrino` never calls `set_dlvtx_calls`, the OFF pass's `DumpHandOff` guard moves an empty vector, `TrackFitting::reset_for_new_event` clears an empty vector. Nothing in master's new code (`main_vertex_swap_apply` now on, `nu_particle_links` / `T_segment`, `kine_overlap_probe`, ICARUS knobs) reads the dump state, and the hand-off sits after master's swap inside the same per-candidate block, so with the knob on the dump records the cluster production actually used.

**Config proof (UAN, go-jsonnet).** Step 1, step 2 and the two obsolete 1-step jobs, sim and data: all 8 compiled configs byte-identical between master's `cfg/` and the merged tree. Dump on adds exactly `SCEFieldTH3:sbnd_dualmap_fwd` and changes `TaggerCheckNeutrino:pr` and `SbndPrMagnifyTrackingVisitor:pr`, as before.

**Runs** (`scripts/master-validate.pbs` job 8907945, `scripts/merged-validate.pbs` job 8907985; both one debug node, queue waits 11 and 17 min, 23 and 26 min wall):
- job A: clean build of master into `$OPT` (+ larwirecell), then the 2-step chain on MC-10 (gen2 CV benchmark reco1, 10 events, 9 paired with the reference) and NCpi0-19 (data) -> `mc10-master-20261007`, `ncsb-master-20261007`; compared with the 2026-09-26 one-step references for attribution of master's own changes.
- job B: the master runs laid out as references (`make-ref-from-2step.sh`), clean build of the merge, the same chain -> `mc10-merged-20261007`, `ncsb-merged-20261007`, then step 2 again with `dl_vtx_dump=true` on the merged step-1 tars (`*-merged-dump-20261007`) with the replay, then the doctests.

| merged vs master, knob off | MC-10 | NCpi0-19 |
|---|---|---|
| step-1 `qlpctree.tar.gz` members (md5 of every member) | 4112/4112 identical | 4094 + 3689 identical |
| `tracking-pr.root`, every branch of every tree | 9/9 | 19/19 |
| Bee, every layer | 9/9 | 19/19 |
| dump on: every shared branch identical, trees only in the dump arm | 9/9, `T_dlvtx_call` + `T_dlvtx_cloud` | 19/19, same |
| replay of the dumped calls | 6 calls, 0 mismatch | 40 calls, 0 mismatch |

Doctests on the merged build: `wcdoctest-clus` 471 cases / 717031 assertions passed, `wcdoctest-root` 9 / 4068 passed.

**Master vs the 2026-09-26 one-step references** (job A, for the record; master's deploy note predicts these): MC-10 3/9 events differ, all only in `T_flash time_us` and the cluster t0 that follows it (change 1, the prompt-time bin rule); NCpi0-19 10/19 differ, 9 of them flash times only, and event 359980 changes its main cluster and kinematics (change 2, `main_vertex_swap_apply`); `T_segment` is added everywhere (change 3). Nothing else moves.

**State.** `$OPT` now holds the merged build (master + dump), larwirecell built against master in job A. Replay totals: 1246 calls, 0 mismatches.
- 2026-10-07: draft PR WireCell/wire-cell-toolkit#536 (`sbnd-dlvtx-35` -> master, head `78f81c64`), body = the dump, knob-off neutrality, the log (f) validation table; Haiwang adds the preamble and un-drafts it.

### (g) 2026-10-07: PR 536 review (Xin) -- the fixes, validated; the bulk sample re-dumped

Xin's review (https://github.com/WireCell/wire-cell-toolkit/pull/536#pullrequestreview-5442481514): 10 numbered points + 4 smaller ones, all verified against the code before acting. Decisions (Haiwang, 2026-10-07): fix all of them; truth per candidate = option A (every interaction as vectors, the reader chooses); `T_dlvtx_cloud` stays one row per point (+ `pass`); the writer doctest = knob-default + struct contract (a full-Ensemble test does not fit the root test file).

**Impact on the existing samples** (`mc1k-dlvtx-20261006`, and issue 38's 5018 events): none of the clouds, payloads or decisions change. Points 1-2 are the `union`/`voxels` modes, production runs `snap` (0 rows `payload_from_off`); point 3: 0 rows with an empty payload; point 4: 6/474 events have two candidates (handled by the cloud-containment selection); 5, 6, 8 are missing diagnostic columns; 9: the only override used (`dl_vtx_cloud_no_exclusion`) is not among the overriding named keys; 10: every dump used the TLA, so the SCE shift was applied. Point 7 settled by measurement on the 373 selected bulk candidates: nearest cloud point to the SCE-shifted truth median 0.42 cm (93 % < 1 cm) vs the raw truth 0.69 cm (69 %); the x offset between the two frames is 0.06 cm median, so the neutrino-time vs flash-time term is negligible for beam neutrinos.

**Toolkit `21562551`** (on `sbnd-dlvtx-35`, pushed; PR 536 updated):
| # | fix |
|---|---|
| 1 | payload recorded right after this call's inference, before the union-mode pooling; `n_off_voxels` |
| 2 | the voxels/union OFF call in `dual_chain_scn_voxels` recorded as `pass = 2` (`off-voxels`): cloud + payload, no decision fields |
| 3 | `status`: 0 ok, 1 the network threw (payload empty), 2 unexpected payload size; the replay skips them |
| 4 | `truth_valid` requires edep > 0; `truth_n` + `truth_all_{nu_idx,pdg,ccnc,E,edep,t,x,y,z,reco_x,reco_y,reco_z}` vectors (every interaction of the event); the scalar max-edep `truth_*` kept |
| 5 | `rerank_valid`, `rerank_x/y/z`, `rerank_row`: the call's own pick before the dual-chain snap |
| 6 | `two_end_veto`; `dual_transferred = 1, accepted = 0` documented as "transferred then vetoed" (9/480 bulk rows) |
| 8 | `trad_row`, `rerank_row`, `dl_row`: index inside the cloud's vertex block, -1 if none |
| 9 | `tcn_overrides` merged last (`tcn_knobs + {named keys} + tcn_overrides`); proof: `pr_knobs={cosmic_consistent_fv:false}` now compiles to false |
| 10 | `truth_sce_applied`; the writer gets its own `dl_vtx_dump` key from the same jsonnet gate; comment in `pr()` says `pr_knobs={dl_vtx_dump:true}` records without the writer keys |
| schema | with the writer key the two trees are written on every event (empty when nothing was recorded): 1006/1006 files have both, 532 empty |
| cloud | `pass` column on `T_dlvtx_cloud` |
| tests | `dl_vtx_dump` default-false checks in `doctest_clus_knob_defaults` and `doctest_sbnd_pr_tracking_defaults`; `clus/test/doctest_dlvtx_dump.cxx` pins the `DlVtxCall` defaults (row indices -1, status 0) |
| doc | `sbnd-dl-vertex-flow.md` sections 2 and 4 current (the dump is implemented; what each column is) |

**Validation** (`scripts/review-fix-validate.pbs`, job 8908664, 215 s queue, 35 min wall): clean build; doctests clus 473/473 (717k assertions), root 10/10; knob-off gate on MC-10 and NCpi0-19 vs the master runs of the morning: `tracking-pr.root` every branch identical 9/9 + 19/19, Bee 9/9 + 19/19; config proof 8/8 byte-identical to master (UAN); dump on: every shared branch identical, only the two trees added, replay 6 + 40 calls 0 mismatch, 0 failed.

**Bulk re-dump** `mc1k-dlvtx-20261007` (step 2 only on the 2026-10-06 step-1 tars, symlinked; the old dump untouched): 1006/1006, 3.1 min node wall; replay 960 calls, 714 bit-identical, 246 equivalent, 0 mismatch, 0 failed; decisions identical to the old dump (off accepted 241, prod accepted 463, transferred 247); new columns: own pick valid 245 (off) / 250 (prod), two_end_veto 4 / 9, `truth_sce_applied` 960/960, `dl_row >= 0` on every accepted row (704), `trad_row >= 0` on 951 = every `trad_valid` row, `truth_n > 1` in 562 rows. The selection-aware truth table is unchanged (373 selected; raw top-1 42 % < 1 cm both clouds; final 65 %). Replay totals: 2252 calls, 0 mismatches.

Reply draft for the PR: `pr536-reply-draft.md` in this directory (not posted; Haiwang posts).
