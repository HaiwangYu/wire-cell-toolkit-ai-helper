# Issue 24 — our 1-step chain vs Xin's 2-step, at the prod0908 production point

**Status: PLAN, awaiting review.** Nothing pushed.

Round 2 of the chain-vs-chain validation (round 1: issue 23, at prod-2026-09-05).
Driven by the updated doc 92 (694 702 bytes, 09-08) and its new epoch:

| | round 1 (issue 23) | **this round** |
|---|---|---|
| production tag | `ref/prod-2026-09-05` | **`ref/prod-2026-09-08`** |
| products | `prod0902` | **`prod0908`** |
| stage-A arm | `work-*-d97fv` / `d99r3prod` (from dumped frames) | **`work-*-d102m`** — **from the reco1 art file directly** |
| stage-B arm | `work-*-d99r3prodpr` | **`work-*-d102mpr`** |
| toolkit the samples were produced at | `94590129` (via libsnap) | **`eacacafe`** = master after the doc-102 fast-forward |
| our branch | `ap-2026-09-05+yuhw` (`609dea85`) | **`master-2026-09-08+yuhw`** (`0ad64223`) |

The change that matters most: Xin's stage A now **reads the same reco1 art file
our 1-step reads**. Round 1 compared our end-to-end against a stage A fed from
dumped frames; this round both chains start from the identical artROOT, so the
comparison is like-for-like from the first byte.

## Where the toolkit stands (done 2026-09-08)

`master-2026-09-08+yuhw` = `origin/master` `c8b2821b` + our 13 commits, as a real
merge (`0ad64223`, parents `c8b2821b` + `609dea85`). Merge base was exactly
`94590129`, because master now contains our 09-05 base. One conflict — both sides
appended a parameter to `fill_bee_points_from_cluster()` — resolved as a union
with upstream's parameter first. `clus.jsonnet` auto-merged.

Checked before committing: both 609dea85 fixes survived (pre_mabc forwarded in
per_face and per_apa; rse_from_metadata on clus_pr); 13-key feature inventory
identical to the working 09-05 tree; our entry compiles for data and sim with
all three attachers; Xin's two entry points compile.

**And the decisive one:** `c8b2821b` is `eacacafe` + 3 commits, all
build-system/gcc15 (0 touch cfg/sbnd, clus, root, match). Compiling `eacacafe`'s
cfg reproduces the shipped `prod_prjob.json` hash **exactly**
(`c754dd0e…`, verified against `consumers.sha256`), and **our merged branch
compiles `prod_prjob.json` byte-identical to that reference.** We start
config-exact to current production, with our features on top.

**Not yet built. Not yet run.**

## Inputs — all local, none depend on the copy

| sample | N | reco1 art file (ours, from sbnd-gen2-data) |
|---|---|---|
| ncpi0 | 19 | `sbnd-gen2-data/nc-sideband-lynn/filtered-reco1/nc-sideband_filtered_frameshift.root` |
| nuecc48 | 48 | `sbnd-gen2-data/nuecc-lynn/filtered-reco1/data_filtered_decoded_reco1-fe6033f3-…_eventidfiltered_frameshift.root` |
| mcp1k | 1000 (gate subset 241) | `sbnd-gen2-data/round2-patrec/data_MCP2025C_reco1_frameshift_first1000ev.root` |
| mcp2k | 2000 | `production-prep/add-frameshift-data-2nd-2k-2026-08-15/…_2nd1k_part{1,2}.root` |

These are the *same files* doc 92 §4.1 names (it points at our `/nfs/data/1/yuhw`
copies), so both sides read identical bytes.

## References — git-tracked, present

- `sbnd_xin/ref/prod-2026-09-08/`: `consumers.sha256`, `gate308-{ncpi0,nuecc48,mcp1k}.txt`
  (19 / 48 / 241), `README.md`. **No `prod_prjob.json` ships** — reproduce it from
  `eacacafe` (done; hash-verified).
- `sbnd_xin/products/prod0908/{ncpi0,nuecc48,mcp1k,mcp2k}-scores-prod0908.tsv`
- all tools (`prod_cfg_gate.py`, `pr_scores_table.py`, `pr142_campaign_ab.py`,
  `d99_root_branch_census.py`, `pr127_sentinels.py`, `run_pr_chain_batch.sh`, …)

## Waiting on the copy from wcgpu1

`/exp/sbnd/data/users/yuhw/sbnd_xin/` was emptied 13:44 for it. Needed:
`work-{ncpi0,nuecc48,mcp1k}-d102m` (stage A) and `-d102mpr` (stage B); mcp2k if
the full-3067 T3 is in scope.

## Chains to run

| id | what | isolates |
|---|---|---|
| **A** | Xin's stage B (`run_pr_chain_batch.sh`) on **his** `d102m` pctree, our binary | our merged **binary** vs his: same config, same inputs ⇒ byte-identity expected modulo the known FP drift |
| **B** | Xin's stage A + B from the reco1 file, our binary (`d102m` reproduction) | whether **imaging + Q/L** reproduce on this machine |
| **C** | **our 1-step end to end** from the same reco1 file | the deliverable: our chain vs production |

A and B use Xin's entry points and need only `wire-cell` (+ `lar` for the
stage-A dumps). C needs larwirecell rebuilt against the new WCT.

## Gates, in order — stop at the first failure

### 0. Build (SL7 only)

`configure-wct.sh` (issue 23 scripts) → `CXXFLAGS=-DSPDLOG_FMT_EXTERNAL ./wcb -p --notests install -j16`
→ larwirecell `make` (not `install`) → hand-copy → `ldd` resolves to opt.

Gate: rc=0; 19 libs incl. `libWireCellMcs.so`; undefined `__libc_single_threaded`
= 0; RUNPATH → `spdlog/v1_14_1`; `miniz.h` present; **and the binary knows the
09-08 keys** — `excl_t0_frame`, `kine_dqdx_skip_zero_dx`,
`kine_near_pointing_impact`, `long_muon_cathode_bridge_track_types` as strings in
the installed libs (the check the wrong-base build failed).

### T0. Configuration — run nothing until clean

| check | gate |
|---|---|
| `prod_cfg_gate.py --ref ref/prod-2026-09-08` | 21/21, **or** only `sbnd_clus`/`sbnd_ql`/`sbnd_simcheck` drifting, each traced to a named feature of ours (opflash_time; issue-10 NF/SP; w-gap rebase) |
| our compiled PR node vs the reproduced 09-08 `prod_prjob.json` | **0 differing keys** after T0's per-event exclusions — **already byte-identical for Xin's entry**; repeat for ours with `dl_weights=` |
| our compiled config vs the arm's own `.wct-cfg-evt<ID>.json` | 0 non-path keys, allowing the `pr_display` stage + `vertex_scoreboard` |
| 15-stage pipeline, order | identical |

### T1. Run integrity (every arm we produce)

rc=0 all; `nusel-events.tsv` = N+1; 8 trees; `T_tagger`/`T_kine` 1 entry (the
09-05 golden arm had one 2-entry event, `18625` — note whether `d102mpr` does
too); 0 `DL vertex failed`; no stray `trash-pr.tar.gz`; RSE correct in `Trun`.

### T2. Byte-identity — chain A vs `d102mpr`, on ncpi0 first

- `nusel-evt<ID>.tsv` byte-identical **19/19** — authoritative
- exhaustive census (`d99_root_branch_census.py`, no early exit): expect **only**
  `T_rec_charge:{q,reduced_chi2}` at ≤1e-12 relative (the cross-machine FP
  signature from round 1, `--expect` them explicitly); anything else is a finding
- member hashes of `mabc-pr.zip` / pctree, never archive bytes

Then **chain C vs `d102mpr`** with the same gates. A difference present in C but
absent in A is stage-A (imaging/Q/L) — chain B localizes it.

### T3. Population — primary instrument, given the FP drift

`pr_scores_table.py --root <arm> --sample s` → `pr142_campaign_ab.py` vs
`products/prod0908/`. Gate: **0 movers** for identical config+binary; any mover
must be attributable, and a label/eval/rc change is a finding.

### T4. Sentinels — report, don't gate

Only **3 of 30** sentinel events fall in the 308 gate (1 ncpi0, 2 nuecc48).
Report PASS/FAIL/SKIP by name; an all-SKIP is vacuous. Meaningful only at
mcp1k/mcp2k scale.

## Sequence

1. build `master-2026-09-08+yuhw` (WCT + larwirecell) — gate 0
2. T0 on the merged tree — the row-2 half is already done
3. **chain A** on ncpi0 (19) → T1, T2 vs `d102mpr`, T3 vs `prod0908`
4. **chain C** on ncpi0 (19) → T1, T2, T3 — the first real deliverable
5. **chain B** on ncpi0 only if C differs where A does not
6. scale C to nuecc48 (48) and the mcp1k gate subset (241) → T2 + T3
7. full mcp1k (1000) → T3 (+T4 becomes meaningful); mcp2k if arms arrive

## Reusable from round 1 (issue 23)

`configure-wct.sh`; `sl7-runner-portability.patch` (the three fixes Xin's
driver needs under bash 4.2.46 / python 3.9.15 — apply to a scratch copy again,
`sbnd_xin` stays read/run-only); the per-event harness; `deep_compare.py`; the
census invocation; and the round-1 baselines under `production-prep/step{1a,2a,3}-*`.

## Open questions

1. **Scope** — start at ncpi0 (19) and scale, or run the 308 gate from the start?
2. **Which arms are coming** — `d102m` + `d102mpr` for ncpi0/nuecc48/mcp1k? mcp2k?
3. **Chain B** — worth running proactively (it is cheap and it is the first time
   Xin's stage A and ours read the same file), or only as a diagnostic?
4. **Runtime** — round 1 measured us ~1.7x slower per event (core time) than
   wcgpu1 at identical physics. Track it this round, or ignore?
5. **T0 row-1 residual** — round 1 left `prod.standalone` / `sbnd_pr.json` /
   `uboone.json` drifting even on pristine upstream (my scratch harness). Fix
   the harness first, or accept "named drift" on those rows?
