# Issue 17 — the 1-step chain does not carry the SBND PR operating point

**Status: recorded, not fixed.** Deliberately. The fix changes reconstruction
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

## Fix options (none applied)

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
