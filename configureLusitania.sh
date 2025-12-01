#!/bin/bash

if [ "$#" -gt 2 ]; then
    echo "Usage: source configure.sh [--ninja] [install_path]"
    echo "Arguments:"
    echo "  --ninja       (Optional) Use Ninja build system generator for faster compilation."
    echo "  install_path  (Optional) Destination directory for the installation."
    return 1 2>/dev/null || exit 1
fi

#module purge

echo "Configuring environment for LUSITANIA"

load_required_module() {
    module load "$1"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to load required module '$1'. Exiting."
        return 1 2>/dev/null || exit 1
    fi
}

echo "Loading essential modules..."
load_required_module "gcc/gcc-11.2.0"
load_required_module "cmake/cmake-3.23"
load_required_module "openblas/openblas-0.3.24"
load_required_module "openmpi/openmpi-4.1.2-gcc11.2.0"
load_required_module "python/python-3.10"

echo "Checking for ccache..."
module load ccache
if [ $? -eq 0 ]; then
    echo "ccache loaded successfully. Compilation will be cached."
    export CC="ccache mpicc"
    export CXX="ccache mpicxx"
else
    echo "WARNING: ccache module not found or failed to load."
    echo "Proceeding with standard mpicc/mpicxx compilation (slower)."
    export CC="mpicc"
    export CXX="mpicxx"
fi

export STORE=$HOME
# CC and CXX are exported above based on ccache availability
export CMAKE_PREFIX_PATH="/lusitania_apps/openblas-0.3.24:$CMAKE_PREFIX_PATH"
export BLA_VENDOR=OpenBLAS

# Locate pybind11
PYBIND_PATH=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())")

if [ -z "$PYBIND_PATH" ]; then
    echo "Error: Could not find pybind11. Make sure to run: pip install pybind11"
    # exit 1
fi

export pybind11_DIR=$PYBIND_PATH
echo "pybind11 found at: $pybind11_DIR"

USE_NINJA=false
INSTALL_PREFIX=""

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


if [ "$USE_NINJA" = true ]; then
  # If INSTALL_PREFIX is empty, cmake uses default (/usr/local or CMakeLists definition)
  cmake -G Ninja -S . -B build/ -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
  ninja -C build -j $(nproc)
  cmake --install build/
else
  cmake -S . -B build/ -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
  time cmake --build build/ --parallel $(nproc)
  cmake --install build/
fi