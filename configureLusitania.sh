#!/bin/bash

# --- 1. Check number of parameters (Maximum 2) ---
if [ "$#" -gt 2 ]; then
    echo "Usage: source configure.sh [--ninja] [install_path]"
    echo "Arguments:"
    echo "  --ninja       (Optional) Use Ninja build system generator for faster compilation."
    echo "  install_path  (Optional) Destination directory for the installation."
    exit 1
fi

module purge

echo "Configuring environment for LUSITANIA"

module load gcc/gcc-11.2.0 cmake/cmake-3.23 openblas/openblas-0.3.24 openmpi/openmpi-4.1.2-gcc11.2.0 python/python-3.10

export STORE=$HOME
export CC=mpicc
export CXX=mpicxx
export CMAKE_PREFIX_PATH="/lusitania_apps/openblas-0.3.24:$CMAKE_PREFIX_PATH"
export BLA_VENDOR=OpenBLAS
PYBIND_PATH=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())")

if [ -z "$PYBIND_PATH" ]; then
    echo "Error: Could not find pybind11. Make sure to run: pip install pybind11"
   # exit 1
fi

export pybind11_DIR=$PYBIND_PATH
echo "pybind11 found at: $pybind11_DIR"

USE_NINJA=false
INSTALL_PREFIX=""

# --- 2. Loop to identify which arg is the path and which is the flag ---
for arg in "$@"; do
    if [ "$arg" == "--ninja" ]; then
        USE_NINJA=true
        echo "Ninja Mode: ENABLED"
    else
        # If argument is not the flag, assume it is the installation path
        INSTALL_PREFIX="$arg"
    fi
done

rm -rf build/

# --- 3. Conditional execution (Using INSTALL_PREFIX variable instead of $1) ---

if [ "$USE_NINJA" = true ]; then
  # If INSTALL_PREFIX is empty, cmake uses default (/usr/local or CMakeLists definition)
  cmake -G Ninja -S . -B build/ -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
  ninja -C build -j $(nproc)
  cmake --install build/
else
  cmake -S . -B build/ -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
  cmake --build build/ --parallel $(nproc)
  cmake --install build/
fi
