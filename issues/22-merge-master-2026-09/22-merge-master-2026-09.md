# Issue 22 — merge `origin/apply-pointcloud` (master+1) into `ap-yuhw`

**Status: CONFIG COMPLETE, GATE AT 0. BUILD BLOCKED** on a broken cvmfs
dependency that is unrelated to this merge (§Build blocker).

- WIP branch: `merge-master-2026-09-02` @ `5366483af`
- **`ap-yuhw` is untouched** at `14f0aeeb2`, also tagged `pre-master-merge-2026-09-02`
- 166 commits since the 2026-08-20 merge base; 4 conflicted files, 10 hunks

## Why merge

Xin's validation guide (`sbnd_xin/docs/92_...html`) ships a **pinned production
reference**, `ref/prod-2026-09-01c/prod_prjob.json`. Diffing our compiled PR node
against it (his T0 check) puts a number on where we stand:

| our config | keys differing from the production pin |
|---|---|
| preflip | **236** |
| sync (issue 17 fix) | **78** |

The 78 residual **is** the 166 commits of drift. That is what this merge closes.

## C++ resolution — complete

| file | resolution |
|---|---|
| both `Sbnd*MagnifyTrackingVisitor.h` | **took upstream**, dropping our `mutable` RSE members |
| both `Sbnd*MagnifyTrackingVisitor.cxx` | removed our orphaned `get_scalar` reads |
| `MultiAlgBlobClustering.cxx` | **union** — both RSE sources advertised |

Upstream now carries RSE as first-class `Ensemble` state (`rse_valid()`,
`runNo()`) and resolves a per-event triplet into `m_evt_*`. That supersedes the
scalar-PC transport we invented in issue 13 G3, so ours was deleted rather than
merged — two writers for one field is worse than either. Our **source** survives:
`rse_from_metadata` (art → `wclsTensorSetMetadataAttacher` → tensor metadata)
sits alongside upstream's `event_from_ident` + `rse_map`, which suit the
standalone driver. Xin's own guide documents our attacher as the LArSoft answer,
so both are wanted.

### A silent regression the merge would have introduced

Upstream guards the publish as:

```cpp
if (m_rse_from_ident || m_event_from_ident) { ensemble.set_rse(...); }
```

**`m_rse_from_metadata` is not in that condition.** With our 1-step config,
`set_rse()` would never fire, `rse_valid()` would stay false, `event_rse()` would
fall back to the visitors' configure-time constants, and `Trun` would report
run/subrun **0** again — exactly the G3 bug, silently, in every campaign. Added
to the guard.

This is the merge's most valuable finding so far, and nothing in the conflict
markers pointed at it: both sides' code was individually correct.

## clus.jsonnet — reconciled, method worth recording

Upstream restructured ~1100 lines in the same regions we had touched, so the
3-way markers were **mis-anchored**: one hunk showed 624 of our lines against 3
of theirs, and the "theirs" content was a `bounds:` block repeated verbatim.
Resolving those hunks as presented would have been guesswork.

Instead the file was rebuilt as **upstream's version + our 99-line feature
patch**: signature and RSE-key hunks unioned, the three large restructured
regions taken from upstream. Our 99 lines across 8 named features are far more
tractable than 1541 lines of mis-aligned conflict. All eight verified present
afterwards: `rse_from_metadata`, `bee_sink`, `pre_mabc`, `save_deadarea`,
`merge_metadata_key`, `merge_node_text`, `emit_empty`, `opflash_time`.

**Trap:** `git apply --3way` labels the sides **opposite to a merge** —
`<<<<<<< ours` is the file being applied *onto* (upstream) and `>>>>>>> theirs`
is the patch. Assuming merge semantics took our old content everywhere and
produced a syntactically invalid file. Read the labels; do not assume.

## Where it stands

| | |
|---|---|
| `wct-pr-perevt.jsonnet` (Xin step 2) | **compiles** |
| `wct-clus-matching-perevt.jsonnet` (Xin step 1) | **compiles** |
| our `wcls-img-clus-matching-xin.jsonnet` | **does not compile yet** |

Xin's entry points compiling is the meaningful signal: the merged `clus.jsonnet`
is valid and upstream's paths are intact.

Ours fails with a chain of `function has no parameter X` — our entry calls
public methods (`per_apa`, `all_apa`, `pr`) whose signatures upstream
restructured, so `pre_mabc` and `rse_from_metadata` need threading through each.
Two are done (`clus_per_face`, `clus_all_apa`, the top-level entry function,
`per_apa`); the chain is not finished.

## Update 2026-09-02: config complete, gate at 0

`merge-master-2026-09-02` @ `c1242e49b`. The compiled-config gate against Xin's
chain reports **0 differences**. All four `sync|preflip` × `sim|data`
combinations compile, as do both of Xin's entry points.

### What it took beyond the conflict resolution

- **`pr()`: `bee_sink` restored.** Upstream replaced it with a `pr_bee` on/off
  boolean, which cannot express "write into the shared zip owned by another
  node" — our G4 design. Re-added with the same idiom `clus_per_face` uses.
- **`eb_fast` / `po_fast` / `dg_fast`** set on our clustering nodes. Part of the
  production operating point, but configured on the *clustering* entry points
  rather than through `pr()`, so the generated PR operating point cannot carry
  them. **Found by the gate, not by reading.**
- **Generator: four fixes, each found by a failure**, not by inspection:
  1. new signature end anchor — upstream inlined `local clus_pr`, so the old
     `clus_pr(anodes,` terminator vanished; `)::` is the real bound
  2. **`tcn_knobs` bag** — upstream (doc 77) moved most tagger knobs off
     `pr()`'s signature into a bag handed to the component verbatim. Now split
     on the real signature, so a knob moving between the two forms is picked up
     automatically on regeneration
  3. **strip `//` comments before extracting parameter names** — `pr()`'s
     signature is 900+ lines of commented jsonnet, and prose like
     `// kink_walk_dqdx_stop / kink_break_protect = the 59335 …` matches a
     `name =` regex, producing a bogus argument and a compile error
  4. cover `SbndPrMagnifyTrackingVisitor` and both BDT scorers — omitting them
     silently left `save_in_scope` (the `T_cluster` tree) and `fast_xgb_forest`
     unset

Result: **22 named args + 212 in `tcn_knobs`**, gate 0.

## Build blocker (not caused by this merge)

The merge adds a new upstream subpackage, `mcs` (`WireCellMcs/MuonMCS.h`), which
the July-2026 build cache predates — so `clus/src/MuonMCSDriver.cxx` cannot find
its header and a reconfigure is required.

**The reconfigure cannot currently succeed**, because the cvmfs `spdlog` product
has changed since July:

- WCT's `Spdlog.h:50` requires spdlog built against **external** fmtlib.
- `spdlog/v1_14_1` (what the working config used) no longer ships
  `spdlog/fmt/bundled/core.h`, so wcb's configure check — which does **not**
  pass `-DSPDLOG_FMT_EXTERNAL` — fails to compile a bare `<spdlog/spdlog.h>`.
- `spdlog/v1_14_1b` does ship the bundled headers, but is therefore the
  *bundled-fmt* build, which WCT rejects outright with
  `#error WCT requires SPDLOG to be compiled against external fmtlib`.
- Supplying `-DSPDLOG_FMT_EXTERNAL` plus the external `fmt/v11_0_2` include and
  `-lfmt` gets the check to compile but not to link.

`fmt` is not set up by `setup-local-opt.sh` at all (`SETUP_FMT` empty, not on
`CPATH`), so the July configure found it by some route the environment no longer
provides. This is the same class as the 2026-08-11 cvmfs larcv2/root conflict.

### Damage, stated plainly

**I overwrote the working July-2026 build cache.** A configure attempt against
`v1_14_1b` succeeded and replaced `build/c4che/_cache.py`, which had been the
last known-good configuration. I then hand-patched that cache back toward
`v1_14_1`; it still does not build.

- **The installed `opt/` libraries are untouched** (Aug 27 build), so the
  runtime used by every campaign is unaffected and all existing results stand.
- Only the *build tree* is broken.
- `ap-yuhw` is untouched at `14f0aeeb2`.
- A copy of the damaged cache is at
  `production-prep/_cache.py.bak`; the original July cache was not backed up
  before the first configure — that is the mistake to avoid repeating.

### To unblock

Either get a working spdlog/fmt combination (ask whoever maintains the cvmfs
stack which `spdlog` + `fmt` pair the SBND e26 profile now expects), or
reconstruct a configure that satisfies `SPDLOG_FMT_EXTERNAL` with external fmt
linked. Only then can the merge be built, and only after that do the smoke,
the T0 gate against `prod_prjob.json`, and the 10-event 2-step check mean
anything.

## Remaining work

1. Finish threading `pre_mabc` / `rse_from_metadata` through the public methods
   until the 1-step compiles in all four `sync|preflip` × `sim|data` combinations
2. **Fix the operating-point generator**: its end anchor `clus_pr(anodes,` no
   longer exists — upstream inlined `local clus_pr` while keeping the public
   `pr()`. It fails loudly (`StopIteration`), not silently
3. Regenerate `pr-operating-point.jsonnet` — `wct-pr-perevt.jsonnet` went from
   **351 to 486 TLAs**, so ~135 new knobs including likely new
   `SBND PRODUCTION ON` flips
4. Clean rebuild **inside SL7** (the glibc-2.34 trap), then larwirecell, then
   hand-copy to `opt`
5. **Gate on Xin's T0** against `ref/prod-2026-09-01c/prod_prjob.json` — expect
   the 78 to go to ~0. Prefer this over our self-compiled gate: it is pinned and
   owner-authored
6. Smoke 1 event; **verify output filenames are unchanged** (`event_filename()`
   and `bee_zip` templating are opt-in via `%`, and we configure plain names, so
   the harness should need no change — but check, do not assume)
7. Re-run the 10-event 2-step exact-match check (was 10/10 on the pre-merge sync)

## Consequences to decide before landing

- Reconstruction output **will** change, so the five datasets in
  [#20](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/20)
  become "the previous chain": regenerate (~10 h) or add a version caveat.
- Upstream's `event_filename()` is a cleaner fix for issue 13 **T2** than our
  per-event-cwd workaround; worth adopting after the merge lands, not during.
- The production pin has `dl_weights` **empty** while we set the SCN path — our
  DL vertexing is on and the reference's appears off. Worth asking Xin.
