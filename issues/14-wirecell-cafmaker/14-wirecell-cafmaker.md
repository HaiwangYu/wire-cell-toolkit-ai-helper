# Issue 14 — Wire-Cell CAFMaker (`larwirecell/CAFMaker`)

Get SBND Wire-Cell reconstruction into the Common Analysis Format, modelled on
`sbncode/CAFMaker`. **Planning only so far — nothing implemented.**

Primary document: `wcp-porting-img/sbnd/docs/6-cafmaker-plan.html`
Work dir: `/exp/sbnd/data/users/yuhw/production-prep/cafmaker-dev`
Follows on from issue #13 (the PR-chain port), which produced the reco output
this consumes.

## Where to find a real `tracking-pr.root`

It is written to the job's CWD under that fixed name, with no RSE in it:

```
<outdir>/work/e_<fileidx>_<evtidx>/tracking-pr.root   # 1-step, 1 event per lar process
<out_root>/pr_evt<ID>/tracking-pr.root                # sbnd_xin 2-step driver
```

The harness deletes its per-event workdir, so no durable copy existed. A
reference set is preserved, renamed by RSE:

```
/exp/sbnd/data/users/yuhw/production-prep/cafmaker-dev/sample-tracking-pr/
    tracking-pr_r925_s23_e{2,6,11,22,24,25}.root     8 kB each
    tracking-pr_r925_s23_e{4,9,18,20}.root      218-318 kB
```

All 10 events of MCP2025C run 925-23, current build, full 15-stage pipeline,
1.2 MB total.

### The two size states matter for CAFMaker

The 8 kB files contain ONLY `T_bad_ch`, `T_proj`, `Trun` -- `T_tagger`,
`T_kine`, `T_rec_charge`, `T_proj_data` are **entirely absent**. That is every
event where the neutrino tagger selected no candidate: **6 of these 10**. So
"no PR content" is the COMMON case and a filler must treat absent trees as
normal, not as an error.

**And that signature is indistinguishable from the G9 multi-event corruption.**
The corrupted `lar -n 5` file was 8261 bytes with T_tagger/T_kine absent; a
legitimate no-candidate event is 8243-8282 bytes with exactly the same three
trees. You cannot tell a silently corrupted production run from one where the
tagger declined every event by inspecting the files -- a further argument for
reading the products in memory, where "no candidate" is an explicit state.

## The two questions, answered

### Q1 — can all of `tracking-pr.root` go into CAF?

Mechanically almost all, but **no, and you would not want it to**. Three reasons.

**Two of the seven trees are display data.** `T_proj_data` (per-channel
projections) and `T_bad_ch` (dead-channel ranges) drive Magnify. Per-channel
waveform-adjacent content is exactly what CAF is designed not to carry; dead
channels are detector state, not per-event reco.

**~97% of `T_tagger` is BDT input, not output.** Measured: 1216 branches, 1026
scalar (1023 float + 3 int) + 190 vector. Only **42 are `*_score`**; the other
~1174 are the features those BDTs consume. Two consequences -- size (1023 floats
= 4.1 kB/interaction before the vectors; CAF is meant to be small and widely
copied) and meaning (they encode uBooNE's selection logic, and nobody has
characterised their SBND behaviour).

**The scores are uncalibrated on SBND.** Both weight sets are stock
uBooNE-trained XMLs, unretrained (doc pr/2 gap G1). Usable for availability and
relative ranking, not as probabilities.

Recommendation: tier it. Core (vertex, Enu, per-particle, 3 headline scores,
TGM/STM/FC/LM verdicts, flash t0) always on; the other 39 scores on; the ~1174
BDT inputs **off** by default; per-point trajectory off, aggregated by default.

### Q2 — is there anything CAF needs that I cannot fill?

Five things.

1. **Truth and truth-matching -- absent entirely.** Verified: `tracking-pr.root`
   has **zero** truth or match branches. CAF needs `truth` / `tmatch` and
   per-particle `match_ids` / `match_overlaps` for any MC analysis. WC's truth
   exists but in a different stream (the labeler's per-blob `trackid`,
   `truth_per_track`, `nugraph.h5`). **Largest single piece of work.**
2. **Flash match / t0** -- `cluster_t0`, `matched_flash_gid`, `lm_flag` live on
   the pctree cluster scalars from QLMatching, not in this file.
3. **Containment / cosmic verdicts** -- TGM/STM/FC/LM are per-cluster flags in
   the Bee `tagger_*` layers and the log. (The `cosmict_*` family in `T_tagger`
   is uBooNE's cosmic BDT -- a different thing, do not substitute it.)
4. **PID richness** -- CAF/DLP want `pid_scores[6]`, `chi2_per_pid[6]`,
   `csda_ke`, `mcs_ke`. WC assigns ONE pdg and ONE KE per particle. Leave the
   arrays empty rather than fabricate.
5. **Bookkeeping** -- `size` (voxels), `fragment_ids`, `ppn_ids`, `module_ids`,
   uncertainties. `cluster_id`/`real_cluster_id`/`sub_cluster_id` are the nearest
   analogues; WC gives per-point chi2/ndf, not propagated errors.

## What is actually in an SBND CAF file (measured)

Sample linked at `cafmaker-dev/sample-gen2-caf/sample.flat.caf.root` ->
`/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/caf/000240/002404/`.
298 files there, ~11 MB each, **all `.flat.caf.root`** -- this production ships
only the flattened form, no nested CAF.

**File shape:** `recTree` 15 entries (one per spill), **2662 branches**,
**631 kB/event compressed**; plus `GenieEvtRecTree` (30), `globalTree`
(SRGlobal systematics config), `TotalPOT`/`TotalEvents`/`TotalGenEvents` for
normalisation, and `env/` + `metadata/` provenance dirs.

**Where the bytes go** (kB/event, share):

| family | #br | kB/evt | % |
|---|---|---|---|
| `rec.slc.reco` | 614 | 174.4 | 27.6 |
| `rec.mc.nu` | 146 | 84.5 | 13.4 |
| `rec.true_particles.genp` | 3 | 84.0 | 13.3 |
| `rec.true_particles.gen` | 3 | 58.1 | 9.2 |
| `rec.true_particles.daughters` | 4 | 33.1 | 5.3 |
| `rec.slc.truth` | 145 | 23.6 | 3.7 |
| `rec.reco.pfp` | 491 | 4.5 | 0.7 |

Truth dominates -- true_particles + mc.nu + slc.truth is well over half the
file; slice reco is ~28%. `rec.reco.pfp` has 491 branches for 0.7% of bytes:
in a flat CAF, branch count and size are only loosely related.

**Blocks by branch count:** `rec.slc` 981, `rec.reco` 608, `rec.dlp_true` 269,
`rec.hdr` 210, `rec.mc` 179, `rec.dlp` 164, `rec.true_particles` 56.

**Occupancy/event:** nslc 2-14 (8.5 avg), ntrue_particles 4922-13275 (7144
avg), nopflashes 30-63, **ndlp = 0**, ndlp_true = 0.

### The DLP block is present but EMPTY

433 `rec.dlp*` branches exist in the schema and occupy space, but `ndlp = 0` in
every event -- SBND production does not run the ML reco that fills them.  So
`SRInteractionDLP` is a **schema precedent, not a working example**: it proves
the "second reconstruction at top level" slot is legitimate and already
carried, but nobody has exercised it in SBND.  No operational pattern to copy;
also no contention if WC takes an adjacent slot.

### Correction to the Q1 size argument

The first draft argued the ~1174 BDT-input branches were a SIZE problem.
Against a measured 631 kB/event, 1023 floats is ~4.1 kB -- about **0.65%**.
Size is a weak argument and should not have led.  What survives is stronger:
**branch count** (2662 -> ~3850, +45% schema width; flat-CAF tooling and
dictionaries scale with branch count, not bytes), **meaning** (one selection's
intermediate features, uncharacterised on SBND), and **review burden** (every
branch is a permanent commitment in a shared schema).  The tiering
recommendation stands; the justification changes.

## Findings that shape the design

**`SRInteractionDLP` is the precedent.** `StandardRecord` carries
`std::vector<SRInteractionDLP> dlp` at TOP LEVEL, beside `slc` -- a second,
independent reconstruction with its own interaction->particle hierarchy,
mirroring **duneanaobj**'s `SRInteraction`/`SRRecoParticle`. That is the shape WC
should take: WC has no slice concept, but it does have one main vertex per
candidate with a particle flow hanging off it. Forcing WC into `SRSlice` would
misrepresent it.

**`SRNuID` is not a home for `T_tagger`.** Despite being described as "BDT
inputs", it is 10 Pandora NeutrinoID features.

**`T_rec_charge` carries `particle_id`** (308 points/event, with
`x y z q ... rr cluster_id real_cluster_id sub_cluster_id particle_id`). So
per-particle geometry is NOT missing as first assumed -- grouping by
`particle_id` yields start/end, direction, length and a dQ/dx-vs-rr profile.
With `T_kine`'s per-particle PDG+KE that is enough for an SRParticle-shaped
object.

**Open question this raises:** do `T_kine`'s particle ordering and
`T_rec_charge`'s `particle_id` refer to the same objects in the same order?
Nothing verifies it today. Phase 1, because a silent mismatch mis-assigns every
particle energy.

## `rec.dlp` is SPINE, and how SPINE actually gets into a CAF

"DLP" is the older name for the ML chain now called SPINE.  It is filled by
NEITHER `sbncode/CAFMaker` nor any art module.

**`justinjmueller/sbn_ml_cafmaker`** is a standalone C++/CMake project -- no art,
no LArSoft.  SPINE runs outside LArSoft and writes HDF5; this tool moves it into
CAF two ways: `merge_sources` (existing CAF + HDF5, matched event-by-event on
`(run,subrun,evt)`, writes a new CAF with both) and `make_standalone` (a CAF with
only ML output).  The merge loop reads the whole record, clears only its own four
members (`dlp`, `ndlp`, `dlp_true`, `ndlp_true`), fills them on a match, and
REBUILDS `recTree` entry by entry -- everything else passes through untouched.

**This is the closest precedent to what we need, and better than an art module.**
WC, like SPINE, produces output from its own chain rather than as art products a
CAFMaker would see.  The merge pattern means no change to sbncode/CAFMaker, no
art integration, no coupling to reco2, and the WC block can be re-made
independently whenever the PR chain changes.  It also explains **why ndlp = 0**
in our production sample: the branches are in the schema but filling them is a
downstream step this production never ran.

**Practical obstacle, ours specifically.** `merge_sources` does
`SetBranchAddress("rec", &rec)` -- it needs a NESTED CAF.  Verified on our
sample: there is no branch named `rec`; branches are `rec.crt_hits..length`,
`rec.dlp.cathode_offset`, ... i.e. flattened.  And a `find` over the whole
`caf/` tree returns **no non-flat `.caf.root` at all** -- SBND Gen2 production
keeps only `.flat.caf.root`.  So the SPINE tool cannot be pointed at our files
as-is; either obtain the nested CAF (presumably transient upstream of the
flattening step) or make the merge work on the flat form, which is harder since
flat branches are fixed-layout.

### Can we add `rec.wc`?

Correction first: **`rec.dlp` is not a TTree.**  There is one `recTree`.  Nested
CAF: one branch `rec` holding a `caf::StandardRecord`, with `dlp` a member.  Flat
CAF: that object exploded into ~2662 dotted branches, 433 of them `rec.dlp*`.  So
`rec.wc` would be a MEMBER of StandardRecord (hence a set of branches), not a
tree.

| | option | cost | verdict |
|---|---|---|---|
| A | `std::vector<SRWireCellInteraction> wc` + `nwc` as new StandardRecord members, parallel to `dlp`/`ndlp` | sbnanaobj PR: record, flat mirror, dictionaries, SBN review | **the real destination** |
| B | reuse the existing EMPTY `dlp` block | zero | **no** -- SPINE-shaped fields, and WC becomes indistinguishable from SPINE the moment SBND enables it.  Tempting because ndlp=0 today; a trap tomorrow |
| C | sidecar TTree (`wcTree`) keyed by (run,subrun,evt) in the same file | none | **good first step**, but not "in the CAF" for tooling -- SRProxy/CAFAna address `recTree`; analysers would join by hand |

Recommended: **C to prove the content, A to ship it.**  C gives real WC-in-CAF
output in days and costs nothing that must be un-done -- the fillers and the RSE
join are the same work either way.  A then converts a schema argument into a
review of something already producing numbers.

This supersedes "sibling visitor / read in memory" as the PRIMARY route.  Reading
in memory is still the right way to OBTAIN the WC quantities (it avoids the 8 kB
ambiguity above), but the CAF-side plumbing should follow the SPINE merge
pattern.  The two are complementary: a WCT visitor writes a compact per-event WC
summary, and a merge step joins it to the CAF on RSE.

## Design decision that outranks both questions

**CAFMaker should not read `tracking-pr.root`.** It is a Magnify/debug artifact
and it is not multi-event safe -- both writers share one filename (RECREATE +
UPDATE), so `lar -n N` silently yields an 8 kB file with `T_tagger`/`T_kine`
absent (issue #13, G9). CAF production runs many events per process, i.e.
precisely the workload that breaks it. CAFMaker should instead read the same
`TaggerInfo` / `KineInfo` / `TrackFitting` / PR-graph objects **in memory** that
`UbooneTaggerOutputVisitor` and `SbndPrMagnifyTrackingVisitor` already consume --
a sibling visitor, not a downstream parser.

## Phasing

1. Verify the `particle_id` <-> `T_kine` join.
2. Interaction level only (vertex, Enu, 3 scores, verdicts) -- smallest
   end-to-end slice that yields a readable CAF.
3. Particles (PDG, KE, geometry aggregated per `particle_id`).
4. Truth (gap 1) -- needs the labeler stream.
5. Score tiers + flash/verdict plumbing (gaps 2, 3).
6. Propose the schema upstream in `sbnanaobj`.

## Open questions for the owner

1. Who consumes this CAF? SBN-wide => the schema must go through `sbnanaobj`
   review; our own studies => a private block is far faster.
2. Must WC sit alongside Pandora in the SAME CAF file (per-event comparison), or
   is a WC-only CAF acceptable?
3. Is truth in scope now? It is the largest piece and the only one needing a
   second input stream.
4. Do the uBooNE-trained, uncalibrated BDT scores belong in CAF at all?
5. Which reco is authoritative for the vertex when WC and Pandora disagree?

## Reference

- `SBNSoftware/sbncode/sbncode/CAFMaker` -- module + free-function fillers
  (`Fill<X>(const In&, ..., caf::SR<Y>&, bool allowEmpty=false)`), links
  `sbnanaobj::StandardRecord`.
- `SBNSoftware/sbnanaobj/sbnanaobj/StandardRecord`
- `DUNE/duneanaobj/duneanaobj/StandardRecord` -- the `SRInteraction` model
