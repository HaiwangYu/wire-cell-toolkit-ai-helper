#!/bin/bash
# Clean WCT configure for the SBND e26 profile, reconstructed from the option
# set recovered from build/config.log (see ai-helper issue 22).
#
# Run INSIDE SL7.  Building on the host links against glibc 2.34 and yields
# plugins that fail to LOAD at runtime (__libc_single_threaded) with no build
# error -- see the build doc.
set -uo pipefail
P=/cvmfs/larsoft.opensciencegrid.org/products
SPD=$P/spdlog/v1_14_1/Linux64bit+3.10-2.17-e26-prof          # external-fmt build
FMT=$P/fmt/v11_0_2/Linux64bit+3.10-2.17-e26-prof             # libfmt.a -- lib64!

# wcb has NO --with-fmt.  waft/generic.py:140,146 splits --with-X-include and
# --with-X-lib on commas, so fmt rides along inside the spdlog options -- which
# is how the 2-element INCLUDES_SPDLOG/LIBPATH_SPDLOG lists arise.
# BOTH fmt paths must be lib64; the previous hand-patched cache said `lib`,
# which does not exist, so -lfmt was searched in an empty directory.
# The define must be on the CHECK compile line, not just the build.  waf does
# NOT read a `DEFINES` env var here (verified: the failing check line carried
# -DEIGEN_HAS_CXX11/-DSPDLOG_ACTIVE_LEVEL but not ours), so it goes through
# CXXFLAGS, which waf's add_os_flags does honour.  Without it, spdlog's
# fmt/fmt.h includes <spdlog/fmt/bundled/core.h>, which an external-fmt build
# does not ship -- the check then fails with "No such file or directory".
export CXXFLAGS="-DSPDLOG_FMT_EXTERNAL"

cd /exp/sbnd/app/users/yuhw/wire-cell-toolkit
./wcb configure --prefix=/exp/sbnd/app/users/yuhw/opt \
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
