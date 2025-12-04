#!/bin/bash

if [ "$#" -gt 2 ]; then
    echo "Usage: source configure.sh [--ninja] [install_path]"
    return 1 2>/dev/null || exit 1
fi

echo "Configuring environment for LUSITANIA (Lusi2 Compat Mode + ccache)"

module load gcc/gcc-11.2.0 cmake/cmake-3.23 openmpi/openmpi-4.1.2-gcc11.2.0 ccache

#ccache -C
#ccache -z # Reset stats

export CC="ccache mpicc"
export CXX="ccache mpicxx"

export STORE=$HOME
export CMAKE_PREFIX_PATH="/lusitania_apps/openblas-0.3.24:$CMAKE_PREFIX_PATH"
export BLA_VENDOR=OpenBLAS

# Pybind11 detection
PYBIND_PATH=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())")
if [ -z "$PYBIND_PATH" ]; then
    echo "Error: Could not find pybind11. Make sure to run: pip install pybind11"
fi
export pybind11_DIR=$PYBIND_PATH

USE_NINJA=false
INSTALL_PREFIX=""

for arg in "$@"; do
    if [ "$arg" == "--ninja" ]; then
        USE_NINJA=true
        echo "Ninja Mode: ENABLED"
    else
        INSTALL_PREFIX="$arg"
    fi
done

rm -rf build/

COMMON_FLAGS="-DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX -DNATIVE_ARCH=OFF -DDDSIM_NATIVE_ARCH=OFF -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE"

if [ "$USE_NINJA" = true ]; then
  cmake -G Ninja -S . -B build/ $COMMON_FLAGS
  ninja -C build -j 1
  cmake --install build/
else
  cmake -S . -B build/ $COMMON_FLAGS
  time cmake --build build/ --parallel 1
  cmake --install build/
fi
