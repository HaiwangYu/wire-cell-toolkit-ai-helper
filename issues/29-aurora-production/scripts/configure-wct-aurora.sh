#!/bin/bash
# Aurora port of configure-wct-polaris.sh: identical product versions, but from
# twester's Flare UPS tree ($UPS_TREE) and our overlay ($Y/products) instead of
# CVMFS.  Run INSIDE SL7 via in-aurora-sl7.sh (setup-aurora-opt.sh sourced).
set -uo pipefail
P=${UPS_TREE:-/lus/flare/projects/neutrinoGPU/scisoft/larsoft}
O=${Y:-/lus/flare/projects/neutrinoGPU/yuhw}/products
SPD=$O/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof          # external-fmt build
FMT=$O/fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof             # libfmt.a -- lib64!
export CXXFLAGS="-DSPDLOG_FMT_EXTERNAL"
: "${WCT_SRC:=/lus/flare/projects/neutrinoGPU/yuhw/wire-cell-toolkit}"
: "${OPT:=/lus/flare/projects/neutrinoGPU/yuhw/opt}"

cd "$WCT_SRC"
# wcb is "#!/usr/bin/env python"; in the clean SL7 env that is python2. Use python3.
python3 ./wcb configure --prefix="$OPT" \
  --build-debug="-O3 -g -fno-omit-frame-pointer" \
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
  --boost-libs=$P/boost/v1_82_0/Linux64bit+3.10-2.17-e26-prof/lib \
  --boost-mt \
  --with-hdf5=$P/hdf5/v1_12_2a/Linux64bit+3.10-2.17-e26-prof \
  --with-spdlog-include=$SPD/include,$FMT/include \
  --with-spdlog-lib=$SPD/lib64,$FMT/lib64 \
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
