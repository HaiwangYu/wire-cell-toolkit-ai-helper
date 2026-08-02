# Issue #3 — Taggers judged on un-split (merged) clusters: 1-step chain missing `save_real_cluster_id`/`save_assoc_cluster_id`

Status: **root-caused & fixed** (2026-07-30). Fix pending re-run of the tagger samples.

## Symptom

For nue data **event 46363** (run 18255 / subrun 1; nskip 4 of the evt-269774
data file), the in-beam nu-candidate main cluster (cluster 19) gets **opposite
FC verdicts** in the two chains:

| chain | FC verdict | cluster 19 |
|---|---|---|
| our 1-step (`wcls-img-clus-matching-xin`) | **FC=false** (exits) | spans BOTH TPCs, x −110→+200, z 37→477 |
| sbnd_xin 2-step (`run_nusel_evt`) | **FC=true** (contained) | compact, one TPC, x −110→−10, z 263→468 |

`tagger_fc` for this event was all-`0` (not tagged) in the 1-step, vs tagged in
the 2-step.

## Diagnosis

The global imaging + clustering + matching is **identical** between the chains
(both 27123 pts; the other main clusters — cid 9 at x 4.9–35.2, cid 13 at
149.4–201.3 — match exactly). Only the nu-candidate cluster 19 differs.

Root cause: the **flash-merge provenance** was missing in the 1-step, so
`ClusteringUnmergeBundle` (in the PR tagger pass, `unmerge_bundle_mode="real"`)
could not split the flash-merged bundle. The 1-step log shows, for every cluster:

```
W <ClusteringUnmergeBundle:pr> cluster 19: no flash-merge provenance
  (save the pctree with save_real_cluster_id, or set mode="component"); not split
```

So cluster 19 stayed **merged across the cathode** (a small ~14-blob West-TPC
fragment fused to the East-TPC nu cluster), extending it to the West anode →
`TaggerCheckFC` sees an endpoint at the boundary → **FC=false** (exiter).

The sbnd_xin 2-step runs its Q/L step with `run_ql_evt.sh -save-rcid`, so the
persisted pctree carries the provenance; `unmerge_bundle` then splits
`cluster 19: 1542 blobs -> main 1528 + 2 associated holding 14 (real mode)` →
compact contained main → **FC=true**.

The bug is **not** in the taggers or their config — it survives matching the FV
margins (fvz/fvzi/fvx/fvy) and the TGM options (chord/rescue/main_pair) between
the chains. It is purely that the 1-step did not attach the provenance the PR
unmerge steps need.

### Impact

Every event whose main cluster needs unmerging (cross-cathode crossers,
multi-bundle flash groups) had its STM/TGM/FC verdicts computed on the **wrong
(merged) geometry**. This affects the earlier 1-step tagger samples (the 10-evt
MC/data and 48-evt data runs in issue #2) — their `tagger_*` sets were computed
on un-split clusters and need re-running.

## Fix

`sbnd/wcls-img-clus-matching-xin.jsonnet` (entry config) — add two args to the
all-APA maker call so the provenance is attached to the grouping the pr_node
consumes:

```jsonnet
local clus_all_apa = clus_maker.all_apa(tools.anodes, dump=false,
                                        bee_sink=bee_shared, premerged=true,
                                        save_real_cluster_id=true,   // flash-merge provenance (unmerge_bundle)
                                        save_assoc_cluster_id=true); // isolated-grouping provenance (unmerge_assoc)
```

**One file only.** `clus.jsonnet` (`all_apa`/`clus_all_apa`) and the larwirecell
labeler already support these — the params were always plumbed; the entry just
wasn't setting them.

## Verification (event 46363, 1-step with the fix)

- `no flash-merge provenance ... not split` warnings: **gone** (count 0).
- `ClusteringUnmergeBundle:pr cluster 19: 1542 blobs -> main 1528 + 2 associated
  holding 14 (real mode)` — **identical to the 2-step**.
- `TaggerCheckFC: cluster 19 → FC=true`; `tagger_fc = {1: 10698}` (compact main
  fully tagged) — now **agrees with sbnd_xin's 2-step**.

## BEE (all `/event/list/`)

- 1-step **buggy** (48-evt set, event 4; tagger_fc all-0):
  https://www.phy.bnl.gov/twister/bee/set/7d081fbf-b08f-4dbd-9c47-cd73a7c98472/event/4/
- sbnd_xin **2-step** (46363):
  https://www.phy.bnl.gov/twister/bee/set/abfb3a1f-28e1-4574-be1d-b31b96b65e34/event/list/
- 1-step **fixed** (46363; FC=true, tagged):
  https://www.phy.bnl.gov/twister/bee/set/bd28b4a8-f474-4e22-aff9-9fc96510325c/event/list/

## Follow-up

- Re-run the issue-#2 tagger samples (10-evt MC/data, 48-evt data) with the fix;
  the verdicts will change on any event with an unmerged main.
- The sbnd_xin 2-step chain was run against **our** local WCT build (Xin's
  `/nfs/data/1/xqian/toolkit-dev` is not reachable on the gpvm). Two run-time
  workarounds were needed and are not code bugs: bind-mount a writable
  `/home/xqian/tmp` (`_runlib.sh:98` hardcode), and `run_nusel_evt.sh -stm-fit`
  to load `WireCellRoot` (which registers `SCEFieldTH3`, pulled in by
  `pctransforms`' `sce_field`; the PR jsonnet otherwise only loads WireCellRoot
  under `save_stm_fit`).

---

## Part 2 — the fix was INCOMPLETE for the isolated grouping (2026-07-31)

The all_apa fix above (`save_real_cluster_id`/`save_assoc_cluster_id`) fixed the
**flash-merge** provenance (`unmerge_bundle`, `real_cluster_id`), which all_apa's
own `examine_bundles` creates. But it did **not** fix the **isolated-grouping**
provenance (`unmerge_assoc`, `assoc_cluster_id`), which is created one stage
earlier — by `clustering_isolated` in the **per-APA** step (`cm.isolated(...)`).

Symptom: MC **32-10-10** (2nd event of the first round1-qlmatch file). Our 1-step
gave `STM=0`, but the 2-step and Xin (doc 67 §10.3) give **STM=1**. The 1-step
logged `ClusteringUnmergeBundle:prassoc … unmerged 0 main clusters` — the isolated
split found no provenance, so the STM main stayed un-refined (148 blobs vs the
132-blob split → wrong verdict).

### Completing fix (per_apa)

The per-APA MABC needs `save_assoc_id=true` to homogenize `assoc_cluster_id` so it
survives serialization out of the per-APA node (otherwise dropped before
`matching_joint`, so the all-APA `save_assoc_cluster_id` has nothing to preserve):

```jsonnet
clus_maker.per_apa(tools.anodes[n], dump=false, bee_sink=bee_shared, save_assoc_id=true)
```

Verified: `prassoc cluster 22: 148 → main 132 + 16` (= 2-step), `STM=1`. Data
evt 46363 still `FC=true` (main further refined). Commit `96c760d`
(wcp-porting-validation).

## Part 3 — sim `use_sce=false` to match Xin, and the full cross-check

Xin runs MC in the **T0-corrected reco scope** (`x_t0cor`), not SCE true space.
Set the sim reco toggle `use_sce: true → false` in `clus.jsonnet` (WCT `master`
commit `d53ba3f9`); data was already `use_sce=false`. This closed the last
residual: with SCE **on**, our 2-step gave 32-10-10 main length **99.0 cm** vs
Xin's 92.9; with SCE **off** we get **92.9 cm** — an exact match.

### Cross-check: our 1-step vs our 2-step vs Xin's doc 67

With the complete provenance fix + sim `use_sce=false`, ran all three chains
(the 2-step = sbnd_xin scripts, doc-59 `NUF` production flags, against our
`master` build):

- **MC (the doc-67 ten: 32-10-{6,10,13,14,16,21,39,43}, 31-88-{5,12})** —
  our 1-step == our 2-step == **doc 67 §10.3, exactly**: STM on
  **32-10-10, 32-10-21, 31-88-12**; TGM on **32-10-13** (501.9 cm); the rest
  nu-candidate; 32-10-6 / 32-10-43 have no in-beam bundle. Main lengths match to
  0.1 cm (92.9 / 501.9 / 53.9 / 116.1 / 74.9 / 263.9 / 126.6 / 234.0 / 192.8).
- **DATA (all 48 events)** — our 1-step == our 2-step, **per-event identical**
  (0 disagreements): STM 0/48, TGM 6/48
  (10550, 116962, 271851, 360535, 389538, 444187), FC 33/48.

**No differences remain** between the 1-step production chain and Xin's 2-step
reference, on either MC or data.

### Note on running Xin's 2-step here

Xin's `/nfs/data/1/xqian/toolkit-dev` isn't reachable on the gpvm, so the 2-step
ran the sbnd_xin scripts against **our** `master` build (same taggers). MC needs
a scratch-copied dump jsonnet overriding the wire/badmask/summary products to the
MC tags (`simtpc2d`/`DetSim` vs data `sptpc2d`/`Reco1`); opflash is the same.
Run per-event (not `all`) with a `/home/xqian/tmp` bind-mount and `-stm-fit`
(loads `WireCellRoot` for `SCEFieldTH3`); the doc-59 `NUF` flags +
`SBND_SAVE_ASSOC=1` are required to match production.

Status: **CLOSED — 1-step now reproduces the 2-step / Xin on MC and data.**
