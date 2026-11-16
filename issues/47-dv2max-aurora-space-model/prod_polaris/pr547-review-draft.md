# Draft: review of WireCell PR #547 (to post as a "Comment" review by Haiwang)

Status: **DRAFT, not posted.** The doctest line (marked TODO) waits for `porting_sbndbuild03`'s run on `c9f61962` (issue 47 comment 6904986947).

---

Thanks @dsnehadri, this is a big step: the vertex gain is real and it carries over into the chain. We validated the code of this PR on SBND, on two machines, before you opened it. Details, scripts and tables: https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/47 (§6 of the doc).

**What we tested**
- **Build:** master `7710c43b` + your `a17e6423` (this PR minus the leak-test commit `c9f61962`) + our `T_dlvtx_space` writer. One commit, `ddbc0488`, built on sbndbuild03 and on Aurora: same compiled-config md5 on both, and the same bundle as you pin here (`bundle.json` sha256 `51588842…`, read from your Polaris clone of `dsnehadri/wire-cell-data:dv2max-sbnd-aurora-space`).
- **Tests:** clus 512/512, pyutil 17/17, `test_dv2max_space.py` 20 OK. The clus/pyutil failures in your Polaris `tests.out` do not reproduce, so they come from that environment, not the code.
  - TODO (head `c9f61962`, master + this PR only): clus __/__, pyutil __/__, leak test __ of 10 runs stable.

**Results**

| check | result |
|---|---|
| in-chain space points = the training-data writer's `T_dlvtx_space` rows (input digest per call) | 229/229 calls (sbndbuild03), 5,277/5,277 (Aurora) |
| **your hold-out, in-chain on Aurora** (500 of the 2,217 hold-out units, 4,494 pass-0 calls), vs your offline re-fit predictions | < 1 cm **identical** per class: all 0.9232, νe CC 0.9557, νμ CC 0.9591, NC 0.7093; your figure's values inside every 95 % CI; picks within 0.1 cm 98.8 % (net 0 change at 1 cm) |
| **the same events for both models:** 141 independent MC events (#43's fg1 files, not in aurora-r2 training), `|final − truth|` < 1 cm | `original` 0.645, `r7_cloud` 0.837, **`aurora_space` 0.957** [0.910, 0.980]; median 0.47 → 0.33 cm; 20 events gained, 3 lost |
| data, nueCC-48 + NCπ0-19 | νe selection unchanged event by event; νμ 6 → 5 (+1 −2) |
| same data on the two machines | 68/68 calls with the same input digest; picks within 1.6e-6 cm |
| cost | DV2 call median 2.4 s vs 0.69 s (`r7_cloud`); whole step 2 +13 % CPU; median RSS +290 MB |

The 141-event row compares both models on the same events, so it answers the apples-to-apples caveat in the description. You may want to quote it there.

**Before merging**
1. **The `aurora_space` bundle needs a wire-cell-data PR (blocking).** WireCell/wire-cell-data has only `dv2max/sbnd/r7_cloud` (your #7). Your fork branch `dsnehadri/wire-cell-data:dv2max-sbnd-aurora-space` (`e3c3a6c`) has the bundle, with the `bundle.json` this PR pins and that we tested (`51588842…`), but there is no PR for it yet. This PR makes `aurora_space` the SBND default, and since #543 a missing bundle fails at configure, so the two should merge together.
2. **The `dl_vtx_dump_space` writer the README cites is not on master.** It is our `T_dlvtx_space` writer (ai-helper #44), still on our fork. We'll open it as a follow-up PR after this one, built on your `BeeClusterPoints`. It also moves the Bee clustering layer onto that helper, so the Bee display, the training-data writer and your in-chain collector use one recipe and one scope setting. Until then the Bee writer keeps its own copy of the same code. A "(follow-up PR)" note in the README would make that clear.
3. **Merge order with #544.** The two conflict on one line of `sbnd-pr-stage.jsonnet`: #544 adds `flat_tree/truth_match/blob_truth`, and you change the default bundle on the same line. Whoever merges second keeps both. #544 is reviewed and current with master, so I'd merge it first, and we can resolve the line here.

**Not blocking, for the record**
- The downstream checks (selections) are on small samples: 153 truth-labelled MC events and 67 data events. Energy and PID are not checked. Before SBND production switches to `aurora_space` I'd like one larger run, which we can do on Aurora.
- `dv2_split_move` never calls the dual-chain OFF pass, so only pass-0 inputs reach the network in the chain, as in your figure.

(The validation runs, cross-checks and this summary were done with Claude Code agents on sbndbuild03, Aurora and Polaris, and checked by a second agent at every step.)
