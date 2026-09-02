# Issue 22 — merge `origin/apply-pointcloud` (master+1) into `ap-yuhw`

**Status: IN PROGRESS.** C++ side complete and reviewed; jsonnet side reconciled
but the 1-step entry config does not yet compile.

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
