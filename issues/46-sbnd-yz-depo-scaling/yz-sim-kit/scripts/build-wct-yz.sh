#!/bin/bash
# Build the Wire-Cell Toolkit branch sbnd-yz-depo-scaling (route B of the
# README) against sbndcode v10_14_02_03's externals (e26:prof), in the SL7
# container.  Then use it with:  export YZ_WCT_LIB=<prefix>/lib; source setup-yz-env.sh
#
# Usage: build-wct-yz.sh <source-dir> <install-prefix> [jobs=8]
#   <source-dir> is cloned from https://github.com/HaiwangYu/wire-cell-toolkit
#   (branch sbnd-yz-depo-scaling) if it does not exist yet.
# Same configure options as ai-helper issue 46 scripts/build-wct-yz.sh (which
# built /exp/sbnd/app/users/yuhw/opt-yz).  Needs ~9 GB for the source + build,
# ~2 GB for the install; 12 min with 12 jobs on sbndbuild03.
SRC=${1:?usage: build-wct-yz.sh <source-dir> <install-prefix> [jobs]}
PREFIX=${2:?usage: build-wct-yz.sh <source-dir> <install-prefix> [jobs]}
JOBS=${3:-8}
if ! grep -q 'release 7' /etc/redhat-release 2>/dev/null; then
    echo "run this inside the fnal-dev-sl7 container" >&2; exit 1
fi
source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh >/dev/null 2>&1
setup sbndcode v10_14_02_03 -q e26:prof || exit 1
set -e
if [[ ! -d "$SRC" ]]; then
    git clone -b sbnd-yz-depo-scaling https://github.com/HaiwangYu/wire-cell-toolkit.git "$SRC"
fi
cd "$SRC"
git log --oneline -1
# The fork carries no tags, and wcb takes its version from `git describe --tags`;
# without a tag it wants a version.txt.
git describe --tags >/dev/null 2>&1 || echo "sbnd-yz-depo-scaling-$(git rev-parse --short HEAD)" > version.txt
P=/cvmfs/larsoft.opensciencegrid.org/products
export CXXFLAGS=-DSPDLOG_FMT_EXTERNAL
./wcb configure --prefix="$PREFIX" --build-debug="-O2 -g" \
  --with-tbb=$P/tbb/v2021_9_0/Linux64bit+3.10-2.17-e26 \
  --with-jsoncpp=$P/jsoncpp/v1_9_5a/Linux64bit+3.10-2.17-e26-prof \
  --with-jsonnet-include=$P/gojsonnet/v0_18_0/Linux64bit+3.10-2.17-e26/include \
  --with-jsonnet-lib=$P/gojsonnet/v0_18_0/Linux64bit+3.10-2.17-e26/lib \
  --with-eigen-include=$P/eigen/v23_08_01_66e8f/include/eigen3/ \
  --with-root=$P/root/v6_28_12/Linux64bit+3.10-2.17-e26-p3915-prof \
  --with-fftw=$P/fftw/v3_3_10/Linux64bit+3.10-2.17 \
  --with-fftw-include=$P/fftw/v3_3_10/Linux64bit+3.10-2.17/include \
  --with-fftw-lib=$P/fftw/v3_3_10/Linux64bit+3.10-2.17/lib \
  --with-fftwthreads=$P/fftw/v3_3_10/Linux64bit+3.10-2.17 \
  --boost-includes=$P/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/include \
  --boost-libs=$P/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/lib --boost-mt \
  --with-hdf5=$P/hdf5/v1_12_2a/Linux64bit+3.10-2.17-e26-prof \
  --with-spdlog-include=$P/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/include,$P/fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof/include \
  --with-spdlog-lib=$P/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof/lib64,$P/fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof/lib64 \
  --with-spdlog-libs=spdlog,fmt \
  --with-protobuf-include=$P/protobuf/v3_21_12a/Linux64bit+3.10-2.17-e26/include/ \
  --with-protobuf-lib=$P/protobuf/v3_21_12a/Linux64bit+3.10-2.17-e26/lib \
  --with-grpc=$P/grpc/v1_35_0c/Linux64bit+3.10-2.17-e26 \
  --with-grpc-include=$P/grpc/v1_35_0c/Linux64bit+3.10-2.17-e26/include \
  --with-grpc-lib=$P/grpc/v1_35_0c/Linux64bit+3.10-2.17-e26/lib \
  --with-triton-include=$P/triton/v2_25_0d/Linux64bit+3.10-2.17-e26/include \
  --with-triton-lib=$P/triton/v2_25_0d/Linux64bit+3.10-2.17-e26/lib \
  --with-libtorch=$P/libtorch/v2_1_1b/Linux64bit+3.10-2.17-e26/ \
  --with-libtorch-include=$P/libtorch/v2_1_1b/Linux64bit+3.10-2.17-e26/include,$P/libtorch/v2_1_1b/Linux64bit+3.10-2.17-e26/include/torch/csrc/api/include \
  --with-libtorch-libs torch,torch_cpu,c10
./wcb -j"$JOBS" --notests install
ls "$PREFIX/lib"/libWireCellGen.so
nm -DC "$PREFIX/lib/libWireCellGen.so" | grep -q 'DepoTransformYZ' && echo "OK: DepoTransformYZ is in $PREFIX/lib/libWireCellGen.so"
