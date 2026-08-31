# Issue 20 — SBND Wire-Cell PR campaigns: summary and data guide

One page covering everything produced by
[#16](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/16),
[#17](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/17),
[#18](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/18) and
[#19](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/19):
**five datasets, ~25,000 events, 320 GB**, all group-readable under `sbnd`.

Written to be shared. If you only read one section, read
[§2 Which dataset to use](#2-which-dataset-to-use) and
[§5 Three things that will bite you](#5-three-things-that-will-bite-you).

> **Status: validation output, not production.** No stability guarantee; it will
> be regenerated as the chain changes. Pin the git hashes in
> [§6](#6-provenance) in anything you publish.

---

## 0. Final validation: our 1-step **exactly reproduces** Xin's 2-step

Run 2026-08-31, before sharing. Xin's canonical 2-step chain was run on the same
10 MC events as the Bee set in §4, and compared against our synchronised 1-step
output **branch by branch**: all 21 `T_kine` branches, all 1216 `T_tagger`
branches, and every `T_rec_charge` point (x, y, z, q, cluster_id, flag_vertex,
flag_shower).

| comparison | exact match |
|---|---|
| **Xin 2-step vs our 1-step `sync`** | **10 / 10** |
| Xin 2-step vs our 1-step `preflip` | 6 / 10 |

**All 4 events with a reconstruction match exactly on `sync`.** Under `preflip`
**all 4 disagree** — the 6 "matches" there are the events where neither chain
found a candidate, which agree trivially.

| event | charge points, 2-step vs preflip |
|---|---|
| 713/0/11 | 147 vs **119** |
| 713/51/3 | 798 vs **1154** |
| 713/70/3 | 161 vs **153** |
| 713/74/3 | same count, `T_kine`/`T_tagger` differ |

So the issue-17 gap was real and material, and closing it made the two chains
agree exactly rather than approximately. **This is the T1 validation that #13
opened and #17 answered by config audit — now confirmed by actually running both
chains.**

### How it was run

Xin's "2-step" is really three stages, and the drivers under `sbnd_xin` hardcode
`/nfs/data/1/xqian/toolkit-dev` and expect pre-made dumps in a layout we do not
have. So the **canonical in-tree jsonnets** were driven directly — the same files
compiled for the #17 audit — with nothing under `sbnd_xin` read or modified:

| stage | what |
|---|---|
| A | `lar -c wcls-img-dump.fcl` and `wcls-flash-dump.fcl` → `icluster-apa*.npz`, `opflash_apa*.tar.gz` |
| B | `wire-cell -c pgrapher/experiment/sbnd/wct-clus-matching-perevt.jsonnet` → `pctree.tar.gz` |
| C | `wire-cell -c pgrapher/experiment/sbnd/wct-pr-perevt.jsonnet` (production 15-stage pipeline) → `tracking-pr.root` |

Scripts: `scripts/run-twostep.sh` (one event end to end),
`scripts/deep_compare.py` (the branch-by-branch comparison).
Outputs kept at `production-prep/twostep-validation-2026-08-31/`.

**Scope of the claim:** 10 MC events, of which 4 have a reconstruction. It
establishes that the two chains agree exactly where they reconstruct, not that
they agree on all 13k — and it says nothing about the data or nueCC samples,
which have no 2-step counterpart here.

## 1. What was run

The 1-step LArSoft chain: imaging → clustering → Q/L matching → TGM/STM/FC
tagging → **pattern recognition** (neutrino tagger + both BDT scorers), one
`lar` process per event.

The four issues in order:

| | what |
|---|---|
| **#16** | 13,213 MC events (Gen2 CV), first campaign with the PR chain on |
| **#17** | Found the 1-step chain was **160 PR knobs adrift** from Xin's 2-step, then fixed it |
| **#18** | 1000 beam-on + 1000 beam-off real-data events |
| **#19** | 8,866 nueCC signal events — the first campaign on the corrected configuration |

**#17 is the reason there are two versions of #16 and #18.** Our chain called
`clus_maker.pr()` with 7 arguments where Xin's entry point passes 351, so it
silently inherited conservative defaults — 139 of the missing knobs on the
neutrino tagger alone. That is now fixed and gated; #16 and #18 were re-run on
the corrected configuration, and **both versions are kept**.

- **`preflip`** — the original, missing the 160 knobs.
- **`sync`** — the SBND production operating point, verified by compiled diff
  against Xin's chain (gate at 0 differences).

**Use `sync` unless you specifically need to reproduce the earlier results.**

## 2. Which dataset to use

| dataset | events | location (under `/exp/sbnd/data/users/yuhw/production-prep/`) | size |
|---|---|---|---|
| **MC CV — sync** | 13,211 | `img-clus-match-tag-pr-mc-1000file-sync-2026-08-30/run/` | 84 G |
| MC CV — preflip | 13,213 | `img-clus-match-tag-pr-mc-1000file-2026-08-20/` | 84 G |
| **nueCC signal — sync** | 8,866 | `img-clus-match-tag-pr-nuecc-1000file-2026-08-29/run/` | 67 G |
| **beam-on data — sync** | 1,000 | `img-clus-match-tag-pr-data-1000evt-sync-2026-08-30/beam-on/` | 2.3 G |
| **beam-off data — sync** | 1,000 | `img-clus-match-tag-pr-data-1000evt-sync-2026-08-30/beam-off/` | 2.3 G |
| beam-on data — preflip | 1,000 | `img-clus-match-tag-pr-data-1000evt-2026-08-21/beam-on/` | 2.3 G |
| beam-off data — preflip | 1,000 | `img-clus-match-tag-pr-data-1000evt-2026-08-21/beam-off/` | 2.3 G |

There is **no nueCC preflip** dataset — that sample was only ever run on `sync`.

Every dataset has the same three deliverables, one file per event, named for its
`(run, subrun, event)` so the three join on the filename:

```
bee/bee_r<run>_s<sub>_e<evt>.zip                 event display, 16-20 layers + mc.json
tracking-pr/tracking-pr_r<run>_s<sub>_e<evt>.root  Trun/T_tagger/T_kine/T_rec_charge/...
nugraph/nugraph_r<run>_s<sub>_e<evt>.h5            ML graph (see the WIP warning)
summary.csv                                        one row per event + the input file path
```

**Read in place** — 320 GB total, please don't copy it.

### For a given task

| you want to… | use |
|---|---|
| train **DL vertexing** | `tracking-pr` → `T_rec_charge` (x,y,z,q in cm) |
| train the **BDT** | `tracking-pr` → `T_tagger` (1216 features) |
| reconstructed ν energy / π⁰ | `tracking-pr` → `T_kine` |
| **truth** for an MC/nueCC event | the Bee `mc.json` (truth ν vertex in `data.start`, cm), or the input file named in `summary.csv` |
| **look at events** | Bee — §4 |
| nugraph / GNN | the `.h5`, **but read §5** |

`tracking_pr` contains **no truth**. On data its `mc.json` is reco-only.

## 3. Results at a glance

| | MC CV | nueCC signal | beam-on | beam-off |
|---|---|---|---|---|
| events ok | 13,211 / 13,217 | 8,866 / 8,877 | 1000 / 1000 | 1000 / 1000 |
| candidates (`kine_reco_Enu>0`) | 45.3% | **93.3%** | 44.3% | 5.5% |
| **`nue_score > 0`** | 0.54% | **52.97%** | 0.50% | **0.00%** |
| `numu_score > 0` | 29.1% | 45.7% | 29.1% | 1.4% |
| wall/event | 68.0 s | 81.5 s | 58.9 s | 64.8 s |

*(sync arm throughout; nueCC efficiency is reconstruction reach, not a selection.)*

**The headline physics check:** a `nue_score > 0` selection keeps **52.97%** of
true nueCC events, **0.54%** of CV background, and **0 of 1000** beam-off data
events — roughly **98:1** signal-to-background, with a clean null off beam.

Separately, beam-on vs beam-off candidate rates differ by **12.7×** (23σ) —
same chain, same config, real data, no truth involved.

**What synchronising changed** (per-event A/B on identical inputs, 13,209 matched
MC events):

- candidate rate 43.9% → 45.3%
- `kine_reco_Enu` moved on **96%** of events kept by both: median shift ≈ 0, but
  p10 −26% and p90 +51% — a redistribution, not an offset
- selected background **down a third**: `nue_score>0` 0.81% → 0.54% on MC,
  0.20% → **0.00%** on beam-off

**Unmeasured:** with no nueCC preflip arm, we cannot show signal efficiency
survived the change. Background rejection clearly improved; the signal side is
unverified across it.

## 4. Bee links (10 events each)

The MC / beam-on / beam-off pairs use the **same events** in both arms, so Bee
event index N is the same physical event — flip between tabs to see what the
sync did.

| sample | sync | preflip |
|---|---|---|
| MC CV | [chain](https://www.phy.bnl.gov/twister/bee/set/f18ad45e-03b7-40d6-acd8-cc1a0d6451ab/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/40e293dc-5942-43f3-8368-e3b06f9ac653/event/list/) | [chain](https://www.phy.bnl.gov/twister/bee/set/7b32d62c-feff-4ace-9a93-ae81ce8472f8/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/58769843-3b83-4a66-864e-911ae74a4d57/event/list/) |
| nueCC signal | [chain](https://www.phy.bnl.gov/twister/bee/set/0acc7d6a-80bd-44f8-8a0b-23c394f55656/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/bb564577-0fe7-4560-93cc-7911b0322ec2/event/list/) | — |
| beam-on data | [chain](https://www.phy.bnl.gov/twister/bee/set/c7165e24-1261-4c14-9110-e9955b53a324/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/df3062c1-4588-4ecc-94f1-85977274e6ac/event/list/) | [chain](https://www.phy.bnl.gov/twister/bee/set/ab182045-96b0-4bbf-8a5c-6de64915e83c/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/ab1514e6-ba9a-4c7f-bfac-dae731417d05/event/list/) |
| beam-off data | [chain](https://www.phy.bnl.gov/twister/bee/set/58e6d925-67fa-4d36-9636-0ab2030d21ef/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/0c0756cf-b490-476b-8618-597e9737e3e2/event/list/) | [chain](https://www.phy.bnl.gov/twister/bee/set/1598bf66-e444-4a74-bb44-0ec830a3ec7b/event/list/) · [nugraph](https://www.phy.bnl.gov/twister/bee/set/b4750a68-97a9-40ff-bf8a-f40c5edda232/event/list/) |

To view any other events, merge their per-event zips and upload:

```bash
python3 issues/18-.../scripts/merge_bee.py out.zip <bee/bee_*.zip ...>
BROWSER=echo bash sbnd/sbnd_xin/upload-to-bee.sh out.zip
```

Caveat on the MC/data sets above: those 10 events happen to contain **no gained
or lost candidates**, while the full sample had 280 gained and 90 lost. They show
energy shifts, not verdict flips.

## 5. Three things that will bite you

**1. Select on `kine_reco_Enu > 0` — never on file size.** There are three
classes of `tracking-pr.root`, and size cannot separate them:

| class | what it is |
|---|---|
| ~8 kB | no trees beyond `Trun`/`T_bad_ch`/`T_proj`. `f.Get("T_tagger")` returns a **null pointer** — a naive loop crashes |
| ~211 kB, **empty** | the tagger ran but found no main vertex: 1216 branches booked, `T_rec_charge` empty, `Enu = 0.00`, and `numu_score` looks like a real number |
| larger | a usable reconstruction |

```python
tk = f.Get("T_kine")
if tk and tk.GetEntries():
    tk.GetEntry(0)
    if tk.kine_reco_Enu > 0:      # usable
        ...
```

Filtering on size over-counts, badly on beam-off (7.5% vs the true 3.3%).
`issues/16-.../scripts/count_criteria.py` reports all three criteria.

**2. `T_tagger`, `T_kine` and `T_rec_charge` carry no RSE.** Only `Trun` and
`T_bad_ch` do. A `TChain` over thousands of files therefore loses event identity
**silently**. Read `Trun` per file, or parse the filename.

**3. `nue_score` is a discretized discriminant, not a continuous score.** It
saturates at three values, and `-15.0000` means "background-like", not "not
evaluated":

| value | MC CV | nueCC signal |
|---|---|---|
| +4.3009 | 0.5% | **45.5%** |
| −4.3009 | 5.5% | 7.8% |
| −15.0000 | 91.8% | 28.1% |

Don't treat it as continuous, and don't read a high `-15` fraction on a
background sample as a bug — it is the discriminant rejecting.

### Also worth knowing

- **nugraph is WIP and unvalidated.** `pos` is in **mm** (Bee and
  `T_rec_charge` are cm); `semantic_classes` is only `['nu','cosmic']`; every
  event is labelled `train`; on **data** the labels are all −1, so it carries
  features and **no training target**. The `apa0` in the dataset key is a naming
  artifact — the graph spans both APAs.
- **Read with the same stack that wrote it**: ROOT 6.28.12 / e26 inside SL7,
  `source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh`.
- **`summary.csv`** carries per-event rc, wall, peak RSS, the three file sizes,
  an `audit` verdict, an `rse_check` verdict, and the input file path.
- **Known chain defects** in these datasets: a `vector::_M_range_check` with
  `__n == size()` (reproducible on ~6 events per 13k, same indices across
  campaigns), occasional SIGSEGV, and **2 nueCC events that hang in
  `TaggerCheckNeutrino.cxx:2431`** — logs preserved in issue 19.

## 6. Provenance

| repo | branch | commit |
|---|---|---|
| wire-cell-toolkit | `ap-yuhw` | `14f0aeeb` (+ merge `40cb45fc`) |
| wcp-porting-img | `main` | `18d9ccb` |
| larwirecell | `dev-v10_14_02_02` | `a02a1a4` |
| sbndcode | `wcp-porting` | `2260962f0` |
| wire-cell-data | `master` | `9e2f4b8` + untracked `uboone/weights/XGB_nue_seed2_0923.xml` (**required**) |

Config: `sbnd/wcls-img-clus-matching-xin.fcl` (`-data.fcl` for data), with
`pr_operating_point: "sync"` or `"preflip"`.

Inputs: MC CV and nueCC from `aurora` dCache; the two data samples are
merged+frameshifted artROOT files under
`production-prep/{add-frameshift-data-2nd-2k-2026-08-15,img-clus-match-tag-pr-data-1000evt-2026-08-21/beam-off-prep}/`.
Every Gen2 real-data file must have `run_frameshift.fcl` applied before this
chain or the TPC/PMT alignment is wrong and Q/L matching is meaningless.

## 7. Open items

1. **No nueCC preflip arm** — signal efficiency across the sync is unmeasured. A
   subset run would close it (~1 h). (The 2-step validation in §0 confirms the
   configuration is right; it does not measure signal efficiency.)
2. **nugraph validation** — nobody has checked the labels.
3. **The `_M_range_check` bug** — reproducible test cases exist across three
   campaigns; unfixed.
4. **The two `TaggerCheckNeutrino` hangs** — pre-existing or exposed by the sync
   is undetermined.
5. `wire-cell-toolkit` and `wcp-porting-img` commits are **unpushed**, pending
   review.

## 8. Contact

Haiwang Yu. Quote a `(run, subrun, event)` — it is the key to all three
deliverables and to `summary.csv`.
