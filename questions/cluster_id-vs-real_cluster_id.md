# Q: How are `cluster_id` and `real_cluster_id` formed, and which one does BEE color by?

Short answer: in the clustering (MABC) Bee output, **`cluster_id`** is the
*flash-t0-merged* cluster id (coarser) and **`real_cluster_id`** is the
*pre-merge geometric* cluster id per blob (finer). **BEE colors the cluster
result by `real_cluster_id`** (falling back to `cluster_id`).

## Where they come from (wire-cell-toolkit)

Both are set in the blob-level Bee dump:
```
bpts.append(pt, point_charge, clid, real_clid);   // append(point, q, cluster_id, real_cluster_id)
```
`clus/src/MultiAlgBlobClustering.cxx:1722`

- **`cluster_id` = `clid = cluster.get_cluster_id()`** = `Cluster::ident()`
  (`MultiAlgBlobClustering.cxx:1591`, `Facade_Cluster.cxx:148`). It is the id of
  the cluster **after** the all-APA flash-t0 merge: in `examine_bundles`
  (run with `use_flash_t0=true`) every geometric cluster matched to the *same
  optical flash* (same t0) is merged into one cluster, so those pieces collapse
  to a single `cluster_id`.
- **`real_cluster_id`** is the per-blob **original (pre-merge) cluster ident**,
  recorded into a `"real_cluster_id"` array in the `"perblob"` point cloud by
  `clustering_examine_bundles.cxx:145-153`
  (`merge_clusters(..., "perblob", "real_cluster_id", ..., "real_cluster_main")`).
  The dumper reads it back and, per blob,
  `real_clid = has "real_cluster_id" ? orig_ids[blob] : clid`
  (`MultiAlgBlobClustering.cxx:1679-1701`) — i.e. it falls back to `cluster_id`
  when the array is absent.

So far-apart members of a flash group keep their **distinct pre-merge ids**
(and thus distinct BEE colors) even though they now share one `cluster_id`.

Knobs: `use_flash_t0` (creates the array), `real_cluster_id_global`
(`restamp_real_cluster_id`, one event-wide numbering epoch),
`save_real_cluster_id` (persist into the pctree tarball). Inverse of the
decompose/merge is `QLMatching::recompose_cluster_groups` (`match/src/QLMatching.cxx`).

## ⚠ The name `real_cluster_id` does NOT always mean the same thing

The Bee JSON key is **hardcoded** in `Bee::Points::asJson()`
(`util/src/Bee.cxx:50`) and always labels the **4th `append()` arg**. So the
*name* is stable end-to-end, but the *value* is positional and set/writer
dependent:

| Bee set | `real_cluster_id` means |
|---|---|
| clustering / MABC | pre-flash-merge **geometric cluster id** (or `= cluster_id` if the perblob array is absent) |
| labeler truth / sed sets (`TensorSetLabeler.cxx:959,1113`) | true **G4 trackid** (== `cluster_id`) |
| labeler unlabeled set (`:1116`) | **reco cluster ident** |

Also: the perblob array name is *configurable* (`merge_clusters` param;
`ClusteringUnmergeBundle.cxx:178 m_id_aname`) while the reader/JSON key are
hardcoded — a name change would silently degrade `real_cluster_id` to
`cluster_id`. And `QLMatching` (standalone chain) is a *different* writer with
its own decompose/recompose, so the same event's `real_cluster_id` can differ
between the standalone and integrated chains.

## How BEE colors it (wire-cell-bee3)

`events/static/js/bee/physics/sst.js:150-154` (Show-Cluster mode):
```js
let color_id = real_cluster_id[i] > 0 ? real_cluster_id[i] : cluster_id[i]; // backward compatible
color_id = Math.floor((color_id + length) % (length - ran));
color = USER_COLORS[theme][color_id];
```
So each point's color = palette-lookup on **`real_cluster_id`**, falling back to
`cluster_id` when `real_cluster_id <= 0` (e.g. absent → sst.js:77 sets it 0).
Other modes: `showCharge` = `q` HSL heatmap; default (both off, `store.js:73-74`)
= one flat per-set color. `ran` is a random 0-4 palette offset only when
`randomClusterColor` is requested (else 0 → deterministic).

## Current data workflow (`sbnd/wcls-img-clus-matching-xin-data.fcl`)

`reality="data"` → the labeler is DATA-mode (no truth sets). The Bee cluster set
is `clus_maker.all_apa(dump=true)` after per-APA MABC + joint `QLMatching`. In
`clus_all_apa` all merge steps + `examine_bundles` run with
`use_flash_t0=true` (`clus.jsonnet:412-430`), so:
- `cluster_id` = flash-t0-merged (+ QL main/associated premerge) grouping,
- `real_cluster_id` = pre-merge geometric clusters — **what BEE colors**.

## Worked example — event 269774 (run 18255/1), Bee diagnostic sets

From set `0fbcecd1-23ff-4103-8a58-cd9a23551d80`, event 20's `clustering-global`
has 21495 points, **9 distinct `cluster_id`**, **13 distinct `real_cluster_id`**
(the flash-t0 merge collapsed 13 geometric clusters into 9 flash groups).

To make the effect visible, a set was built with four clustering layers on the
same points:

| layer | colors by | # colors | content |
|---|---|---|---|
| `clustering-global` | real_cluster_id | 13 | all geometric clusters |
| `clustering-global-no-rci` | cluster_id (rci array removed) | 9 | flash-t0-merged grouping |
| `clustering-global-diff-rci` | real_cluster_id | 9 (in 3 ci) | only points whose `cluster_id` spans >1 `real_cluster_id` (ci 12,13,14; 13074/21495 pts) |
| `clustering-global-diff-rci-no-rci` | cluster_id | 3 | same points, rci removed → the 3 merged groups |

Bee (all four layers, event 20):
https://www.phy.bnl.gov/twister/bee/set/ae769e36-5900-426b-9a31-927c0f7b2e16/event/list/

`diff-rci` vs `diff-rci-no-rci` isolates exactly where the flash-t0 merge fused
distinct geometric clusters: 9 pieces (by rci) lumped into 3 cluster_ids (by ci).

The layers were produced by downloading the original event's JSON layers,
deriving the extra layers in Python (drop / filter the `real_cluster_id` array),
and re-uploading via `sbnd_xin/upload-to-bee.sh`.
