Track what the SBND SAM definitions we consume actually are: naming convention, and whether the reco1 and CAF definitions the gen2 data wiki lists for the "Run 1 Fixed Analysis Development Sample" are the same events.

## 1. Naming convention — the observation is right, with three refinements

`<data-type>_<campaign>_<sample>_<sbndcode-version>_<tier>_sbnd`

| example | data-type | campaign | sample | version | tier |
|---|---|---|---|---|---|
| `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd` | data | MCP2025C | Fall25-Run1_BNB_FixedDev_bnblight | v10_14_02 | reco1 |
| `data_SBND2026A_SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin_v10_14_02_04_caf_sbnd` | data | SBND2026A | SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin | v10_14_02_04 | caf |
| `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` | aurora (MC via the aurora system) | SBND2026A | gen2_BNBLight_prodgenie_…_CV | v10_14_02_03 | reco1 |

Refinements: (1) **the version is that of the stage that produced the tier**, not of the whole chain — a respin of reco2+CAF on old reco1 gets a new version and a new campaign prefix while the reco1 stays; (2) the campaign prefix can appear twice (`data_SBND2026A_SBND2026A_gen2_…`) and `data`/`mc`/`aurora`/`test_`/`snapshot_<user>_`/`<user>_…_limit_N` prefixes exist — only `data_`/`mc_`/`aurora_` are production; (3) sub-samples are *queries* on a parent definition, not new productions: `FixedDev` = `Dev and (run 18255 or 18259)`, `RollingDev` = the other runs (checked 2026-09-10).

## 2. Are the wiki's reco1 and CAF the same data? **Yes — same events, different processing generation.**

Checked with samweb + ROOT (2026-09-11):

| | reco1 `…FixedDev_bnblight_v10_14_02_reco1_sbnd` | CAF `…FixedDev_Respin_v10_14_02_04_caf_sbnd` |
|---|---|---|
| files | 1,820 | 1,817 |
| runs (400-file sample) | 18255 (68 %), 18259 (32 %) | 18255 (74 %), 18259 (26 %) |
| created | 2026-03-10 | 2026-04-07 |

- **Parentage:** every one of the 1,817 CAF files has exactly one parent, and **all 1,817 parents are members of the reco1 FixedDev definition** (`samweb list-files "isparentof: (defname: CAF) and defname: RECO1"` → 1,817). The CAF's project is `sbnd_reco2_caf_data`, stage `reco2_caf`, version v10_14_02_04, i.e. **reco2 + CAF were re-run ("Respin") on the unchanged v10_14_02 reco1 files** — that is why the campaign prefix and version differ. The reco1's own parent is the DAQ file (`data_EventBuilder5_art2_run18255_46_strmBNBLight_…`).
- **RSE:** one CAF file vs its parent reco1 file: 50 events each, **50 in common, 0 either side** (e.g. 18255/1/366028, 366270, 366578).
- 3 of the 1,820 reco1 files have no Respin child (1,820 − 1,817); each is a normal 50-event file, so ~150 events of the reco1 set are not in the CAF. (`minus ischildof:` did not resolve in SAM; the 1,817 forward count is the reliable one.)
- There is also a same-generation CAF, `data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_caf_sbnd`; the wiki points to the Respin, so the analysis CAFs are v10_14_02_04 reco2 on v10_14_02 reco1.

**Consequence for us:** our round-3 beam-on (#26) runs Wire-Cell on the reco1 tier — the *same* events the Respin CAFs describe — so any CAF-level comparison can be joined on (run, subrun, event) directly; no re-selection needed. For the off-beam side the wiki's `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` is a genuine v10_14_02_02 reco1 (decode→reco1 re-run), not a respin — so its CAF partner should be checked the same way before joining.

Doc: `issues/28-samdef-naming-and-fixeddev-lineage/` (this text + the samweb commands).
