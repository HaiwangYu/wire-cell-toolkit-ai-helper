# Real data: `original` (uboone SCN) vs `aurora_space` (DV2-MAX), with Bee (issue 47, task A; 2026-11-16 UTC)

Request: prod_polaris, relaying Haiwang, 2026-11-16. Nothing was pushed or posted on a WireCell PR.

## Setup

| item | value |
|---|---|
| build | local `dataA-master-pr547` `139b50d7` = master `c6be329e` (#544 merged) + #547 head `c9f61962`. The one-line `sbnd-pr-stage.jsonnet` conflict was resolved keeping #544's `flat_tree/truth_match/blob_truth` and #547's `aurora_space` default. **Same git tree as #547's new head `e426d988`** (`186a75cc`). Not pushed. `/exp/sbnd/data/users/yuhw/opt-dataA` (the #43 configure) |
| inputs | the #43 data step-1 tars: nueCC-48 (6 slices) + NCπ0-19 (3 slices), 67 events |
| arms | same build, same tars, production data TLAs (`dl_vtx_dump`, `flat_tree`), Bee on (`mabc-pr.zip`): **`original`** = `vertex_method=original` (the pre-DV2 chain, uboone SCN net); **`aurora_space`** = `vertex_method=dv2_split_move`, `dv2_bundle=dv2max/sbnd/aurora_space/bundle.json` |
| runs | `scripts/run-step2.sh` (`SETUP=scripts/setup-dataA.sh SPACE=false`), one pinned core each, `GODEBUG=asyncpreemptoff=1`: 18/18 rc 0, no "DL vertex failed" |
| analysis | `scripts/data-compare.py` → `tables/data-orig-vs-aur-{event,cand}.csv`, `-summary.json`; Bee: `scripts/bee-pack.py` → one zip per arm, one shared event order, `tables/data-orig-vs-aur-bee-index.csv` |

**Checks:**
- The final vertex of a candidate is `T_dlvtx_call.final_*`, which is the same on every call of the candidate (spread 0). For the selected candidate it equals `T_tagger.nu_x/y/z`: within 1.4e-5 cm for `original`, exactly for `aurora_space`.
- Both arms reproduce the earlier builds event by event (`T_tagger` vertex and scores, 67/67 each):
  - `original` = #544-on-master `opt-p544`;
  - `aurora_space` = the P4 test build `ddbc0488`.

**DL-based:** some call of the candidate has `accepted = 1`, i.e. the DL vertex was taken (for `original`, the SCN proposal; otherwise the traditional vertex).

## Results

**Vertex** (68 candidates in 67 events; both arms have every candidate and select the same one in every event):

| \|final(`original`) − final(`aurora_space`)\| | candidates |
|---|---|
| < 0.1 cm | 6 |
| < 1 cm | 51 |
| < 2 cm | 54 |
| ≥ 5 cm | 9 (max 48.6 cm) |
| median | 0.46 cm |

- **DL-based:** `original` 67/68 (NCπ0 18259/1/105946 keeps the traditional vertex; 2.8 cm from aurora's), `aurora_space` 68/68.
- `original` makes 2 calls per candidate (the dual chain), `aurora_space` 1.

**Selection** (the #43 cuts: generic = `numu_cc_flag ≥ 0`, nue = generic and `nue_score > 7`, numu = generic and `numu_score > 0.9`):

| sample | `original` generic / nue / numu | `aurora_space` generic / nue / numu |
|---|---|---|
| nueCC-48 | 48 / **38** / 5 | 48 / **41** / 4 |
| NCπ0-19 | 19 / 1 / 2 | 19 / 1 / 1 |
| all 67 | 67 / 39 / 7 | 67 / 42 / 5 |

**9 events change, 8 of them in nueCC-48** (they are first in the table and in Bee, indices 0–8):
- nue: +5 / −2;
- numu: +1 / −3.

**Hand-scan vertex:** none found.
- nueCC-48 and NCπ0-19 are hand-scanned for the event selection only; the lists in `sbnd-gen2-data` (`lynn-nuecc-rse.csv`, `nc-sideband-rse.csv`) hold run/subrun/event only.
- #35 / #43 have no per-event vertex labels for data either, and I found none in Lynn's area.
- So the distances here are between the two arms, not to a truth or scan vertex. Bee is the way to judge them.

## Per event, with Bee (both sets have the same event order: change the set, keep the index)

- **Bee `original`:** https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/list/
- **Bee `aurora_space`:** https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/list/

Layers: `clustering-pr`, `track_fit`, `shower_track`, `vertices`, `tagger_*`.

How to read the table:
- Order: the changed events (bold) first, then by distance, largest first.
- d(final) is between the selected candidates' final vertices.
- "sel" lists the selections passed (nue / numu); – = neither.
- A nue score of −15 is the tagger's value for "no nue candidate shower".

| # | sample | run/subrun/event | Bee `original` | Bee `aurora_space` | d(final) cm | DL-based o / a | sel o → a | nue score o → a | numu score o → a |
|---|---|---|---|---|---|---|---|---|---|
| 0 | nuecc48 | **18255/1/271851** | [0](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/0/) | [0](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/0/) | 48.63 | 1 / 1 | **– → numu** | -15.00 → -15.00 | -0.42 → 1.09 |
| 1 | nuecc48 | **18259/1/111412** | [1](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/1/) | [1](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/1/) | 39.16 | 1 / 1 | **numu → nue** | -1.85 → 8.08 | 1.58 → -1.07 |
| 2 | nuecc48 | **18255/1/235435** | [2](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/2/) | [2](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/2/) | 32.16 | 1 / 1 | **numu → nue** | -15.00 → 7.96 | 2.63 → 0.28 |
| 3 | nuecc48 | **18255/1/163543** | [3](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/3/) | [3](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/3/) | 16.99 | 1 / 1 | **– → nue** | 3.23 → 9.91 | -0.77 → -1.18 |
| 4 | nuecc48 | **18255/1/268067** | [4](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/4/) | [4](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/4/) | 2.90 | 1 / 1 | **nue → –** | 8.34 → -15.00 | 0.51 → 0.52 |
| 5 | ncpi0 | **18255/1/71372** | [5](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/5/) | [5](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/5/) | 1.99 | 1 / 1 | **numu → –** | -15.00 → 0.87 | 1.80 → 0.51 |
| 6 | nuecc48 | **18255/1/360535** | [6](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/6/) | [6](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/6/) | 0.73 | 1 / 1 | **nue → –** | 10.46 → -15.00 | -0.47 → 0.09 |
| 7 | nuecc48 | **18255/1/268784** | [7](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/7/) | [7](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/7/) | 0.45 | 1 / 1 | **– → nue** | 6.15 → 8.39 | 0.57 → 0.08 |
| 8 | nuecc48 | **18255/1/168596** | [8](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/8/) | [8](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/8/) | 0.30 | 1 / 1 | **– → nue** | -0.27 → 10.90 | 0.34 → 0.25 |
| 9 | nuecc48 | 18259/1/116962 | [9](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/9/) | [9](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/9/) | 48.64 | 1 / 1 | – → – | -4.82 → -15.00 | 0.15 → -0.04 |
| 10 | ncpi0 | 18255/1/463565 | [10](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/10/) | [10](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/10/) | 35.38 | 1 / 1 | – → – | -1.69 → -15.00 | -0.03 → 0.42 |
| 11 | ncpi0 | 18255/1/180801 | [11](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/11/) | [11](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/11/) | 29.81 | 1 / 1 | – → – | -15.00 → -15.00 | -0.10 → -0.42 |
| 12 | ncpi0 | 18345/1/259542 | [12](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/12/) | [12](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/12/) | 26.15 | 1 / 1 | – → – | -15.00 → -15.00 | 0.38 → 0.30 |
| 13 | ncpi0 | 18255/1/56982 | [13](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/13/) | [13](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/13/) | 7.40 | 1 / 1 | – → – | 2.83 → -15.00 | 0.23 → 0.15 |
| 14 | nuecc48 | 18255/1/469665 | [14](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/14/) | [14](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/14/) | 3.59 | 1 / 1 | – → – | 3.81 → 2.96 | -0.49 → -0.13 |
| 15 | ncpi0 | 18345/1/21073 | [15](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/15/) | [15](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/15/) | 3.58 | 1 / 1 | – → – | -7.36 → -7.43 | 0.56 → -0.76 |
| 16 | ncpi0 | 18259/1/105946 | [16](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/16/) | [16](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/16/) | 2.80 | 0 / 1 | – → – | -15.00 → -15.00 | -0.23 → -0.46 |
| 17 | ncpi0 | 18255/1/142421 | [17](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/17/) | [17](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/17/) | 2.74 | 1 / 1 | numu → numu | -15.00 → -15.00 | 2.69 → 2.87 |
| 18 | nuecc48 | 18255/1/196649 | [18](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/18/) | [18](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/18/) | 1.85 | 1 / 1 | nue → nue | 7.97 → 12.45 | -0.54 → -0.41 |
| 19 | nuecc48 | 18304/1/38856 | [19](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/19/) | [19](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/19/) | 1.18 | 1 / 1 | nue → nue | 13.69 → 14.21 | -0.90 → 0.26 |
| 20 | nuecc48 | 18255/1/69314 | [20](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/20/) | [20](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/20/) | 0.82 | 1 / 1 | numu → numu | -15.00 → -9.77 | 2.96 → 2.13 |
| 21 | ncpi0 | 18255/1/314838 | [21](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/21/) | [21](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/21/) | 0.78 | 1 / 1 | – → – | -15.00 → -15.00 | -0.06 → -0.62 |
| 22 | ncpi0 | 18259/1/18625 | [22](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/22/) | [22](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/22/) | 0.76 | 1 / 1 | – → – | -15.00 → -15.00 | 0.59 → 0.70 |
| 23 | ncpi0 | 18255/1/506746 | [23](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/23/) | [23](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/23/) | 0.69 | 1 / 1 | – → – | -15.00 → -15.00 | 0.58 → 0.51 |
| 24 | ncpi0 | 18261/1/285567 | [24](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/24/) | [24](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/24/) | 0.68 | 1 / 1 | – → – | -7.23 → -6.52 | 0.79 → -0.01 |
| 25 | nuecc48 | 18255/1/122660 | [25](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/25/) | [25](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/25/) | 0.64 | 1 / 1 | nue → nue | 10.36 → 10.65 | 0.53 → 0.47 |
| 26 | nuecc48 | 18255/1/90055 | [26](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/26/) | [26](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/26/) | 0.53 | 1 / 1 | nue → nue | 11.27 → 10.95 | -0.73 → -0.76 |
| 27 | nuecc48 | 18255/1/437699 | [27](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/27/) | [27](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/27/) | 0.52 | 1 / 1 | nue → nue | 8.51 → 9.64 | -0.69 → -0.97 |
| 28 | nuecc48 | 18264/1/137238 | [28](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/28/) | [28](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/28/) | 0.51 | 1 / 1 | numu → numu | -15.00 → -15.00 | 1.65 → 2.02 |
| 29 | nuecc48 | 18259/1/42280 | [29](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/29/) | [29](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/29/) | 0.48 | 1 / 1 | nue → nue | 12.72 → 8.88 | -1.73 → -0.71 |
| 30 | nuecc48 | 18342/1/30504 | [30](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/30/) | [30](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/30/) | 0.47 | 1 / 1 | nue → nue | 9.21 → 11.61 | -0.45 → -0.30 |
| 31 | nuecc48 | 18255/1/269774 | [31](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/31/) | [31](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/31/) | 0.47 | 1 / 1 | nue → nue | 10.83 → 11.42 | -1.06 → -0.83 |
| 32 | nuecc48 | 18259/1/52672 | [32](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/32/) | [32](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/32/) | 0.47 | 1 / 1 | nue → nue | 13.28 → 11.17 | -0.10 → -0.09 |
| 33 | nuecc48 | 18255/1/46363 | [33](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/33/) | [33](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/33/) | 0.46 | 1 / 1 | nue → nue | 9.55 → 7.89 | -0.81 → -0.71 |
| 34 | ncpi0 | 18255/1/114446 | [34](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/34/) | [34](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/34/) | 0.46 | 1 / 1 | – → – | -15.00 → -15.00 | -0.64 → -0.72 |
| 35 | nuecc48 | 18253/1/444187 | [35](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/35/) | [35](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/35/) | 0.42 | 1 / 1 | nue → nue | 10.35 → 11.51 | 0.48 → 0.39 |
| 36 | nuecc48 | 18255/1/138009 | [36](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/36/) | [36](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/36/) | 0.40 | 1 / 1 | nue → nue | 10.03 → 14.13 | 0.16 → -0.14 |
| 37 | ncpi0 | 18255/1/521075 | [37](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/37/) | [37](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/37/) | 0.39 | 1 / 1 | – → – | -15.00 → -15.00 | -0.42 → -0.79 |
| 38 | nuecc48 | 18255/1/423981 | [38](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/38/) | [38](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/38/) | 0.39 | 1 / 1 | nue → nue | 10.83 → 13.14 | 0.23 → 0.15 |
| 39 | nuecc48 | 18255/1/433451 | [39](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/39/) | [39](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/39/) | 0.37 | 1 / 1 | nue → nue | 9.19 → 10.05 | -0.35 → -1.78 |
| 40 | nuecc48 | 18259/1/54095 | [40](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/40/) | [40](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/40/) | 0.31 | 1 / 1 | nue → nue | 11.51 → 12.27 | -1.21 → -1.54 |
| 41 | nuecc48 | 18355/1/400474 | [41](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/41/) | [41](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/41/) | 0.31 | 1 / 1 | nue → nue | 11.79 → 14.02 | 0.34 → 0.01 |
| 42 | ncpi0 | 18259/1/37112 | [42](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/42/) | [42](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/42/) | 0.31 | 1 / 1 | – → – | -2.75 → -1.70 | 0.64 → 0.63 |
| 43 | nuecc48 | 18255/1/234638 | [43](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/43/) | [43](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/43/) | 0.29 | 1 / 1 | nue+numu → nue+numu | 7.23 → 7.45 | 1.41 → 1.00 |
| 44 | nuecc48 | 18255/1/388 | [44](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/44/) | [44](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/44/) | 0.29 | 1 / 1 | nue → nue | 13.02 → 13.95 | -1.77 → -1.77 |
| 45 | ncpi0 | 18255/1/359980 | [45](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/45/) | [45](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/45/) | 0.27 | 1 / 1 | – → – | -15.00 → -15.00 | -1.12 → -1.30 |
| 46 | nuecc48 | 18269/1/342199 | [46](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/46/) | [46](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/46/) | 0.23 | 1 / 1 | nue → nue | 11.49 → 11.30 | 0.31 → 0.31 |
| 47 | nuecc48 | 18253/1/172230 | [47](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/47/) | [47](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/47/) | 0.23 | 1 / 1 | nue → nue | 10.62 → 11.23 | -1.40 → -0.01 |
| 48 | ncpi0 | 18255/1/506114 | [48](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/48/) | [48](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/48/) | 0.22 | 1 / 1 | – → – | -15.00 → -15.00 | -0.92 → -0.92 |
| 49 | nuecc48 | 18259/1/74544 | [49](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/49/) | [49](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/49/) | 0.20 | 1 / 1 | nue → nue | 11.06 → 12.53 | -0.91 → -0.41 |
| 50 | ncpi0 | 18364/1/84229 | [50](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/50/) | [50](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/50/) | 0.20 | 1 / 1 | – → – | -15.00 → -15.00 | 0.50 → 0.86 |
| 51 | nuecc48 | 18255/1/174637 | [51](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/51/) | [51](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/51/) | 0.18 | 1 / 1 | nue → nue | 10.67 → 9.63 | 0.81 → 0.72 |
| 52 | nuecc48 | 18255/1/350186 | [52](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/52/) | [52](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/52/) | 0.18 | 1 / 1 | nue → nue | 9.51 → 12.30 | -1.52 → -1.59 |
| 53 | nuecc48 | 18255/1/422851 | [53](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/53/) | [53](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/53/) | 0.17 | 1 / 1 | nue → nue | 13.06 → 14.38 | -1.08 → -1.27 |
| 54 | nuecc48 | 18255/1/389538 | [54](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/54/) | [54](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/54/) | 0.16 | 1 / 1 | nue → nue | 10.91 → 15.05 | 0.49 → -0.16 |
| 55 | ncpi0 | 18255/1/399860 | [55](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/55/) | [55](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/55/) | 0.15 | 1 / 1 | nue → nue | 9.00 → 10.53 | -0.89 → -0.11 |
| 56 | nuecc48 | 18255/1/447477 | [56](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/56/) | [56](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/56/) | 0.13 | 1 / 1 | nue → nue | 10.90 → 11.67 | 0.00 → -0.16 |
| 57 | nuecc48 | 18255/1/239794 | [57](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/57/) | [57](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/57/) | 0.12 | 1 / 1 | nue → nue | 13.05 → 12.89 | -0.59 → -0.75 |
| 58 | nuecc48 | 18313/1/81597 | [58](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/58/) | [58](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/58/) | 0.12 | 1 / 1 | nue → nue | 14.40 → 12.25 | 0.36 → 0.25 |
| 59 | nuecc48 | 18306/1/256587 | [59](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/59/) | [59](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/59/) | 0.11 | 1 / 1 | nue → nue | 10.34 → 10.93 | -1.09 → -1.06 |
| 60 | nuecc48 | 18255/1/489330 | [60](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/60/) | [60](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/60/) | 0.10 | 1 / 1 | nue → nue | 12.94 → 13.87 | 0.06 → -1.36 |
| 61 | nuecc48 | 18255/1/246579 | [61](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/61/) | [61](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/61/) | 0.08 | 1 / 1 | nue → nue | 11.45 → 13.57 | -0.46 → -0.49 |
| 62 | nuecc48 | 18259/1/131357 | [62](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/62/) | [62](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/62/) | 0.08 | 1 / 1 | nue → nue | 11.61 → 11.57 | -0.69 → -0.71 |
| 63 | nuecc48 | 18409/1/214469 | [63](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/63/) | [63](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/63/) | 0.07 | 1 / 1 | nue → nue | 11.65 → 10.96 | -1.31 → -1.45 |
| 64 | nuecc48 | 18255/1/219295 | [64](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/64/) | [64](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/64/) | 0.06 | 1 / 1 | nue → nue | 9.84 → 8.84 | -1.08 → -1.33 |
| 65 | nuecc48 | 18255/1/10550 | [65](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/65/) | [65](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/65/) | 0.05 | 1 / 1 | nue → nue | 13.23 → 12.65 | -0.38 → -0.39 |
| 66 | nuecc48 | 18279/1/267597 | [66](https://www.phy.bnl.gov/twister/bee/set/89cdea53-c227-476c-8f67-0ae765f804b4/event/66/) | [66](https://www.phy.bnl.gov/twister/bee/set/431dc57f-997d-4cff-88e1-4e33fd743ab8/event/66/) | 0.04 | 1 / 1 | nue → nue | 11.59 → 11.82 | 0.02 → -1.81 |

Data: `/exp/sbnd/data/users/yuhw/production-prep/issue47/dataA/` (`runs/{orig,aur}/<unit>/`, `bee/`, `ana/`).
