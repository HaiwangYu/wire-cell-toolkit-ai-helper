#!/bin/bash
# Extract run 270 / subrun 6 / event 46 (entry 11) -> data/evt-270-6-46.root
source /nashome/y/yuhw/.bashrc >/dev/null 2>&1
source /exp/sbnd/app/users/yuhw/wcp-porting-img/sbnd/setup-local-opt.sh >/dev/null 2>&1
HERE=$(cd "$(dirname "$0")" && pwd); D=$(dirname "$HERE")
SRC=/pnfs/sbn/data_add/sbn_nd/poms_production/mc/MCP2025C_FallProduction/v10_14_02/prodgenie_corsika_proton_rockbox0p1_sbnd/CV/reco1/a5/gen_g4_detsim_reco1-a5f42e7e-aae1-243a-11b2-fad9417d6ce0.root
cd "$D/data"
lar -c "$HERE/extract-evt.fcl" -s "$SRC" -n 1 --nskip 11 > "$D/data/extract.log" 2>&1
echo "lar rc=$?"
ls -la evt-270-6-46.root 2>/dev/null | awk '{printf "  %.1f MB  %s\n",$5/1048576,$NF}'
