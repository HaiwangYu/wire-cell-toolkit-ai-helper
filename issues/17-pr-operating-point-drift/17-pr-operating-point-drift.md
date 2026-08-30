# Issue 17 — the 1-step chain does not carry the SBND PR operating point

**Status: FIXED 2026-08-29** (`wcp-porting-img` `05957e9`). Originally recorded and deliberately left unfixed; The fix changes reconstruction
output for every event, so it wants its own before/after gate rather than being
folded into other work.

Found 2026-08-21 while auditing the [issue #16](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/16)
13,213-event campaign against Xin's 2-step chain.

## The finding

Our 1-step chain (`sbnd/wcls-img-clus-matching-xin.jsonnet`) calls
`clus_maker.pr()` with **7** arguments. Xin's 2-step chain
(`cfg/pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet`) calls it with **351**.

Compiled effective difference: **160 knobs that Xin sets and we leave at
default** (179 total differences including the keys the 1-step adds on purpose).

| component | knobs Xin sets that we don't |
|---|---|
| `TaggerCheckNeutrino:pr` | **139** |
| `ClusteringProtectBundle:pr` | 5, plus `graph_name` differs |
| `CreateSteinerGraph:pr` / `:prrefresh` | 3 each |
| `ClusteringUnmergeBundle:pr` | 2 |
| `TaggerCheckTGM:pr` | 2 |
| `UbooneTaggerOutputVisitor:pr` | 2 |
| `TaggerCheckFC:pr`, `TaggerCheckSTM:pr`, `ClusteringExamineBundles:all` | 1 each |
| **total** | **160** |

The 139 on the tagger break down as 39 `shower_*`, 24 `mvga_*` (main-vertex
graph audit), **10 `kine_*`**, 4 `nu_*`, 3 `assoc_*`, 3 `main_vertex_*`,
3 `track_pid_*`, 2 `fit_*`, plus `fiducial` + `fv_tolerance` and singletons.

Full machine-generated list:
[`issues/16-mc-1000file-pr/config-diff-1step-vs-2step.md`](../16-mc-1000file-pr/config-diff-1step-vs-2step.md).
Raw audit output as of discovery: [`audit-2026-08-21.txt`](audit-2026-08-21.txt).

## What is *not* wrong

Worth stating, because it narrows the fix to one file:

- **Both chains compile the same clus jsonnets.** `sbnd_xin/clus.jsonnet` is a
  10-line re-export of `pgrapher/experiment/sbnd/clus.jsonnet`;
  `sbnd_xin/wct-pr-perevt.jsonnet` is a one-line re-export of the in-tree
  module; `cfg/pgrapher/common/clus.jsonnet` is imported from exactly one place.
  No divergence is possible in either clus jsonnet.
- **The clustering half matches.** `apa0-0`, `apa1-0` and `clus_all_apa` differ
  only in keys added deliberately for the 1-step (`bee_sink`,
  `rse_from_ident`, `rse_from_metadata`, `save_deadarea=false` for the G4
  shared-Bee-zip dead-area guard). Xin additionally sets
  `bee_flash_pred_min: 0`.
- **The PR pipeline matches** — same 15 stages, same order.

So this is one gap, in one place: the PR operating point.

## Where the operating point lives

| layer | location |
|---|---|
| **TLA declarations + production values** | `cfg/pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet` **lines 43–2320** — one `function(...)` with **351** parameters |
| **forwarding to clus.jsonnet** | same file, **lines 2353–2709** (`clus_maker.pr(anodes, dump=true, …)`) |
| **the shim Xin invokes** | `sbnd/sbnd_xin/wct-pr-perevt.jsonnet` — one-line re-export; TLAs bind through unchanged |
| **runtime overrides** | `sbnd/sbnd_xin/run_pr_chain_batch.sh` + `_isolated72/75/75base` variants; almost all gated on `SBND_*` env vars, so with none set the signature defaults *are* the operating point |
| **conservative counterparts** | `cfg/pgrapher/experiment/sbnd/clus.jsonnet` — `clus_pr()` at line 737, `pr()` at 2966, dispatch at 3570 |

Sample knobs, to show the pairing:

| knob | wct-pr-perevt.jsonnet | clus.jsonnet |
|---|---|---|
| `fit_exclusion` | `true` (:196) | `false` (:1099) |
| `iso_endpoint` | `true` (:410) | `false` (:1153) |
| `neutrino_type_bitmask` | `true` (:1108) | `false` (:1297) |
| `nu_per_bundle` | `true` (:1123) | `false` (:1301) |
| `shower_bragg_protect_start_segment` | `true` (:1569) | `false` (:1446) |
| `kine_mass_rules` | `true` (:1658) | `false` (:1466) |
| `mvga_satellite` | `3.0` (:1917) | `null` (:1603) |

## Why it happened

Structural, and documented in the code. `wct-pr-perevt.jsonnet:568`:

> Per doc 68 the SBND operating point lives HERE only; clus.jsonnet's
> `clus_pr()`/`pr()` function defaults stay null.

That is a deliberate, reasonable design: one file owns the operating point, and
`clus.jsonnet` stays neutral so other detectors and older configs are unaffected.
The knobs are default-OFF in C++ *specifically* so config selects them.

The 1-step chain calls `clus_maker.pr()` **directly**, bypassing that file. It was
therefore never going to inherit the operating point — not through any single
mistake, but because Route A's shape excludes the only place the values live.
**Absent means pre-flip behaviour, not "same as production."**

### The process failure worth keeping

`wcls-img-clus-matching-xin.jsonnet` carries this comment:

```
// Match the SBND production operating point (apc doc pr/24 sec 16): the
// 2-step wct-pr-perevt.jsonnet sets iso_endpoint=true; mirror it here so the
// 1-step uses the same endpoint finder for the FC/containment check.
iso_endpoint=true);
```

One knob of roughly 160 was mirrored, with a comment that reads as though the
operating point had been handled. Every later reader — including the author —
took it at face value for weeks. **A comment asserting parity is not parity.
Only a compiled diff is**, which is why this issue ships the diff as a script
rather than a claim.

## Impact

Already caveated in the [dataset guide](../16-mc-1000file-pr/16-dataset-guide.md);
repeated here so this issue stands alone.

- `T_tagger` / `T_kine` in the 13,213-event dataset are **pre-flip**. The 10
  `kine_*` knobs (charge dedup/rebuild, mass rules, hadronic dQ/dx, long-muon
  mode) feed `kine_reco_Enu` directly.
- `nu_per_bundle=true` books per-bundle `T_tagger` branches in Xin's chain, so
  the dataset is **not schema-compatible** with a production 2-step `T_tagger`.
- The 45.1% candidate yield and the hand-scan false positives are **not
  production numbers**. Several missing knobs
  (`shower_bragg_protect_start_segment`, the `*_straight_guard` family,
  `shower_nv_bridge_track`) exist to suppress exactly the misclassification the
  scan found — including the w-prolonged cosmic reconstructed as a candidate
  ([issue #10](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/10)).
- 14 `pf_*` knobs are off, so the Bee `mc.json` reco tree uses pre-flip
  parentage/shower rules. Display only.
- `T_rec_charge` geometry and the nugraph inputs come from the clustering half,
  which matches, so they are least affected.
- This also answers issue #13's **T1** ("validate Route A against Xin's original
  2-step chain"): **Route A was not equivalent.**

## Fixed 2026-08-29 — gate at 0

`sbnd/pr-operating-point.jsonnet`: a **generated** wrapper around
`clus_maker.pr()` carrying **151 knobs**, imported by the 1-step chain.

### Design

- **Generated, not hand-written.** Hand-copying 351 arguments is how the drift
  happened; `scripts/gen-pr-operating-point.py` can be re-run after the owner
  flips more knobs.
- **Values from the COMPILED Xin config**, not from parsing jsonnet source. The
  call site contains expressions (`pr_y_top - 17`,
  `[t * wc.us for t in beam_window_us]`) that only resolve after compilation.
- **Names from `clus.jsonnet`'s `pr()` signature** — identity for most, unique
  suffix match for prefixed ones (`cathode_rejoin_angle` →
  `protect_cathode_rejoin_angle`).
- **Xin's file is untouched**, so his chain is unaffected and there is nothing
  to conflict on when he edits it.
- **Baseline is the BARE 1-step** (`pr()` with structural args only). Diffing
  against that rather than against the current 1-step is what keeps the file
  self-contained without dragging in component wiring.

### The gate

`compile-both.sh` now **exits 0**. The 18 remaining compiled differences are all
deliberate 1-step design — `bee_sink`, `rse_from_ident`, `rse_from_metadata`,
`save_deadarea`, `bee_points_sets`, `bee_pf`, `dump_mode` (the issue-13 G3/G4/G5
work) — and are declared as an **explicit `--expected-key` allowlist** rather
than silently tolerated, so any *new* difference still fails the gate.

### Reproducibility of the earlier campaigns

New extVar `pr_operating_point`: `sync` (default) or `preflip`.
**`preflip` reproduces the pre-fix config exactly — verified 0 compiled
differences against what issues 16 and 18 actually ran**, so those campaigns
remain reproducible. `wcls-img-clus-matching-xin-preflip.fcl` selects it.

### Three bugs caught while building it, all by the gate

1. The `pr()` argument extractor was anchored `^`, so it saw only the first name
   on lines packing several (`main_vertex_require_descriptor=false,
   main_vertex_candidate_flag=false,`) — 4 knobs silently unmapped.
2. The derived-knob map was global, but `fv_tolerance` comes from
   `stm_consistent_fv` on `TaggerCheckSTM` and `neutrino_consistent_fv` on
   `TaggerCheckNeutrino`. A global map mis-assigns it. Now keyed by
   (component type, data key).
3. Diffing against the *current* 1-step instead of a bare baseline dropped
   `iso_endpoint`, which the 1-step had been setting inline — it looked like
   "already agrees" and was skipped.

Each would have been an invisible hole in a hand-written file. All three showed
up as a non-zero gate, which is the argument for having one.

### What synchronising changes physically

A/B on the 10 events of the issue-16 pilot:

| | preflip | sync |
|---|---|---|
| candidates | 4/10 | 4/10 |
| tagger verdict flips | — | **0** |
| `kine_reco_Enu` changed | — | **3 of 4** |

`372.8 → 347.8`, `1512.2 → 1500.4`, `283.1 → 203.3` MeV (a 28% shift on the
last), with `numu_score` moving accordingly (`-1.322 → -0.563`,
`3.728 → 3.043`). The accept/reject decision is stable; the reconstructed
energy is not — as expected, since the `kine_*` family (charge dedup/rebuild,
mass rules, hadronic dQ/dx, long-muon mode) feeds `kine_reco_Enu` directly.

**Consequence for existing datasets:** issues 16 and 18 were produced preflip.
Their `T_kine`/`T_tagger` values are not what this chain now produces, and
regenerating them is the only way to make all campaigns homogeneous.

## PROCEDURE — re-syncing after the owner flips more knobs

**When:** after any `wire-cell-toolkit` pull whose log mentions
`SBND PRODUCTION ON`, or before any campaign whose numbers you intend to quote.
The owner flips knobs in `wct-pr-perevt.jsonnet` continuously; our chain does not
follow automatically, and nothing warns when it falls behind.

**One command:**

```bash
issues/17-pr-operating-point-drift/scripts/resync-operating-point.sh [workdir]
```

Run it inside SL7. It is **idempotent** — if nothing drifted, the generated file
is unchanged and the gate still exits 0.

### What it does

| step | action | what to look at |
|---|---|---|
| 1 | compile the **bare** 1-step (`pr()` with structural args only) | `drift before regeneration: N differences` — how far behind we were |
| 2 | regenerate `sbnd/pr-operating-point.jsonnet` | `unchanged`, or a diff of exactly which knobs moved |
| 3 | **GATE**: compile `sync`, diff against Xin | must print `0 differences [exit 0]` |
| 4 | compile `preflip`, confirm it still reproduces issues 16/18 | the full gap, unchanged |

**Step 3 is the acceptance test.** If it is non-zero the script aborts and says
*"Do NOT run production on this config"*. Never accept the sync on inspection of
the knob list — that is precisely what failed the first time.

### Then, before trusting new physics

```bash
scripts/ab_compare.py <preflip-run-dir> <sync-run-dir>
```

Run ~10 events each way. Expect the tagger verdict to be stable and
`kine_reco_Enu` to move; if the *verdict* flips a lot, understand why before
launching a campaign.

Commit `sbnd/pr-operating-point.jsonnet` **together with** the toolkit commit
that caused the drift, so the pair is recoverable.

### The three modes

`pr_operating_point` (fcl param / jsonnet extVar):

| value | meaning |
|---|---|
| `sync` | **default** — the SBND production operating point, via the generated file |
| `preflip` | the pre-2026-08-29 behaviour; reproduces issues 16 and 18 exactly |
| `bare` | `pr()` with structural args only. **A regeneration baseline, not a physics config** — step 1 uses it and nothing else should |

### Rules

1. **Never hand-edit `sbnd/pr-operating-point.jsonnet`.** It is generated, and
   hand-mirroring is the original bug. The header says so.
2. **Never accept a sync without the gate at 0.**
3. **Never widen the `--expected-key` allowlist** to make the gate pass. Those
   seven keys are deliberate 1-step design (issue 13 G3/G4/G5). Adding an eighth
   to silence a failure re-creates this issue in a form that looks green.

### Two bugs this procedure itself shipped with, both found by running it

Recorded because both are the same class as the original issue — a failure that
looks like success:

- The generator used `subprocess.run(capture_output=…)`, which is python 3.7+,
  while the bare SL7 container has **3.6**. It crashed — and the wrapper
  swallowed it, left the *previous* generated file in place, and printed
  **GATE PASSED**. The gate was green on stale content. The script now aborts
  on generation failure, and says why.
- The provenance header degraded to `toolkit ?` because `git` is not on PATH in
  the bare container, losing the one fact identifying which operating point the
  file represents. It now reads `.git/HEAD` directly, and refuses to write
  without it.

The signature is also located by **content, not line numbers** — `clus.jsonnet`
is edited often, and a hardcoded `NR>=2966` silently starts reading the wrong
function.

## Fix options as originally scoped (option B was taken)

**A. Factor the operating point into a shared jsonnet — recommended.** Extract
the 351 defaults from `wct-pr-perevt.jsonnet`'s signature into one importable
object, and have both entry points import it. One source of truth; a future owner
flip lands in both chains at once.
*Cost:* touching a 2743-line file that is the reference chain, so it needs a
byte-identical-compile gate for the 2-step before anything else changes.

**B. Copy the arguments into the 1-step.** Fastest, and testable immediately.
*Cost:* guarantees the same drift again on the next owner flip — copying is how
this happened. If chosen, it should be generated from `wct-pr-perevt.jsonnet`
rather than hand-written, and re-generated in CI.

**C. Route the 1-step through `wct-pr-perevt.jsonnet`.** Most faithful, but that
file builds a whole standalone graph with a `TensorFileSource`, so it would need
splitting into "operating point" and "graph" halves — which converges on A.

**A is the recommendation**, with **B acceptable as a stopgap** only if generated.

## Verification gate

`scripts/compile-both.sh` compiles both chains and diffs the component `data`
blocks; `scripts/audit-config-diff.py` does the diff and **exits non-zero on any
difference**, so it works as a CI gate.

```
./scripts/compile-both.sh /tmp/audit    # exit 0 == operating points equivalent
```

Today it reports 179 differences and exits 1. After the fix, everything except
the deliberate 1-step additions (`bee_sink`, `rse_from_*`, `save_deadarea`,
Bee set names) must be gone. **Do not accept the fix on "the knobs look right" —
accept it on this script.**

Then: re-run the issue-16 10-event pilot, hand-scan those 10 against the current
Bee sets to see which false positives the flipped knobs remove, and regenerate
the 13k.

### Two traps to preserve

1. **Compile the 2-step with the production `pipeline_names` TLA.** Its
   in-signature default (`wct-pr-perevt.jsonnet:101`) is the **10-stage**
   pre-adoption list, while every runner passes the 15-stage string. Compiling
   bare defaults reports a phantom 10-vs-15 pipeline difference. The first pass
   of this audit fell into it. Note the shim's header claims the
   `pipeline_names` default *is* the production operating point — it is not.
2. **`set -u` only after sourcing the setup scripts.** The ups/mrb setup scripts
   read unset variables; `set -u` before them kills the script silently, with
   empty output and no error. That also happened on the first run here.
