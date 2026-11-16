# DRAFT — starting point only. Haiwang writes the PR description (the WCT repo wants the human's own text).

Branch: `HaiwangYu/wire-cell-toolkit:sbnd-dlvtx-space-pr` (one commit on master `c6be329e`). PR not opened.

---

## What (draft)

An opt-in recording of the space points a space-point DL vertexer looks at, in `tracking-pr.root`:

- **`T_dlvtx_space`**, written once per event: `cluster_id, blob_index, x, y, z, q` of every in-scope cluster that touches the cloud of at least one recorded DL-vertex call. "Touches" means some point within `space_touch_cm`, 1 cm by default. These are the same points as the PR-stage Bee `clustering-pr` layer.
- **`T_dlvtx_call.space_cluster_id` / `n_space`**: for each call, the clusters it touches and how many points they hold.
- With `flat_tree`, the same columns appear in `recTreeWireCell`.

Knob: `dl_vtx_dump_space` (needs `dl_vtx_dump`). It is wired through `clus.jsonnet` `pr()`, `sbnd-pr-stage.node()` and a `wct-pr.jsonnet` TLA. Off by default: every key is omitted, so the compiled configs and the outputs are unchanged.

`clus/BeeClusterPoints.{h,cxx}` factors out of `MultiAlgBlobClustering::fill_bee_points_from_cluster` the scope gate, the blob-by-blob point loop and the per-point charge. These are byte-identical to the files in #547, which uses them for the in-chain collector. The MABC Bee writer now calls them, with the same order, values and filter semantics.

## Why (draft)

- The `aurora_space` DV2-MAX model (#547) takes these points as input next to the trajectory-fit cloud.
- With this tree, a production `tracking-pr.root` / flat CAF holds the exact network input of every call:
  - training data for the next model, without re-running step 2 or parsing Bee zips;
  - offline re-inference;
  - a per-call check that the in-chain input equals the recorded one (input digest).
- Parsing Bee zips is not reliable for this: multi-event step-2 zips merged events at about 4 % before the #544 fix.

## Tests (draft; numbers from ai-helper issue 47, `porting_sbndbuild03/dump-pr-gates.md`)

- knob off vs master: compiled configs identical; every tree of `tracking-pr.root` identical by value; Bee zips identical (the #43 inputs: MC CV, MC nueCC, data);
- knob on: only the new tree and the two new branches (plus their `recTreeWireCell` columns);
- doctests;
- with #547 merged too: for every DL-vertex call, the in-chain input digest (cloud + space) equals the one rebuilt from `T_dlvtx_cloud` + `T_dlvtx_space`.

## Relation to #547 (draft)

- Independent of #547; merges cleanly either way. The only overlap is the identical `BeeClusterPoints` add, plus a one-line cfg conflict in `sbnd-pr-stage.jsonnet` `node()` (both add arguments): keep both.
- After both are in, the writer's scope (`space_pcname` / `space_coords` / `space_touch_cm`) and #547's collector (`dv2_space_pcname` / `dv2_space_coords`, touch from the bundle) should come from one setting; see the proposal in `porting_sbndbuild03/dump-pr-gates.md`.
