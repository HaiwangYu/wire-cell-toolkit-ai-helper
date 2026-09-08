# Issue 23 — 2-step validation against Xin's `ap-2026-09-05` sample

**Status: PLAN AGREED, awaiting the validation-sample details.**

Supersedes the approach in
[#22](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/22).
Issue 22's `merge-master-2026-09-02` is **not a git merge** — both its commits
are single-parent and no upstream commit is an ancestor; it is a squashed
hand-application of the upstream delta (140 files, +21123/−5163). That is why
merging new upstream onto it is *worse* than starting clean: 36 conflict
markers vs `origin/apply-pointcloud`, against 10 from `ap-yuhw`.

## The strategy

Separate the two things issue 22 conflated — **configuration** and **our code
changes** — and validate them one at a time against a sample Xin actually
produced.

### Step 1 — validate CONFIGURATION ONLY on pristine upstream

Branch `ap-2026-09-05` = `origin/master` @ `e88f364d` (2026-09-02), created
2026-09-03. **No yuhw changes on it.** Validate only the
jsonnet / fcl / PR-knob configuration against Xin's validation sample.

Because the branch is pristine, any disagreement is *ours* — a configuration
difference in how we drive the chain — and cannot be a code difference. That
is the property issue 22 never had.

### Step 2 — add our functions/fixes, re-validate

Merge the real content of `merge-master-2026-09-02` into `ap-2026-09-05` as
`ap-2026-09-05+yuhw`, then run the same validation. Any new disagreement is
attributable to our code, because step 1 already cleared the configuration.

## What upstream already gives us

`ap-2026-09-05` carries the owner flips we were otherwise going to hand-chase:

| commit | what |
|---|---|
| `ae4fbaf5` | `sep_fv_point` ON for production (doc 97, `ref/prod-2026-09-04`) |
| `0913743f` | `stm_entry_rise_guard` DEFAULT ON for SBND production |
| `ec93bf55` | `stm_vertex_hadron_guard` DEFAULT ON for SBND production |
| `6100d8f0` | cmake builds the `mcs` package, matching waf ("pre-master-merge fix") |

The first three are exactly the `TaggerCheckSTM` knobs that showed as
differences against `ref/prod-2026-09-03` in #22 — six of which did not exist
in our C++ at all. Merging upstream closes that gap at the source.

## Local state, established 2026-09-03

| item | value |
|---|---|
| `origin/master` | `e88f364d` (2026-09-02) |
| `origin/apply-pointcloud` | `ed035408` (2026-09-03) — contains **all** of master + 20 |
| `ap-2026-09-05` (new, local) | `e88f364d`, tracking `origin/master` |
| `ap-yuhw` | `14f0aeeb2`, untouched, tag `pre-master-merge-2026-09-02` |
| `merge-master-2026-09-02` | `7c61098d` — the six restored features committed to preserve state |
| `wcp-porting-img` | **257 commits behind** `origin/main` (remote `wcp-porting-validation`) |
| `sbnd_xin` | a plain directory inside `wcp-porting-img`, **not** a submodule |
| newest reference in-tree | `ref/prod-2026-09-05/` (consumers.sha256, gate308-*, prod_prjob.json) |
| products in-tree | `products/prod0901`, `prod0901b`, `prod0902` |

`ref/prod-2026-09-05` matches this branch name, so it is very likely the
operating point that goes with the validation sample.

## What is needed from the other machine

To be filled in from the Claude Code agent on the machine where Xin generated
the sample. What the validation needs:

- [ ] **Where the sample lives** — absolute path to the arm(s). Doc 92 §4.1
      names them only relatively (`work-<label>-<sample>`), rooted at
      `sbnd_xin/`, and no `work-*` directory exists in our clone.
- [ ] **Which samples/events** — nuecc48 (48), ncpi0 (19), mcp1k (1000),
      mcp2k (2000), or the 308-event gate subset?
- [ ] **The input reco1 files** — doc 92 names `input_files_reco1/…`
      relatively; are those reachable from here or do they need staging?
- [ ] **Which reference tag** — `ref/prod-2026-09-05` + `products/prod0902`,
      or something newer that arrives with the 257-commit update?
- [ ] **Stage layout** — Xin's arms are `<arm>/pr_evt<event>/…`; our harness
      writes `evt_r<run>_s<sub>_e<evt>/`. Which side adapts?
- [ ] **What counts as agreement** — byte-identity (T2) on the same stage-A
      products, or the population comparison (T3) against the committed
      score tables?

## Reusable assets already built (issue 22)

| asset | where |
|---|---|
| 1-step vs 2-step branch-by-branch comparator | `issues/20-campaign-summary/scripts/deep_compare.py` |
| one-event 3-stage 2-step runner | `issues/20-campaign-summary/scripts/run-twostep.sh` |
| per-event 1-step harness | `.../prabhjot-100file-Aug5-debug-25evt/chain/scripts/run-harness.sh` |
| compiled-config component diff | `issues/17-.../scripts/audit-config-diff.py` |
| T0 row-1 gate, paths repointed | `production-prep/t0-row1-scratch-2026-09-02/` |
| clean WCT configure (spdlog/fmt solved) | `production-prep/wct-build-record-2026-09-02/configure-wct.sh` |
| baseline to reproduce | **35/35** exact 1-step ≡ 2-step, two samples |

## Step 0 (FIRST ATTEMPT — WRONG BASE, superseded; kept for the record)

Branch `ap-2026-09-05` @ `e88f364d`, identical to `origin/master`, **no yuhw
commits in its ancestry** (verified: `ap-yuhw` is not an ancestor).

Clean configure from `production-prep/wct-build-record-2026-09-02/configure-wct.sh`
after `rm -rf build`; artefacts in `production-prep/wct-build-ap20260905/`.

**Configure gate 8/8:** spdlog `v1_14_1` external-fmt (not `v1_14_1b`/`v1_9_2`);
all four include/lib paths exist; fmt path is `lib64` holding `libfmt.a`;
`LIB_SPDLOG` includes fmt; `CXXFLAGS` carries `-DSPDLOG_FMT_EXTERNAL`; `mcs`
among 24 `SUBDIRS`; `PREFIX=/exp/sbnd/app/users/yuhw/opt`.

**Build:** `rc=0`, **13m01s** wall (181m CPU), **0 error lines**.

**Post-install gate 8/8:**

| check | result |
|---|---|
| build rc=0, no errors | ok |
| WireCell libs installed | 19 |
| `libWireCellMcs.so` present | ok |
| undefined `__libc_single_threaded` (Util, Clus) | **0** — correctly built inside SL7 |
| RUNPATH → `spdlog/v1_14_1` | ok |
| fmt statically linked (`NEEDED fmt` = 0) | ok |
| `miniz.h` in `opt/include` | ok |

`opt/` now holds the pristine-upstream build (`ap-2026-09-05 e88f364d`),
replacing the merge build. Rollback: `production-prep/opt-backup-2026-09-02-pre-merge-build`
(the pre-merge `ap-yuhw` build); the merge build is rebuildable from `7c61098d`.

**Note for step 1b onward:** `opt/larwirecell` is still the older build.
Step 1a needs only the standalone `wire-cell` binary, so it can start now;
**larwirecell must be rebuilt against this WCT before any LArSoft 1-step run**
(steps 1b / 3).

## Step 0 CORRECTED — `ap-2026-09-05` = `6365aa00`: PASS (2026-09-07)

**The first build was on the wrong base and could never have gated.** Per the
wcgpu1 review, `origin/master` `e88f364d` *predates the entire doc-99 chain* —
it is literally the parent of `dc0cc9af`. Verified locally, not taken on trust:

| check | `e88f364d` | `6365aa00` |
|---|---|---|
| files mentioning `flash_by_gid` | **0** | 14 |
| files mentioning `merge_flash_pcs` | **0** | 4 |

A binary at `e88f364d` cannot honour the two 09-05 flash knobs, so step 1a could
not have reached a gate. Also verified: `6365aa00` correctly **excludes** the two
post-pin clus commits (`19830863`, `c27ec4b1`) and the 09-06 operating-point flip
`4c84855c`; `ap-yuhw` is not an ancestor (still pristine).

Branch re-pointed to `6365aa00` (tracking `origin/apply-pointcloud`), rebuilt
from a clean configure.

**Build:** `rc=0`, 13m37s wall (187m CPU), 0 error lines.

**Gate 9/9:**

| check | result |
|---|---|
| build rc=0, no errors | ok |
| WireCell libs / `libWireCellMcs.so` | 19 / present |
| undefined `__libc_single_threaded` (Util, Clus) | **0** — SL7 build |
| RUNPATH → `spdlog/v1_14_1`, fmt static | ok |
| `miniz.h` in `opt/include` | ok |
| **`flash_by_gid` in the installed libs** | **ok** (config-key strings present) |
| **`merge_flash_pcs` in the installed libs** | **ok** |

The last two are new gate items added because of this correction: checking the
*binary* knows the config keys, not merely that the build succeeded. That is the
check whose absence let the wrong-base build look green.

### Corrections carried into the plan

- **Step 5 gate changed.** `d144fixprod` is at 09-05 **plus** the pr/144 pair
  (cut after `4c84855c`), so byte-identity against it is the wrong gate at the
  09-05 point. Use `nusel-evt<ID>.tsv` byte-identity + compiled-config diff
  against `d99r2bothpr` from
  `archive/records/campaign-close-20260904/gate-chain/` (32 M, staged).
- **`dl_weights` splits by target**: keep the SCN path when diffing against the
  golden arm's `.wct-cfg-evt<ID>.json` (verified to carry it); blank it only
  against the pin `prod_prjob.json`, which compiles with `-A dl_weights=`.
- **`pr_scores_table.py` was never missing** — it is git-tracked at
  `sbnd/sbnd_xin/pr_scores_table.py`. My earlier "not in the staged tree" search
  looked only at the staged *data* directory, which excludes tracked files.
  The full harness (`run_pr_chain_batch.sh`, `d99r3_flip_gate.sh`,
  `d97_ql_arm.sh`, `_runlib.sh`) is tracked there too, so step 1a's invocation
  is no longer a guess.
- **Do not build toolkit HEAD** for this comparison: `4c84855c` and the pr/145–147
  flips make HEAD a later operating point than `ref/prod-2026-09-05`.
## Revised plan — validate CURRENT MASTER against the 09-05 production (2026-09-07)

Owner direction: validate **current `origin/master`** against Xin's 09-05
production. We are **not** validating `apply-pointcloud` past 09-05, and **not**
following the doc-99 chain. Revised accordingly; the previous 1a/1b structure is
kept, the gates change.

### Step 0 — DONE. `ap-2026-09-05` = `origin/master` `e88f364d`

Re-fetched: master has not moved, still `e88f364d` (09-02). Branch reset to it,
pristine (`ap-yuhw` not an ancestor), rebuilt clean.

`rc=0`, 13m40s wall (186m CPU), 0 error lines. Gate 7/7: 19 WireCell libs,
`libWireCellMcs.so` present, undefined `__libc_single_threaded` = **0** in Util
and Clus (SL7 build), RUNPATH → `spdlog/v1_14_1` external-fmt, `miniz.h` present.

Recorded as **expected-absent**, not a failure: `flash_by_gid` and
`merge_flash_pcs` are 0 in the installed libs — master predates the doc-99 fixes
by design.

### The gap is exactly one key, and it is measured

Enumerating every `data` key in `ref/prod-2026-09-05/prod_prjob.json`:

> **404 distinct keys; exactly 1 is unknown to master — `flash_by_gid`.**

(`merge_flash_pcs` lives in `sbnd_ql.json`, likewise absent from master.) So the
config gap between master and the 09-05 point is not diffuse — it is those two
doc-99 knobs and nothing else.

### Which gate applies — doc 92 decides this, not preference

> "T2 applies **only when your job runs the same binary and config** on the same
> stage-A inputs (then the answer is byte-identity, and anything else is a
> finding). **T3 is the population comparison when the inputs differ.**"

Master is not at the 09-05 config point, so **byte-identity is the wrong
pass/fail gate**. T2's tooling stays, but as a *diagnostic* to localize
differences and prove they are confined to the two known paths.

### Revised gates

| step | gate |
|---|---|
| **T0** — compiled config vs `prod_prjob.json` (ours compiled with `dl_weights=`) | **exactly 1 differing key, `flash_by_gid`, and 0 others.** Any second key is a finding |
| **T0** — `prod_cfg_gate.py --ref ref/prod-2026-09-05` | 21/21, or only artifacts explained by the two doc-99 knobs, each named |
| **T1** — run integrity, 19 ncpi0 events | rc=0 19/19; 8 trees; `T_tagger`/`T_kine` exactly 1 entry; 0 `DL vertex failed`; no stray `trash-pr.tar.gz` |
| **T2** — vs `work-ncpi0-d99r3prodpr` (**diagnostic**) | differences **confined to** `T_cluster.{flash_id,flash_time_us,flash_pe}` on clusters with no valid flash, and the pctree optical datapaths. Anything outside that set is a finding, reported with the first divergent event |
| **T3** — `pr_scores_table.py` + `pr142_campaign_ab.py` vs `products/prod0902/` | **primary instrument.** Movers must be attributable to the flash paths; an unattributed mover is a finding |
| **T4** — `pr127_sentinels.py` | report PASS/FAIL/SKIP with entry names; SKIP is not a pass |

Doc 92 §4.2 already characterises the expected delta: `flash_by_gid` affects
`T_cluster` flash columns on clusters **with no valid flash**, and "no row where
a real flash exists differs anywhere." That is the exclusion set above — and it
is the guide's own statement, so we are not inventing an allowance.

### Step 1a / 1b unchanged in structure

- **1a** — Xin's stage B (`wct-pr-perevt.jsonnet`) on Xin's stage-A pctree from
  `work-ncpi0-d99r3prod/`, master binary, via the verbatim `d99r3_flip_gate.sh`
  invocation (`PR_EXTRA_TLA=<empty file>`, `PR_EXTRA_STAGES=pr_display`,
  `PR_JOBS=8`). Isolates **binary/config-point** difference with our
  configuration entirely out of the picture.
- **1b** — same pctree, our jsonnet/fcl/PR-knob configuration. Any difference
  beyond 1a's is **ours and purely configuration**.

Step 5 (308 scale) uses `d99r2bothpr` from the staged retire records rather than
`d144fixprod`, per the earlier correction — noting that at the master config
point the flash exclusions apply there too.

### Note

`opt/larwirecell` is still the Aug-20 build. 1a needs only the standalone
`wire-cell` binary and can run now; larwirecell must be rebuilt against this WCT
before any LArSoft 1-step run (1b, step 3).

## Step 0 FINAL — `ap-2026-09-05` = `94590129`: PASS (2026-09-07)

Third and final base. The pin was chosen by **measurement**, not by date:

| candidate | compiled `prod_prjob.json` vs `ref/prod-2026-09-05` |
|---|---|
| `e88f364d` (master) | differs — 1 key: `flash_by_gid` (ours absent, ref true) |
| `eb6e57f3` (adds the knob, default OFF) | differs — same 1 key |
| **`94590129`** (flips both ON for SBND) | **BYTE-IDENTICAL** |
| `5d0b4e77` (last 09-05 commit) | BYTE-IDENTICAL, but +38 more C++ commits |

`ref/prod-2026-09-05` is a **generation counter, not a date** — its README says
it was cut 2026-09-03 on the owner's word after doc 99 round 2. And **no commit
touches `cfg/pgrapher/experiment/sbnd/` between `94590129` and the last 09-05
commit**, so every commit in that window is SBND-config-equivalent. `94590129`
is therefore the tightest pin that reproduces the config point.

**Build:** `rc=0`, 12m49s wall (179m CPU), 0 error lines. **Gate 9/9**, including
the two items added after the wrong-base episode — `flash_by_gid` and
`merge_flash_pcs` present in the installed libraries, i.e. the *binary* can
honour the config it will be handed.

Live-checkout confirmation: the compiled PR config from the actual working tree
is byte-identical to `ref/prod-2026-09-05/prod_prjob.json`.

### The trade-off, recorded because no commit resolves it

`19830863` and `c27ec4b1` **are** present at `94590129` (05:30 / 05:33 vs the
05:51 flip). The wcgpu1 side recommended `6365aa00` precisely to exclude them,
but the flip is strictly downstream, so config-exactness and excluding those
commits are mutually exclusive. Five commits separate them:

    94590129 05:51  flip the doc-99 flash knobs ON for SBND production
    a2827cfc 05:39  allocation-free Grouping::test_good_point (step 4)
    fb70eb37 05:39  drop the dead knn(5) seed query (step 3)
    c27ec4b1 05:33  port doc 78's busy-gated lazy walk (step 2)
    19830863 05:30  hoist connect_graph_relaxed_strict's closest-pair walk (step 1)

All four intervening clus commits describe themselves as byte-neutral. **If step
1a diverges, they are the first suspects** — a tractable four-commit bisection.

### What the golden arm's outputs can and cannot tell us

No version string is recorded anywhere in the arm — not in
`.wct-cfg-evt<ID>.json`, the 140 kB per-event log, `stdout.log`,
`calib-pr-evt<ID>.json`, `rc.txt`, or the `mabc-pr.zip` members. So the exact
commit is **not** recoverable from the outputs. What is recoverable:

- **lower bound `>= 94590129`**: the arm's config carries `flash_by_gid = true`
  from committed defaults (it ran with plain defaults + an empty TLA file)
- **binary `>= eb6e57f3`**, measured: **1871 of 1872** rows with a valid flash
  satisfy `flash_time_us == cluster_t0_us` (99.9%); without the read fix this is
  ~50.7%
- **upper bound `< 4c84855c`**: `excl_t0_frame` and `kine_dqdx_skip_zero_dx` are
  absent from the arm's config

Since no `cfg/sbnd` commit falls inside that window, the config cannot
distinguish commits within it even in principle — which is exactly why both
`94590129` and `5d0b4e77` compile byte-identically.

**Open question for Xin:** the arm shows **1871/1872**, not 1872/1872. Commit
`eb6e57f3` claims 100.0% on this metric. One row does not satisfy the identity —
possibly the deliberate "a gid naming two flashes is REFUSED" case, but that is
unconfirmed. It is their own stated gate metric, so worth asking.
## Step 1a result — PASS on the authoritative gates; the only difference is float noise in `T_rec_charge.q` (2026-09-07)

`ap-2026-09-05` = **`94590129`**, Xin's stage B on Xin's stage-A pctree
(`work-ncpi0-d99r3prod`), 19 ncpi0 events, verbatim `d99r3_flip_gate.sh` recipe
(`PR_EXTRA_TLA=<empty file>`, `PR_EXTRA_STAGES=pr_display`, `PR_JOBS=8`).
**19/19 rc=0, BATCH_RC=0.**

| gate | result |
|---|---|
| **1. `nusel-evt<ID>.tsv` byte-identity** (authoritative) | **19 / 19 IDENTICAL**, 0 differing, 0 missing |
| merged `nusel-table.tsv` / `nusel-events.tsv` | **BYTE-IDENTICAL** |
| **2. `pr85_hash_gate.py`** member hashes, `mabc-pr.zip` + pctree | **PASS, 38 / 38 archives byte-identical**, `# missing/unpaired events: 0` |
| **3. `pr87_root_tree_diff.py`** every shared ROOT tree, NaN-aware | **differs — one branch, `T_rec_charge.q`, on all 19 events**; no trees only in A or B; every other tree and branch identical |

### The `q` difference is machine float noise, quantified

| | |
|---|---|
| rows compared | 13 682 (row counts identical on every event) |
| rows where `q` differs | 10 033 (73.3 %) |
| **max absolute `\|dq\|`** | **4.47e-09** |
| **relative `\|dq\|/\|q\|`** | **median 8.0e-16**, max 7.6e-12 |

Median 8e-16 is ~3-4 ULP of a double. This is exactly the shape your review
anticipated: *"a different OS/compiler/libm can legitimately break FP
bit-identity even for a perfect port… that is the machine-difference signal, and
T3 becomes the primary instrument rather than the fallback."*

We are on **EL9 (sbndgpvm02)** running the SL7 apptainer; the golden arm was
produced on wcgpu1.

Two things worth recording about it:

- **It is confined to `q`.** Our first hypothesis — that `q` is a `Double_t`
  while the matching branches are floats that quantise the difference away — is
  **wrong**: `chi2`, `ndf`, `pu`, `pv`, `pw`, `pt`, `reduced_chi2` and `rr` are
  all `Double_t` and match **bit-for-bit**. So it is specific to how `q` is
  produced, not to storage precision.
- **Everything that decides physics is identical.** All verdicts, scores and
  labels in `nusel-evt<ID>.tsv` are byte-identical, and so are `mabc-pr.zip` and
  the pctree. The drift never reaches a decision.

### What this settles about the pin

`94590129` includes the four clus commits doc 99 pinned its libsnap to exclude
(`19830863`, `c27ec4b1`, `fb70eb37`, `a2827cfc`) — we flagged them as the first
suspects if 1a diverged. **They are byte-neutral in practice**: everything except
ULP-level `q` reproduces exactly. That closes the provenance-gap caveat from your
earlier comment; a clean build at this pin does reproduce the arm.

### Three SL7 incompatibilities in the driver, fixed in a scratch mirror

`sbnd_xin` is untouched (`git status`: 0 modified). The mirror is 100 symlinks to
your real files plus 2 patched files; inverting the mechanical transform leaves
exactly one line, so it is *original + 2 deliberate fixes + 22 mechanical
guards*, both files passing `bash -n` under bash 4.2.

1. **`run_pr_chain_batch.sh:1848`** takes `LIBDIR` from the live `python3` but
   hardcodes `libpython3.11.so.1.0`. SL7 has python **3.9.15**
   (`libpython3.9.so.1.0`) -> `ERROR: libpython not found`. Patched to derive the
   soname from `sysconfig.get_config_var('INSTSONAME')`.
2. **`_runlib.sh:174`** uses `wait -n -p VARNAME`, which its own comment notes
   needs **bash >= 5.1**. The SL7 apptainer ships **4.2.46**, where `wait -n`
   does not exist at all, so `_pid` stayed unset and `set -u` aborted the batch.
   Patched to reap a specific pid. **Deviation to note:** slots now free in
   insertion order rather than completion order — wall clock only, per-event
   outputs are independent.
3. **22 array expansions** `"${A[@]}"`: under `set -u`, bash 4.2 treats an
   *empty* array as unset (fixed in 4.4) -> `TFJSON_TLA[@]: unbound variable`.
   Rewritten mechanically to `${A[@]+"${A[@]}"}`, preserving `set -u` for scalars.

The host bash here is 5.1.8, so these would run unpatched outside the container —
but the WCT build is SL7-only, so the container is required. If you would rather
carry these three fixes upstream in `sbnd_xin` (they are no-ops on bash >= 4.4),
say so and we will send them as a patch.

### Next

Step 1b: same pctree, our jsonnet/fcl/PR-knob configuration. Given 1a, the
baseline is now established — any difference beyond ULP-level `q` in 1b is
**ours and purely configuration**. Requires rebuilding larwirecell against this
WCT first (currently the Aug-20 build).
## Step 1b: not achievable as framed, and the PR-knob answer (option A) — 2026-09-07

### 1b cannot run on pristine upstream — our config depends on our code

Our entry jsonnet does not compile against `ap-2026-09-05` at all:

    RUNTIME ERROR: function has no parameter rse_from_metadata
      wcls-img-clus-matching-xin.jsonnet:117

Checking each parameter our config hands to `clus.jsonnet`:

| our config needs | in 09-05 upstream |
|---|---|
| `rse_from_ident`, `bee_sink` | present |
| **`rse_from_metadata`**, **`pre_mabc`**, **`emit_empty`**, **`merge_node_text`** | **absent** |

So our configuration is **not a pure config layer** on top of upstream — four of
the things it passes *are* our features. There is no intermediate state where our
config runs without our code, which means **1b (and step 3) collapse into step 2**:
they require `ap-2026-09-05+yuhw` to exist first. Worth stating plainly because the
config-then-code separation was the point of the 1a/1b split, and it only half
holds.

`larwirecell` was rebuilt against this WCT anyway (needed for step 2): 24 `.cxx`
compiled, 5 libs linked, `make install` hit the documented `/usr/local` prefix
trap after a successful compile, and all five libs are **byte-identical** to the
deployed ones — larwirecell is unaffected by the WCT change.

### The separable part: our PR knob set vs the 09-05 TLA defaults

Pure configuration, no events, no features needed. Source of truth is
`wct-pr-perevt.jsonnet`'s TLA defaults at 09-05 (**499** of them); our
`pr-operating-point.jsonnet` carries **151**, generated against toolkit
`14f0aeeb2` (Aug 27).

| class | count | meaning |
|---|---|---|
| **A'. genuinely different value** | **1** | real drift |
| A. differs only in format/units | 12 | `4` vs `4.0`, `15 * wc.cm` vs `150`, quote style — **not** drift |
| B. 09-05 value is `null` and we omit it | 151 | `null` = keep the C++ default = same as omitting — **not** drift |
| **B'. 09-05 sets a real value we do not carry** | **184** | real drift |
| C. we set something 09-05 no longer has | **0** | nothing retired under us |

The one value difference:

    sccc_max_gap    ours = 6    09-05 = 10

That is commit `49754bf8`, *"sccc_max_gap 6 -> 10 cm, restoring the pr/93 r4 fix
for 137238 (owner 2026-08-29)"* — our operating point predates it.

**So our PR-knob configuration is 185 knobs adrift from 09-05** (184 unset + 1
wrong value), with nothing retired. For scale, issue 17 originally found 160
adrift and closed it; upstream then flipped knobs continuously from Aug 28 to
Sep 3, so it has re-drifted past the original gap. That is an argument for
regenerating rather than hand-chasing: `scripts/gen-pr-operating-point.py` derives
the whole set from the tree's TLA defaults, and is the step-2 action.

### Two measurement corrections we made on ourselves

Both would have produced badly wrong headline numbers:

1. **First parse reported 36 TLA defaults and "139 knobs no longer exist".** The
   depth counter walked **raw** lines, so parentheses inside comments closed the
   `function(` signature early. Stripping comments *before* counting gives 499 and
   `C = 0`. Our 151 knobs were generated *from* this file, so "139 missing" was
   self-evidently impossible — that implausibility is what prompted the recheck.
   This is the third time comment-vs-code parsing has bitten in this file family.
2. **Raw diff said 13 value differences and 335 missing.** Normalising units and
   formats collapses 12 of the 13, and `null` entries are equivalent to omission,
   which removes 151 of the 335. Reporting 13/335 would have overstated the drift
   by an order of magnitude.

### Recommendation

Proceed to **step 2**: merge our functions into `ap-2026-09-05` as
`ap-2026-09-05+yuhw`, regenerate `pr-operating-point.jsonnet` against the 09-05
tree (closing all 185 in one scripted step), then run 1b and 3 there against the
same golden arm, with 1a's result as the baseline — any difference beyond
ULP-level `T_rec_charge.q` is then ours.
## Step 1a result: PASS on the authoritative gate, with a bounded FP-drift finding (2026-09-07)

`ap-2026-09-05` = `94590129`, built at FNAL on SL7. Xin's stage B
(`run_pr_chain_batch.sh`) run on Xin's stage-A pctree from
`work-ncpi0-d99r3prod`, 19 ncpi0 events, verbatim recipe
(`PR_EXTRA_TLA=<empty file>`, `PR_EXTRA_STAGES=pr_display`, `PR_JOBS=8`,
reality=data). **Batch: ok 19, failed 0.**

### Gates

| gate | result |
|---|---|
| **`nusel-evt<ID>.tsv` byte-identity** (authoritative) | **19 / 19 IDENTICAL** |
| compiled config vs the arm's own `.wct-cfg-evt<ID>.json` | **0 non-path differing keys** (only `inname`, `outname`, `bee_zip`, `output_filename` — all T0 exclusions, ours vs `/home/xqian`) |
| exhaustive branch census (`d99_root_branch_census.py`, no early exit) | 19 events, 152 tree instances, **24 985 branch instances**, **2** differing pairs |

### The finding: two FP branches of one tree, at machine epsilon

    UNEXPECTED  T_rec_charge:q             19 events
    UNEXPECTED  T_rec_charge:reduced_chi2  19 events

Measured, not assumed:

| | |
|---|---|
| row counts | **identical** every event (844/844, 482/482, 498/498, …) |
| `q` max relative difference | **8.1e-13** (max abs 6.5e-11 on charges ~1e3–1e4) |
| `q` rows differing | ~66 % of rows |
| **sum of `q` per event** | agrees to **1.3e-16 – 1.8e-16** — i.e. double-precision epsilon |
| `reduced_chi2` | 2436 finite rows differ, max relative **6.2e-13**; only 4 rows are NaN, so this is *not* merely the documented NaN artifact |

Both branches are products of the same dQ/dx least-squares solve, so a single
FP-ordering difference explains both. **No selection decision moves** — the
nusel tables are byte-identical, which is why the authoritative gate passes
while bit-identity does not.

This is precisely the shape wcgpu1 predicted: *"different OS/compiler/libm can
legitimately break FP bit-identity even for a perfect port… if 1a fails only in
numeric-drift shape, that is the machine-difference signal, and T3 becomes the
primary instrument rather than the fallback."* We read it that way, so **T3 is
now primary**.

It also settles the pin trade-off empirically: the four clus commits between
`6365aa00` and `94590129` (`19830863`, `c27ec4b1`, `fb70eb37`, `a2827cfc`) are
**byte-neutral in practice** — had any of them moved physics, it would not show
up as 1e-13 noise with identical row counts and byte-identical nusel tables.
The doc-99 provenance gap (a peer's then-uncommitted PDVD work in the arm's
libsnap) is likewise confirmed inert on SBND.

### Three portability blockers hit on the way — all in the runner, none in the config

The recipe could not run as-is in the FNAL SL7 apptainer. Fixed in a **scratch
copy** (`production-prep/step1a-runner-scratch/`); `sbnd_xin` was not modified.
Worth upstreaming:

1. **`run_pr_chain_batch.sh:1848` hardcodes the libpython filename.**
   `PYLIB=$(python3 -c '…LIBDIR')/libpython3.11.so.1.0` — LIBDIR comes from the
   running interpreter but the soname is fixed at 3.11. FNAL SL7 is python
   3.9.15, so it aborts with `ERROR: libpython not found: …/v3_9_15/…/libpython3.11.so.1.0`.
   Fix: derive it, `sysconfig.get_config_var('INSTSONAME')`.
2. **`_runlib.sh:_batch_reap_one` needs bash ≥ 5.1.** `wait -n -p VARNAME`; the
   SL7 container has **bash 4.2.46** (`wait -n` alone needs 4.3). `_pid` was
   never assigned and `set -u` aborted the batch:
   `_runlib.sh: line 179: _pid: unbound variable`. Fix here: reap by blocking on
   all outstanding pids (wave scheduling); accounting unchanged.
3. **Empty-array expansion under `set -u` on bash < 4.4.** `"${TFJSON_TLA[@]}"`
   with no TLA overrides — which is exactly the plain-defaults case this gate
   requires — dies with `TFJSON_TLA[@]: unbound variable` at line 1918. 25 sites
   guarded with `${A[@]+"${A[@]}"}`, identical behaviour on every bash.

The first two fail loudly. The third is the nastiest: it triggers *only* on the
no-override path, so a machine that always passes TLAs would never see it.

### Also for you

The two `PR_CFG_TREE`/`WCT_BASE` lines (56–57) hardcode
`/nfs/data/1/xqian/toolkit-dev`. Not a blocker — `PR_CFG_TREE` plus a pre-set
`WIRECELL_PATH`/`PYTHONPATH` is enough, since the script appends them and the
nonexistent paths are skipped. No copy needed for that part.

Still open from before: the arm's own gate metric reads **1871/1872** rows with
`flash_time_us == cluster_t0_us`, where `eb6e57f3` claims 100.0 %.

Next: T1 integrity on this arm, then T3 (`pr_scores_table.py` +
`pr142_campaign_ab.py` vs `products/prod0902/`) as the primary instrument, then
step 1b with our own configuration on the same pctree.
## Steps 2a / 2b on `ap-2026-09-05+yuhw` (`700226d5`): both PASS (2026-09-08)

The merge branch created on sbndgpvm02 before it crashed is a **real git merge**
(parents `94590129` + `14f0aeeb2`), tree clean. Rebuilt here on sbndbuild03:
`rc=0`, **12m54s**, 0 error lines. Its OOM there (`cc1plus` killed, 24m41s wall
vs 11m26s user) was that machine's memory, not the code.

Build gate 11/11, including that the binary knows **both** the 09-05 knobs and
our restored features: `flash_by_gid`, `merge_flash_pcs`, `rse_from_metadata`,
`emit_empty` all present in the installed libraries.

### Plan correction: 1b was impossible as written

Our entry point calls `clus(rse_from_metadata=true, ...)`
(`wcls-img-clus-matching-xin.jsonnet:117`), and `rse_from_metadata` exists in
**0** files at pristine `94590129` versus 1 at `700226d5`. So "our config on
pristine upstream" can never compile — that is exactly the
`function has no parameter rse_from_metadata` failure the other session hit. Our
features live in `clus.jsonnet`, not only in the entry file, so config is not
separable from code on the pristine tree.

Re-ordered onto the merged branch, which answers the same two questions:

- **2a** — *Xin's* entry point on the merged branch. Isolates **our code**.
- **2b** — *our* entry point on the merged branch. Isolates **our config**.

### 2a — our code is inert for Xin's path

19 ncpi0 events, same stage-A pctree, same verbatim recipe. Batch ok 19 / failed 0.

| gate | result |
|---|---|
| vs our own step-1a `nusel-evt<ID>.tsv` (same machine, only our code differs) | **19/19 byte-identical** |
| vs step-1a, exhaustive census | **0 differing pairs** of 24 985 branch instances |
| vs golden arm, `nusel-evt<ID>.tsv` | **19/19 byte-identical** |
| vs golden arm, census with `--expect T_rec_charge:q,T_rec_charge:reduced_chi2` | **VERDICT: PASS** — only those two, 19 events each |
| merged `nusel-table.tsv` / `nusel-events.tsv` vs step-1a | identical |

Zero, not "small": merging our 12 commits of SBND features into 09-05 changes
**nothing at all** when Xin's own entry point runs. Comparing 2a against our own
step-1a rather than against the arm is what makes this exact — same machine,
same compiler, same libm, so the ~1e-13 cross-machine drift is removed and
byte-identity becomes the achievable gate.

### 2b — our configuration reproduces the 09-05 production config

Our entry point compiled on `700226d5` (`reality=data`, `pr_operating_point=sync`):
222 components. Diffed against the golden arm's own `.wct-cfg-evt<ID>.json`,
all 19 events:

| class | count |
|---|---|
| per-event / path keys (`inname`, `outname`, `bee_zip`, `output_filename`, RSE, `output_dir`) | 171 — excluded by T0's own rule |
| documented 1-step design differences (issue 13 shared-Bee-zip: `bee_sink`, `bee_pf`, `bee_points_sets`, `save_deadarea`, `rse_from_*`) | 95 |
| ref-only components (the 2-step's pctree handoff + the dump stage): `TensorFileSource:pr_pctree`, `TensorFileSink:clus_pr`, `PrDisplayDump:pr` | 3 |
| **substantive differing keys** | **2 → both explained, see below** |

The two were `MultiAlgBlobClustering:clus_pr.pipeline` and
`TaggerCheckNeutrino:pr.vertex_scoreboard`. Both are the arm's
`PR_EXTRA_STAGES=pr_display` diagnostic option, not config drift:

- pipeline: ref 16 stages = our 15 **+ `PrDisplayDump:pr`**, and the shared 15
  are in **identical order**
- `vertex_scoreboard=true` is auto-set by `run_pr_chain_batch.sh:219` when
  `pr_display` is requested, and is consumed *only* by `PrDisplayDump`

So **0 substantive configuration differences**. The 15-stage production pipeline
matches exactly.

### Note on the operating point

`sbnd/pr-operating-point.jsonnet` was regenerated against `700226d5` by the
other session. Checked rather than inherited: the **only** change from the
pre-merge version is one comment line (`toolkit 5366483af` →
`toolkit 700226d53`). 23 named args and 177 `tcn_knobs` entries both before and
after — the generator produced the same operating point against the merged tree.

### Status of the whole sequence

| step | result |
|---|---|
| 0 — build `ap-2026-09-05` (`94590129`) | PASS, gate 9/9, config byte-identical to `ref/prod-2026-09-05` |
| 1a — Xin's stage B, pristine 09-05 | PASS: nusel 19/19; 2 FP branches at ≤1e-12 |
| 0' — build `ap-2026-09-05+yuhw` (`700226d5`) | PASS, gate 11/11 |
| **2a — Xin's entry, merged branch** | **PASS: 0/24 985 vs step-1a** |
| **2b — our entry, merged branch** | **PASS: 0 substantive config keys** |

Still open: T1 integrity counts on these arms, T3 population vs
`products/prod0902/` (primary instrument given the FP drift), and the arm's own
`1871/1872` flash-identity metric where `eb6e57f3` claims 100.0 %.
## T1 integrity and T3 population: both PASS (2026-09-08)

Run on both arms — `step1a` (pristine `94590129`) and `step2a`
(merged `700226d5`) — 19 ncpi0 events each.

### T1 — run integrity

| check | step1a | step2a |
|---|---|---|
| return codes (`rc=0` everywhere) | **0** files without it | **0** |
| `nusel-events.tsv` rows = N+1 | **20** | **20** |
| `DL vertex failed` in logs | **0** events | **0** |
| stray `trash-pr.tar.gz` | none | none |
| 8 trees present per event | 19/19 | 19/19 |

**One deviation, and it is not ours.** Doc 92 T1 expects `T_tagger` and `T_kine`
at exactly 1 entry. On **`pr_evt18625`** both carry **2** entries — and the
**golden arm shows exactly the same**:

    step1a   19 events: 18 ok, 1 bad [('pr_evt18625','entries',(2,2))]
    step2a   19 events: 18 ok, 1 bad [('pr_evt18625','entries',(2,2))]
    golden   19 events: 18 ok, 1 bad [('pr_evt18625','entries',(2,2))]

So our arms reproduce production faithfully; the reference itself departs from
the stated expectation on that event. Given doc 92 attributes the 1-entry rule
to the writers not being multi-event safe on one filename (doc 5 G9), a
double-append on one event looks worth a look on your side — we are not
treating it as a finding against the port.

### T3 — population comparison vs `products/prod0902/`

`pr_scores_table.py` per arm, then `pr142_campaign_ab.py` against the committed
reference table (19 rows each side, fully joined).

    4. NUSEL event_label MIGRATION
       nu-candidate -> nu-candidate    19
       nu_evaluated flips: 0

    5. MOVERS against the pre-registered thresholds
       |dEnu| > 50 MeV or > 10% | |dnumu| > 0.05 | |dnue| > 0.05 | vtx > 1 cm | any label/eval/rc change
       0 movers of 19 joined events (0.00%)

Working points: `nue>4.30103` and `nue>0.7` both **net +0** (1 pass-both, 0
either-only). Movers TSV written with **0 rows**.

This is the calibration figure you gave for identical config+binary, met
exactly — and it is the tier that matters here, since the FP drift in
`T_rec_charge:{q,reduced_chi2}` makes bit-identity the wrong pass/fail gate
across machines.

### One observation, not a gate: we are ~1.7x slower per event

| arm | core median | p90 | peak RSS median |
|---|---|---|---|
| prod0902 (wcgpu1) | 12.1 s | 21.0 | 1.20 GiB |
| step2a (sbndbuild03) | 20.2 s | 34.1 | 1.29 GiB |

Core time, not wall, so this is not our concurrency. Same 19 events, same
pctree, same 15-stage pipeline, and physics identical to 0 movers — so it is a
host/build difference (CPU, or our `-O3 -g -fno-omit-frame-pointer` build
flags), not a chain difference. Flagging it in case the production sizing
numbers in doc 92 are expected to transfer between machines; they will not at
this ratio.

### Sequence status

| step | result |
|---|---|
| 0 — build `94590129` | PASS 9/9; compiled config byte-identical to `ref/prod-2026-09-05` |
| 1a — Xin's stage B, pristine | PASS: nusel 19/19; 2 FP branches ≤1e-12 |
| 0' — build `700226d5` (merged) | PASS 11/11 |
| 2a — Xin's entry, merged | PASS: **0 of 24 985** branch instances differ vs step1a |
| 2b — our entry, merged | PASS: **0 substantive config keys** |
| **T1** | **PASS** both arms (the one 2-entry event is shared with the golden arm) |
| **T3** | **PASS: 0 movers / 19, 0 label flips** |

Remaining open item from earlier: the arm's own flash-identity metric reads
**1871/1872** where `eb6e57f3` claims 100.0 %.
## Step 3: our 1-step LArSoft chain end-to-end — 19/19 exact match, after two defects only a real run could find (2026-09-08)

**Result first: our 1-step reproduces the golden arm exactly on all 19 ncpi0
events** — every `T_kine` and `T_tagger` branch hashed, plus every
`T_rec_charge` point (319–1465 points per event):

    => exact match 19/19, differ 0/19

19/19 `rc=0`, `check-pr-run.sh` audit ok, `rse_check` ok. This is the full
LArSoft chain from `recob::Wire` — our own imaging, clustering, Q/L matching and
PR — not a stage-B replay, so it agrees with Xin's chain despite doing stage A
itself.

### Prerequisites

- **larwirecell rebuilt** against the merged WCT: compile clean (15 `.cxx`,
  5 libs). `make install` died on the read-only `/usr/local` prefix exactly as
  the build doc documents, so the libs were hand-copied from
  `$MRB_BUILDDIR/larwirecell/lib/` (deployed set backed up first). All five
  came out **byte-identical** to the Aug-20 build, i.e. the merged WCT changes
  no header larwirecell depends on.
- **Input**: `input_files_reco1/nc-sideband_filtered_frameshift.root` — 19
  events, **all 19 of the ncpi0 gate**. Note `extracted-ncpi0/` holds *dumped
  frames*, not an artROOT, so it cannot feed a LArSoft job; and
  `data_MCP2025C_reco1_frameshift_first1000ev.root` is a **dangling symlink**
  into `/nfs/data/1/yuhw/`.

### Two defects in the merge, both invisible to every static gate

**1. `pre_mabc` silently dropped in `per_apa` (rc=66, all 19 events).**

    NamedFactory: Failed to find instance "rse_apa0" of class "wclsTensorSetMetadataAttacher"

    pre-merge per_apa:  bee_sink=bee_sink, pre_mabc=pre_mabc, rse_from_ident=...
    merged    per_apa:  bee_sink=bee_sink, rse_from_ident=..., event_from_ident=...
                                           ^^^^ pre_mabc= gone from the forward

`per_apa` still *accepts* `pre_mabc`, so our call type-checks — the value just
goes nowhere and `clus_per_face` always sees `null`. The per-APA attachers were
therefore never spliced into the graph, while the fcl still lists
`wclsTensorSetMetadataAttacher:rse_apa0/1` as inputers, which LArSoft resolves
by NamedFactory at module construction. Compiled config confirmed only
`rse_all_apa`; after the fix, `['rse_all_apa','rse_apa0','rse_apa1']`.

**2. `rse_from_metadata` missing on the `clus_pr` MABC node — `Trun` = 0/0/\<evt\>
on all 19 events.** The issue-13 G3 bug, recurring: upstream restructured that
node and the merge resolution took upstream's block. Five of the six features I
had restored on the old merge branch survived this merge (the resolver kept
`ap-yuhw`'s side); this one did not, because it lives inside a block upstream
rewrote.

Note `7c61098d` — the commit carrying those six restorations — is **not** an
ancestor of `700226d5`: the merge took `ap-yuhw` (`14f0aeeb2`), not the
merge-master branch. Worth knowing when this is re-merged.

### Why the static gates could not see either

- **2b (config diff)** compares only components present on **both** sides. A
  component missing entirely from ours, and absent by design from Xin's
  standalone job, is structurally invisible. 2b reported 0 substantive keys
  while the chain could not even configure.
- **The site-count check** called `pre_mabc` "ok" (5 → 6 sites): the name
  appears *more* often after the merge. Only the single forwarding site that
  matters lost it. Same shape as `save_deadarea` (count 3 → 3, value changed).
  **Counting occurrences catches deletions; it never catches a dropped
  argument or a changed value.**

The general lesson, stated plainly: three tiers of gate passed — compiled-config
diff at 0 keys, 2a at 0 of 24 985 branch instances, T3 at 0 movers — while our
actual production workflow could not run at all. Only executing it found these.

### Sequence status

| step | result |
|---|---|
| 0 — build `94590129` | PASS; config byte-identical to `ref/prod-2026-09-05` |
| 1a — Xin's stage B, pristine | PASS: nusel 19/19; 2 FP branches ≤1e-12 |
| 0' — build `700226d5` merged | PASS 11/11 |
| 2a — Xin's entry, merged | PASS: 0 of 24 985 branch instances |
| 2b — our config, compiled | PASS: 0 substantive keys (but see the blind spot above) |
| T1 / T3 | PASS / PASS (0 movers of 19) |
| **3 — our 1-step end-to-end** | **PASS: 19/19 exact, after 2 fixes** |

Both fixes are uncommitted in the working tree, for review.
