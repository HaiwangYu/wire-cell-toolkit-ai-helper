#!/bin/bash
# Configure + build + install WCT 0.32.x (patched) inside SL7.  Mirrors the UPS
# recipe build-framework-wirecell-ssi-build/build_wirecell.sh (e26:prof) so the
# result is a drop-in for the cvmfs wirecell v0_32_1 libraries.
# Usage: SL7_SETUP=none in-gpvm-sl7.sh bash build-wct-0.32.sh [configure|build|install|all]
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$here/env-0.32.sh"
cd "$WCT_SRC"
step=${1:-all}
NJ=${NJ:-32}
if [[ $step == configure || $step == all ]]; then
  env CC=gcc CXX=g++ FC=gfortran CXXFLAGS="-std=c++17" \
  ./wcb configure \
    --prefix="$WCT_PREFIX" \
    --with-spdlog="$SPDLOG_FQ_DIR" --with-spdlog-lib="$SPDLOG_LIB" \
    --with-jsoncpp="$JSONCPP_FQ_DIR" --with-jsoncpp-lib="$JSONCPP_LIB" \
    --with-jsonnet="$GOJSONNET_FQ_DIR" \
    --with-eigen-include="$EIGEN_DIR/include/eigen3" \
    --with-root="$ROOTSYS" \
    --with-fftw="$FFTW_FQ_DIR" --with-fftw-include="$FFTW_INC" --with-fftw-lib="$FFTW_LIBRARY" \
    --with-fftwthreads="$FFTW_FQ_DIR" \
    --with-tbb="$TBBROOT" \
    --boost-includes="$BOOST_FQ_DIR/include" --boost-libs="$BOOST_FQ_DIR/lib" --boost-mt \
    --build-debug="-O3 -g -DNDEBUG -fno-omit-frame-pointer" \
    --with-libtorch="$LIBTORCH_FQ_DIR/" --with-libtorch-libs torch,torch_cpu,c10
fi
if [[ $step == build || $step == all ]]; then
  ./wcb --notests build -j"$NJ"
fi
if [[ $step == install || $step == all ]]; then
  ./wcb --notests install
  echo "INSTALLED: $(ls "$WCT_PREFIX"/lib/libWireCell*.so | wc -l) libWireCell*.so in $WCT_PREFIX/lib"
fi
echo "WCB_RC=0 step=$step"
