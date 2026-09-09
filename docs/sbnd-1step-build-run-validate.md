# SBND 1-step chain on sbndbuild/sbndgpvm: build, run, validate

A procedure, not a narrative. Every step names its **gate** and the **trap** it
exists to catch. Written 2026-09-09 after two validation rounds (ai-helper #23,
#24); the narrative lives in `wcp-porting-img/sbnd/docs/8-build-and-run-both-chains.md`.

**Everything builds and runs inside the SL7 apptainer.** Use
`/exp/sbnd/app/users/yuhw/claude-utilities/in-gpvm-sl7.sh <cmd>`; it sources
`sbnd/setup-local-opt.sh` by default (`SL7_SETUP=<path>` to override, `none` for a
bare container). A host build links glibc 2.34 and fails at plugin *load*, not at
build — there is no error until you run.

Machines: sbndbuild03 (64 cores, 125 GB) is the workhorse; gpvm nodes are shared
and smaller. Container facts that break scripts written for a newer host:
**bash 4.2.46** (no `wait -n`; `"${ARR[@]}"` on an empty array trips `set -u`),
**python 3.9.15**.

---

## 0. Before touching anything: which tree runs?

`setup-ap.sh` **prepends the wire-cell-toolkit checkout's `cfg/`** to
`WIRECELL_PATH`. A `git checkout` in that repo silently changes what every `lar`
and `wire-cell` job runs, with nothing rebuilt. Seen twice: `unknown graph flavor
relaxed_fast`, `function has no parameter assoc_clear_on_merge` — config from one
branch meeting binaries from another.

    cd /exp/sbnd/app/users/yuhw/wire-cell-toolkit && git status --short && git branch --show-current

**Gate:** clean tree, on the branch you mean, and `opt/lib` was built *from this
branch* (compare `git rev-parse HEAD` to the build record). Pin the branch, not
just the build.

---

## 1. Build wire-cell-toolkit

    cd /exp/sbnd/app/users/yuhw/wire-cell-toolkit
    rm -rf build                                    # never hand-patch build/c4che/_cache.py
    in-gpvm-sl7.sh bash -c '<ai-helper>/issues/24-validation-vs-prod0908/scripts/configure-wct.sh'
    in-gpvm-sl7.sh bash -c 'CXXFLAGS="-DSPDLOG_FMT_EXTERNAL" ./wcb -p --notests install -j16'   # ~10-15 min

`configure-wct.sh` is the whole recovered option set. The parts that cost a day:

| fact | consequence |
|---|---|
| ambient ups spdlog is **v1_9_2, bundled-fmt**, which `Spdlog.h` rejects | must override; the default env can never satisfy WCT |
| need spdlog **v1_14_1** e26-prof (external-fmt) + fmt **v11_0_2** (`libfmt.a`) | both in `lib64`, not `lib` |
| `v1_14_1` and `v1_14_1b` share SONAME `libspdlog.so.1.14` | a misconfigure is invisible to the loader; only `Spdlog.h`'s `#error` sees it. **Check `INCLUDES_SPDLOG` in `_cache.py` names `v1_14_1`** |
| wcb has **no `--with-fmt`**; `waft/generic.py` splits `--with-X-include/-lib` on commas | fmt rides inside the spdlog options: `--with-spdlog-include=$SPD/include,$FMT/include`, `--with-spdlog-lib=$SPD/lib64,$FMT/lib64`, `--with-spdlog-libs=spdlog,fmt` |
| `-DSPDLOG_FMT_EXTERNAL` must reach the **configure check** | via `CXXFLAGS`; waf ignores a `DEFINES` env var |
| pkg-config is unusable for these products | `.pc` prefixes are build-machine paths and this pkg-config predates `--define-prefix` |

**Gate (all required):**
- `WCB_RC=0`, 0 error lines
- 19 `libWireCell*.so` incl. `libWireCellMcs.so`
- `nm -D -u opt/lib/libWireCell{Util,Clus}.so | grep -c __libc_single_threaded` = **0** (else it was a host build)
- RUNPATH → `spdlog/v1_14_1/…/lib64`; `readelf -d libWireCellUtil.so | grep -c "NEEDED.*fmt"` = 0 (fmt is static)
- `opt/include/WireCellUtil/custard/miniz.h` present (`wcb install` does not install it; larwirecell needs it)
- **the binary knows the config keys it will be handed**:
  `strings opt/lib/libWireCell{Clus,Root,Match}.so | grep -c '^<key>$'` ≥ 1 for each knob the production pin sets that is newer than your last build. **A build on the wrong commit passes every other check and is useless** — this happened (`origin/master e88f364d` had `flash_by_gid` in 0 files).

### 1a. Strip the build-tree RPATH — do this every install

wcb's `rpathify` leaves `DT_RPATH` entries pointing into `wire-cell-toolkit/build/<pkg>`
in **18 libs + `wire-cell` + `wcsonnet`**. `DT_RPATH` is transitive and beats
`LD_LIBRARY_PATH`, so seven WCT libs load from `build/`, not `opt/`. Harmless only
while the two are byte-identical; `rm -rf build` breaks the deployed runtime, and a
partial rebuild makes jobs silently run mixed binaries.

    in-gpvm-sl7.sh bash -c '
    O=/exp/sbnd/app/users/yuhw/opt
    for f in $O/lib/libWireCell*.so $O/lib/libWCP*.so $O/bin/wire-cell $O/bin/wcsonnet; do
      old=$(patchelf --print-rpath "$f"); echo "$old" | grep -q wire-cell-toolkit/build || continue
      rest=$(echo "$old" | tr : "\n" | grep -v wire-cell-toolkit/build | grep -v "^$O/lib$" | paste -sd:)
      patchelf --force-rpath --set-rpath "$O/lib${rest:+:$rest}" "$f"
    done'

**Gate:** `mv build build.HIDDEN`, then `ldd` every `opt/lib/libWireCell*.so` and
`opt/bin/wire-cell` → 0 `not found`, 0 WireCell deps outside `opt/lib`; `mv` back.
Back up `opt/lib` first (`production-prep/opt-rpath-backup-<date>`).

---

## 2. Build larwirecell

Use the MRB tree `larsoft-wct036/v10_14_02/srcs/larwirecell` — **not**
`/exp/sbnd/app/users/yuhw/larwirecell`, which is source-only.

    in-gpvm-sl7.sh bash -c '
    export WIRECELL_FQ_DIR=/exp/sbnd/app/users/yuhw/opt
    export CMAKE_PREFIX_PATH=/exp/sbnd/app/users/yuhw/opt:$CMAKE_PREFIX_PATH
    source .../localProducts_larsoft_v10_14_02_02_e26_prof/setup && mrbsetenv
    cd $MRB_BUILDDIR/larwirecell && make -j12'          # NOT `make install`

`make install` **always** fails: `CMAKE_INSTALL_PREFIX` is the read-only
`/usr/local`, and it dies copying `README.md` *after* a successful compile. Build,
then hand-copy `$MRB_BUILDDIR/larwirecell/lib/*.so` →
`opt/larwirecell/v10_01_28/slf7.x86_64.e26.prof/lib/` (back up the deployed set first).

**Gate:** `MAKE_RC=0`; `ldd` on each deployed lib resolves every `libWireCell*` under
`/exp/.../opt/lib` and shows **no cvmfs `wirecell` product** (if it does,
`WIRECELL_FQ_DIR` was not set when cmake re-ran — `touch` a `CMakeLists.txt` to
force it). **Expect most libs byte-identical** to the previous deploy; a lib that
changed is worth a sentence explaining why (this round: `QLMatch` and `AIML` gained
a `libWireCellMcs.so` dependency).

---

## 3. Sync the PR operating point — after EVERY toolkit merge or pull

Our 1-step calls `clus_maker.pr()` directly, so it never sees the production knob
values Xin records as TLA defaults in `wct-pr-perevt.jsonnet`. `sbnd/pr-operating-point.jsonnet`
(GENERATED — do not edit) carries them; it goes stale the moment the toolkit moves.

    <ai-helper>/issues/17-pr-operating-point-drift/scripts/resync-operating-point.sh <workdir>

It compiles the **bare** baseline (`PR_OP=bare`), regenerates, and gates. Read its
"CHANGED:" block — it should list exactly the knobs the owner flipped since your
last sync, and nothing removed.

**Gate:** `compile-both.sh` **0 differences**, and the generated file's header count
is plausible (this epoch: 22 named + 218 `tcn_knobs`). Then commit the regenerated
file **together with** the toolkit commit that caused the drift.

**Traps:**
- Never call `gen-pr-operating-point.py` directly on a non-bare compile directory:
  it emitted **only** the six new knobs and dropped ~200 (gate 6 → 245). The script
  exists to prevent exactly this.
- In round 2 the gate already read "6 differences" *before* anyone looked. It was
  not re-run after the merge, and the cost was an 18/19 divergence and a half-day
  of localisation. **Run it before any event runs.**
- `eb_fast` / `po_fast` / `dg_fast` live on the *clustering* entry points, not
  `pr()`, so the generated file cannot carry them — they are set in
  `wcls-img-clus-matching-xin.jsonnet` by hand. The gate is what finds them missing.

---

## 4. Config gates before running events (T0)

    scripts/cfg/prod_cfg_gate.py --ref ref/prod-<current>       # 21 artifacts vs consumers.sha256
    scripts/cfg/compile_prjob_cfg.sh <cfgtree> /tmp/p.json && cmp /tmp/p.json ref/prod-<current>/prod_prjob.json

**Gate:** `prod_prjob.json` **byte-identical** to the pin (ours has been, both
rounds, once on the right commit). 21/21 on the tripwire, or only
`sbnd_clus`/`sbnd_ql`/`sbnd_simcheck` drifting, each traced to a **named** feature
of ours (opflash_time; issue-10 NF/SP; w-gap rebase).

**Traps:**
- `ref/prod-<date>` is a **generation counter, not a commit date**
  (`prod-2026-09-05` was cut 09-03). Pick the toolkit commit by **measurement** —
  compile the candidate's cfg and `cmp` against the pin — never by date.
- `git log -S` **cannot find a `false`→`true` flip** (occurrence count unchanged).
  Use `git log -G`.
- The pin compiles with `-A dl_weights=` on purpose (machine-dependent path). Blank
  it on *our* side for the diff; keep the SCN path in the job.
- Xin's `compile_consumers.sh` hardcodes `/nfs/data/1/xqian` in six scripts. Run it
  from a **scratch copy** with paths repointed (`production-prep/t0-row1-scratch-*`);
  `sbnd_xin` is read/run-only. Without that, every compile returns rc=127 and the
  gate reports a *false* DRIFT from empty files — a vacuous gate that fails.

---

## 5. Run the 1-step

    run-harness.sh <manifest> <outdir> <nworkers> <cores> <fcl>     # fcl REQUIRED, no default

- fcl: `wcls-img-clus-matching-xin.fcl` (MC, `simtpc2d`) or `-data.fcl` (data,
  `sptpc2d`). A silently-wrong default once cost 3h16m and 13 217 failed events.
- Manifest: `<file>\t<nskip>\t<run>\t<subrun>\t<event>`. **`--nskip k` counts in
  art's FileIndex (RSE-sorted) order, not Events-tree order** — assign `k` over the
  RSE sort or a merged file mislabels every output. The harness renames from the
  job's own `Trun`, so a wrong prediction shows up as `rse_check=MISMATCH`, not as
  silently wrong files.
- Sizing: measured peak RSS **2.1 GB** per `lar` process. Size on *sampled
  concurrent* RSS, not sum of peaks; run a sampler (`memwatch.sh`) so the budget
  is measured. `taskset` the TBB pool.
- `timeout -k 60 3600` — plain `timeout` sends only SIGTERM and never fires.

**Gate (T1):** rc=0 all; `audit=ok` (checks the DL vertex did not silently fall back
to geometric); `rse_check=ok`; 8 trees in `tracking-pr.root` with `T_tagger`/`T_kine`
at 1 entry; 0 `DL vertex failed` in logs.

---

## 6. Run Xin's 2-step here (for P1: our binary == his)

Stage A: `run_chain_group.sh <reco1.root> <out> data --size 16 --layout perevt`
(+ `--fsproduct 'sbnd::timing::FrameShiftInfo_frameshift__FILTERFRAMESHIFT.'` for ncpi0 only).
Stage B: `run_pr_chain_batch.sh <ql_root> <out> data [evt ...]` with `PR_EXTRA_STAGES=pr_display`
and `PR_EXTRA_TLA=<EMPTY FILE>` (empty file, not unset — deliberate). Per-sample
settings are in `scripts/d102m_stageA.sh`; use them verbatim.

**Traps — the driver assumes a newer host than SL7:**
- `run_pr_chain_batch.sh:1848` hardcodes `libpython3.11.so.1.0`; derive
  `sysconfig.get_config_var('INSTSONAME')`.
- `_runlib.sh` uses `wait -n -p` (bash ≥ 5.1); `run_chain_group.sh` uses `wait -n`
  (≥ 4.3). Replace with a poll / block-on-all-pids.
- `"${ARR[@]}"` on empty arrays under `set -u` (25 + 12 sites) — and it fires
  **only** on the no-TLA-override path a gate needs. Guard with `${ARR[@]+"${ARR[@]}"}`.
- `WCT_BASE=/nfs/data/1/xqian/...` on lines 56–67: pre-set `PR_CFG_TREE`,
  `WIRECELL_PATH`, `PYTHONPATH`, `SBND_RECO1` and the script appends them; the
  nonexistent paths are skipped. `${SBND_RECO1}/lib` → cmake installs to `lib64`.
- **Scrub LArSoft dictionaries from `LD_LIBRARY_PATH`** before stage A
  (`lardataobj|canvas|sbndcode|sbnobj|artdaq|lardataalg`) or the bare-ROOT reco1
  reader segfaults on a duplicate `recob::Wire` dictionary.
- **Keep `wire-cell-sbnd-reco1` current and rebuilt against the current WCT.** The
  July build ignored `entry_begin`/`entry_count`; in group mode two groups then
  processed all events and **raced on the same output files**, corrupting three
  pctrees. Its cmake install also has no RPATH — `patchelf` it to
  `opt/lib:<spdlog>/lib64:<fmt>/lib64`.

All fixes go in a **scratch copy** (`production-prep/step1a-runner-scratch/`);
patch at `issues/24-*/scripts/sl7-runner-portability.patch`. Nothing in `sbnd_xin`
is ever modified.

**Gate:** `STAGEA_RC=0`, `STAGEB_RC=0`, **and** every expected `ql_evt*/pctree*.tar.gz`
passes `gzip -t` with no "trailing garbage", **and** every `pr_evt*/tracking-pr.root`
exists. A job reading an empty pctree exits **0**.

---

## 7. Compare (T2 / T3)

| question | tool | gate |
|---|---|---|
| P1 selection | `cmp nusel-evt<ID>.tsv` vs the production arm | byte-identical N/N |
| P1 stage A | md5 of every pctree member (never the archive — gzip carries timestamps) | identical N/N |
| P1 exhaustive | `scripts/analysis/d99_root_branch_census.py A B --samples s --root R --expect 'T_rec_charge:q,T_rec_charge:reduced_chi2'` | only the expected pairs; **and the "compared N events" line equals N** |
| P2 | `issues/20-*/scripts/deep_compare.py` (our 1-step vs Xin's 2-step, same binary) | **exact** N/N — same machine, so no FP allowance |
| T3 | `pr_scores_table.py --root <arm> --sample s` → `scripts/pr142_campaign_ab.py --a products/<epoch>/<s>-scores-*.tsv --b …` | **0 movers**, 0 label/eval flips |

Legitimate cross-machine residual (measured, both rounds): `T_rec_charge:{q,reduced_chi2}`
at ~1e-12 relative, `kine_mcs_ambiguity` at ~7e-8, and rarely (1/241) an FP-seeded
discrete shower-sampling change that stays below every score and label. Anything
else is a finding to report with the first divergent event, not something to tune.

**Traps:**
- `pr87_root_tree_diff.py` **truncates at 12 lines** — it answers "did anything
  move?", never "nothing moved except X". Use the census for exhaustive claims.
- The census **silently skips** events missing on one side. A PASS on 16 of 19 is
  not a PASS.
- A per-event config diff compares only components present on **both** sides. A
  component missing from ours and absent by design from Xin's standalone job is
  invisible — the config gate read 0 keys while our chain could not configure
  (`NamedFactory: Failed to find instance "rse_apa0"`).
- Counting occurrences of a feature name catches deletions and **never** a dropped
  argument or a changed value: `pre_mabc` went 5→6 sites and `save_deadarea` 3→3
  while both were broken. Only running the workflow found them.
- `pgrep -f` / `pkill -f <pattern>` match the invoking shell's own command line.
  Use `-x <comm>`.

---

## 8. What "done" looks like

Round 2, 308-event gate, all data: P1 `nusel` 308/308, pctrees 308/308, 0 movers;
**P2 exact 308/308**. Reached only after fixing, in order: the operating point (§3),
the reco1 reader (§6), and the RPATH (§1a). Every one of those was invisible to
the static gates and found by running events and reading real outputs. The gates
are necessary; they are not sufficient. Run the workflow.
