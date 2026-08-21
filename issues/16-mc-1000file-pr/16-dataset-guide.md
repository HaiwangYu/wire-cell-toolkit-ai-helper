# SBND Wire-Cell pattern-recognition dataset — 13,213 MC events

A user guide for the output of the 2026-08-20 campaign: the full 1-step
Wire-Cell chain (imaging → clustering → Q/L matching → TGM/STM/FC tagging →
**pattern recognition**) run over 13,213 Gen2 MC events.

Production details, measurements and failure analysis:
[ai-helper issue #16](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/16)
· [production doc](16-mc-1000file-pr.md)

> **Status: validation output, not production.** This exists to be looked at and
> to seed training work. It carries no stability guarantee and will be
> regenerated as the chain changes. Pin the git hashes below in anything you
> publish from it.

---

## 1. Where it is

All three datasets are one file per event, group-readable (`yuhw:sbnd`, mode
644), under a common root:

```
/exp/sbnd/data/users/yuhw/production-prep/img-clus-match-tag-pr-mc-1000file-2026-08-20/
```

| dataset | path | files | size | per event |
|---|---|---|---|---|
| **Bee** event displays | `bee/bee_r<run>_s<subrun>_e<event>.zip` | 13,213 | 67 GB | 5.41 MB mean, 38.8 MB max |
| **`tracking_pr`** reco trees | `tracking-pr/tracking-pr_r<run>_s<subrun>_e<event>.root` | 13,213 | 1.6 GB | 0.12 MB mean |
| **nugraph** ML graphs | `nugraph/nugraph_r<run>_s<subrun>_e<event>.h5` | 13,213 | 16 GB | 1.25 MB mean, 9.4 MB max |

Plus `summary.csv` — one row per event (run, subrun, event, rc, wall time, peak
RSS, the three file sizes, audit verdict, **and the input reco1 file path**).
That last column is how you get back to the truth in the source file.

**Read in place.** 85 GB total; please don't copy it wholesale.

**Filenames are the event ID.** Every file is named for its `(run, subrun,
event)`, and all 13,213 triplets are unique — so the three datasets join on the
filename, and no file was silently overwritten.

## 2. Which dataset answers which question

| you want to… | use | notes |
|---|---|---|
| train **DL vertexing** | `tracking_pr` → **`T_rec_charge`** | 3D reco charge points; §4 |
| train the **BDT** | `tracking_pr` → **`T_tagger`** | 1216 features; §5 |
| **look at events** / get truth for a `tracking_pr` event | **Bee** zip | §3 |
| reconstructed ν energy, π⁰ kinematics | `tracking_pr` → `T_kine` | 21 branches |
| **nugraph / GNN** work | nugraph `.h5` | **WIP, unvalidated** — §6 |

### `tracking_pr` is reco-only — truth lives in the Bee

`tracking-pr_*.root` contains **no truth at all**. To get the truth for one of
its events, open the Bee zip with the same RSE in its filename. The Bee
`mc.json` carries the true interaction and the **true neutrino vertex**, which
is what makes the pair usable as a training set.

The other route, for truth the Bee doesn't carry (`SimChannel`, full
`MCParticle` trees): the input reco1 file path in `summary.csv`, from which
everything was reconstructed.

## 3. Bee — `mc.json` now carries truth **and** reco

This is new in this campaign. Bee renders one particle tree per event, so truth
and reco had to be grafted into a single array:

- **truth** nodes at top level — e.g.
  `1 numu RES NC Etot 3842.7 MeV Edep 12.8 MeV T 1.455 us`, with the **true
  neutrino vertex** in that node's `data.start` as `[x, y, z]` in cm;
- **reco** hung under one node reading
  `reco nu <kine_reco_Enu> MeV numu <numu_score> nue <nue_score>`.

Measured over 300 random events: **`mc.json` present in 300/300**, of which
45.7% are truth+reco and 54.3% truth-only. Truth is never dropped because reco
is absent.

Twenty point/label layers per event, of which **seventeen are always present**:
`img-global`,
`clustering-{global,apa0-face0,apa1-face0}`, `clustering-pr-global`,
`truth_trackid_labeled`, `truth_unlabeled`, three `sed-*` (SCE / smearing
variants), `op`, four `tagger_{tgm,stm,fc,lm}`, two `channel-deadarea-*`.
The remaining **three appear only when the event has a reconstructed
candidate**: `track_fit-global`, `shower_track-global`, `vertices-global`.

To view: upload a merged zip to <https://www.phy.bnl.gov/twister/bee>. Merge
per-event zips into one multi-event set with `scripts/merge_bee.py out.zip
in0.zip in1.zip ...`. Two 10-event examples are live:
[full chain](https://www.phy.bnl.gov/twister/bee/set/958ac47a-c5b7-49ac-8f06-6794dff7986a/event/list/)
· [nugraph space points](https://www.phy.bnl.gov/twister/bee/set/58769843-3b83-4a66-864e-911ae74a4d57/event/list/)

## 4. DL vertexing — `T_rec_charge`

One entry per reconstructed 3D charge point — over 300 sampled candidate
events, median **225** points, p90 639, max 1282 — in 19 branches:

```
x  y  z  q  nq  chi2  ndf  pu  pv  pw  pt  reduced_chi2
flag_vertex  flag_shower  rr
cluster_id  real_cluster_id  sub_cluster_id  particle_id
```

- `x, y, z` in **cm**, in SBND detector coordinates (measured spans: x ±201,
  y ±200, z 0–501).
- `q` is charge; it can be **negative** (a −1000 sentinel appears) — filter
  before training.
- `flag_vertex` / `flag_shower` mark vertex and shower-like points.
- **`T_rec_charge` can have 0 entries even in a non-stub file** — the tree
  exists but is empty. Check `GetEntries()`, don't assume.
- Target: the true neutrino vertex from the Bee `mc.json` truth node's
  `data.start` (also cm), same RSE.

## 5. BDT — `T_tagger`

One entry per event, **1216 branches** — the full feature set the neutrino
tagger computes: `nu_{x,y,z}`, the `cosmic_*` family, and the per-topology
blocks. Alongside it `T_kine` (21 branches) carries `kine_reco_Enu`,
`kine_energy_particle` and the π⁰ block.

**Read `numu_score` and `nue_score` with care.** Measured over 400 random
candidate events:

| | min | median | max |
|---|---|---|---|
| `numu_score` | −4.10 | 0.80 | 4.30 |
| `nue_score` | −15.00 | **−15.00** | 4.30 |

`nue_score` is **exactly −15.00 in 75% of events** — a floor/sentinel, not a
score. Do not treat it as a continuous variable without understanding that
clipping first. `numu_score` looks like a genuine BDT output.

## 6. nugraph — work in progress, **not validated**

Treat this as a preview. It is produced, it is self-consistent, and **nobody has
validated it**. Do not publish physics from it.

Per file: one `dataset/<run>_<subrun>_<event>__rec-lab-apa0-1` record with
`sp/` 3D nodes (`pos`, 6 `features`, `y_semantic`, `y_instance`,
`edge_label_index`, `edge_y`) and per-plane `u/ v/ y/` nodes with `pos`, 15
features, and `*_nexus_sp/edge_index` linking planes to 3D.

Four things to know before using it:

1. **`pos` is in mm**, unlike everything else here (Bee and `T_rec_charge` are
   cm).
2. **`semantic_classes` is only `['nu', 'cosmic']`** — a two-class labelling,
   not the multi-class semantics a nugraph model usually expects.
   `y_semantic == -1` marks ghost/unlabeled points, and these are a large
   fraction (155 to 2040 of a few thousand across the 10 hand-scanned events).
3. **The `apa0` in the key is a naming artifact, not a coverage limit.** The
   graph spans both APAs — sampled x ranges run −234 to +234 cm, roughly
   balanced across the cathode. You are not missing half the detector.
4. **Every event is labelled `train`** (`samples/train` holds the one key;
   `test` and `val` are empty). Re-split yourself.

## 7. Gotchas that will bite you

**Only `Trun` and `T_bad_ch` carry RSE.** `T_tagger`, `T_kine` and
`T_rec_charge` have **no run/subrun/event branches**. A `TChain` over 13,213
files therefore loses event identity entirely, silently. Either read `Trun`
per file, or parse the filename — and if you build a flat training table, add
the RSE column yourself.

**55% of `tracking-pr.root` files are stubs, and the trees are *absent*, not
empty.** 7,253 of 13,213 events (54.9%) had no neutrino candidate; those files
are ~8.2 kB and contain only `Trun`, `T_bad_ch`, `T_proj`. `f.Get("T_tagger")`
returns a **null pointer**, so a naive loop crashes rather than skipping.
Guard on it, or pre-filter on file size > 20 kB — size alone is a reliable
index of "the tagger accepted this event", verified against a hand scan.

So the usable sample for BDT / vertex training is **5,960 events (45.1%)**, not
13,213.

**Four events are missing** — don't chase them. They crashed and were
discarded:

| run/subrun/event | mode |
|---|---|
| 719/77/35 | `vector::_M_range_check` |
| 714/44/10 | `vector::_M_range_check` |
| 471/18/33 | SIGSEGV in clustering |
| 718/51/3 | `vector::_M_range_check` |

Three of the four reproduce from the previous campaign at the same event with
the same out-of-range index, so they are a standing chain bug, not corruption
of this dataset.

**Environment.** Everything was written by ROOT 6.28.12 / e26 inside the SL7
container. Read with the same stack:
`source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh`.

**Known physics defects**, from a 10-event hand scan by the owner: W-plane
prolongation of cosmics appeared in 2 of 10 events and in one case produced a
neutrino candidate from a cosmic
([issue #10](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/10));
one event reconstructed a candidate with no in-beam activity; π⁰
reconstruction was correct in one of two π⁰ events. The false-positive rate is
not yet quantified on the full 13k.

## 8. Provenance

### Input

1000 files of
`aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/reco1`,
13 events each. File list `files-1000.lst`, md5
`4dc75514e652bddf49e41459a5091080` — byte-identical to the list used by
[issue #11](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/11),
so the two campaigns are directly comparable event by event. Coverage: 16 runs,
1000 distinct run/subrun pairs.

These inputs carry production `dnnsp` signal processing and **no
`raw::RawDigit`**, so nothing here exercises noise filtering or signal
processing — this measures clustering, matching, tagging and pattern
recognition on production SP.

### Code

Local repositories as they stood when the run started. None of this is on a
release; `wire-cell-toolkit` in particular is a personal branch.

| repo | path | branch | commit | last commit |
|---|---|---|---|---|
| wire-cell-toolkit | `/exp/sbnd/app/users/yuhw/wire-cell-toolkit` | `ap-yuhw` | `40cb45fcc` | 2026-08-20 20:35 |
| wcp-porting-img | `/exp/sbnd/app/users/yuhw/wcp-porting-img` | `main` | `4afb6f218` | 2026-08-20 13:48 |
| larwirecell | `/exp/sbnd/app/users/yuhw/larsoft-wct036/v10_14_02/srcs/larwirecell` | `dev-v10_14_02_02` | `a02a1a4d8` | 2026-08-18 12:51 |
| wire-cell-data | `/exp/sbnd/app/users/yuhw/wire-cell-data` | `master` | `9e2f4b841` | 2026-07-13 14:35 |
| sbndcode | `/exp/sbnd/app/users/yuhw/sbndcode` | `wcp-porting` | `2260962f0` | 2026-08-18 12:56 |

`wire-cell-toolkit` `40cb45fcc` is a merge of `origin/apply-pointcloud` into
`ap-yuhw`; that branch is **not pushed** as of writing.

`wire-cell-data` is clean except for one **required** untracked file,
`uboone/weights/XGB_nue_seed2_0923.xml` — the nue BDT weights. Without it the
`nue_score` column is meaningless.

Installed libraries actually loaded at run time (a separate install tree that
can drift from source — these are the timestamps that matter):

| library | built |
|---|---|
| `opt/lib/libWireCell{Util,Aux}.so` | 2026-08-20 20:48 |
| `opt/lib/libWireCell{Clus,Img,Match,Root,Sio}.so` | 2026-08-20 20:51–20:53 |
| `opt/larwirecell/.../libWireCell{AIML,Larsoft,QLMatch}.so` | 2026-08-20 21:09 |

### Configuration

`sbnd/wcls-img-clus-matching-xin.fcl` + `sbnd/wcls-img-clus-matching-xin.jsonnet`
in `wcp-porting-img`, with `reality: "sim"`, `enable_tracking_root: "true"`, and
DL (SCN) vertexing enabled via `sbnd/setup-dlvtx.sh`. The 15-name `clus_pr`
pipeline runs the neutrino tagger and both BDT scorers.

### Run

One `lar` process per event, 32 concurrent, 2026-08-20 22:42 → 2026-08-21 05:11
CDT (6 h 29 m, 192 core-hours). **13,213 of 13,217 events succeeded (99.97%)**
with zero missing or zero-size deliverables and zero RSE collisions.

Every event was audited for silent failure — DL-vertex fallback to geometric,
unregistered RSE attacher, unlabeled pass-through, blob loss — and **none
fired** on any of the 13,213 successes. The `audit` column in `summary.csv`
records this per event.

## 9. Contact

Haiwang Yu. Questions about a specific event: quote its `(run, subrun, event)`
— that is the key to all three datasets and to `summary.csv`.
