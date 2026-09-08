# Issue 22 — merge `origin/apply-pointcloud` (master+1) into `ap-yuhw`

**Status: CONFIG COMPLETE, GATE AT 0. NOT YET BUILT.**

The build is *not* blocked by a cvmfs regression — that diagnosis was mine and
it was wrong; see §Update 2026-09-02b. The correct external-fmt spdlog + fmt
pair is on cvmfs and verified working. What remains is a clean reconfigure and
build, then validation. The §Build blocker section below is kept for the record
but **its conclusion is superseded**.

## OPEN ITEMS — dropped features (deal with later)

**Six features dropped, all fixed in the working tree, none committed.**

> **OWNER DECISION 2026-09-02: DEFERRED — do not pursue.** These are debugging
> options, not production requirements. The fixes are already applied and
> verified in the working tree and are left in place; no further work on them.
> Focus moved to reproducing Xin's 2-step results exactly.
>
> One caveat kept on the record: **`rse_from_metadata` is not a debugging
> option.** It is what carries run/subrun into `Trun`; without it every output
> is labelled `0/0/<evt>` (the issue-13 G3 bug) and the harness renames files
> from a wrong RSE. It affects labelling, not physics — Xin's standalone chain
> gets RSE from its own TLAs, which is why the compiled-config diff against his
> chain is zero either way. Keep it on.
>
> The other five are Bee-output plumbing only: shared-zip layer naming
> (`clustering-pr`), the dead-area writer gate, and the three mc.json summary
> keys. They do not affect `tracking-pr.root`, which is what the 2-step
> comparison measures — consistent with the 10/10 exact match having passed
> while all six were broken.

The master merge silently dropped SBND features from `cfg/`. Two rounds found
three plus one; **all four are fixed in the working tree, none are committed.**

### Fixed, verified, awaiting commit

| # | key | where | what it does | status |
|---|---|---|---|---|
| 1 | `rse_from_metadata` | `clus.jsonnet` PR-stage MABC (`clus_pr`) | run/subrun reach `Trun`; without it `Trun` reads `0/0/<evt>` — the issue-13 G3 bug | **RESTORED**, verified `36/77/17` |
| 2 | `merge_metadata_key` | `bee_pf` 'mc' block | grafts the reco flow onto the labeler truth tree | **RESTORED** |
| 3 | `merge_node_text` | `bee_pf` 'mc' block | the "reco nu …MeV" node text | **RESTORED** |
| 4 | `emit_empty` | `bee_pf` 'mc' block | always emit `mc.json`; without it the file vanishes on no-candidate events, taking the truth tree | **RESTORED**, verified `146/60/31` |

Items 2–4 are one block — commit `14f0aeeb`, the mc.json reco-neutrino summary
fix. Measured impact before the fix: `mc.json` present on **15 of 25** events
(pre-merge: 25 of 25), missing on exactly the 10 no-candidate ones. The Bee set
published 2026-09-02 (`e9fb2c4c-351f-4aee-8c13-62cc0561d558`) is degraded for
those 10 events and **should be regenerated or withdrawn**.

### The nine open keys — READ, 2026-09-02. Two more regressions found

(There were nine, not eight; the earlier count was wrong.)

`local clus_pr(...)` spanned pre-merge lines 737–1790 (signature) with one call
site at 3570; upstream inlined it. Classifying every lost occurrence as
signature / call-expression / body:

| key | pre | sig | call | body | merged | verdict |
|---|---|---|---|---|---|---|
| `dump` | 21 | 1 | 2 | 18 | 18 | accounted for by inlining |
| `pos_offset_on` | 38 | 1 | 2 | 35 | 35 | accounted for |
| `rse_from_ident` | 20 | 1 | 2 | 17 | 17 | accounted for |
| `rse_from_metadata` | 20 | 1 | 2 | 17 | 17 | accounted for |
| `tensor_outname` | 14 | 1 | 2 | 11 | 11 | accounted for |
| `output_dir` | 26 | 1 | 2 | 23 | 17 | rest are signatures that gained params — constructs verified present |
| `pipeline_names` | 20 | 1 | 2 | 17 | 16 | same |
| `bee_sink` | 38 | 1 | 2 | 35 | 31 | same |
| `clustering` | 8 | 0 | 0 | 8 | 7 | **REGRESSION — see 5 below** |

Constructs then checked individually in the merged file rather than by count:
`mabc-pr.zip`, `tracking_pr_root`, `tracking-stm.root`, `nue_bdt_scorer` gate,
`mabc-all-apa.zip`, sink-append — all present. **One was not:**

### 5. `clustering-pr` layer rename — LOST, now RESTORED

    pre : name: if bee_sink == null then 'clustering' else 'clustering-pr',
    post: name: 'clustering',

Issue-13 G4: when the PR MABC writes into another node's sink, its clustering
layer must be renamed or it collides with the one `clus_all_apa` already wrote
into the same zip.

### 6. `save_deadarea` gate — LOST, now RESTORED

    pre  (PR node): save_deadarea: bee_sink == null,
    post (PR node): save_deadarea: true,

Only one node may write dead area into a shared zip. **The site count for this
key was 3 → 3, so the count-based check called it "ok" — the VALUE changed, not
the count.** Counting sites catches deletions, never substitutions.

### Measured in the published Bee set (25 events)

| layer | pre-merge | post-merge |
|---|---|---|
| `clustering-global` | 25 | **50** (duplicated) |
| `clustering-pr-global` | 25 | **0** (gone) |
| `channel-deadarea-apa0-face0` | 25 | **50** |
| `channel-deadarea-apa1-face0` | 25 | **50** |
| `mc` | 25 | **15** |

After restoring both, on 2 events: every layer at 2 of 2, including
`clustering-pr-global`.

So **six** SBND features were dropped by the merge in total (1 `rse_from_metadata`,
2–4 the mc.json block, 5 the layer rename, 6 the deadarea gate) — all now fixed
in the working tree, none committed.

### Still OPEN
- [ ] **Re-run the 25 events with a CONTENT check**, not a size check: per event,
      Bee zip member list + `mc.json` present/nodes/reco-nu text; `tracking-pr.root`
      tree list and entry counts; nugraph dataset names and shapes.
- [ ] **Regenerate or withdraw** the degraded Bee set above.
- [ ] Report to Xin: the `dl_weights` gate artifact, and the nine
      `TaggerCheckSTM` knobs in `ref/prod-2026-09-03` (six of which postdate our
      merge base).

### The verification method (validated, reusable)

Derive the inventory from `git diff 6bf0aafb..pre-master-merge-2026-09-02 -- cfg/`
— **5 files, 76 keys**, not the hand-written list of 8 that missed all of this —
then count code sites per key (comments stripped) pre-merge vs merged. The
extractor must catch quoted conditional keys
(`[if cond then 'key']:`), not only bare `key:`; the first version missed items
2 and 3 for exactly that reason. Validated by running it against the raw merge
tip `c1242e49b`, where it flags all four known regressions.

**Landing status: NOT READY** until the eight open keys are read and the content
check passes.

- WIP branch: `merge-master-2026-09-02` @ `c1242e49b`
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
  become "the previous chain". **DECIDED 2026-09-02: do not regenerate** — add a
  version caveat naming `ap-yuhw` `14f0aeeb2` as the producing code.
- Upstream's `event_filename()` is a cleaner fix for issue 13 **T2** than our
  per-event-cwd workaround; worth adopting after the merge lands, not during.
- The production pin has `dl_weights` **empty** while we set the SCN path — our
  DL vertexing is on and the reference's appears off. Worth asking Xin.

## Update 2026-09-02b: the build blocker was MY DIAGNOSIS, not cvmfs

**Correction.** The blocker above says the reconfigure "cannot currently
succeed" and advises asking the cvmfs maintainers which `spdlog`+`fmt` pair the
e26 profile expects. That was wrong, and it pointed the fix at the wrong people.
The correct pair is present on cvmfs and works:

| | |
|---|---|
| spdlog | `spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof` — **external-fmt build** |
| fmt | `fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof` (`libfmt.a`) |

Verified by compiling, linking and **running** a `spdlog::info()` test program
in SL7: `[info] ok`. `Spdlog.h` keys solely off `defined(SPDLOG_FMT_EXTERNAL)`,
which this configuration satisfies.

### The three real causes

1. **`v1_14_1` does have an e26 flavor.** I had looked at `v1_14_1` and seen
   only `c14-debug`; it ships c14/e26/e28 × debug/prof. The earlier claim that
   the e26-compatible spdlog is necessarily the bundled `v1_14_1b` is false —
   `v1_14_1` e26-prof is external-fmt, exactly what WCT wants.
2. **`-DSPDLOG_FMT_EXTERNAL` must be passed, and fmt's include path with it.**
   An external-fmt spdlog's `fmt/fmt.h` includes `spdlog/fmt/bundled/core.h`
   unless that macro is defined, so a bare `<spdlog/spdlog.h>` cannot compile by
   construction. wcb's check does not pass it. This is a *configure* gap, not a
   product defect.
3. **The libraries are in `lib64`, not `lib`.** My "gets the check to compile
   but not to link" conclusion was `-L…/lib -lfmt` against a directory that does
   not exist. Nothing was wrong with fmt.

So `fmt` never needed to be `setup` at all for the July build — it only needs to
be on the include and link lines. There is no cvmfs regression here and nothing
to ask anyone for.

### What is still genuinely broken

Only the build *cache*: I overwrote the known-good July `_cache.py` with a
`v1_14_1b` configure and hand-patched it afterwards. That damage stands and the
cache is not trustworthy — the fix is a **clean `./wcb configure` from scratch**
inside SL7 with the flags above, not further patching. Damaged copy remains at
`production-prep/_cache.py.bak`.

Unchanged and worth restating: **installed `opt/` libraries are untouched**
(Aug 27), so every campaign result stands, and `ap-yuhw` is untouched at
`14f0aeeb2`.

## Corrected remaining work

Items 1-3 of the previous list are **done** (config complete, generator fixed,
operating point regenerated, gate at 0). What is actually left:

1. Clean `./wcb configure` **inside SL7** (glibc-2.34 trap) with external-fmt
   spdlog + `-DSPDLOG_FMT_EXTERNAL` + `lib64` paths, then build. The merge adds
   the `mcs` subpackage (`WireCellMcs/MuonMCS.h`), which is why a reconfigure is
   needed at all.
2. Build larwirecell, hand-copy the `.so`s to `opt`.
3. **Gate on Xin's T0** against `ref/prod-2026-09-01c/prod_prjob.json` — expect
   78 → ~0.
4. Smoke 1 event; verify output filenames unchanged.
5. Re-run the 10-event 2-step exact-match check (10/10 on pre-merge sync).

### Note for any run while this issue is open

Campaign runs need **both** trees pinned pre-merge — `wire-cell-toolkit` on
`ap-yuhw` (`14f0aeeb2`) and the wcp-porting-img jsonnets at HEAD — because
`WIRECELL_PATH` reads `cfg/` out of the checkout at runtime. See issue 21 §8,
where this cost two smoke attempts.

## Plan to finish the merge (2026-09-02)

**Decision taken:** the issue-20 datasets are **not** regenerated. They get a
version caveat instead — they are "the pre-merge chain", produced by `ap-yuhw`
`14f0aeeb2`. No ~10 h regeneration.

### Step 0 — how spdlog must be handed to wcb (established, not assumed)

| fact | consequence |
|---|---|
| ambient ups spdlog is **v1_9_2**, a **bundled-fmt** build | the default environment can never satisfy `Spdlog.h`; it must be overridden explicitly |
| `spdlog/v1_14_1` e26-prof is **external-fmt**, and its `.pc` even carries `-DSPDLOG_FMT_EXTERNAL` + `Requires: fmt` | this is the right product |
| every `.pc` `prefix` is a build-machine path (`/scratch/workspace/...`) and **this pkg-config has no `--define-prefix`** | pkg-config cannot be used for these products; paths must be given explicitly |
| libraries live in **`lib64`** | `-L…/lib` finds nothing |
| wcb offers `--with-spdlog`, `--with-spdlog-include`, `--with-spdlog-lib`; **no `--with-fmt`** | spdlog goes through flags; fmt's include/lib must arrive via `CPATH`/`LIBRARY_PATH` or `CXXFLAGS`/`LINKFLAGS` |

Verified working combination (compiled, linked, ran in SL7):

    SPD=$P/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof     # external fmt
    FMT=$P/fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof        # libfmt.a

### Step 1 — clean configure inside SL7

Everything below runs inside `claude-utilities/in-gpvm-sl7.sh` after sourcing
`setup-local-opt.sh`. Building on the host links against glibc 2.34 and produces
plugins that fail to load at runtime with `__libc_single_threaded` — a runtime
failure, not a build error, so it is easy to miss.

1. `./wcb clean` and **delete `build/c4che/`** — the cache is damaged and
   hand-patched; do not try to repair it further.
2. Configure with `--prefix=/exp/sbnd/app/users/yuhw/opt`,
   `--with-spdlog-include=$SPD/include`, `--with-spdlog-lib=$SPD/lib64`,
   fmt's include/lib exported, and `REQUIRES` as recorded in the old cache
   (`jsoncpp zlib eigen3 protobuf hdf5 python3-embed fftw3f spdlog tbb grpc++`).
3. **Gate:** configure output must show spdlog resolving to `v1_14_1`, not
   `v1_9_2` or `v1_14_1b`. Check `build/c4che/_cache.py` for
   `INCLUDES_SPDLOG`/`LIBPATH_SPDLOG` before building anything.
4. **Back up the good cache immediately** to
   `production-prep/_cache.py.july-equivalent` — the omission that caused the
   damage in the first place.

### Step 2 — build

1. `./wcb -p --notests install` (the new `mcs` subpackage is why a reconfigure
   was needed at all: `clus/src/MuonMCSDriver.cxx` needs `WireCellMcs/MuonMCS.h`).
2. larwirecell in the MRB tree at `larsoft-wct036/v10_14_02/srcs/larwirecell`
   (**not** `/exp/sbnd/app/users/yuhw/larwirecell`, which is source-only), then
   hand-copy the `.so`s to `opt/larwirecell/...`.
3. Watch for the taginfo-ABI and RPATH landmines recorded in the ap-yuhw build
   notes.

### Step 3 — validate, in increasing cost

1. **T0 gate** — diff the compiled PR node against Xin's pinned
   `ref/prod-2026-09-01c/prod_prjob.json`. Expect **78 → ~0**. Prefer this over
   our self-compiled gate: it is pinned and owner-authored. A non-zero residual
   here stops everything downstream.
2. **1-event smoke** — and explicitly check output filenames are unchanged.
   `event_filename()` and `bee_zip` templating are opt-in via `%` and we
   configure plain names, so the harness should need no change; verify rather
   than assume, because a changed name silently breaks every harness mv.
3. **10-event 2-step exact match** — was 10/10 on pre-merge sync. This is the
   real acceptance test.
4. **10-event 1-step vs the 25-event set** — re-run issue 21's 25 events and
   compare against the pre-merge results now on record (byte-identical outputs
   documented there). The 10 empty-PR events are the sharpest available probe:
   if the merge changes reconstruction, it should show up there first.

### Step 4 — land

Only after step 3 passes: merge `merge-master-2026-09-02` into `ap-yuhw`, keep
the `pre-master-merge-2026-09-02` tag as the rollback point, and leave the push
for review.

### Rollback

At every point before step 4, rollback is `git checkout ap-yuhw` plus restoring
`opt/` from the Aug-27 libraries. The installed runtime is only overwritten in
step 2 — **that is the first irreversible action**, so the Aug-27 `opt/lib`
and `opt/larwirecell` should be copied aside before it.

### Still open (not blocking)

- `dl_weights` is **empty** in the production pin while we set the SCN path —
  their DL vertexing appears off and ours on. Ask Xin; it may explain part of
  the residual if T0 does not reach 0.
- Adopt upstream's `event_filename()` for issue 13 **T2** after landing, not
  during.

### Exact versions, confirmed from the working build

The versions are not a choice — they are readable off the Aug-27 libraries that
every campaign has been running.

**Framework side** (`setup-local-opt.sh`): sbndcode **v10_14_02_03** `-q e26:prof`,
larsoft **v10_14_02_02**, root **v6_28_12** (root must be pinned *before*
`setup sbndcode`, or the dependency line changes and the setup dies on a version
conflict). larwirecell **v10_01_28**, hand-installed under `opt`.

**What WCT needs:**

| product | version / flavor | how it is used |
|---|---|---|
| spdlog | **v1_14_1**, `Linux64bit+3.10-2.17-e26-prof` — the **external-fmt** build | runtime shared lib |
| fmt | **v11_0_2**, `Linux64bit+3.10-2.17-e26-prof` (`libfmt.a`) | **build time only** |

Evidence, from `readelf -d` on the installed `libWireCellUtil.so` and
`libWireCellClus.so`:

    NEEDED   libspdlog.so.1.14
    RUNPATH  .../spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/lib64

**fmt is static.** No WCT library has a `NEEDED` entry for fmt, because
`fmt/v11_0_2` ships only `libfmt.a`. This corrects the earlier speculation that
"the July configure found fmt by some route the environment no longer provides":
there is no route to lose. fmt only ever needed to be on the include and link
lines, which is exactly why `setup-local-opt.sh` never sets it up.

**Coexistence is fine.** The ups environment activates spdlog **v1_9_2**
(bundled-fmt, `SONAME libspdlog.so.1`) as a framework dependency, while WCT
needs `SONAME libspdlog.so.1.14`. Different sonames, and nothing under
`art/v3_14_04` references spdlog at all, so the two do not collide in one `lar`
process and overriding spdlog for the WCT build only is safe.

**Trap — `v1_14_1` and `v1_14_1b` share a SONAME.** Both are
`libspdlog.so.1.14`, and they differ *only* in bundled vs external fmt. So a
build accidentally configured against `v1_14_1b` still satisfies its runtime
soname from whichever copy the RPATH names — there is no loader error to reveal
the mix-up. `v1_14_1b` is rejected at *compile* time by `Spdlog.h`'s `#error`,
which is the only place the difference is visible. Always check
`INCLUDES_SPDLOG` in `_cache.py` names `v1_14_1`, not `v1_14_1b`.

### Can the ambient `spdlog/v1_9_2` be used with external fmt? No.

Worth closing off, since v1_9_2 is what the environment already activates and
using it would avoid an override. It cannot work, for three independent reasons.

1. **Compile-time API mismatch — fails before ABI even matters.** spdlog 1.9.2's
   headers are written against the fmt **8.x** API. Forcing
   `-DSPDLOG_FMT_EXTERNAL` with `fmt/v11_0_2` breaks inside spdlog's own
   `common.h`:

       common.h:127: error: 'basic_runtime' is not a member of 'fmt'
       common.h:137: error: incomplete type 'spdlog::is_convertible_to_basic_format_string<...>'

2. **ABI mismatch, if it had compiled.** v1_9_2 is a `SPDLOG_COMPILED_LIB`
   build with its bundled fmt **8.0.1** (`FMT_VERSION 80001`) linked in:
   `libspdlog.so.1.9.2` exports **481 `fmt::v8` symbols**. External fmt 11.0.2
   provides `fmt::v11` (612 symbols). Different inline namespaces mean different
   mangled names — undefined references at best.

3. **It is declared bundled.** Its `.pc` carries `-DFMT_SHARED
   -DSPDLOG_COMPILED_LIB` with an empty `Requires:`, i.e. explicitly the
   bundled-fmt build — which `Spdlog.h` rejects with `#error WCT requires SPDLOG
   to be compiled against external fmtlib`.

There is also no fmt 8.x on cvmfs (only `fmt/v11_0_2`), so no compatible
external fmt exists for v1_9_2 in the first place.

**Conclusion: `spdlog/v1_14_1` e26-prof stands** — it is already what the
working Aug-27 build links against, and its own `.pc` supplies both
`-DSPDLOG_FMT_EXTERNAL` and `Requires: fmt`. The v1_9_2 activation in the
environment is harmless (different SONAME, no runtime consumer in `lar`); it
just must not be what WCT builds against.

## Update 2026-09-02c: the actual configure options, and two corrections

### Who built `ap-yuhw`, and where its options went

**Not this session.** The installed libraries are Aug 20 / Aug 27; `ap-yuhw` was
built in earlier sessions. **The original option set is no longer recorded
anywhere**: `build/config.log` is what `docs/0-build-...md` points to for "the
full original option set", and my Sep-2 01:04 configure overwrote it. That is a
second piece of the same damage, not previously noted.

### The options actually on record (Sep-2 01:04 attempt, from `config.log`)

    ./wcb configure --prefix=/exp/sbnd/app/users/yuhw/opt \
      --build-debug=-O3 -g -fno-omit-frame-pointer \
      --with-tbb=…/tbb/v2021_9_0/…-e26 \
      --with-jsoncpp=…/jsoncpp/v1_9_5a/…-e26-prof \
      --with-jsonnet-include=…/gojsonnet/v0_18_0/…/include \
      --with-jsonnet-lib=…/gojsonnet/v0_18_0/…/lib \
      --with-eigen-include=…/eigen/v23_08_01_66e8f/include/eigen3/ \
      --with-root=…/root/v6_28_12/…-e26-p3915-prof \
      --with-fftw{,-include,-lib}=…/fftw/v3_3_10/… \
      --with-fftwthreads=…/fftw/v3_3_10/… \
      --boost-includes=…/boost/v1_82_0/…-e26-prof/include --boost-libs=…/lib --boost-mt \
      --with-hdf5=…/hdf5/v1_12_2a/…-e26-prof \
      --with-spdlog-include=…/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/include \
      --with-spdlog-lib=…/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/lib64 \
      --with-protobuf-{include,lib}=…/protobuf/v3_21_12a/…-e26/… \
      --with-grpc{,-include,-lib}=…/grpc/v1_35_0c/…-e26/… \
      --with-triton-{include,lib}=…/triton/v2_25_0d/…-e26/… \
      --with-libtorch=…/libtorch/v2_1_1b/…-e26/ \
      --with-libtorch-include=…/include,…/include/torch/csrc/api/include \
      --with-libtorch-libs torch,torch_cpu,c10

**spdlog and fmt specifically:**

| | |
|---|---|
| `--with-spdlog-include` | `…/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/include` |
| `--with-spdlog-lib` | `…/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/lib64` |
| fmt | **no option — wcb has none.** It reached the build only by hand-editing the cache |

### Correction 1: the two caches were reported backwards

The §Damage section says the cache was replaced by a `v1_14_1b` configure and
hand-patched "toward v1_14_1", implying the live cache is the bad one. It is the
other way round:

- **live `build/c4che/_cache.py` is the REPAIRED one** — `v1_14_1` (external
  fmt), `DEFINES = ['SPDLOG_FMT_EXTERNAL=1']`, and fmt's include/lib folded into
  `INCLUDES_SPDLOG` / `LIBPATH_SPDLOG` / `LIB_SPDLOG = ['spdlog','fmt']`.
- **`production-prep/_cache.py.bak` is the DAMAGED `v1_14_1b` copy** — so the
  "backup" is the one not to restore.

### Correction 2: the repair has a one-character bug — `lib`, not `lib64`

    LIBPATH_SPDLOG = [ …/spdlog/v1_14_1/…-e26-prof/lib64,
                       …/fmt/v11_0_2/…-e26-prof/lib ]     <-- WRONG

`fmt/v11_0_2/…-e26-prof` contains only `include` and **`lib64`**; there is no
`lib`. So `-lfmt` was searched in a directory that does not exist. This is the
same `lib` vs `lib64` slip made in the manual probe, and it is very likely the
whole of "I hand-patched that cache back toward v1_14_1; it still does not
build".

So the build may be one path away from working. **The plan does not change** —
still a clean `./wcb configure` rather than another cache edit, since a
hand-patched cache also cannot register the merge's new `mcs` subpackage, which
is what required a reconfigure in the first place. But the clean configure now
has a known-good option set to reproduce, recovered above, and the fmt paths
must read `lib64` in both places.

## Update 2026-09-02d: BUILT. WCT + larwirecell done, opt/ deployed

`opt/` was backed up in full first: `production-prep/opt-backup-2026-09-02-pre-merge-build`
(750 files, 2.6 GB, checksums verified) — the rollback point, since `install`
is the first irreversible step.

### Configure (clean, from scratch)

Script kept at `production-prep/wct-build-record-2026-09-02/configure-wct.sh`,
together with the recovered original argv and before/after caches and logs.
**Two things the first attempt got wrong:**

1. `export DEFINES=SPDLOG_FMT_EXTERNAL=1` **does not work** — waf does not read
   a `DEFINES` env var here. The failing check line carried
   `-DEIGEN_HAS_CXX11`/`-DSPDLOG_ACTIVE_LEVEL` but not ours, so spdlog's
   `fmt/fmt.h` still reached for the bundled header. It must go through
   **`CXXFLAGS="-DSPDLOG_FMT_EXTERNAL"`**, which waf's `add_os_flags` honours.
2. `Libs for SPDLOG` came out `['spdlog']` alone; fmt needs
   **`--with-spdlog-libs=spdlog,fmt`**.

Mechanism worth recording: wcb has **no `--with-fmt`**. `waft/generic.py:140,146`
splits `--with-X-include` / `--with-X-lib` on commas (and `:104` splits
`--with-X-libs`), so fmt rides *inside* the spdlog options — which is exactly how
the original two-element `INCLUDES_SPDLOG`/`LIBPATH_SPDLOG` lists arose.

**Gate: PASS**, all seven checks — spdlog is v1_14_1 (not v1_14_1b/v1_9_2);
every path exists; fmt lib path is `lib64` and holds `libfmt.a`; `LIB_SPDLOG`
includes fmt; and `SUBDIRS` has 24 entries **including `mcs`**, the subpackage
that forced the reconfigure.

### WCT build

`./wcb -p --notests install -j16` — **rc=0, 15m03s wall (206m CPU), zero errors.**

| check | result |
|---|---|
| libs installed | 19, **including the new `libWireCellMcs.so`** |
| glibc-2.34 trap | `__libc_single_threaded` undefined count = **0** in Util and Clus — correctly built inside SL7 |
| spdlog linkage | `NEEDED libspdlog.so.1.14`, `RUNPATH …/spdlog/v1_14_1/…-e26-prof/lib64` |
| fmt | **0** `NEEDED` entries — statically linked, as expected |
| `miniz.h` | survived the install; landmine did not fire |

### larwirecell build — and a notable result

Compile **succeeded** (24 `.cxx` recompiled, 5 shared libs linked), against
`-isystem /exp/…/opt/include` with **zero** stale `cvmfs wirecell/v0_32_1`
references, so `WIRECELL_FQ_DIR`/`CMAKE_PREFIX_PATH` took effect.

`make install` then failed with `MAKE_RC=2` — the **documented prefix trap**
(`CMAKE_INSTALL_PREFIX` is the read-only `/usr/local`; it dies copying
`README.md` *after* a successful compile). Libs land in
`$MRB_BUILDDIR/larwirecell/lib/` instead.

**All five rebuilt libs are byte-identical (md5) to what is already deployed in
`opt/larwirecell`** — `libWireCellLarsoft`, `libWireCellAIML`,
`libWireCellQLMatch`, `liblarwirecell_Tools_WCLS_tool`,
`liblarwirecell_LArInterface_WireCellNoiseFilter_module`.

That is a real finding, not a no-op: larwirecell genuinely recompiled against
the merged WCT headers and produced identical object code, which means **the
merge changed no header larwirecell depends on in a code-affecting way**. So no
hand-copy was needed and the failed `install` is harmless. (Had they differed,
the deploy would be the `cp` from `.../larwirecell/lib/` per the build doc.)

### State

- WCT: **merge built and installed** to `opt` from `merge-master-2026-09-02` @ `c1242e49b`
- larwirecell: rebuilt, verified equivalent, nothing to redeploy
- `ap-yuhw` still untouched at `14f0aeeb2`; rollback = restore the opt backup + `git checkout ap-yuhw`

**Next: step 3 validation** — T0 gate against `prod_prjob.json`, 1-event smoke
(checking output filenames unchanged), 10-event 2-step exact match, and the
25-event issue-21 set against its byte-identical pre-merge results.

## Update 2026-09-02e: harness check on the merged build — found the G3 bug again

Ran the img-clus-match-pr harness on the 25-event file
(`prabhjot-100file-Aug5-debug-25evt/debug-25evt-reco1.root`) against the merged
build, as a workflow check before T0.

### The 1-event smoke failed the RSE guard

    run subrun event  rc  rse_check
    0   0      17     0   MISMATCH(manifest=36/77/17)

`Trun` reported run/subrun **0** with the event number correct — the exact
issue-13 G3 signature, and exactly the regression §"A silent regression the
merge would have introduced" was written to prevent. The job returned rc=0 and
produced all three deliverables; **only the harness's Trun-vs-manifest check
caught it**, which is the whole reason that check exists.

### Root cause: the guard was right, the config was incomplete

The C++ guard is correct and does include `m_rse_from_metadata`. The defect was
in the merged `clus.jsonnet`: the **PR-stage MABC node (`clus_pr`, inside
`pr()`)** emitted

    [if rse_from_ident then 'rse_from_ident']: true,
    [if event_from_ident then 'event_from_ident']: true,
    [if event_from_ident && …rse_map…]: rse_map,

but **not** `rse_from_metadata`. `clus_per_face` (line ~385) and `clus_all_apa`
(line ~626) both had it; the third site did not. With only `rse_from_ident`, the
tensor ident supplies the EVENT while run/subrun stay 0 — so
`tracking-pr.root`'s `Trun` reports `0/0/<evt>`.

Fix: one line in the `clus_pr` node, same idiom, resolving
`rse_from_metadata` from the enclosing `function()` at line 768 exactly as
`rse_from_ident` already does (neither is a `pr()` parameter). No rebuild — the
harness reads `cfg/` from the checkout via `WIRECELL_PATH`.

After the fix: `36/77/17`, `rse_check=ok`.

### The lesson about my own verification

The merge notes claim "all eight verified present afterwards", listing
`rse_from_metadata` among them. That check asked *does the feature appear in the
file* — and it did, at two of its three sites. **Presence is not the same as
presence at every call site.** A feature threaded through N nodes needs
verifying N times. The compiled-config gate did not catch this either, because
the gate diffs against Xin's chain, whose standalone driver does not use
`rse_from_metadata` at all — so the key is legitimately absent on both sides and
the diff stays at zero.

### Output does change slightly (expected)

Event 36/77/17, pre-merge → post-merge:

| output | pre-merge | post-merge |
|---|---|---|
| bee | 6492302 | 6493006 |
| tracking-pr | 243078 | 248521 |
| nugraph | 1542012 | **1542012 (identical)** |

166 commits of upstream change, so a small delta is expected; nugraph being
byte-identical is a useful sign the labeler path is untouched.

### 25-event run on the merged build: harness works, physics stable

**25/25 ok, 1m58s wall, 16 workers.** Zero failures, zero audit failures, zero
RSE mismatches (after the `clus_pr` fix). All three deliverables for all 25.

- Bee (source-set numbering): <https://www.phy.bnl.gov/twister/bee/set/e9fb2c4c-351f-4aee-8c13-62cc0561d558/event/list/>
- nugraph sp: <https://www.phy.bnl.gov/twister/bee/set/19d48222-f533-4e8b-b13e-66cb69ab4010/event/list/>
- outputs: `chain/run-postmerge/`, pre-merge baseline in `chain/run/`

Index→RSE verified against the source set from the packed JSON payloads:
idx 5 = 827/27/4, idx 9 = 36/77/17, all 25 match.

| comparison | result |
|---|---|
| reconstructed / empty split | **15 / 10 pre-merge, 15 / 10 post-merge** |
| events whose status changed | **0** — the same ten events reconstruct nothing |
| nugraph | **25 of 25 byte-identical** |
| bee | all 25 differ slightly |
| tracking-pr | all 25 differ slightly (empties 8→12 kB, reconstructed +2-5%) |
| wall time | faster across the board, e.g. 155s→74s, 63s→43s |

Reading: the merge shifts reconstruction output a little everywhere but changes
**no event's outcome**, and leaves the nugraph path byte-identical. The ten
empty-PR events are therefore a property of the events, not of either code
version — they survived a 166-commit upstream change untouched, which makes them
a sound target for the issue-21 debugging.

The empties growing 8→12 kB while still lacking `T_rec_charge`/`T_kine`/
`T_tagger` is worth a look during that debugging: something new is being written
into the no-candidate case.

**This is not a substitute for T0.** It shows the workflow and harness still
function on the merged build and that behaviour is stable; the compiled-config
diff against the pinned production reference is still the gate that has to pass.

## Update 2026-09-02f: T0 run — 78 → 1 substantive difference

Artifacts in `production-prep/wct-build-record-2026-09-02/` (`t0-*`).

| T0 row | result |
|---|---|
| 1. Config tripwire (21 artifacts) | **NOT RUN — see below** |
| 2. Compiled PR job == production | **1 substantive difference** vs the guide's `prod-2026-09-01c` (was 78) |
| 3. 15 stages, in order | **PASS** — identical list and order to the reference |
| 4. Operating-point sentinels | **PASS**, except the `dl_weights` question |
| 5. Data files resolve | **PASS** — 0 `Persist::resolve` failures over 25 events, 36/36 BDT weights resolve |

### Row 1 could not be run, and its output was vacuous

`scripts/cfg/compile_consumers.sh` hardcodes Xin's machine throughout —
`AB/SX/QL/DATA` and `wcsonnet` all under `/nfs/data/1/xqian/…`, none of which
exist here. All five compiles returned **rc=127** and 20 of 21 artifacts came
back `MISSING`.

**Its one verdict, `DRIFT: bare_prjob.json`, is an artifact, not a finding:** the
failed compile's `>` redirect still created an empty file, whose hash naturally
differs from the reference. This is exactly the trap the guide warns about —
*"a gate that compares nothing passes; read the counts it prints, not its exit
line."* Here it did the mirror image and reported a false failure.

It is runnable with scratch copies: `abtest`, `qlport` and `wire-cell-data` all
exist locally, and `opt/bin/wcsonnet` is ours. Only the five path variables need
repointing. Not attempted yet — and per the standing rule it must be a scratch
copy, never an edit inside `sbnd_xin`.

### Row 2 detail (vs `prod-2026-09-01c`, the reference the guide names)

Excluded per T0's own rule: 9 per-event/output keys
(`runNo`/`subRunNo`/`eventNo`, `bee_zip`, `output_filename`). Excluded as
documented issue-13 design differences: 5 (`bee_sink`, `rse_from_ident`,
`rse_from_metadata`, `bee_pf`, `bee_points_sets`) plus `Pgrapher.edges` and
`wire-cell.plugins`, which differ by construction between a 1-step graph and a
standalone PR job. Two ref-only components (`TensorFileSink:clus_pr`,
`TensorFileSource:pr_pctree`) are the 2-step's pctree handoff, which the 1-step
has no use for.

**What is left is one key:**

    TaggerCheckNeutrino:pr . dl_weights
      ours = "uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth"
      ref  = ""

So the merge closed the operating-point drift. The single remainder is the
open DL-vertex question, and it is sharper than before: **T0's own sentinel row
requires `dl_weights` set, while the pinned reference has it empty.** The
checklist and the pin disagree, so this cannot be settled by reading either —
it needs Xin. Ours is the value that satisfies the written sentinel.

### Against Xin's NEWEST reference: 10 differences, but not merge drift

`ref/prod-2026-09-03` (written Sep 2 09:49, newer than the guide's) adds nine
`TaggerCheckSTM` guard knobs that we leave unset. **Six of them
(`entry_rise_guard`, `guard_entry_frac`, `guard_entry_kink_deg`,
`guard_entry_{max,min}_cm`, `guard_entry_min_len_cm`) do not exist in our C++ at
all** — they postdate our merge base (`origin/apply-pointcloud` @ `26716eb58`,
Sep 1). Three (`guard_hadron_len_cm`, `guard_hadron_mip`,
`vertex_hadron_guard`) do exist in our tree but are unset.

That is Xin having moved on after our merge, not drift the merge introduced. It
does mean the operating point will need another resync round to reach the
current production line.

### Three method errors of mine this round, all caught before reporting

1. **Compiled `reality=sim` against a data-lineage reference.** That produced a
   phantom `DetectorVolumes.pos_offset` difference (ours absent, ref
   `[0,-1.1,6.7]`). `pos_offset` is gated on `reality` exactly as the guide
   says; recompiled with `reality=data`, ours matches the reference exactly.
   **A pinned reference must be compared against a compile of the same lineage.**
2. **Wrong sentinel key names.** `beam_window_us` is really
   `beam_window_low`/`beam_window_high` (200/2200 ns = 0.2–2.2 µs) and
   `trackfitting_config` is `trackfitting_config_file`. Both match the reference;
   my first lookup reported them as null/absent.
3. **Wrong stage-name test.** Row 3's "ends `tracking_visitor, tagger_output`"
   was tested against literal stage names, but the compiled list carries
   `type:name` — the last two entries are `SbndPrMagnifyTrackingVisitor:pr` and
   `UbooneTaggerOutputVisitor:pr`, which are those stages. Row 3 passes.

Also confirmed: the internal 1-step-vs-Xin gate is still **0 differences** after
the `clus_pr` fix — and note it carries `--expected-key rse_from_metadata`,
which is structurally why it could never have caught that bug.

### RESOLVED: the `dl_weights` difference is an artifact of the reference generator

Chased into the code and the runners. The pin's empty value is not production's
value:

| site | value |
|---|---|
| `wct-pr-perevt.jsonnet:844` (entry-point TLA default) | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` |
| `clus.jsonnet:894`, and `:2175` in words | same path — *"dl_weights defaults to the uBooNE-trained SCN net = DL vertex ON"* |
| `run_pr_chain_batch.sh:267` | `SBND_NO_DL=1` forces empty, but is **UNSET BY DEFAULT** — *"this driver keeps running the DL (SCN) vertex, which is the production default"* |
| `scripts/cfg/compile_prjob_cfg.sh:19` | passes **`-A "dl_weights="` unconditionally** |

So the reference JSON is compiled with the DL vertex **off**, while production
runs it **on**. `TaggerCheckNeutrino.h:457` is explicit about what that means:
`empty = DL disabled`, and an empty path skips `Persist::resolve` entirely, so
the geometric vertex is used instead of `determine_overall_main_vertex_DL`.

The generator's own header says it mirrors "the dl_weights / save_tensors
choices `run_pr_chain_batch.sh` makes" — but the runner makes **no** dl_weights
choice by default. The generator has effectively baked in the `SBND_NO_DL=1`
*diagnostic* setting.

**Consequences:**

1. **T0 row 2 is effectively ZERO substantive differences.** Our
   `dl_weights` is the production default, character for character. The
   operating-point drift the merge set out to close is closed.
2. This is a **defect in Xin's gate**, not in our config: anyone running the
   production DL vertex will see a permanent 1-key difference against
   `prod_prjob.json`, and T0's own sentinel row ("`dl_weights` set") contradicts
   the pin it ships with. Worth reporting — either the generator should drop
   `-A dl_weights=`, or the sentinel and the pin need reconciling.
3. My earlier framing ("the single remainder is the open DL-vertex question…
   needs Xin") was **wrong about the substance**. It is not an open question
   about whether DL should be on: the code, the entry-point default and the
   runner all say on, and we are on. What needs Xin is only the gate artifact.

## Update 2026-09-02g: 10-event 2-step exact-match check — 10/10 PASS

Both chains re-run on the merged build, on the same 10 MC events as the
pre-merge validation (issue 20 §0). Work kept at
`production-prep/twostep-validation-2026-09-02-postmerge/`; scripts are issue
20's `run-twostep.sh` / `deep_compare.py`, unchanged.

Both arms clean: 1-step **10/10 rc=0**, audit ok, `rse_check` ok on all;
2-step **10/10** `tracking-pr.root`, no stage failures.

### The acceptance test

    ### Xin 2-step vs our 1-step (merged, sync)
      r713_s0_e11   IDENTICAL (147 charge pts)
      r713_s51_e3   IDENTICAL (798 charge pts)
      r713_s70_e3   IDENTICAL (161 charge pts)
      r713_s74_e3   IDENTICAL (4 charge pts)
      + 6 events with no candidate, identical
      => exact match 10/10, differ 0/10

Compared branch by branch: every `T_kine` and `T_tagger` branch hashed, and
every `T_rec_charge` point (x, y, z, q, cluster_id, flag_vertex, flag_shower).
**Same 10/10 as pre-merge** — the merge did not disturb 1-step ≡ 2-step
equivalence, and all four events that reconstruct still agree exactly.

### And the merge DID change reconstruction — both chains together

Pre-merge vs post-merge, same chain, same events:

| | |
|---|---|
| 2-step unchanged | 6 (all of them no-candidate events) |
| 2-step changed | **4 — exactly the four that reconstruct** |
| changed in | `T_kine`, `T_tagger`; `charge_hash` on 713/70/3 and 713/74/3 |

So the 166 upstream commits do move reconstruction, on every event that has a
reconstruction — and they move **both** chains identically, which is why the
cross-check still reads 10/10. That is the desired outcome: the merge changes
physics, our 1-step tracks Xin's 2-step through the change exactly.

Note the charge-point counts are unchanged from the pre-merge reference (147,
798, 161), so the shift is in fitted/derived quantities rather than in which
points are selected — consistent with the 25-event result, where the same 15/10
reconstructed/empty split survived and nugraph stayed byte-identical.

### Validation status after this

| step | result |
|---|---|
| Configure gate | PASS (7/7) |
| WCT + larwirecell build | PASS, rc=0 |
| Workflow/harness check (25 events) | PASS — and caught the `clus_pr` RSE bug |
| T0 row 2 (compiled config vs pin) | **0 substantive differences** (78 → 0) |
| T0 rows 3, 4, 5 | PASS |
| T0 row 1 (21-artifact tripwire) | still NOT RUN (needs scratch copies) |
| 10-event 2-step exact match | **10/10 PASS** |

Remaining before landing: T0 row 1, and reporting the `dl_weights` gate artifact
and the nine post-merge-base `TaggerCheckSTM` knobs to Xin.

## Update 2026-09-02h: T0 row 1 run — and it found a SECOND dropped feature

Scratch copies at `production-prep/t0-row1-scratch-2026-09-02/` (six scripts,
15 hardcoded `/nfs/data/1/xqian` paths repointed; `ref/` symlinked to
`sbnd_xin/ref` and read only; `--refresh` never used). Nothing in `sbnd_xin`
was modified.

Three setup faults had to be fixed before it compared anything: `QL` must point
at the **real** `qlport` (the scratch copy holds only the rewritten script);
`compile_ub_cfg.sh` must sit at `$QL/scripts/`; and `compile_all_cfg.sh`'s
`WCT=` is a multi-parent root (`$WCT/toolkit` → `wire-cell-toolkit`,
`$WCT/wcp-porting-img`, `$WCT/wire-cell-data`), not a single prefix.

**Result: 21/21 compile, 15 match the reference, 6 drift** —
`prod.standalone`, `sbnd_clus.json`, `sbnd_pr.json`, `sbnd_ql.json`,
`sbnd_simcheck.json`, `uboone.json`.

**`prod_prjob.json` is NOT among them** — our merged cfg tree reproduces Xin's
production PR job byte-for-byte, and it *differs from the pre-merge tree*. The
merge moved that artifact **onto** the reference. Independent confirmation of
the T0 row 2 result at the artifact level.

### Naming the drift found a regression

Compiling the same consumers from the pre-merge tag and diffing
(`cmp_consumers.sh`) isolated what the merge changed. `sbnd_pr.json` changed in
exactly one key — `bee_pf` on `clus_pr`, where pre-merge had `emit_empty: true`
and post-merge does not.

Checking all eight features **site by site** (comments stripped) rather than
merely "is the name present in the file":

| feature | pre | merged | verdict |
|---|---|---|---|
| `rse_from_metadata` | 12 | 10 (+1 restored earlier) | OK — the 2 "missing" were the inlined `clus_pr` signature and its pass-through, replaced by lexical scope |
| `bee_sink` | 24 | 17 | OK — 6 of the 7 were the same inlined-`clus_pr` sites |
| `merge_metadata_key` | 1 | **0** | **LOST** |
| `merge_node_text` | 1 | **0** | **LOST** |
| `emit_empty` | 1 | **0** | **LOST** |
| `pre_mabc`, `save_deadarea`, `opflash_time` | — | — | OK |

All three lost keys are in **one** `bee_pf` 'mc' block — which is commit
`14f0aeeb`, **the mc.json reco-neutrino summary fix the owner reported and asked
for**. The merge dropped it whole.

### Measured impact — it was live in today's published Bee set

| run | zips | with `mc.json` | with "reco nu" |
|---|---|---|---|
| pre-merge | 25 | **25** | 15 |
| post-merge | 25 | **15** | 15 |

`mc.json` vanished on **exactly the 10 no-candidate events**, taking the truth
tree with it — precisely what the pre-merge comment warned `emit_empty` existed
to prevent. **The post-merge Bee set published earlier today
(`e9fb2c4c-351f-4aee-8c13-62cc0561d558`) is degraded for those 10 events.**

Restored all three keys; re-ran one reconstructing and one no-candidate event:

    r146_s60_e31   mc.json PRESENT (4011 B)  reco-nu text: False   <- was MISSING
    r36_s77_e17    mc.json PRESENT (4674 B)  reco-nu text: True

### Why every earlier gate missed it

- **T0 row 2 and the 10/10 2-step check**: `merge_metadata_key` and
  `merge_node_text` are gated on `bee_sink != null`, which only our 1-step sets,
  and neither check inspects Bee zips at all.
- **The internal 1-step-vs-Xin gate**: carries `--expected-key bee_pf`.
- **The 25-event harness check**: I compared output *sizes*, not content. The
  Bee zips were the right size and the wrong contents.

This is the second feature the merge dropped and my "all eight verified present"
claim missed. That claim was wrong twice, for the same reason both times:
**counting whether a name appears in the file is not verification.** The
site-by-site table above is what verification looks like, and it should be
re-run — mechanically — before this merge lands.

**Landing status: NOT READY.** Two regressions found only by running real events
and reading real outputs. Before landing, re-derive the full feature inventory
from `git diff pre-master-merge..ap-yuhw -- cfg/` and check each site, and
re-run the 25 events with a Bee **content** check, not a size check.

## Update 2026-09-03: 2-step reproduction extended to 25 events — 25/25

Second sample, 2.5x the statistics. Work at
`production-prep/twostep-validation-25evt-2026-09-03/`.

| | |
|---|---|
| sample | MCP2025C FallProduction CV **v10_14_02** (the issue-21 debug set) |
| vs the 10-event check | **different sample** — that one was aurora Gen2_2026 **v10_14_02_03** |
| 1-step | 25/25 rc=0, 0 audit failures, 0 RSE mismatches |
| 2-step | 25/25 `tracking-pr.root`, no stage failures |
| **exact match** | **25 / 25, differ 0** |

Compared branch by branch: every `T_kine` and `T_tagger` branch hashed, plus
every `T_rec_charge` point. 15 events reconstruct (91–685 charge points), 10
produce no candidate; both classes agree exactly.

Running total for 1-step ≡ 2-step on the merged build: **35 / 35 events across
two samples and two reco1 versions.**

Note this passed with all six dropped features still broken at the time of the
10-event run, and with them fixed here — consistent with the owner's assessment
that they are Bee-output plumbing and do not touch `tracking-pr.root`, which is
what this comparison measures.

### T4 (shipped-fix liveness): NOT RUNNABLE here — deliberately not run

Two independent blockers:

1. `pr127_sentinels.py` reads arms laid out as
   `<arm>/pr_evt<event>/mabc-pr.zip` + `calib-pr-evt<N>.json` + `*.log`,
   which is Xin's runner layout. Ours is `evt_r<run>_s<sub>_e<evt>/`.
2. Its 52 sentinels assert on **30 named events** (37112, 47212, 52693, …).
   **None are in either validation set** (our event numbers are 2–44).

A sentinel whose event is absent reports **SKIP**, so running it as-is would
produce an all-SKIP vacuous pass — precisely the failure mode the guide warns
about ("a gate that compares nothing passes"). Making T4 meaningful requires
staging those 30 production events and running the chain on them; that is a
data-staging job, not a tooling fix.
