# Issue 21 — "type2" 8-event debug set: build, run, and why 7 of 8 have no candidate

Eight hand-picked events from a Bee evaluation set, extracted from the
production MC sample, merged into one artROOT, and run through the full
img → clus → match → tag → PR chain on the **synchronised** operating point
([#17](https://github.com/HaiwangYu/wire-cell-toolkit-ai-helper/issues/17)).

Work dir:
`/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-type2/`

**Result: 8/8 events processed cleanly, 1/8 produced a neutrino candidate.** The
other 7 are explained below and, on the evidence here, look like correct
behaviour rather than a chain failure — but the 4 near-boundary cases are worth
a physics opinion.

## 1. How the merged artROOT was built

Source: Bee indices **5, 9, 11, 15, 17, 18, 19, 24** of set
<https://www.phy.bnl.gov/twister/bee/set/763d6e03-16c1-44a2-be59-23ffd78bd872/event/list/>

### Step 1 — Bee index → RSE

| Bee | RSE | | Bee | RSE |
|---|---|---|---|---|
| 5 | 827/27/4 | | 17 | 707/18/12 |
| 9 | 36/77/17 | | 18 | 146/60/31 |
| 11 | 966/2/22 | | 19 | 921/29/10 |
| 15 | 304/6/28 | | 24 | 658/38/25 |

**Trap: only the `truth_unlabeled` layer carries the real RSE.** Every other
layer in that set reports `run/subrun = 0` with `event` = the ident, because the
set predates the RSE fix (#13 G3). Reading `clustering-global` would have given
`0/0/4` for Bee 5 and matched nothing downstream. Two owner-supplied values
(Bee 5 = 827-27-4, Bee 9 = 36-77-17) confirmed the extraction.

### Step 2 — RSE → reco1 file (samweb)

Definition
`mc_MCP2025C_FallProduction_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_reco1_sbnd`
(99,978 files).

**Trap: the MC query differs from the data recipe, and fails silently.** The
documented data form —
`defname:<DEF> and run_number <R> and sbnd.event_number_list %_<EVT>_%` —
returned **NOT FOUND for all 8**, because MC files **do not carry
`sbnd.event_number_list` at all**. That reads as "these events are not in the
sample" rather than "wrong query". There is also no `event_number` dimension
(`Unknown dimension: 'event_number'`).

The MC form is:

```
defname:<DEF> and run_number <run>.<subrun>
```

MC metadata encodes run/subrun as `Runs: 32.0010 (physics)`, and this returns
**exactly one file per run/subrun**; select the event inside the file afterwards.
All 8 resolved to 8 distinct files, each with the target event inside its
`First Event`–`Last Event` range.

### Step 3 — select + merge

The ported `FilterEventID` module (see
`larwirecell/Modules/FilterEventID_module.cc`, ported from sbndcode `feature/lynnt_evtfilter`),
run over the 8 files with one `RootOutput`:

```bash
lar -c filter-type2-rse.fcl -S reco1-files.lst
```

→ `type2-8evt-reco1.root`, **0.21 GB, exactly 8 events**, verified event by event
against the request (no extras, no missing), 76 products carried through
including `simtpc2d:dnnsp`, `SimChannel`, `OpFlash`, `MCTruth`.

**Caveat on the method:** `FilterEventID` matches on `run && event` and **ignores
subRun**. That is safe here only because all 8 runs are distinct; extending this
list needs that re-checked.

## 2. Chain run

`wcls-img-clus-matching-xin.fcl`, `pr_operating_point: "sync"`, one `lar` process
per event, 8 workers.

**8/8 rc=0, 0 audit failures, 0 RSE-check failures**, wall 50–110 s.
Output in `chain/run/{bee,tracking-pr,nugraph}`.

## 3. Why 7 of 8 have no candidate

Every one of the 8 has a true numu interaction. Splitting on deposited energy and
true vertex position (SBND active volume is roughly x ±200, y ±200, z 0–500 cm):

| event | Edep | true ν vertex (x, y, z) cm | reco | verdict |
|---|---|---|---|---|
| 36/77/17 | 320.3 | (−58.7, −128.1, 467.6) | **YES** — 329.0 MeV | interior |
| 304/6/28 | 932.4 | (−157.5, −168.9, 119.3) | no | near y edge |
| 658/38/25 | 691.5 | (163.8, **196.7**, 302.5) | no | at the y = +200 edge |
| 827/27/4 | 475.3 | (18.6, −163.2, **62.9**) | no | near the z = 0 face |
| 921/29/10 | 155.0 | (−132.4, **197.4**, **482.0**) | no | at the y and z edges |
| 146/60/31 | **0.0** | (−221.4, −426.4, 1154.1) | no | **outside the TPC** |
| 707/18/12 | **0.0** | (−260.1, −55.6, 431.9) | no | **outside (\|x\| > 200)** |
| 966/2/22 | **0.0** | (300.5, −417.1, 1040.0) | no | **outside the TPC** |

So the 7 split into two groups — but see the **correction** below: the first
group is not what it first appeared.

**Three report Edep = 0.0** with vertices well outside the active volume. My
first reading was "rock interactions, nothing to reconstruct, correctly
declined". ~~That is wrong~~ — see §3a.

**Four deposit 155–932 MeV but every in-beam cluster fails containment.**
Per-event tagger verdicts, from re-runs with the logs kept:

| event | in-beam clusters | FC | STM | tagger |
|---|---|---|---|---|
| 827/27/4 | 18, 19 | **false, false** | 1, 0 | "no neutrino candidate among 3 evaluated activities" |
| 304/6/28 | 5 | **false** | 1 | "…among 2 evaluated activities" |
| 658/38/25 | 16 | **false** | — | "…among 2 evaluated activities" |
| 921/29/10 | 5 | **false** | — | "…among 1 evaluated activity" |

**`FC=false` on every in-beam cluster in all four.** The neutrino tagger requires
a contained candidate, so it declines. The one event that reconstructs is the one
with a comfortably interior vertex.

That is consistent — activity starting at a boundary is likely to exit — so on
this evidence the chain is behaving as designed, not failing.


### 3a. CORRECTION (2026-09-01): the Edep = 0.0 events do have neutrino charge in the TPC

Found while uploading these events to Bee. The three "Edep = 0.0" events carry
**85–149 neutrino-labelled 3D points, well inside the active volume**:

| event | Edep (Bee truth node) | ν-labelled 3D points | their extent (cm) |
|---|---|---|---|
| 707/18/12 | **0.0** | **149** | x[−201, −38] y[116, 200] z[237, 500] |
| 146/60/31 | **0.0** | **140** | x[−191, 113] y[−199, −70] z[209, 368] |
| 966/2/22 | **0.0** | **85** | x[−11, −2] y[−200, −126] z[34, 84] |
| 827/27/4 (for scale) | 475.3 | 161 | x[−48, 82] y[−161, −122] z[4, 108] |

The vertices are outside the TPC, but daughters clearly entered and deposited
charge that the labeller attributes to the neutrino. **So "nothing to
reconstruct" was unsupported** — all 7 non-reconstructed events have
neutrino-attributed charge in the detector, not 4.

Worse, the two numbers disagree with each other. `Edep` is built in
`TensorSetLabeler.cxx:678-692` by summing `sim::SimEnergyDeposit::Energy()` over
deposits whose `abs(TrackID)` maps to a beam-neutrino interaction — the comment
calls it "the visible (reconstructable) energy". The nugraph `y_semantic == 0`
labels come from **the same truth trackid → neutrino association** in the same
module. They cannot both be right:

- if `Edep = 0.0` is correct, those 85–149 points are **mislabelled** as neutrino;
- if the labels are correct, `Edep` is **under-reporting**, and the Bee "mc" node
  energy is wrong for these events.

**Not resolved here.** It is a truth-labelling question, independent of the
containment question in §4, and it affects the `nu_edep` event metadata and the
Bee truth node text wherever it occurs — not just these 3 events.

**Method note for the record:** I drew the original conclusion from a single
field (`Edep`) without cross-checking it against another view of the same truth.
The nugraph labels were available the whole time and contradict it.

## 4. The open questions

**(a) Is `FC=false` correct for the four boundary events**, or is the
containment check too aggressive there?

**(b) Why does `Edep` read 0.0 on events with 85–149 neutrino-labelled 3D
points** (§3a)? One of the two truth views is wrong.

Deciding it needs more than these 8 events can give:

- whether the true final-state particles actually exit the active volume, or are
  contained and the clustering/containment check is losing them;
- whether the reconstructed cluster extent matches the true energy deposition —
  932 MeV (304/6/28) is a lot of energy to place at a boundary and discard.

Both are answerable from the Bee displays plus `SimChannel`, and neither is
answered here. **Nothing in this issue should be read as "the chain has a
containment bug"** — only that four energetic in-FV-ish events were rejected on
containment and that is worth an expert look.

## 5. Reproduce

```bash
# build the merged file
lar -c filter-type2-rse.fcl -S reco1-files.lst
# run the chain
run-harness.sh chain/lists/type2.manifest chain/run 8 1 wcls-img-clus-matching-xin.fcl
```

Scripts and the BEE→RSE→file audit trail (`found.map`, `rse.csv`) are in this
folder and in the work dir.
