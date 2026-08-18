# Issue 14 — Wire-Cell CAFMaker (`larwirecell/CAFMaker`)

Get SBND Wire-Cell reconstruction into the Common Analysis Format, modelled on
`sbncode/CAFMaker`. **Planning only so far — nothing implemented.**

Primary document: `wcp-porting-img/sbnd/docs/6-cafmaker-plan.html`
Work dir: `/exp/sbnd/data/users/yuhw/production-prep/cafmaker-dev`
Follows on from issue #13 (the PR-chain port), which produced the reco output
this consumes.

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
