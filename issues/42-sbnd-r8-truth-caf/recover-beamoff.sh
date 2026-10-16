source /nashome/y/yuhw/.bashrc >/dev/null 2>&1; source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1; setup sam_web_client >/dev/null 2>&1; export SAM_EXPERIMENT=sbnd
W=/exp/sbnd/data/users/yuhw/production-prep/r8-prep; D=data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd
runs=$(cut -f1 $W/beam-off-runsub.txt | sort -u | paste -sd,)
samweb list-files "defname: $D and run_number $runs" | sort -u > $W/beam-off-cand-files.txt; wc -l < $W/beam-off-cand-files.txt
