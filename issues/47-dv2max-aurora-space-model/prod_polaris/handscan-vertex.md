# Real data vs Xin's round-2 hand scan: `original` vs `aurora_space` vertices (prod_polaris, 2026-11-16)

This scores the task-A vertices (`porting_sbndbuild03/data-orig-vs-aur.md`, `tables/data-orig-vs-aur-cand.csv`, the selected candidate of each event) against Xin's round-2 hand scan of the same events.
- The sheet's tabs "NueCC sample" (gid 0) and "NC pi0" (gid 1175668810), "Round 2" block, are nueCC-48 and NCπ0-19.
- Script: `scripts/handscan_vtx.py`. Table: `tables/handscan-vs-arms.csv` (the scanners' free-text comments are left out).

## The reference vertex

For each event, round 2 gives a verdict on Xin's round-2 reconstructed vertex (its Bee sets: nueCC `9e2a1a1e…`, NCπ0 `13900b8c…`).

| verdict | reference used | events |
|---|---|---|
| Good / OK | **Xin's round-2 vertex**: the common start point of the top-level particles in his Bee set's `mc` (particle-flow) layer | 48 |
| Not OK / Not good, with "(x, y, z)" in the comment | **the scanner's point**, eyeballed in Bee, so good to about a cm | 15 (one, NCπ0 180801, carries a "?") |
| Not good, no coordinates | none | 3 |

The coordinates in the two "Good" rows that have them mark other defects ("missing clustering points", "missing vertex proton"), so those rows use Xin's vertex.

Frames agree: where the scan is Good, our `original` vertex is a median 0.43 cm from Xin's round-2 vertex.

## Excluded

- **6 events where our selected candidate is a different interaction from the scanned one:** both arms more than 10 cm from the reference and within 0.2 cm of each other. These are nueCC 10550, 42280, 52672 and NCπ0 84229, 114446 ("QL mismatch"), 521075.
  - In NCπ0 84229, Xin's particle-flow layer has 5 different top-level starts, so his vertex is ambiguous.
  - The two arms always pick the same candidate, so these say nothing about the vertexer.
- **3 events without a usable reference:** "Not good" with no coordinates.
- **Sheet typos, corrected** (checked against the RSE of Xin's round-2 Bee event for that row): 18255-234538 → 18255/1/234638, 18355-40074 → 18355/1/400474. One of our nueCC-48 events (18259/1/116962) is not in the sheet, which has 47 nueCC rows.

## Results (57 events)

| reference | n | < 1 cm `original` / `aurora` | < 2 cm | < 3 cm | median cm | `aurora` closer |
|---|---|---|---|---|---|---|
| scan Good/OK → Xin's round-2 vertex | 44 | 32 / **34** | 35 / **38** | 39 / **41** | 0.43 / **0.34** | 26 of 44 |
| scan Not good → scanner's point | 13 | 4 / **8** | 6 / **11** | 6 / **12** | 5.15 / **0.93** | 10 of 13 |
| — of which nueCC-48 | 8 | 4 / 5 | 6 / 7 | 6 / 8 | 1.06 / 0.80 | 5 |
| — of which NCπ0-19 | 5 | 0 / 3 | 0 / 4 | 0 / 4 | 25.6 / 0.94 | 5 |
| **all** | **57** | 36 / **42** | 41 / **49** | 45 / **53** | 0.60 / **0.56** | 36 of 57 |

**The events the scanners flagged and located** (distance to the scanner's point, cm):

| event | `original` | `aurora_space` |
|---|---|---|
| nueCC 30504 | 0.86 | 0.56 |
| nueCC 38856 | 1.56 | 0.74 |
| nueCC 46363 | 0.60 | 0.79 |
| nueCC 111412 | 39.72 | **1.41** |
| nueCC 268784 | 0.40 | 0.82 |
| nueCC 271851 | 50.12 | **2.33** |
| nueCC 350186 | 1.26 | 1.09 |
| nueCC 489330 | 0.16 | 0.18 |
| NCπ0 56982 | 8.12 | **0.93** |
| NCπ0 71372 | 5.15 | 4.25 |
| NCπ0 180801 (?) | 30.50 | **0.93** |
| NCπ0 259542 | 25.55 | **0.94** |
| NCπ0 463565 | 34.49 | **1.50** |

**Reading:**
- Where the scanners found the round-2 vertex wrong and marked the right place, `aurora_space` lands within 1.5 cm of their point in 11 of 13 events (within 2.4 cm in 12). `original` is far off (5–50 cm) in 7 of them.
- `original` already fixes 6 of these 13 relative to Xin's round 2 (≤ 1.6 cm), because our current chain is newer than his round 2.
- Where the scan is Good/OK, `aurora_space` is about as close to Xin's vertex as `original` (34 vs 32 within 1 cm). That is in spite of the reference being a vertex from the same family of chain as `original`, which favours `original`.
- Larger `aurora_space` misses to look at in Bee:
  - nueCC 469665: 4.70 cm, vs 1.16 for `original`; the scan says "electron trunk ided as muon";
  - nueCC 196649: 2.01 vs 0.16;
  - NCπ0 71372 (4.25) and 37112 / 506746 (≈ 4 cm, both arms).

**Limits:** small samples; scanner points good to about a cm; the Good/OK reference is itself a reconstruction, not truth.
