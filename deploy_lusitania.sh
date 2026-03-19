#!/bin/bash
# ==============================================================================
# SCRIPT DE DESPLIEGUE DE CUNQA PARA LUSITANIA
# ==============================================================================

# Detener el script si hay errores críticos
set -e

if [ -z "$1" ]; then
    echo "ERROR: Debes especificar la ruta de instalación (prefix)."
    echo "Uso: $0 <install_prefix>"
    exit 1
fi

INSTALL_PREFIX="$1"
echo "======================================================="
echo " Desplegando CUNQA en LUSITANIA "
echo " Directorio destino: $INSTALL_PREFIX "
echo "======================================================="

echo ">>> Cargando módulos del sistema..."
set +e
module purge
module load gcc/gcc-11.2.0 \
            cmake/cmake-3.23 \
            openblas/openblas-0.3.24 \
            openmpi/openmpi-4.1.2-gcc11.2.0 \
            python/python-3.10 \
            boost/boost-1.85.0 \
            ccache/ccache-4.8.3
set -e

# ==============================================================================
# 1. RESOLUCIÓN DE DEPENDENCIAS PYTHON
# ==============================================================================
echo ">>> Comprobando dependencias de Python (Cython, PyZMQ, Pybind11)..."
if ! python3 -c "import cython; import zmq; import pybind11" 2>/dev/null; then
    echo "Faltan dependencias en Python 3.10. Intentando instalar..."
    if ! python3 -m pip install --user cython pyzmq pybind11; then
        PYTHON_310_BIN=$(which python3)
        set +e
        module purge
        mkdir -p /tmp/cunqa_offline_pkgs
        cd /tmp/cunqa_offline_pkgs
        python3 -m pip download cython pyzmq pybind11 --only-binary=:all: --python-version 3.10 --abi cp310 --platform manylinux2014_x86_64
        module load gcc/gcc-11.2.0 cmake/cmake-3.23 openblas/openblas-0.3.24 openmpi/openmpi-4.1.2-gcc11.2.0 python/python-3.10 boost/boost-1.78.0
        $PYTHON_310_BIN -m pip install *.whl
        cd -
        rm -rf /tmp/cunqa_offline_pkgs
        set -e
    fi
fi

PYBIND_PATH=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())" 2>/dev/null)
if [ -n "$PYBIND_PATH" ]; then
    export pybind11_DIR=$PYBIND_PATH
    echo ">>> Pybind11 detectado e inyectado en: $PYBIND_PATH"
fi

# ==============================================================================
# 2. CONFIGURACIÓN DE COMPILADORES
# ==============================================================================
export CC="gcc"
export CXX="g++"
export BLA_VENDOR=OpenBLAS

# ==============================================================================
# 3. LIMPIEZA PREVIA 
# ==============================================================================
echo ">>> Limpiando directorio de construcción..."
rm -rf build/
mkdir -p build/

# ==============================================================================
# 4. LANZAMIENTO DE CMAKE (Fase de configuración y descargas)
# ==============================================================================
echo ">>> Configurando CMake..."
cmake -S . -B build/ \
    -DCMAKE_C_COMPILER_LAUNCHER=ccache \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_RPATH="$INSTALL_PREFIX/lib" \
    -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE \
    -DNATIVE_ARCH=OFF \
    -DDDSIM_NATIVE_ARCH=OFF \
    -DUSE_MPI_BTW_QPU=OFF \
    -DUSE_ZMQ_BTW_QPU=ON

# ==============================================================================
# 5. COMPILACIÓN E INSTALACIÓN
# ==============================================================================
echo ">>> Compilando (Paralelismo: $(nproc) cores)..."
cmake --build build/ -j $(nproc)

echo ">>> Instalando archivos en $INSTALL_PREFIX ..."
cmake --install build/

echo ">>> Estadísticas de ccache:"
ccache -s

echo "======================================================="
echo " ¡Despliegue finalizado con éxito! "
echo "======================================================="
