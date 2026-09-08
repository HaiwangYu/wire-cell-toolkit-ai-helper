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

---

## 7. Extension: the full 25-event list (2026-09-02)

The original extraction took only the 8 events I had been asked to look up by
BEE index.  On request, the same method was re-run for **all 25 events** of BEE
set `763d6e03-16c1-44a2-be59-23ffd78bd872`, merged into one artROOT.

**Output:** `/exp/sbnd/data/users/yuhw/wcp-porting-img/sbnd/img-clus-matching-eval/prabhjot-100file-Aug5-debug-25evt/`
- `debug-25evt-reco1.root` -- 0.66 GB, exactly 25 events, 76 products
- `rse.csv`, `found.map`, `reco1-files.lst`, `filter-25evt-rse.fcl`, `filter.log`, `README.md`

Both traps from S3 applied unchanged: RSEs come only from the
`truth_unlabeled` layer, and the samweb query is
`defname:<DEF> and run_number <run>.<subrun>` (MC has no
`sbnd.event_number_list` and no `event_number` dimension).

### New wrinkle at 25 events: file and pair collisions

The 8-event subset happened to hit 8 distinct run/subruns.  The full list does
not -- **20 unique files carry the 25 events**:

| run.subrun | selected events |
|---|---|
| 105.23 | 2, 5, 21 |
| 651.84 | 12, 34 |
| 890.21 | 16, 39 |
| 921.29 | 10, 41 |

Two consequences:

1. `found.map` contains repeats, so it **must** be deduplicated before being
   handed to `lar -S`; the list is 20 lines, not 25.
2. `FilterEventID` matches on `(run, event)` and **ignores subRun** (see
   `FilterEventID_module.cc:111`).  With several subruns of the same run now in
   play, that could silently admit an unrequested event.  Checked before
   running: all 25 `(run, event)` pairs are unique here, so the filter is
   exact.  **This check is mandatory for any future extraction** -- a
   same-`(run, event)` in a different subRun would pass the filter, and the
   only way you would notice is the final `EventAuxiliary` comparison.

### Verification

`lar -c filter-25evt-rse.fcl -S reco1-files.lst` -- 1m58s, rc=0, 25
`is_in_list: 1`.  Reading `EventAuxiliary` via PyROOT, the set of
`(run, subrun, event)` in the output is an **exact match** for the 25 requested
triplets: nothing missing, nothing extra.

The full-chain run (`img-clus-match-tag-pr`) on these 25 events has **not** been
done yet -- only the 8-event subset in S4-S6 above has chain results.

## 8. Full chain on the 25 events (2026-09-02)

`img-clus-match-tag-pr` over all 25, same harness as S4 (per-EVENT manifest,
one `lar` per event, `taskset`, `/usr/bin/time -v`, `check-pr-run.sh` audit,
Trun-authoritative renaming).

**25/25 ok, 2m38s wall, 16 workers x 1 core**, 1.8-2.3 GB peak RSS and 44-155 s
per event.  Zero failures, zero audit failures, zero RSE mismatches.
fcl `wcls-img-clus-matching-xin.fcl`, `pr_operating_point` default = **sync**.

- Bee (25 evt): <https://www.phy.bnl.gov/twister/bee/set/98bb8bb8-2f81-4a4e-bed1-2b70fd99ad9b/event/list/>
- nugraph sp: <https://www.phy.bnl.gov/twister/bee/set/95bca6c8-2842-4a54-810d-67398339313f/event/list/>
- outputs + `summary.csv` + `lists/bee-order.txt` (Bee index -> RSE) under
  `.../prabhjot-100file-Aug5-debug-25evt/chain/`

### Candidate rate 15/25 = 60%

`tracking-pr` splits cleanly in two, with nothing in between:

| class | n | size | trees |
|---|---|---|---|
| reconstructed | 15 | 227-324 kB | + `T_proj_data`, `T_rec_charge`, `T_kine`, `T_tagger` |
| empty | 10 | ~8 kB | `Trun`, `T_bad_ch`, `T_proj` only |

The empty ones have **no** `T_rec_charge`/`T_kine`/`T_tagger` -- no PR candidate
was selected at all.  Consistent with the `kine_reco_Enu > 0` definition of
"usable reconstruction" adopted in issue 20.  Empty: 105/23/21, 146/60/31,
272/2/30, 304/6/28, 411/27/8, 658/38/25, 707/18/12, 827/27/4, 921/29/10,
966/2/22.  These 10 are the natural work list for the debugging this event set
was assembled for.

### The 8-event subset reproduces byte-for-byte

All three deliverables for the 8 overlapping events are byte-identical between
the S4 run and this one (e.g. 36/77/17: bee 6492302, tracking-pr 243078,
nugraph 1542012 in both).  Worth stating explicitly: it means the config was
restored exactly, so the 10 empty-PR events are a property of the events, not
of a drifted configuration.

### Trap: the run needs BOTH trees at the pre-merge state

Two smoke attempts failed first, because the checkouts had drifted onto the
issue-22 merge work while `opt/` still holds the pre-merge build:

| tree on merge state | error at job construction |
|---|---|
| `wcp-porting-img` jsonnet (`eb_fast/po_fast/dg_fast`) | `unknown graph flavor relaxed_fast` |
| `wire-cell-toolkit` on `merge-master-2026-09-02` (its `cfg/`) | `function has no parameter assoc_clear_on_merge` |

Both are config-vs-installed-library mismatches: the source trees are read at
runtime (`WIRECELL_PATH` points into the WCT checkout's `cfg/`), so switching a
branch silently changes what a job runs even though nothing was rebuilt.
**Any campaign run while issue 22 is open must pin `wire-cell-toolkit` to
`ap-yuhw` (`14f0aeeb2`) and keep the wcp-porting-img jsonnets at HEAD.**  Both
trees were returned to their merge-WIP state afterwards (WIP backed up to the
scratchpad first, since in wcp-porting-img it is working-tree-only and exists
in no branch).

### Re-uploaded with the source set's event numbering

The first upload numbered Bee events by the RSE sort, which does not line up
with the source set 763d6e03 and so cannot be cross-referenced against it.
Re-packed in the original index order and re-uploaded:

- Bee (25 evt): <https://www.phy.bnl.gov/twister/bee/set/9bcfbad4-4091-4ae3-b955-e3df51e81c66/event/list/>
- nugraph sp: <https://www.phy.bnl.gov/twister/bee/set/84a6695f-70d8-4e1c-8d16-537a85f3f932/event/list/>
- superseded (RSE-sorted): bee `98bb8bb8-...`, nugraph `95bca6c8-...`

Bee index now equals the source set's index for all 25 -- idx 5 = 827/27/4,
idx 9 = 36/77/17, matching the two the source set was originally queried for.
Verified by reading `runNo`/`subRunNo`/`eventNo` back out of the JSON payloads
in the packed zip, not by trusting the file order.

`package-bee.sh` now takes an explicit order file (`<idx> <run> <sub> <evt>`)
instead of the manifest, and **asserts** it is contiguous from 0 and that every
event has a Bee zip.  `merge_bee.py` renumbers by argument position, so a gap or
a non-contiguous index column would silently shift every later event's number --
the one failure mode that produces a plausible-looking but wrong set.  Two order
files are kept: `lists/bee-orig-order.txt` (source-set numbering, used here) and
`lists/bee-order.txt` (RSE-sorted).
