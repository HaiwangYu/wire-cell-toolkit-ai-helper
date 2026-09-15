# Full run environment for the 1-step chain on Polaris: opt + AP layering + DL vertex.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$HERE/setup-polaris-ap.sh"
source "$HERE/setup-polaris-dlvtx.sh"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
