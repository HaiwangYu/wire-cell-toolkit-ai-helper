# ai-helper #47 (prod_aurora): run setup for the dv2max-aurora-space test build (sourced inside SL7).
# = the production run setup with the test install, + scipy/lightgbm (SL7 build) and the aurora_space bundle.
Y=/lus/flare/projects/neutrinoGPU/yuhw
P=$Y/production-prep/dv2max-aurora-space
export WC_OPT=${WC_OPT:-$Y/opt-dv2test} WC_WCT_SRC=${WC_WCT_SRC:-$Y/wct-dv2test}
source $Y/sbnd-wirecell-production/aurora/env/aurora/setup-aurora-run.sh
export WIRECELL_PATH=$P/wcdata:$WIRECELL_PATH
export PYTHONPATH=$PYTHONPATH:$Y/products/dv2-extra-py39/site
export DV2_THREADS=1 DV2_STRICT=1
