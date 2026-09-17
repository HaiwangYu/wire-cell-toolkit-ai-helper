# Aurora: validate the SBND 1-step chain against the FNAL reference (MC CV pilot, 18 events)

Written 2026-09-17 by the FNAL session for the **Aurora Claude Code session** to review and execute. Goal: show that the 1-step chain built on Aurora reproduces, event by event, the FNAL run that was itself shown exact against Xin's 2-step production ([#24](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/24), [#26](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/26)). Report results as a comment on #26. Ask before deviating; do not "fix" a difference by changing config — a difference is the finding.

## 0. What is being compared

| | FNAL reference | Aurora |
|---|---|---|
| input | `reco1-detsim-g4-gen-Gen2_2026-dcb3-ca6c-2a43-8740.root` (MC BNB CV, run 717 subrun 29, 18 events, 502 MB, md5 `21e15199859020fe60acb5ce69c4df1c`) | same file, staged (§2) |
| chain | 1-step `lar -c wcls-img-clus-matching-xin.fcl`, one job per event | same |
| toolkit | `wire-cell-toolkit` `master-2026-09-08+yuhw` @ **`0ad64223`** (= PR [WireCell#530](https://github.com/WireCell/wire-cell-toolkit/pull/530)) | must match |
| job config | `wcp-porting-validation` @ **`e100a631`** (`sbnd/wcls-img-clus-matching-xin.fcl` + `.jsonnet`, `pr-operating-point.jsonnet`, `enable_nugraph_h5: "false"`) | must match |
| larwirecell | SBND fork with `WireCellAIML` labeler (FNAL MRB tree `larsoft-wct036/v10_14_02`) | the Aurora build of the same source |
| weights | `wire-cell-data` @ `9e2f4b8` + untracked `uboone/weights/XGB_nue_seed2_0923.xml` (199,034,452 B, md5 `2bdb5cec111bf6cb6dd828cd59fe7ea0`); DL vertex `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` (md5 `9cc1413e053c09534edc2d37cdfdc1d4`) | present under `/lus/flare/projects/neutrinoGPU/yuhw/wire-cell-data/` — verify md5 |
| reference outputs | `run-C-noh5/` — 18 `tracking-pr.root` + 18 Bee zips | produced by you |

## 1. Pre-flight gates (stop at the first failure, report it)

```
cd <wire-cell-toolkit>; git status --short; git rev-parse HEAD          # clean, 0ad6422357ab7002e011822a740646889081403a
cd <wcp-porting-validation>; git status --short; git rev-parse HEAD     # clean, e100a6318b888ddf60fbf9cb47dc7c8b24acece2
md5sum <wire-cell-data>/uboone/weights/XGB_nue_seed2_0923.xml <wire-cell-data>/uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth
```
- **G1 build tree = run tree.** `WIRECELL_PATH` must put the checkout's `cfg/` (or the `opt/share/wirecell` installed *from that commit*) ahead of any sbndcode cfg. A `git checkout` after the build silently changes what runs. Record `echo $WIRECELL_PATH`.
- **G2 no build-tree RPATH.** `readelf -d <opt>/lib/libWireCellClus.so | grep -i r.*path` — no `…/build/…` entries; likewise `wire-cell` and `libWireCellAIML`/`larwirecell` libs. (FNAL trap: wcb leaves RPATH into the build dir, which beats `LD_LIBRARY_PATH`.)
- **G3 binary knows the config keys.** `strings <opt>/lib/libWireCellClus.so | grep -c flash_by_gid` ≥ 1 (a binary from an older commit passes every other gate and fails at run time).
- **G4 operating-point gate = 0 differences.** From `<wcp-porting-validation>/sbnd`: `PR_OP=sync <ai-helper>/issues/17-pr-operating-point-drift/scripts/compile-both.sh <workdir>` must end with `0 differences`. This compiles our 1-step and Xin's two jsonnets and diffs them; it is the check that the ~240 PR knobs are in sync. If it is not 0, stop — do **not** run `gen-pr-operating-point.py` by hand (it drops ~200 knobs); report.
- **G5 DL vertex import works.** In the run environment: `python3 -c "import sparseconvnet"` (or whatever `setup-dlvtx.sh` provides on Aurora) exits 0. If the SCN import fails the chain **silently** falls back to the geometric vertex; the per-event `audit` catches it after the fact, this catches it before.
- **G6 spdlog/fmt.** `wire-cell --version` runs; `ldd <opt>/lib/libWireCellUtil.so | grep -E "spdlog|fmt"` resolves to the intended external-fmt spdlog.

## 2. Inputs (already staged on Aurora)

```
/lus/flare/projects/neutrinoGPU/yuhw/production-prep/r3-pilot-mccv-reference/
  input/reco1-detsim-g4-gen-Gen2_2026-dcb3-ca6c-2a43-8740.root
  pilot.manifest            # 18 lines: <FNAL path> <nskip> 717 29 <event>   -> rewrite column 1 to the Aurora path, keep nskip
  run-C-noh5/{tracking-pr,bee,summary.csv}          # FNAL reference
  REFERENCE-CHECKSUMS-run-C-noh5.txt                # host-independent hashes of the reference
  scripts/{deep_compare.py, compare_bee_zips.py, reference_checksums.py}
```
`nskip` is the art **FileIndex** (RSE-sorted) index, already computed; for this single-run MC file it equals tree order. The harness renames outputs from the job's own `Trun`, so a wrong prediction shows as `rse_check=MISMATCH`, never as a silently mislabeled file.

## 3. Run

Either the FNAL harness (`run-harness.sh <manifest> <out> <nworkers> 1 wcls-img-clus-matching-xin.fcl` — 5th arg is **required**; it writes `bee/`, `tracking-pr/`, `summary.csv` with `rc, wall_s, peak_rss_kb, audit, rse_check` per event) or an equivalent loop of

```
lar -n 1 --nskip <k> -c wcls-img-clus-matching-xin.fcl -s <input.root> --no-output     # per event, own cwd
```
with `FHICL_FILE_PATH` including `<wcp-porting-validation>/sbnd`, `OMP_NUM_THREADS=MKL_NUM_THREADS=1`, `timeout -k 60 3600`. Expect ~40–100 s and ~2.2 GB RSS per event on FNAL hardware; 18 concurrent is fine at ~40 GB.

**MC fcl, not the data one**: this is `simtpc2d` MC — `wcls-img-clus-matching-xin.fcl`. (`-data.fcl` would fail loudly on product tags; there is no FrameShift on MC.)

## 4. Gates on your own output (T1)

| check | want |
|---|---|
| rc | 0 for all 18 |
| `tracking-pr.root` present | 18; 5 of them (events 6, 11, 29, 37, 47) have 8 trees incl. `T_kine`/`T_tagger` (1 entry each); the other 13 have 4 (`Trun, T_bad_ch, T_cluster, T_proj`) |
| Bee zips | 18, each with the 21 MC layers (`sed-*` ×3, `truth_*` ×2, `tagger_*` ×4, `clustering-*` ×4, `img-global`, `mc`, `op`, `shower_track-global`, `track_fit-global`, `vertices-global`, `channel-deadarea-*` ×2) |
| `DL vertex failed` in any log | 0 (grep) |
| `Trun` run/subrun/event | 717 / 29 / the manifest event |

## 5. Compare to the FNAL reference (T2)

**ROOT — never `cmp` the files** (ROOT embeds timestamps/UUIDs). Use the content hash tool:
```
R=/lus/flare/projects/neutrinoGPU/yuhw/production-prep/r3-pilot-mccv-reference
mkdir -p cmp/ours
for f in $R/run-C-noh5/tracking-pr/*.root; do e=${f##*_e}; e=${e%.root}; mkdir -p cmp/evt_$e; ln -sf $f cmp/evt_$e/tracking-pr.root; done
for f in <yours>/tracking-pr/*.root; do e=${f##*_e}; ln -sf $f cmp/ours/tracking-pr_$e; done
python3 $R/scripts/deep_compare.py cmp cmp/ours aurora
```
Reads per event `IDENTICAL (T_kine+T_tagger hashes match, N charge pts)` or `DIFFERS in [...]`, then `=> exact match N/18`.

**Bee:**
```
python3 $R/scripts/compare_bee_zips.py $R/run-C-noh5/bee <yours>/bee
```
Per event: `identical` (all layer md5 equal) / `numeric-only, max rel …` (JSON equal to rtol 1e-9 — float last-digit formatting) / `DIFFERS` with the layer and first differing path.

Alternative without our files: `python3 $R/scripts/reference_checksums.py <yours> | diff - $R/REFERENCE-CHECKSUMS-run-C-noh5.txt`.

## 6. How to read the result

| outcome | meaning | action |
|---|---|---|
| `deep_compare` **exact 18/18**, Bee **identical 18/18** | Aurora build ≡ FNAL ≡ Xin's production on this input | report; done |
| `T_kine`/`T_tagger` identical, `DIFFERS in ['charge_hash']` on some events, and per-branch it is `T_rec_charge` `q`/`reduced_chi2` at ≤ ~1e-12 relative | the known cross-host FP residual (seen FNAL↔wcgpu1 at 1e-13) | report the max relative difference and the branches; acceptable |
| Bee `numeric-only` with max rel ≤ 1e-9 | float printing / same FP residual | acceptable, report |
| any `T_kine` or `T_tagger` difference, a Bee layer missing, a `mc.json` difference, different `nue_score`/`numu_score`/`kine_reco_Enu` | **real** — most likely a config/pin mismatch (G1/G4), a weights-file mismatch (md5), a DL-vertex fallback (G5, check `audit`/logs), or a different larwirecell | do not tune; report the first divergent event with its `deep_compare` line, the branch-level diff, and the G1–G6 outputs |
| rc≠0 / crash | if it is event 471/18/33 you are on the wrong sample; otherwise report the log tail | |

Per-branch diff helper for one event (adapt paths):
```
python3 - <<'EOF'
import ROOT; a=ROOT.TFile.Open('<ref>.root'); b=ROOT.TFile.Open('<yours>.root')
for tn in ['T_kine','T_tagger','T_rec_charge']:
    ta,tb=a.Get(tn),b.Get(tn); d={}
    for i in range(ta.GetEntries()):
        ta.GetEntry(i); tb.GetEntry(i)
        for br in [x.GetName() for x in ta.GetListOfBranches()]:
            va,vb=getattr(ta,br),getattr(tb,br)
            if va!=vb:
                try: rel=abs(va-vb)/max(abs(va),abs(vb),1e-300)
                except TypeError: rel=float('nan')
                e=d.setdefault(br,[0,0.0]); e[0]+=1; e[1]=max(e[1],rel)
    print(tn, {k:(n,'%.1e'%r) for k,(n,r) in d.items()} or 'identical')
EOF
```

## 7. What to report (comment on #26)

1. G1–G6 outputs (commit hashes, md5s, `WIRECELL_PATH`, RPATH check, `compile-both` tail).
2. T1 table (rc, trees, layers, DL fallbacks, wall/RSS per event).
3. `deep_compare` summary line + `compare_bee_zips` summary line, and the per-event lines that are not IDENTICAL.
4. For any difference: the per-branch table above for the first divergent event.
5. Where your outputs live on Aurora.

## 8. Traps that bit us at FNAL (so you don't re-find them)

- Pin the **branch**, not the build — `WIRECELL_PATH` reads the checkout live.
- wcb leaves **RPATH into the build tree** → `patchelf --force-rpath --set-rpath`.
- The **operating point** file is generated; it goes stale on every toolkit move (G4). Never run the generator on a non-bare compile dir.
- **DL vertex falls back silently**; only `audit` / `DL vertex failed` reveal it.
- `run-harness.sh` **requires the fcl argument**; a wrong default once failed 13,217 events silently.
- A `--nskip` mislabel is invisible unless `Trun` is checked (the harness does).
- Byte-comparing ROOT files is meaningless; compare content.
- Multi-hour runs at FNAL needed a Kerberos renewer — not applicable on Aurora, but check that the job's filesystem access does not depend on a token that expires mid-run.
