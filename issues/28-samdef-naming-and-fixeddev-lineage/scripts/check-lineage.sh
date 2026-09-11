#!/bin/bash
# Inside SL7: source sbnd/setup-local-opt.sh; setup sam_web_client; export SAM_EXPERIMENT=sbnd
R=${1:-data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd}
C=${2:-data_SBND2026A_SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin_v10_14_02_04_caf_sbnd}
for d in $R $C; do echo "== $d"; samweb describe-definition $d | grep -i 'Dimensions\|Creation'; samweb list-files --summary "defname: $d"; done
echo "CAF parents:               $(samweb list-files "isparentof: (defname: $C)" | wc -l)"
echo "...in the reco1 def:       $(samweb list-files "isparentof: (defname: $C) and defname: $R" | wc -l)"
f=$(samweb list-definition-files $C | head -1); samweb get-metadata $f | grep -i 'sbnd_project\|Parents'
# RSE spot check: open the CAF (recTree: rec.hdr.run/subrun/evt) and its parent reco1 (Events: EventAuxiliary) with PyROOT and intersect.
