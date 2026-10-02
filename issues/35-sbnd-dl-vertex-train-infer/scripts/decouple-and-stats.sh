#!/bin/bash
# issue 35: decoupling test + decision statistics (run INSIDE SL7 via run-sl7.pbs: CMD=$0)
python3 /lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit-ai-helper/issues/35-sbnd-dl-vertex-train-infer/scripts/dlvtx-decouple.py /lus/flare/projects/neutrinoGPU/yuhw/production-prep/ncsb-dlvtx-20261001 /lus/flare/projects/neutrinoGPU/yuhw/production-prep/ncsb-dlvtx-nodual-20261002
echo; echo '--- stats, dual chain ON dumps (MC-9, NCpi0-19, nueCC-48)'
python3 /lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit-ai-helper/issues/35-sbnd-dl-vertex-train-infer/scripts/dlvtx-stats.py /lus/flare/projects/neutrinoGPU/yuhw/production-prep/mc50-dlvtx-20261001/pr/c*/pr_evt*/tracking-pr.root /lus/flare/projects/neutrinoGPU/yuhw/production-prep/ncsb-dlvtx-20261001/pr/c*/pr_evt*/tracking-pr.root /lus/flare/projects/neutrinoGPU/yuhw/production-prep/nuecc48-dlvtx-20261001/pr/c*/pr_evt*/tracking-pr.root
echo; echo '--- stats, dual chain OFF (NCpi0-19)'
python3 /lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit-ai-helper/issues/35-sbnd-dl-vertex-train-infer/scripts/dlvtx-stats.py /lus/flare/projects/neutrinoGPU/yuhw/production-prep/ncsb-dlvtx-nodual-20261002/pr/c*/pr_evt*/tracking-pr.root
