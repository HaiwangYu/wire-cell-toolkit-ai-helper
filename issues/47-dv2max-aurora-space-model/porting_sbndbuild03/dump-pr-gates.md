# Task B: the `T_dlvtx_space` dump PR, prepared (issue 47 / ai-helper #44; 2026-11-16 UTC)

Request: prod_polaris, relaying Haiwang, 2026-11-16. Prepare only: the PR is **not opened**, and nothing is posted on WireCell PRs.

## Branch

| item | value |
|---|---|
| branch | `HaiwangYu/wire-cell-toolkit:sbnd-dlvtx-space-pr` **`794d7817`** = master `c6be329e` + **one commit** (`55177882` cherry-picked), **pushed** to the fork |
| conflicts | `sbnd-pr-stage.jsonnet` `node()` and `wct-pr.jsonnet` `pr_stage.node(...)`: both sides add arguments (#543's `vertex_method/dv2_bundle`, ours `dl_vtx_dump_space`); both kept |
| `BeeClusterPoints.h` / `.cxx` | **byte-identical to #547's** (git blobs `7b8b7b25` / `6793f563` in both), so whichever PR merges second sees an identical add |
| `MultiAlgBlobClustering.cxx` | **only in this PR**: #547 adds `BeeClusterPoints` for its collector but leaves MABC as on master. The MABC Bee writer calling the helpers is this PR's change, so the "Bee identical" gate below is the refactor's test |
| with #547 | master + #547 (`e426d988` tree) + this branch: `BeeClusterPoints` and MABC merge cleanly. The only conflict is the same one-line `sbnd-pr-stage.jsonnet` `node()` signature (both add args; keep both + the `aurora_space` default) |
| builds | `/exp/sbnd/data/users/yuhw/opt-dumppr` (the branch), `/exp/sbnd/data/users/yuhw/opt-dumpgate` (master + #547 + branch, local `f6c456e7`, not pushed) |
| master baseline | master `c6be329e` has the same git tree as `5aa05cf1` (`9f966e53`), so `opt-p544` and its P5 runs (`runs-p544/r7c`) are the master build and outputs |

## One setting for the writer's scope and #547's collector (proposal)

Today, with both PRs in, three places in `clus.jsonnet` `pr()` must name the same point set:

| consumer | keys | value |
|---|---|---|
| the PR MABC Bee layer `clustering-pr` | `bee_points_sets[0].pcname / coords` | `'3d'`, `common_corr_coords(pos_offset_on)` |
| #547's in-chain collector (`TaggerCheckNeutrino`) | `dv2_space_pcname / dv2_space_coords` | `'3d'`, `common_corr_coords(pos_offset_on)` |
| this PR's writer (`SbndPrMagnifyTrackingVisitor`) | `space_pcname / space_coords` | `'3d'`, `common_corr_coords(pos_offset_on)` |

Plus the touch distance:
- the collector takes it from the bundle (`bundle.json` `space.touch_cm`, 1 cm for `aurora_space`);
- the writer takes it from `pr(space_touch_cm=1.0)`.

**Proposal.**
- One local in `pr()`, used by all three:
  ```jsonnet
  // The Bee clustering-layer scope: the points a space-point DV2 bundle reads in the chain (#547),
  // the T_dlvtx_space writer records (#44), and the PR Bee layer shows.  One setting, so they cannot diverge.
  local pr_space_scope = { pcname: '3d', coords: common_corr_coords(pos_offset_on) },
  ```
  `dv2_space_pcname: pr_space_scope.pcname`, `space_pcname: pr_space_scope.pcname`, and so on, and the Bee set's `pcname/coords` too.
- **Touch.** Make the writer's default follow the bundle. Next to #547's `dv2_bundle_sha256` map, add a map `dv2_bundle_space_touch_cm` (`'dv2max/sbnd/aurora_space/bundle.json': 1.0`). The writer uses it when the effective bundle is listed, `space_touch_cm` otherwise.
  - jsonnet cannot `import` a computed path, so the manifest itself can't be read here.
  - Alternative in C++: the writer reads `touch_cm` from the same `DV2_Load` report as the collector. That is a bigger change, and it ties the writer (`root`) to `pyutil`.
- **Which PR carries the wiring: this one (the dump PR).**
  - It merges last in the proposed order (#544 → wire-cell-data #8 + #547 → dump PR).
  - Its rebase onto master-with-#547 is where both sides exist. It then changes #547's two collector lines to use the local, plus the Bee layer, and adds its own.
  - #547 stays as reviewed.
  - If the dump PR were to merge first, #547 would carry it instead. Either way, the PR that merges second wires all three.
- The runtime guard stays the digest gate below: the in-chain input (cloud + space) must equal what `T_dlvtx_cloud` + `T_dlvtx_space` rebuild, for every call.

## Gates — all pass

Runs: the 27 #43 step-1 tars (8 MC CV, 10 MC nueCC, 9 data slices; 276 events), `scripts/run-step2.sh` with production step-2 TLAs (`dl_vtx_dump`, `flat_tree`, `truth_match` on MC), one pinned core each. 81 runs, all rc 0 (`scripts/tasks-dumppr.txt`).

| gate | arms | result |
|---|---|---|
| 1a. knob off, compiled configs = master (`scripts/dumppr-config-compare.sh`, `tables/dumppr-config.txt`) | branch vs master `c6be329e` cfg | **equal**: step 2 sim/data × `dv2_split_move`/`original`, step 1 sim/data (6/6) |
| 1b. knob off, `tracking-pr.root` = master (`scripts/compare-trees.py`, every tree/branch by value; `tables/dumppr-trees-off-vs-master.txt`) | `opt-dumppr` knob off vs `opt-p544` (= master tree) P5 runs, default `r7_cloud` | 276/276 files: only `Trun.wct_version` (+ its `recTreeWireCell` column), and in 1 file (nueCC 3750 evt 1844) `T_rec_charge` rows 879/880 swapped with identical values. That swap is **run-to-run**: the knob-on run of the same branch equals master there, and the P4 test build shows it too. **Pass** |
| 2. Bee output = master after the MABC refactor (`scripts/bee-compare.py`, member by member, bytes; `tables/dumppr-bee-off-vs-master.txt`) | same | **27/27 units, 2,325/2,325 members byte-identical** |
| 3. knob on vs off (`tables/dumppr-trees-on-vs-off.txt`, `tables/dumppr-bee-on-vs-off.txt`) | `opt-dumppr` on vs off | the only differences: **new tree `T_dlvtx_space`, `T_dlvtx_call.space_cluster_id` / `n_space`**, and their `recTreeWireCell` columns (276/276 files); plus the same run-to-run `T_rec_charge` 879/880 swap in evt 1844. Bee 2,325/2,325 identical. Configs: the only added keys are `dl_vtx_dump_space`, `space_touch_cm`, `space_pcname`, `space_coords` (6 leaves) |
| 4. doctests (`scripts/run-doctests.sh`) | `opt-dumppr`; `opt-dumpgate` | branch: clus 507/507, pyutil 12/12, root 14/14, `test_dv2max.py` 33 OK (= master's counts: the commit adds no doctest). Gate merge: clus 512/512, pyutil 17/17, root 14/14, 33 + 20 OK |
| 5. in-chain input == `T_dlvtx_space`, every call (`scripts/percall.py`, `tables/dumppr-percall-gate-aur.csv`) | `opt-dumpgate` = master + #547 + branch (local `f6c456e7`), `aurora_space`, knob on | **229/229** digests (cloud + space) rebuilt from the dump equal the in-chain call's; `n_space` 229/229; 1,417,696 space points; standalone replay within 1.6e-5 cm. Identical to P4 (`ddbc0488`) |

**Gap.** The commit adds no doctest of its own.
- `bee_touching_clusters` (inclusive touch, empty cloud, zero distance) is tested by #547's `clus/test/doctest_dv2_space.cxx`. So once #547 is in, the shared helper is covered.
- The writer is not unit-tested; only the end-to-end gates above cover it. Examples: a `T_dlvtx_space` row equals `bee_cluster_points`, and `dl_vtx_dump_space` without `dl_vtx_dump` is a configure error.
- A small root doctest of the configure error would be the obvious addition before opening.

Locations: builds `opt-dumppr`, `opt-dumpgate`; worktrees `wct-dumppr` (the branch), `wct-dumpgate`; runs `/exp/sbnd/data/users/yuhw/production-prep/issue47/dumppr/runs/{dumppr-off-r7c,dumppr-on-r7c,dumpgate-on-aur}/`.
