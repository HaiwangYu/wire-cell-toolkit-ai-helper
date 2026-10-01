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

## Plan

| milestone | content | gate |
|---|---|---|
| M0 | this doc and issue | -- |
| M1 (task 1) | `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md`: a mermaid diagram of the per-candidate sequence (both chains, where the network input is taken, where the refits happen), with file:line anchors | review |
| M2 (task 2a) | **Dump.** A knob (e.g. `dl_vtx_dump`, default off) records every network call: pass (`off` / `prod`), `nu_index`, the exact `vec_xyzq`, top-K, the returned voxels and scores, the chosen and traditional vertices, and the snap outcome. `SbndPrMagnifyTrackingVisitor` writes it as `T_dlvtx_cloud` (one row per point) and `T_dlvtx_call` (one row per call: outputs and decision). On MC each call also carries the truth vertex transformed into the cloud's frame. | knob off: compiled config and outputs byte-identical; knob on: `T_dlvtx_*` present, and the production result unchanged |
| M3 (task 2b) | **Standalone inference.** A script reads `T_dlvtx_cloud`, calls `SCN_Vertex.SCN_Vertex` with the same weights and top-K, and compares with `T_dlvtx_call`. | identical voxels and scores (bit-exact, or a stated float tolerance) for every call on MC-9, NCpi0-19 and nueCC-48 |
| M4 | **Training-data note.** How to build a training set from `T_dlvtx_*` and the truth: which pass, frame, cuts. Point Xin's pipeline at the exact cloud instead of the rebuilt one. | -- |
| M5 (task 3) | **Streamlining proposal**, after M1–M4: for example one parameterised PR-stage sequence run twice instead of `run_dual_chain_off_pass`'s copy, and the per-candidate loop structure. It must give identical results. | identical `tracking-pr.root` and Bee on the three samples |

## Open items

- **Truth frame.** The fit points live in the reco frame: drift x with the cluster t0 correction, and data y/z position offsets. The MC truth vertex needs SCE true->reco plus the same t0/drift convention. `wclsTensorSetLabeler` already shifts the depos true->reco (`sce_field_fwd`), so M2 should reuse that convention, then check it against the hand-scan labels on MC.
- **The OFF pass and harvesting.** Today it explicitly disables the harvest. M2 must capture its call without changing its result.

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
