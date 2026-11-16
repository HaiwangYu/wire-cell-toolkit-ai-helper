# DRAFT — starting point only. Haiwang writes the PR description (the WCT repo wants the human's own text).

Branch: `HaiwangYu/wire-cell-toolkit:sbnd-dlvtx-space-pr`, two commits on master `e7242071` (#547 merged). PR not opened.
- `99d6d368`: the `T_dlvtx_space` writer (ai-helper #44).
- `db3c5ec1`: one PR Bee scope for the Bee layer, the DV2 space collector and the writer, plus the knob doctest (ai-helper #47).

---

## What (draft)

An opt-in recording, in `tracking-pr.root`, of the space points the DV2-MAX space-point model (`aurora_space`, #547) reads in the chain:

- **`T_dlvtx_space`**, written once per event: `cluster_id, blob_index, x, y, z, q` of every in-scope cluster that touches the cloud of at least one recorded DL-vertex call.
- **`T_dlvtx_call.space_cluster_id` / `n_space`**: for each call, the clusters it touches and how many points they hold.
- With `flat_tree`, the same columns appear in `recTreeWireCell`.

Knob: `dl_vtx_dump_space` (needs `dl_vtx_dump`). It is wired through `clus.jsonnet` `pr()`, `sbnd-pr-stage.node()` and a `wct-pr.jsonnet` TLA. Off by default: every key is omitted, so the compiled configs and the outputs are unchanged.

**One scope.** In `clus.jsonnet` `pr()`, a `pr_space_scope` local (`pcname: '3d'`, `coords: common_corr_coords(pos_offset_on)`) now feeds three consumers, so they cannot diverge:
- the PR Bee clustering layer;
- the DV2 collector (`dv2_space_pcname` / `dv2_space_coords`);
- the writer (`space_pcname` / `space_coords`).

The writer's touch distance follows the effective bundle through `dv2_bundle_space_touch_cm`, next to `dv2_bundle_sha256` (`aurora_space`: 1 cm, as in its `bundle.json`). `pr(space_touch_cm)` now defaults to `null`, meaning that map, else 1 cm; a number overrides.

**MABC.** The Bee writer (`MultiAlgBlobClustering::fill_bee_points_from_cluster`) now calls the `BeeClusterPoints` helpers that #547 added. It keeps the same order, values and filter semantics, so the Bee output is byte-identical.

## Why (draft)

With this, a production `tracking-pr.root` / flat CAF holds the exact network input of every DL-vertex call, cloud plus space points. That gives:
- training data for the next model, without re-running step 2 or parsing Bee zips;
- offline re-inference;
- a per-call check that the in-chain input equals the recorded one (input digest).

## Tests (draft; numbers from ai-helper issue 47, `porting_sbndbuild03/dump-pr-gates.md`)

On the #43 inputs (MC CV, MC nueCC, data; 27 step-1 tars, 276 events):
- knob off vs master: the compiled configs, including master's SBND default (`aurora_space` + `dv2_split_move`), are identical; every tree of `tracking-pr.root` is identical by value; the Bee zips are byte-identical;
- knob on: only the new tree and the two new branches (plus their `recTreeWireCell` columns);
- for every DL-vertex call, the in-chain input digest (cloud + space) equals the one rebuilt from `T_dlvtx_cloud` + `T_dlvtx_space`;
- doctests, including the new `root/test/doctest_sbnd_dlvtx_space_knob.cxx`: default off; configure refuses the knob without `dl_vtx_dump` or with `space_coords` not naming 3 arrays.
