# Issue 24 — our 1-step chain vs Xin's 2-step, at the prod0908 production point

**Status: PLAN v2 (revised to the owner's two purposes), build running.** Nothing pushed from the toolkit.

## The two purposes, and what each compares

| | purpose | comparison | proves |
|---|---|---|---|
| **P1** | our local binaries + cfg == Xin's | **chain B** (Xin's 2-step, our binary) vs **Xin's prod0908 output** (`work-*-d102mpr`) | same entry points, same config, same input file ⇒ any difference is the build/machine |
| **P2** | our 1-step chain == Xin's 2-step | **chain C** (our 1-step) vs **chain B** | same binary, same input ⇒ any difference is the 1-step workflow itself |

Chain B is the pivot: P1 anchors it to production, P2 measures our chain against it.
Both chains start from the **same reco1 art file** — new this epoch, since Xin's
stage A now reads reco1 directly.

## Data — what is here, what is needed

| item | status | needed for |
|---|---|---|
| **`work-*-d102mpr` — Xin's stage-B output** (`tracking-pr.root`, `nusel-evt<ID>.tsv`, `mabc-pr.zip`) | **MISSING** | **P1's reference. Required.** Both purposes compare final outputs to it |
| `work-*-d102m` — Xin's stage-A output (imaging npz + pctree), all four samples complete: 19 / 48 / 1000 / 2000 | present, 44 G | **not required** for P1 or P2. Diagnostic only: if B ≠ d102mpr, compare B's pctree to d102m to localize stage A vs stage B |
| `ref/prod-2026-09-08/prod_prjob.json` | present | T0 — **already byte-identical** to our merged branch's compile (hash `c754dd0e…`, also = my `eacacafe` reproduction) |
| `products/prod0908/*-scores-prod0908.tsv` | present (git) | T3 population — runnable **now**, without d102mpr |
| reco1 inputs (ours, `sbnd-gen2-data/`) | present | the common input of B and C |

**What was copied is the inverse of what P1 and P2 need.** Stage A (`d102m`) is the
optional diagnostic; stage B (`d102mpr`) is the required reference. Until
`d102mpr` arrives, P1/P2 can proceed only at the T3 (population) level via the
score tables, not at byte-identity.

## Toolkit

`master-2026-09-08+yuhw` (`0ad64223`) = `origin/master` `c8b2821b` + our 13 commits,
a real merge, one union-resolved conflict. `c8b2821b` = `eacacafe` (the commit
prod0908 was produced at) + 3 build-system commits touching nothing in
cfg/sbnd, clus, root, match. **We start config-exact to production, with our
features on top.** Building now (WCT → larwirecell → hand-copy), all in SL7.

## Chains

| id | what | binary | input | output compared to |
|---|---|---|---|---|
| **B** | Xin's `run_pr_chain_batch.sh` stage A+B from reco1 (his entry points, plain 09-08 defaults, `PR_EXTRA_TLA=<empty>`) | ours | reco1 art file | `d102mpr` (P1) |
| **C** | our 1-step LArSoft chain, per-event harness, `wcls-img-clus-matching-xin-data.fcl` | ours | same reco1 art file | **B** (P2), and `d102mpr` |
| A (optional) | Xin's stage B only, on **his** `d102m` pctree | ours | his pctree | `d102mpr` — isolates stage B alone; cheap pre-check while B runs |

## Gates, in order — stop at the first failure

**0. Build.** rc=0; 19 libs incl. `libWireCellMcs.so`; undefined
`__libc_single_threaded` = 0 (SL7); RUNPATH → `spdlog/v1_14_1`; `miniz.h`; and
**the binary knows the 09-08 keys** (`excl_t0_frame`, `kine_dqdx_skip_zero_dx`,
`kine_near_pointing_impact`, `long_muon_cathode_bridge_track_types` present as
strings). larwirecell: `make` not `install`, hand-copy, `ldd` → opt.

**T0. Config.** `prod_cfg_gate.py --ref ref/prod-2026-09-08`: 21/21 or only
`sbnd_clus`/`sbnd_ql`/`sbnd_simcheck` drifting, each traced to a named feature of
ours. Compiled PR node vs the pin: **done, byte-identical.** Our entry vs the
arm's `.wct-cfg-evt<ID>.json`: 0 non-path keys (allow `pr_display` +
`vertex_scoreboard`).

**T1. Integrity** (B and C): rc=0 all; `nusel-events.tsv` = N+1; 8 trees;
`T_tagger`/`T_kine` 1 entry; 0 `DL vertex failed`; no stray `trash-pr.tar.gz`;
`Trun` RSE correct.

**T2. Byte-identity** — the P1 and P2 gates proper:
- **P1: B vs `d102mpr`** — `nusel-evt<ID>.tsv` byte-identical N/N (authoritative);
  exhaustive census (`d99_root_branch_census.py`) with **only**
  `T_rec_charge:{q,reduced_chi2}` expected, at ≤1e-12 relative (the
  cross-machine FP signature measured in round 1); anything else is a finding.
- **P2: C vs B** — same two checks. Same machine, same binary ⇒ **no FP
  exclusion**: this one must be exact.

**T3. Population** — `pr_scores_table.py` → `pr142_campaign_ab.py` vs
`products/prod0908/`: **0 movers**, 0 label/eval/rc changes. Runnable before
`d102mpr` arrives; primary instrument if P1's byte-identity breaks in FP-drift shape.

**T4.** `pr127_sentinels.py` — report by name, do not gate; only 3 of 30 sentinel
events fall in the 308 gate.

## Sequence

1. build — gate 0 *(running)*
2. T0 on the merged tree
3. **chain B** on ncpi0 (19) → T1 → T3 now; T2 (P1) when `d102mpr` arrives
4. **chain C** on ncpi0 (19) → T1 → **T2 vs B (P2)** → T3
5. scale B and C to nuecc48 (48) and the mcp1k gate subset (241); then full mcp1k
6. A / stage-A pctree comparison **only if** P1 fails

## Reusable

`configure-wct.sh`; `sl7-runner-portability.patch` (Xin's driver needs it under
bash 4.2.46 / python 3.9.15 — scratch copy, `sbnd_xin` untouched); the per-event
harness; `deep_compare.py`; round-1 baselines under `production-prep/step*`.

## Open questions

1. **`d102mpr`** — can you copy it? It is the reference both purposes need. Sizes
   will be similar to `d102m`.
2. **Scope** — ncpi0 first and scale, or the 308 gate from the start?
3. **Chain A** as a cheap pre-check while B runs (his pctree is here, ~2 min for 19
   events) — yes or skip?
4. **P2 tolerance** — I have written C-vs-B as exact byte-identity (same machine,
   same binary). If our 1-step legitimately differs in a known place, say where.
