# Round 3: re-run the four SBND samples on the validated 1-step chain

Supersedes the #16/#18/#19 datasets (summarised in #20) with outputs from the
chain validated in #24: toolkit `master-2026-09-08+yuhw` `0ad64223`, `opt`
RPATH-stripped, operating point resynced at the 09-08 epoch, P1/P2 exact
308/308 on data. **Nothing is rebuilt for this round** — the whole point is to
run the validated binaries+cfg as they are.

Samples: MC BNB CV, MC nueCC (same inputs as before), beam-on and beam-off data
(**10,000 events each**, up from 1,000). Budget: 20 cores, 50 GB, host
sbndbuild/sbndgpvm.

Status: **RUNNING — MC BNB CV DONE 13,216/13,217 (2026-09-10 10:23; 1 deterministic toolkit crash, see issue comments); nueCC running since 10:37.** MC CV launched 2026-09-09 19:34 CDT (20 workers, `production-prep/r3-mc-cv-2026-09-09/`). Owner decisions taken (§6): same MC lists; fresh random 200 beam-on files; **no nugraph this round**; 10-event B-vs-C + Bee of both chains for every sample. Beam-off = **`data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd`** (owner, 2026-09-10, on a colleague's advice; supersedes the 09-09 choice). Data staged (§3a), data spot checks exact 16/16 + 16/16 (§1a).

---

## 0. Pre-flight — all measured 2026-09-09, none of it re-run for this round

| check | result |
|---|---|
| toolkit tree | `master-2026-09-08+yuhw` `0ad64223`, clean; `origin/master` still `c8b2821b` (0 behind) |
| `opt/lib` RPATH | `opt/lib:<cvmfs …>:spdlog v1_14_1/lib64:fmt v11_0_2/lib64` — no build-tree entries |
| operating point | `compile-both.sh` (PR_OP=sync) **0 differences** at this tree |
| DL vertex | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` md5 `9cc1413e…`, identical in 1-step and 2-step compiled cfgs; `dl_vtx_{dual_chain,rerank}=true, min_accept=10, top_k=5, score_scale=1000` |
| BDT weights | 41 `uboone/weights/*.xml` referenced, the **same set** in both compiled cfgs; all resolve under `wire-cell-data` (incl. the untracked `XGB_nue_seed2_0923.xml`) |
| reco1 reader | `wire-cell-sbnd-reco1` `85b7932`, RPATH patched |
| host | 64 cores, 125 GB; `/exp/sbnd/data` 87 TB free of 125 TB; `users/yuhw` = 362 GB |

**Gap this round closes:** #24 validated P2 on *data* (ncpi0, nuecc48, mcp1k are
all real data, `sptpc2d`). MC (`simtpc2d`, truth labeler) was last shown exact
vs the 2-step in #20 at the 08-30 epoch, 10 events. The pilot (§1) is the MC
check at the current epoch.

## 1. Pilot — MC BNB CV, one random reco1 file (18 events), chain B vs chain C

`production-prep/r3-pilot-mccv/`. Input: one file drawn with `random.seed(20260909)`
from the #16 `files-1000.lst` (run 717 subrun 29, 18 events) — a random file, not
the manifest head (#18 showed head sampling is 2× biased).

**Result: P2 exact 18/18** (`deep_compare.py`: `T_kine`+`T_tagger` hashes and every
`T_rec_charge` point identical on all 18; 5 events carry a reconstruction —
1914/515/787/281/36 charge points — 13 have none).

| arm | how | result |
|---|---|---|
| chain B | Xin's drivers (scratch copy), `run_chain_group.sh … sim --size 16 --layout perevt` → `run_pr_chain_batch.sh … sim`, `PR_EXTRA_STAGES=pr_display` | `STAGEA_RC=0 STAGEB_RC=0`; 18 pctrees, 0 corrupt; 18 `tracking-pr.root`; 0 `DL vertex failed`; 16:37→16:50 |
| chain C | `run-harness.sh pilot.manifest run-C 18 1 wcls-img-clus-matching-xin.fcl` | 18/18 rc=0, `audit=ok` 18, `rse_check=ok` 18; wall mean **95 s** (40–263), peak RSS mean 1.81 / max 2.29 GB, 6.83 MB/evt; 4.5 min wall |

So MC at the current epoch is in sync with the 2-step, on top of #24's data result.
Two caveats: 18 events with 5 reconstructions is a pilot, not a population
statement; and the 95 s/event is ~1.4× the 68 s the same chain averaged in the
08-30 MC run — the host had other users' jobs on it during the pilot, and the
09-08 toolkit added stages (MCS, long-muon chain), so §2 quotes the estimate as a
range until the first campaign hour measures it.

**Stage A on MC needed one driver change.** `run_chain_group.sh` is data-only:
it hardcodes `caf_offset_mode=product` (needs `FrameShiftInfo`, which MC has none
of) and the `sptpc2d/Reco1` product names. The scratch copy now keys on
`reality=sim` to pass exactly what Xin's own MC recipe passes
(`scripts/dbg25_stage.sh`): `caf_offset_mode=none`,
`wire_product=recob::Wires_simtpc2d_dnnsp_DetSim.`,
`badmask_product=ints_simtpc2d_badmasks_DetSim.`,
`summary_product=doubles_simtpc2d_wienersummary_DetSim.`, `frameshift_product=`.
`reality=data` is byte-identical to before. Patch: `scripts/run_chain_group-sim.patch`.

## 1a. Data spot checks — beam-on and beam-off, chain B vs chain C: exact 16/16 each

Run 2026-09-09 20:45–21:07 alongside the MC campaign (6 workers, inside the 50 GB).
One 16-entry reader group of each sample's `chunk00.root` (groups 37 and 11 —
arbitrary, not the head); chain B = Xin's drivers `data`, stage A via the reader
(`caf_offset_mode=product`, FrameShift present), stage B `PR_EXTRA_STAGES=pr_display`;
chain C = `run-harness.sh … wcls-img-clus-matching-xin-data.fcl` on the same 16 RSE
from the campaign manifest.

| sample | chain B | chain C | `deep_compare` | reconstructed |
|---|---|---|---|---|
| beam-on | `STAGEA_RC=0 STAGEB_RC=0`, 16 pctrees, 16 `tracking-pr.root` | 16/16 rc=0, audit ok, rse ok | **exact 16/16** | 8/16 |
| beam-off | same | same | **exact 16/16** | 1/16 |

0 `DL vertex failed` in any log. Bee, both chains, same order (`spot-*/bee-upload/bee-order.txt`):

| | Xin's 2-step | our 1-step |
|---|---|---|
| beam-on | <https://www.phy.bnl.gov/twister/bee/set/68608c5d-15d0-4770-ba9d-8af3f507c036/event/list/> | <https://www.phy.bnl.gov/twister/bee/set/1c94a5dc-9465-425e-b2ab-33b8b9b07217/event/list/> |
| beam-off | <https://www.phy.bnl.gov/twister/bee/set/b37fba4f-a105-4c8d-8fae-e69a3174bdb9/event/list/> | <https://www.phy.bnl.gov/twister/bee/set/a40ff0c4-325b-4b07-b483-4eda67bbe8db/event/list/> |

With the MC pilot (§1) that is all three realities/streams the campaign runs
shown exact against the 2-step at this epoch, on inputs drawn from the campaign
itself. nueCC (MC, same fcl and products as MC CV) gets its own 10-event check
before its run, per the owner's instruction.

## 2. Resources

Per-event cost measured on this host in the #16/#18/#19 sync runs (same event
mix; the toolkit moved since, so the pilot numbers are the cross-check):

| sample | events | wall/evt (mean, p99) | peak RSS mean / max | out MB/evt |
|---|---|---|---|---|
| MC CV | 13,217 | 68 s, 160 s | 2.16 / 3.55 GB | 6.8 |
| nueCC | 8,877 | 81.5 s, 240 s | 2.35 / 3.64 GB | 8.0 |
| beam-on | 10,000 | 58.9 s, 140 s | 2.07 / 2.31 GB | 2.5 |
| beam-off | 10,000 | 64.8 s, 150 s | 2.48 / 2.90 GB | 2.4 |

Sizing rule from #16: budget on *sampled concurrent* RSS (~1.9–2.5 GB/job),
not sum of peaks, and run `memwatch.sh` so the number is measured, not assumed.

| sample | workers | core-h | wall | mean concurrent RSS | outputs |
|---|---|---|---|---|---|
| MC CV | 20 | 250 | **12.5 h** | ~43 GB | 90 GB |
| nueCC | 18 | 201 | **11.2 h** | ~42 GB | 71 GB |
| beam-on | 20 | 164 | **8.2 h** | ~41 GB | 25 GB |
| beam-off | 18 | 180 | **10.0 h** | ~45 GB | 24 GB |
| **total** | | **~795 core-h** | **~42 h sequential** | | **~210 GB** |

If the pilot's 95 s/event (vs 68 s) is the new MC cost rather than host load,
MC CV becomes ~17.5 h and nueCC ~15.5 h: **42–55 h** total, i.e. 2–2.5 days at
20 cores. The first hour of each sample gives the real number.

18 rather than 20 workers on the two heavy samples keeps the 50 GB cap with
headroom for the 3.6 GB tails; both #18 and #19 had to back off from 32 to 26 for
the same reason at 64 GB.

**Disk**: outputs ~210 GB + staged frameshifted data inputs ~78 GB (2 × 10 ×
3.9 GB; deletable after the run) → **~290 GB peak**, settling to ~210 GB.
`/exp/sbnd/data` has 87 TB free; `users/yuhw` is at 362 GB, of which the #16/#19/#18
sync datasets are 156 GB and become retirable once this round passes. No per-user
quota is visible from here — owner to confirm.

## 3. Inputs

### MC — same samples as before (owner: confirm §6 Q1)

| | list | files | events |
|---|---|---|---|
| MC BNB CV | `img-clus-match-tag-pr-mc-1000file-sync-2026-08-30/lists/files-1000.lst` | 1,000 | 13,217 |
| MC nueCC | `img-clus-match-tag-pr-nuecc-1000file-2026-08-29/lists/files-1000.lst` | 1,000 (1 unreadable) | 8,877 |

`prodgenie_corsika_proton_rockbox0p1_sbnd` Gen2_2026 CV `v10_14_02_03`, and
Gen2_Exclusive_2026 nuecc `v10_14_02_05`. Read in place from `/pnfs`; the
existing RSE-sorted manifests are reused as-is (single run per file, so the
`--nskip` FileIndex-order trap does not bite; `Trun` is verified anyway).

### Data — availability on `/pnfs` (counted 2026-09-09, 8 files sampled per campaign for events/file)

| campaign | reco1 files | events/file | ≈ events | frameshifted? | used before |
|---|---|---|---|---|---|
| **beam-on** `v10_14_02/Fall25-Run1_BNB_Dev_bnblight` | 3,335 | 50 | **~167k** | no | yes (#18, 1k of 3k staged) |
| **beam-off (a)** `v10_14_00/FallValidationII_RollingDev_offbeamlight` | 738 | 50 | **~36.9k** | no | yes (#18: the 1k came from here) |
| **beam-off (b)** `v10_14_02/Fall25-Run1_InTime_offbeamlight` | 1,525 | 45–50 | **~68k** | no | no |

**SAM check (2026-09-09, `samweb` in SL7):** a reco1 definition for (b) does exist —
`data_MCP2025C_Fall25-Run1_InTime_offbeamlight_v10_14_02_reco1_sbnd`, 1,525 files,
308 GB, matching the 1,525 reco1 artROOT files on `/pnfs` (alongside its
`caf/flatcaf/histreco2/larcvreco1` siblings). Metadata of one file: parent
`data_EventBuilder6_art2_run18259_4_strmOffBeamLight_…`, fcl chain
`run_decoders_job / run_DigitalNoiseEventFilter / reco1_data / reco2_data /
run_sbndbnbextinfo_sbn / cafmakerjob_sbnd_data_sce_offbeamlight`, v10_14_02 —
i.e. the same decode→reco1 chain as beam-on (`run_sbndbnbinfo` ↔ `…bnbextinfo`),
from the OffBeamLight stream. (a)'s chain is the same minus the ext-info step,
at v10_14_00. What "InTime" selects on top of OffBeamLight is not in the
metadata — that is the SBND production question to settle before using (b).

So **10,000 each is available** — beam-on comfortably, beam-off from either
source. (a) is what #18 used but is a different campaign and sbndcode version
from beam-on (`FallValidationII_RollingDev` v10_14_00 vs `Fall25-Run1` v10_14_02);
(b) is the same campaign/version as beam-on but has not been used here and its
"InTime" selection needs confirming with SBND before it is treated as the plain
beam-off stream. **Owner decision, §6 Q2.**

Every Gen2 data file must get the `FrameShift` product first
(`run_frameshift.fcl`; memory `reference_gen2_frameshift`). Cost is small: 40–80 s
and 3.9 GB per 1,000-event merged file. Plan: 200 files per sample chosen at
random (seeded) across the campaign, merged in 10 × 1,000-event chunks, then
`prep-beam-off.sh`-style verification that the product actually landed, an
RSE-uniqueness check across chunks, and the RSE-sorted manifest.

### 3a. Data staged (2026-09-09 20:30–20:45) — `production-prep/r3-data-stage-2026-09-09/`

| | source files | selection | staged | events | manifest |
|---|---|---|---|---|---|
| beam-on | 3,335 (`…BNB_Dev_bnblight` v10_14_02 reco1) | 200 random (`seed 20260909`) + 6 top-up (`seed 20260910`, disjoint) | 11 chunks, 39 GB | 10,121 | **10,000** |
| beam-off | 1,525 (`…InTime_offbeamlight` v10_14_02 reco1) | 200 random + 18 top-up | 11 chunks, 41 GB | 10,196 | **10,000** |

Each chunk = `lar -c run_frameshift.fcl -S <20 files> -o chunkNN.root` (45–80 s,
1.3 GB RSS), accepted only after a branch check finds
`sbnd::timing::FrameShiftInfo_frameshift__FRAMESHIFT.` — all 22 chunks did. Top-ups
were needed because InTime off-beam files are short (777–1000 events per 20 files;
one had 9 events), and beam-on had two 950s. Manifests: EventAuxiliary RSE per
entry, sorted into art FileIndex order per chunk, `--nskip` index assigned on the
sort, cross-chunk duplicate check (0 duplicates), cut at 10,000. Run coverage:
beam-on 55 runs, beam-off 68 runs, both dominated by 18255/18259 (≈40%/16%).
The staged inputs are deletable after the run; the manifests point at them.

### 3b. Beam-off re-staged from the SBND2026A production (2026-09-10 12:02–12:08)

Owner switched beam-off to `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd`
(a colleague's recommendation): **49,020 reco1 files, 2.23 M events, 9.5 TB**, on
dCache under `/pnfs/…/SBND2026A/v10_14_02_02/gen2_InTime-Run1/reco1/offbeamlight/`,
v10_14_02_02, same decode→reco1 chain and `sptpc2d` products, OffBeamLight stream.
12 random files opened fine (18–50 events each). Selection: 240 random files
(`seed 20260910`) → 12 FrameShift chunks, all 12 verified for the
`FrameShiftInfo_frameshift__FRAMESHIFT.` branch, 10,631 events → manifest cut at
**10,000**, 0 duplicates, **94 runs** (18250…). The 09-09 `Fall25-Run1_InTime_offbeamlight`
staging and its spot check were deleted (41 GB).

Spot check on the new sample (one 16-entry group of `chunk00`, chain B vs C):
**exact 16/16**, 0 `DL vertex failed` — but **0 of the 16 carry a reconstruction**
(beam-off is a ~5 % candidate stream), so this agreement is the trivial kind #20
warned about. Follow-up recorded in §4: after the beam-off run, take 10 events with
`kine_reco_Enu > 0` from `summary.csv` and run chain B on them for a non-trivial
exact check. Bee, both chains, same order:
[2-step](https://www.phy.bnl.gov/twister/bee/set/5b2ae9aa-43c3-4411-9abd-5358b6f13a03/event/list/) ·
[1-step](https://www.phy.bnl.gov/twister/bee/set/568162f1-9ab1-4a43-a846-ee86e28e4cfd/event/list/).

The same production has the beam-on counterpart
`data_SBND2026A_gen2_BNB-Run1_v10_14_02_02_reco1_sbnd` (100,934 files, 4.8 M events,
same version). Our staged beam-on is MCP2025C `Fall25-Run1_BNB_Dev_bnblight`
v10_14_02. **Open: switch beam-on too for a version-matched pair?** (~15 min to
re-stage; beam-on has not run.)

## 4. Run plan

Gates are the #24 procedure's; nothing new. Stop at the first failure.

| step | what | gate | cost |
|---|---|---|---|
| 0 | pre-flight (§0) — re-check tree/RPATH/opset **immediately before** step 3 | clean tree at `0ad64223`; `compile-both.sh` 0 differences | 5 min |
| 1 | pilot (§1) | chain B and C both 18/18; `deep_compare.py` **exact 18/18** | **done** |
| 2 | stage data (§3a) | FrameShift product present in every chunk; 10,000 unique RSE per sample | **done** (`Trun` check happens per event in the harness) |
| 2b | 16-event chain B vs C spot-check on each data sample (§1a) | exact | **done: 16/16, 16/16** |
| 3 | smoke: 10 random events per sample through the campaign fcl (`-xin.fcl` MC, `-xin-data.fcl` data) | rc=0, `audit=ok`, `rse_check=ok`, 8 trees | 15 min |
| 4 | run, one sample at a time, `memwatch.sh` alongside: **MC CV (running since 19:34) → nueCC → beam-on → beam-off** | T1: rc=0 all, `audit=ok`, `rse_check=ok`, 0 `DL vertex failed`; sampled RSS ≤ 50 GB | ~42 h |
| 4b | beam-off only: after the run, chain B on 10 events with `kine_reco_Enu > 0` (the spot-check group had none) | exact 10/10 | ~20 min |
| 5 | per sample: 10-event Bee, candidate / `nue_score>0` rates vs the #20 table | rates move only where the 09-08 knobs moved them; no rc≠0 event unexplained | 1 h |
| 6 | close-out: summary doc, delete staged inputs (78 GB), owner decides on retiring the 156 GB of #16/#18/#19 sync outputs | | |

Concurrency: 20/18/20/18 workers × 1 core as in §2 (MC CV is running at 20: first 1,926 events 43 s/evt mean, max concurrent RSS 33.6 GB, 5.7 MB/evt, ETA ~03:45 CDT); `taskset` the TBB pool;
`timeout -k 60 3600` per event. Same harness (`run-harness.sh`) and the same
`(run,subrun,event)`-named three deliverables per event as #20.

## 5. Traps carried forward (from #24 and the procedure doc)

- **Operating point**: the gate is re-run in step 0 even though nothing moved —
  round 2 lost half a day to a "6 differences" that nobody re-read.
- **Pin the branch, not the build**: any `git checkout` in `wire-cell-toolkit`
  changes what every job runs via `WIRECELL_PATH`. No toolkit work during the run.
- **fcl is not defaulted**: MC → `wcls-img-clus-matching-xin.fcl`, data →
  `-data.fcl`. The wrong one once cost 3 h and 13,217 failed events.
- **Merged data files + `--nskip`**: FileIndex (RSE-sorted) order; the harness
  names outputs from `Trun` and flags `rse_check=MISMATCH`.
- **Select on `kine_reco_Enu > 0`**, never on file size; `T_tagger`/`T_kine`
  carry no RSE.
- **DL vertex silent fallback**: `audit=ok` per event + 0 `DL vertex failed`.
- **`pkill -f` self-match**: `-x` only.
- **Head-of-manifest pilots are biased 2×** — sample randomly.

### Pilot Bee sets (same 18 events, same order — index N is the same event in both)

- Xin's 2-step (chain B): <https://www.phy.bnl.gov/twister/bee/set/72b1738a-0736-4b18-88f6-a17a45f3569d/event/list/>
- our 1-step (chain C): <https://www.phy.bnl.gov/twister/bee/set/92129f66-99c5-4275-9a23-54012cd1ae68/event/list/>

Order in `r3-pilot-mccv/bee-upload/bee-order.txt` (event ids ascending: 4, 6, 7, 11, …, 47).

### nugraph off — verified inert

`enable_nugraph_h5` (new fcl param → `labeler_truth.hdf5_output`) set `"false"` in
both fcls. Re-ran chain C on the 18 pilot events: `deep_compare` vs chain B still
**exact 18/18**, and every Bee zip's members hash-identical to the h5-on run.
`compile-both.sh` passes `enable_nugraph_h5=true` explicitly and still reads 0
differences. Change is in `wcp-porting-img` working tree, uncommitted (owner to
review); the diff is saved next to the run record.

## 5a. Open defect — to fix ourselves later (owner, 2026-09-10)

**MC CV event 471/18/33 crashes deterministically in both chains** (1 of 13,217;
in the 2-step's group mode it takes its whole 14-event group). Not filed upstream;
we fix it in our tree when the campaign is done.

- Where: stack overflow — 34,370 recursive `nanoflann::KDTreeBaseClass::divideTree`
  frames — from `DynamicPointCloud::index_new_points` (`clus/src/DynamicPointCloud.cxx:245`,
  the per-plane 2D k-d tree `kd2d.append`) ← `DynamicPointCloud::add_points` (`:153`)
  ← `clustering_connect1` (`clus/src/clustering_connect.cxx:702`,
  `global_skeleton_cloud->add_points(make_points_linear_extrapolation(…))`) ←
  `ClusteringConnect1::visit` ← `MultiAlgBlobClustering::operator()` (`:3961`).
- Hypothesis (unverified): a non-finite `dir1` / `extending_dis` / 2D projection for
  one cluster gives nanoflann points it cannot split on, so `middleSplit_` never
  makes progress. First thing to check: print/assert `std::isfinite` on the points
  returned by `make_points_linear_extrapolation` for this event.
- Fix shape, to decide: guard in `DynamicPointCloud::add_points` (drop non-finite
  points, log once) and/or fix the producer in `clustering_connect1`. Then re-run
  the event through both chains; the rest of the sample must stay byte-identical.
- Reproducer (~2 min): `production-prep/r3-crash-471-18-33/work-B/g0/.wct-cfg-ql.json`
  → `wire-cell -c` under gdb in SL7 (see `gdb-ql.log` there). Reco1 file
  `…/CV/reco1/000017/000170/reco1-detsim-g4-gen-Gen2_2026-67a3-4e42-52e3-19f7.root`,
  `--nskip 7`. Condensed backtrace: `crash-471-18-33-backtrace.txt` in this folder.
- Campaign impact: MC CV delivered 13,216/13,217; this event is absent from
  `run/bee` and `run/tracking-pr` and marked rc=11 in `summary-merged.csv`.

## 6. Owner decisions (2026-09-09)

1. **MC inputs**: same two `files-1000.lst` lists as #16/#19 — **yes**.
2. **Beam-off source**: (a) `FallValidationII_RollingDev_offbeamlight` v10_14_00 — used before, 36.9k available; or (b) `Fall25-Run1_InTime_offbeamlight` v10_14_02 — same campaign/version as beam-on, 68k available, never used here.
3. **Beam-on selection**: **fresh random 200 files** across the 3,335.
4. **Disk**: no known per-user quota. Retiring the old sync outputs: decide after the round.
5. **nugraph `.h5`**: **off this round** (see above).
6. **Step 2b**: **yes** — 10-event chain B vs C on every sample, plus Bee of both chains per sample.

2 (beam-off source) is still open; the SAM check is in §3.
