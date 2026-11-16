# Issue 48: site config for bin/run-pairs.sh on sbndbuild03 with the 0.38.0 release (scripts/setup-wcl.sh).
# The owner's load rules: at most half the machine (cores 32-63, 50 GB own RSS), half that 08:00-20:00.
source /exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/site/fnal-sbndbuild03.sh
export WC_SL7_SETUP=/exp/sbnd/data/users/yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/porting_sbndbuild03/scripts/setup-wcl.sh
export WC_MAXPAR=${WC_MAXPAR:-28} WC_DAY_MAXPAR=${WC_DAY_MAXPAR:-14}
# both production passes, aurora_space
export WC_DV2_BUNDLE=dv2max/sbnd/aurora_space/bundle.json
export GODEBUG=asyncpreemptoff=1
