#!/bin/bash

# ==============================================================================
# SCRIPT DE DESPLIEGUE DE MÓDULO PARA LUSITANIA
# Uso: ./deploy_module.sh /ruta/de/instalacion/final
# Ejemplo: ./deploy_module.sh /opt/cesga/software/cunqa/0.3.1
# ==============================================================================

# Detener el script si hay errores
set -e

if [ -z "$1" ]; then
    echo "ERROR: Debes especificar la ruta de instalación (prefix)."
    echo "Uso: $0 <install_prefix>"
    echo "Ejemplo: $0 /lustre/software/cunqa/0.3.1"
    exit 1
fi

INSTALL_PREFIX="$1"
echo ">>> Iniciando despliegue de CUNQA en: $INSTALL_PREFIX"

echo ">>> Cargando módulos del sistema..."

set +e

module purge
module load gcc/gcc-11.2.0 \
            cmake/cmake-3.23 \
            openblas/openblas-0.3.24 \
            openmpi/openmpi-4.1.2-gcc11.2.0 \
            python/python-3.10

set -e

PYBIND_PATH=$(python3 -c "import pybind11; print(pybind11.get_cmake_dir())" 2>/dev/null)
if [ -z "$PYBIND_PATH" ]; then
    echo "ADVERTENCIA: No se detectó pybind11 instalado en Python."
    echo "Intentando cargar módulo pybind11..."
    module load pybind11 2>/dev/null || echo "No se encontró módulo pybind11. La compilación podría fallar."
else
    export pybind11_DIR=$PYBIND_PATH
    echo ">>> Pybind11 detectado en: $PYBIND_PATH"
fi

export CC="mpicc"
export CXX="mpicxx"
export BLA_VENDOR=OpenBLAS
# si OpenBLAS da problemas, descomenta la siguiente línea:
# export CMAKE_PREFIX_PATH="/lusitania_apps/openblas-0.3.24:$CMAKE_PREFIX_PATH"

echo ">>> Limpiando directorio de construcción..."
rm -rf build/
mkdir -p build

# -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE: Ayuda a que el binario encuentre las librerías cargadas por módulos
echo ">>> Configurando CMake..."
cmake -S . -B build/ \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_RPATH="$INSTALL_PREFIX/lib" \
    -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=TRUE \
    -DNATIVE_ARCH=OFF \
    -DDDSIM_NATIVE_ARCH=OFF

echo ">>> Compilando (Paralelismo: $(nproc) cores)..."
cmake --build build/ -j $(nproc)

echo ">>> Instalando archivos en $INSTALL_PREFIX ..."
cmake --install build/

PY_VER_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_VER_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
SITE_PACKAGES="$INSTALL_PREFIX/lib/python${PY_VER_MAJOR}.${PY_VER_MINOR}/site-packages"

echo ""
echo "=============================================================================="
echo "¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "=============================================================================="
echo "Ahora crea el archivo de módulo (.lua) con la siguiente información:"
echo ""
echo "prepend_path('PATH', '$INSTALL_PREFIX/bin')"
echo "prepend_path('LD_LIBRARY_PATH', '$INSTALL_PREFIX/lib')"
echo "prepend_path('PYTHONPATH', '$SITE_PACKAGES')"
echo "setenv('CUNQA_ROOT', '$INSTALL_PREFIX')"
echo ""
echo "=============================================================================="
