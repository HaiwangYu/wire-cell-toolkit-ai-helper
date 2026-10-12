#!/bin/bash
# find-pairs for the open FixedDev BNB data: reco1 MCP2025C FixedDev, CAF = the gen2 FixedDev Respin flat CAF (direct child of the reco1)
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1; setup sam_web_client >/dev/null 2>&1; export SAM_EXPERIMENT=sbnd
cd /exp/sbnd/data/users/yuhw/production-prep/opendata-fixeddev-prep; /usr/bin/time -f "wall=%e s" python3 /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/bin/find-pairs.py --reco1-samdef data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd --caf-samdef data_SBND2026A_SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin_v10_14_02_04_flatcaf_sbnd --reality data -o pairs.tsv
