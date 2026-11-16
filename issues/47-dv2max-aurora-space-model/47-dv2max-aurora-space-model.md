# Issue 47: DV2-MAX aurora-r2 space-point model — locate the weights, port to sbndbuild03, validate in-chain inference

GitHub: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/47

Builds on:
- #43: the PR #543 review and its validation method;
- #44: the `T_dlvtx_space` data product and the space-point inference plan;
- sbnd-wirecell-production #4: the aurora-r2 reprocessing that produced the training data.

## 0. The request (Haiwang, 2026-11-15)

1. Sne trained a new DV2-MAX model on Avinay's Aurora sample (aurora-r2, 478k training events, trajectory fit + space points). He shared the figure below, but has not uploaded the model. Find the weights in his work dir on Polaris.
2. Post the likely model files and the reasoning here; upload his figure.
3. Draft a Slack message asking Sne to confirm.
4. `porting_sbndbuild03` (the Claude Code agent on sbndbuild03):
   - rsync the model to sbndbuild03;
   - review whether master + PR #544 can run space-point DL-vertex inference inside WCT;
   - if it can, validate against Sne's numbers (method: #43);
   - if the validation passes, draft a message asking Sne to review PR #544.
5. This issue is the channel between the Claude Code agents.

![Sne's figure: aurora-r2 vs r7, efficiency vs distance to the true vertex](eff_vs_distance_aurora_vs_r7.png)

## 1. The likely model (found by `prod_polaris`, 2026-11-15; not yet confirmed by Sne)

**Run:** `/lus/eagle/projects/neutrinoGPU/snehadri/sbnd-vertexer/dv2max/runs/aurora_space` (`$RUN` below).

### Why this run

- **The figure is this run's hold-out evaluation.**
  - `aurora/plot_aurora_vs_r7_eff.py`, which wrote `aurora/plots/eff_vs_distance_aurora_vs_r7.png` (the figure above, byte for byte), reads `dv2max/runs/aurora_space/eval_holdout/eff_vs_distance.csv`.
  - `$RUN/eval_holdout/eval_test.md` has exactly the figure's numbers:

    | | figure | `eval_test.md` |
    |---|---|---|
    | νe CC | 0.951, n = 7,531 | `dv2max` 0.951, n = 7,531 |
    | νμ CC | 0.955, n = 5,958 | 0.955, n = 5,958 |
    | NC | 0.719, n = 1,511 | 0.719, n = 1,511 |

- **Training data.** `config.yaml` is `name: aurora_space`. The cache (`cache/aurora_space`, 985,994 events) was built from our aurora-r2 merged CAFs, i.e. `wc.T_dlvtx_call/cloud/space`. Those come from toolkit `sbnd-dlvtx-space-44` `55177882`, mirrored to `/lus/eagle/projects/neutrinoGPU/snehadri/dlvtx/aurora-r2`.
- **Hold-out.** `aurora/holdout_r2/`: 15,000 labeled events (BNB 7,397 + nue 7,603) in 2,217 whole units (merged CAFs), never trained on.

### The files

| role | file under `$RUN` | bytes | sha256 (first 16) | notes |
|---|---|---|---|---|
| pass-1 CNN | `models/pass1/f0/seed0/final.pt` | 80,460,790 | `a2b53531b7b70700` | final weights (2026-11-12 08:39), same layout as `r7_cloud`'s `pass1.pt` |
| pass-2 CNN | `models/pass2/f0/seed0/final.pt` | 80,458,182 | `8c1ed9326f127d3f` | 2026-11-12 18:50 |
| ranker (LightGBM) | `ranker_refit/ranker_fold0.txt` | 4,221,737 | `e536850272bb3e86` | **a re-fit**, 2026-11-14; see below |
| isotonic calibrator | `ranker_refit/isotonic_fold0.json` | 11,695 | `0ad6bd7f86b85440` | |
| ranker features | `ranker_refit/feature_names_fold0.json` | 8,190 | `aef4e60ec8ea17e3` | 382 features |
| config | `config.yaml` (and each model dir's copy) | 5,690 | `0021f7b3d6db6385` | |
| inference constants | `/lus/eagle/projects/neutrinoGPU/snehadri/sbnd-vertexer/cache/aurora_space/calibration.json` | | | `x_shift_cm` **0.29** (r7: 0.31); `q_ratio` **0.2474** (r7: 0.2408); `link_cm` 3.0; touch `match_cm` 1.0 |

Not the model:
- `models/*/last.pt` (400 MB): resumable training checkpoints with the optimiser state.
- `models/pretrain/*`: the pre-training stage.

**There is no `bundle.json` yet.** Sne has not run `make_bundle.py` for this run.

### Caveat: the ranker in the figure is not the ranker on disk

- The training run saved only the ranker's **predictions**, not the model. `aurora/refit_ranker.py` re-fit it from the saved union, and wrote `ranker_refit/NOT_REPRODUCED`: in the best mode, `force_col_wise`, only 94.5 % of the calls get the same top-1.
- Sne scored the re-fit itself (`ranker_refit/score_refit.md`) on the same 15,000 hold-out events. It is statistically the same:

  | | training-run ranker (figure) | re-fit (on disk) | difference |
  |---|---|---|---|
  | all, < 1 cm | 0.9291 | 0.9288 | −0.0003, CI95 [−0.0011, 0.0003], p 0.46 |
  | νe CC | 0.9511 | 0.9507 | |
  | νμ CC | 0.9547 | 0.9547 | |
  | NC | 0.7187 | 0.7174 | |
  | median | 0.146 cm | 0.146 cm | |

- **So the target for our validation** is the re-fit's per-call predictions, `ranker_refit/refit_test_fold0.csv`, not `preds/fold0_dv2max.csv`.

**Questions for Sne** (Slack draft, §3):
1. Are these the files?
2. Is the re-fit ranker the one to ship?
3. Will he make the bundle (`make_bundle.py`, wire-cell-data `uboone/dsnehadri/`), or should we?

## 2. Preliminary code check (by `prod_polaris`, for `porting_sbndbuild03` to confirm)

> **Superseded (2026-11-15):** `porting_sbndbuild03/review.md` corrects this. Sne has already pushed `dsnehadri/dv2max-aurora-space` `a17e6423` (in-chain space inference = #44 B2, bundle format v2, clean merge into master) and built the `aurora_space` bundle from the §1 files plus the re-fit ranker. So master + #544 alone still cannot run it, but the code exists.

| ref | what it has |
|---|---|
| master `7710c43b` (2026-11-12) | **PR #543 is merged**: DV2-MAX `r7_cloud`, `vertex_method`. `DV2_Vertex(weights, x, y, z, q, n_vertex_rows, trad, q_scale, q_offset)` takes the **trajectory-fit cloud only**; no space-point argument |
| PR #544 (`sbnd-wc-flatcaf`, head `b6278234`) | flat CAF, truth match, per-event names, review fixes. **No `T_dlvtx_space`, no space-point input to the vertexer** |
| fork `sbnd-dlvtx-space-44` `55177882` | PR #544 review fixes + `T_dlvtx_space`: the **dump** (#44 proposal A). It does not feed the network |
| #44 B2 (in-chain space-point inference) | **not implemented anywhere**, as far as I can see |

**Likely answer:** master + PR #544 cannot yet run space-point inference inside WCT. It needs:
- the #44 dump code (or the same touch test in the DL step);
- the B2 hook (space arrays into `DV2_Vertex`, the bundle declaring `input: cloud+space`, the cloud q × `q_ratio`, the cluster-id rule);
- a space-aware event builder: `prep_aurora_cache.py` / `prep_r7_space_cache.py`, not the `r7_cloud` one in `dv2max_vertexer/vertexer.py`;
- an `aurora_space` bundle.

## 3. Slack draft to Sne

> Hi Sne, great result on the aurora-r2 model, thanks for the plot! Before you upload it, I'd like to start testing it in WCT on sbndbuild03. I looked in your Polaris area, and I think the model is `dv2max/runs/aurora_space`:
> - pass 1: `models/pass1/f0/seed0/final.pt` (sha256 a2b53531…)
> - pass 2: `models/pass2/f0/seed0/final.pt` (8c1ed932…)
> - ranker: `ranker_refit/ranker_fold0.txt` (e5368502…) + `isotonic_fold0.json` + `feature_names_fold0.json`
> - constants from `cache/aurora_space/calibration.json`: x shift 0.29 cm, q ratio 0.2474
>
> Could you confirm these are the right files? Two more questions:
> 1. Your figure uses the training-run ranker, but the file on disk is the re-fit (NOT_REPRODUCED, 94.5 % same top-1; your `score_refit.md` shows 0.9288 vs 0.9291 overall). Is the re-fit the one you'd ship?
> 2. Will you build the bundle (`make_bundle.py`, like `r7_cloud`), or shall we?
>
> We're tracking this in https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/47. Thanks!

## 4. Agent protocol

- **Channel:** comments on GitHub issue 47. The first line of every comment is `[from <agent>] <topic>`; `prod_polaris` and `porting_sbndbuild03` are the agents so far. Address a request as `@<agent>`.
- **Files:** commit to `issues/47-dv2max-aurora-space-model/<agent>/` (scripts, tables, logs; no model files or data).
- **Status lines:** each agent keeps one line in §5 up to date (state, last commit, what it waits for).
- **Owner decisions** go to Haiwang (chat or issue); agents do not decide them for each other.
- **Direct messages** (Claude Code `SendMessage`) only for "please read the issue": the issue holds the content.

## 5. Status

| agent | state | waiting for |
|---|---|---|
| `prod_polaris` | Sne opened PR #547 (= validated `a17e6423` + test-only `c9f61962`); review + Slack drafts in `prod_polaris/` (not posted/sent) | `porting_sbndbuild03`'s doctests on `c9f61962` (comment 6904986947); then Haiwang posts |
| `porting_sbndbuild03` | dump PR branch finished on master `e7242071`: `sbnd-dlvtx-space-pr` `db3c5ec1` pushed (PR not opened); `pr_space_scope` + per-bundle touch map + root knob doctest; all gates pass (`dump-pr-gates.md`); description draft updated | Haiwang: rewrite the description and open the PR |
| `prod_aurora` | done: Track 2 + cross-checks (`prod_aurora/results.md`; wording fix e51f455) | Haiwang |

## 6. Joint summary (prod_polaris, porting_sbndbuild03, prod_aurora; 2026-11-15)

**Conclusion.** Sne's `aurora_space` DV2-MAX model runs inside WCT and reproduces his result. The build is master `7710c43b` + our `T_dlvtx_space` commit `55177882` + Sne's `dsnehadri/dv2max-aurora-space` `a17e6423`, i.e. test branch `HaiwangYu/wire-cell-toolkit:dv2max-aurora-space-test` `ddbc0488`.
- **On his own hold-out**, in-chain equals his offline evaluation exactly.
- **On independent MC**, it beats `r7_cloud` clearly.
- **On data**, the νe selection is unchanged.
- **Both machines** give identical inputs and predictions.
- **Every number** was recomputed by a second agent.

| check | where | result | cross-checked by |
|---|---|---|---|
| same build | both | commit `ddbc0488`; step-2 config md5 `r7_cloud` `d390e20f…`, `aurora_space` `a5c3df18…`; bundle `51588842…` (Sne's, from the §1 `final.pt` files + re-fit ranker) | both, equal |
| tests | both | `clus` 512/512, `pyutil` 17/17, `root` 14/14, `test_dv2max_space.py` 20 OK; Sne's Polaris failures are environmental | — |
| in-chain input == `T_dlvtx_space` | sbndbuild03 | 229 / 229 calls (input digest); in-chain vs standalone ≤ 1.6e-5 cm | prod_aurora (5,277 / 5,277 calls on Aurora) |
| **Sne's hold-out**, 500 units, 4,494 pass-0 calls | Aurora | < 1 cm in-chain = offline re-fit: **all 0.9232, νe CC 0.9557, νμ CC 0.9591, NC 0.7093**; the figure (0.951 / 0.955 / 0.719) inside every 95 % CI; picks within 0.1 cm 98.82 % | porting_sbndbuild03 (labels independently from Sne's `index.csv`; agrees, 6e-14 cm), prod_polaris (class fractions) |
| independent MC, the #43 events (not in aurora-r2 training) | sbndbuild03 | < 1 cm, 141 events: `original` 0.645, `r7_cloud` 0.837, **`aurora_space` 0.957**; median 0.47 → 0.33 cm; 20 gained / 3 lost (all CV) | prod_aurora (identical, the same events) |
| data nueCC-48 + NCπ0-19 | both | νe 42 → 42 (event by event), νμ 6 → 5 (+1 −2); the two machines: 68 / 68 equal digests, picks within 1.6e-6 cm | each other |
| cost | both | DV2 call median 2.4 s (sbndbuild03) / 1.5 s (Aurora) vs 0.69 s for `r7_cloud`; step-2 CPU +13 %; median RSS +290 MB | — |
| PR #544 updated on master | sbndbuild03 | `5aa05cf1` pushed; doctests pass; `original` configs identical; tree differences explained (review item 8, a known row swap) | — |

**The 4 hold-out calls that cross 1 cm (in-chain vs offline), all νμ CC:**
- 2 move inside: 25.96 → 0.16 cm and 1.96 → 0.45 cm;
- 2 move outside: 0.70 → 2.12 cm (a pick flip), and 0.72 → 1.01 cm (a 0.30 cm pick shift);
- one more pick flip misses either way (1.19 → 6.01 cm);
- net 0. (Correction by `porting_sbndbuild03`; `prod_aurora/results.md` fixed in `e51f455`.)

**Not done, waiting for Sne / Haiwang:**
- no PR from Sne's branch;
- nothing in wire-cell-data;
- SBND default unchanged;
- no message to Sne sent.

**Decisions for Haiwang:**
1. One message to Sne: confirm the files; review #544; open his WireCell PR; put the bundle into wire-cell-data. Drafted on request.
2. `aurora_space` as the SBND default: large, validated vertex gain, for about 3× DL-call CPU (+13 % step 2).

## Log

- 2026-11-15 (`prod_polaris`): issue opened; §1–§5.
- 2026-11-15 (`porting_sbndbuild03`): model + bundle copied, review (§2 superseded): Sne's branch has B2; #544 conflicts with master in 3 cfg files; plan P1–P6.
- 2026-11-15 (`porting_sbndbuild03`): model copied to `/exp/sbnd/data/users/yuhw/production-prep/dv2max-aurora-space/` (hashes match); found Sne's branch `dsnehadri/dv2max-aurora-space` and bundle; review and gap list in `porting_sbndbuild03/review.md`.
- 2026-11-15 (`prod_polaris`): Haiwang's go-ahead relayed (comment 6889547625): Track 1 sbndbuild03 (P1/P2/P4/P5), Track 2 Aurora (hold-out reproduction), then a cross-check (same build, same nueCC-48/NCπ0-19 inputs by input digest, each re-analyses the other's tables).
- 2026-11-15 (`porting_sbndbuild03`): P1 test branch `ddbc0488` + config md5s; P2 tests; P4 in-chain check; P5 #544 updated on master (`5aa05cf1`, pushed). Results in `porting_sbndbuild03/results.md`, tables in `porting_sbndbuild03/tables/`.
- 2026-11-15 (`porting_sbndbuild03`): P1/P2/P4/P5 done (`results.md`, comment 6890344733). (`prod_polaris`): `prod_aurora` told the test branch is on the fork.
- 2026-11-15 (`prod_aurora`): Track 2 done (comment 6890782810). (`prod_polaris`): Aurora's per-class numbers recomputed from its table: agree; `porting_sbndbuild03` asked for the last cross-check direction.
- 2026-11-15 (`porting_sbndbuild03`): recheck of prod_aurora's 500-unit hold-out numbers with labels from Sne's cache index: agree (comment 6890814492). Stopped.
- 2026-11-15 (`porting_sbndbuild03`): recheck of Aurora's hold-out numbers agrees (comment 6890814492). (`prod_polaris`): joint summary §6.
- 2026-11-16 (`prod_polaris`): Sne opened WireCell PR #547 (head `c9f61962` = `a17e6423` + a test-only leak-test commit). Missing: the `aurora_space` bundle in wire-cell-data (blocking; the PR makes it the default). Review draft and Slack draft in `prod_polaris/`; doctests on the head requested from `porting_sbndbuild03` (offline, so posted as comment 6904986947).
- 2026-11-16 (`prod_polaris`): review posted on PR #547 (Comment, pullrequestreview-5914254473); the head-commit doctest counts follow in a PR comment once `porting_sbndbuild03` reports.
- 2026-11-16 (`porting_sbndbuild03`): PR #547 as it would merge (master + `c9f61962`, `opt-pr547`): all doctests and Python tests pass; the only differences from `ddbc0488` are #544's 4 clus + 3 root cases; the new leak test passed 30/30 (least batch 0 < 500); the pinned bundle hash `51588842…` equals our copy.
- 2026-11-16 (`porting_sbndbuild03`): doctests on PR #547 head pass (comment 6905426354). (`prod_polaris`): follow-up posted on #547 (issuecomment-6905784393). Open: Sne's wire-cell-data PR; the Slack message (Haiwang).
- 2026-11-16 (`prod_polaris`): **PR #544 merged** into master (`c6be329e`, merge commit), with Haiwang's go-ahead after Sne agreed to #544 first. **wire-cell-data PR #8** (Sne, head `e3c3a6c3`) checked: all 7 files' git blobs equal Sne's Polaris clone, the tested copies' source; `SHA256SUMS` OK; `bundle.json` `51588842…`. It is exactly the bundle we tested. Tasks sent to `porting_sbndbuild03`: (A) data nueCC-48 + NCπ0-19, `original` vs `aurora_space` `dv2_split_move`, Bee sets; (B) prepare the `T_dlvtx_space` dump PR (`sbnd-dlvtx-space-pr`, not opened). Merge order proposed: #544 (done) → wire-cell-data #8 + #547 together → the dump PR.
- 2026-11-16 (`prod_polaris`): **wire-cell-data PR #8 merged** (`99c6497f`, merge commit, head `e3c3a6c3` = the tested bundle); master now has `dv2max/sbnd/aurora_space` and `r7_cloud`. Remaining for #547: the one-line `sbnd-pr-stage.jsonnet` conflict with #544, then merge.
- 2026-11-16 (`prod_polaris`): **#547 conflict resolved** and pushed to Sne's branch: `e426d988` = merge of master `c6be329e` into `c9f61962` (kept #544's `flat_tree/truth_match/blob_truth` args + `aurora_space` default in `sbnd-pr-stage.jsonnet`). Compiled `wct-pr.jsonnet`: defaults == #547 head, `original` == master, vs master+aurora only #547's 3 keys. #547 now MERGEABLE/CLEAN. Note for `porting_sbndbuild03` task A: build from `e426d988`.
- 2026-11-16 (`porting_sbndbuild03`): task A done (`data-orig-vs-aur.md`, comment 6921769482): data `original` vs `aurora_space`, nue 39 → 42 (+5/−2), numu 7 → 5; vertex shift median 0.46 cm, 9 ≥ 5 cm; Bee sets 89cdea53 (original) / 431dc57f (aurora). (`prod_polaris`): summary + links posted on #547 (issuecomment-6921785658). Task B gates still running.
- 2026-11-16 (`porting_sbndbuild03`): task B done: `sbnd-dlvtx-space-pr` `794d7817` (master `c6be329e` + `55177882`) pushed to the fork, PR not opened. Gates (`dump-pr-gates.md`): knob-off configs and trees = master (only `wct_version` + a run-to-run row swap), Bee 2,325/2,325 identical, knob on adds only `T_dlvtx_space` + 2 branches, doctests pass, master + #547 + branch 229/229 digests. Proposal: one `pr_space_scope` local for the Bee layer, #547's collector and the writer, carried by the dump PR.
- 2026-11-16 (`prod_polaris`): deck linked on #547 (issuecomment-6924445256) and **PR #547 merged** (`e7242071`, merge commit). Master now defaults SBND to `aurora_space` + `dv2_split_move`. Haiwang's visual read of the deck: the new model looks very good, no clear failures; some hand-scan vertices may themselves be off. (`porting_sbndbuild03`): task B gates pass (`sbnd-dlvtx-space-pr` `794d7817`, comment 6924433745); next: rebase onto `e7242071` + the shared `pr_space_scope` wiring + a doctest.
- 2026-11-16 (`porting_sbndbuild03`): dump PR round 2 on master `e7242071` (#547 merged): `sbnd-dlvtx-space-pr` rewritten to `db3c5ec1` (rebased writer `99d6d368` + `db3c5ec1`: one `pr_space_scope` for the Bee layer, #547's collector and the writer; `dv2_bundle_space_touch_cm`; `doctest_sbnd_dlvtx_space_knob.cxx`). Gates: knob-off configs (incl. the `aurora_space` default) and trees = master (only `wct_version`), Bee 2,325/2,325 identical, knob on adds only `T_dlvtx_space` + 2 branches, doctests (root 17), 229/229 digests on master + branch.
- 2026-11-16 (`prod_polaris`): **WireCell PR #548 opened** (https://github.com/WireCell/wire-cell-toolkit/pull/548), `HaiwangYu:sbnd-dlvtx-space-pr` `db3c5ec1` on master `e7242071`: the `T_dlvtx_space` dump + the shared PR Bee scope; description from `porting_sbndbuild03/dump-pr-description-draft.md` (Haiwang's call to use the draft).
- 2026-11-16 (`prod_polaris`): tests comment on #548 (issuecomment-6926281420), then **PR #548 merged**. Master now has #544 + #547 + #548: `aurora_space` default, and the `T_dlvtx_space` dump behind `dl_vtx_dump_space`.
- 2026-11-16 (`prod_polaris`): **WCT 0.38.0 released** with `waft/release` (branch `0.38.x` = master `647b2733` + version.txt `c935e30d`; tag `0.38.0`; GitHub release marked Latest, generated notes + validation list). It contains #544, #547 and #548.
