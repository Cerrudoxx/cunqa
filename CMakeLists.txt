cmake_minimum_required(VERSION 3.21)

project(CUNQA VERSION 0.3.1 LANGUAGES CXX)

# --- PARCHE DE ARQUITECTURA (Lusi2 / Sandy Bridge) ---
set(NATIVE_ARCH OFF CACHE BOOL "Force disable MQT native" FORCE)
set(DDSIM_NATIVE_ARCH OFF CACHE BOOL "Force disable DDSim native" FORCE)
set(ENABLE_AVX2 OFF CACHE BOOL "Disable AVX2 usage in Aer" FORCE)
set(ENABLE_NATIVE OFF CACHE BOOL "Generic native disable" FORCE)

set(FLAGS_BLACKLIST 
    "-march=x86-64"      
    "-mtune=sandybridge" 
    "-mno-avx2"          
    "-mno-fma"       
    "-mno-bmi"           
    "-mno-bmi2"          
    "-mno-f16c"          
    "-mno-rdrnd"         
    "-mno-movbe"         
    "-mno-abm" 
    "-mno-fsgsbase"      
)

add_compile_options(${FLAGS_BLACKLIST})
add_link_options(${FLAGS_BLACKLIST})

# [FIX] Silenciar warnings y errores de deprecación GLOBALMENTE
add_compile_options("-w")
add_compile_options("-Wno-error=deprecated-declarations")

message(STATUS "CMAKE BUILD TYPE: ${CMAKE_BUILD_TYPE}")
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Adding C++20 standard as required
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
message(STATUS "C++ version ${CMAKE_CXX_STANDARD} configured.")

set(CUNQA_DATA_DIR "share/cunqa") 

set(CUNQA_FULL_DATA_PATH "${CMAKE_INSTALL_PREFIX}/${CUNQA_DATA_DIR}")
set(CUNQA_PATH "${CUNQA_FULL_DATA_PATH}")
set(QPUS_FILEPATH "${CUNQA_FULL_DATA_PATH}/qpus.json")
set(COMM_FILEPATH "${CUNQA_FULL_DATA_PATH}/communications.json")

include_directories("${CMAKE_BINARY_DIR}/src")

# Configuración de instalación estándar
set(CMAKE_INSTALL_LIBDIR "lib")
set(CMAKE_INSTALL_BINDIR "bin")

set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}")
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

message(STATUS "Install location (Prefix): ${CMAKE_INSTALL_PREFIX}")
message(STATUS "CUNQA Data location: ${CUNQA_FULL_DATA_PATH}")

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
set(PYTHON_SITE_PACKAGES "lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}/site-packages")
message(STATUS "Found Python: ${Python3_EXECUTABLE} (Version: ${Python3_VERSION})")

find_package(pybind11 CONFIG REQUIRED)
message(STATUS "Found Pybind11: ${pybind11_DIR} (Version: ${pybind11_VERSION})")

set(PYBIND11_PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}" CACHE STRING "")

find_package(Threads REQUIRED)
find_package(MPI REQUIRED)
find_package(OpenMP REQUIRED)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)

# =====================================================================
#  BOOST (FIX CRÍTICO)
# =====================================================================
# 1. Buscamos Boost 1.78.0 (del sistema).
find_package(Boost 1.78.0 REQUIRED COMPONENTS json serialization container)

if(Boost_FOUND)
    message(STATUS "Boost Found! Include Dir: ${Boost_INCLUDE_DIRS}")
    # Inyectar globalmente para el proyecto principal
    include_directories(SYSTEM ${Boost_INCLUDE_DIRS})
else()
    message(FATAL_ERROR "Boost not found. Please load the module: module load boost/1.78.0")
endif()

# 3. Targets dummy
if(NOT TARGET Boost::multiprecision)
    add_library(Boost::multiprecision INTERFACE IMPORTED)
    set_target_properties(Boost::multiprecision PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIRS}")
endif()
if(NOT TARGET Boost::json)
    add_library(Boost::json INTERFACE IMPORTED)
    set_target_properties(Boost::json PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${Boost_INCLUDE_DIRS}")
endif()


include(FetchContent)

function(find_or_fetch_package PACKAGE_NAME GIT_REPOSITORY VERSION TAG)
  find_package(${PACKAGE_NAME} ${VERSION} QUIET)
  if(NOT ${PACKAGE_NAME}_FOUND)
    message(STATUS "Package ${PACKAGE_NAME} not found, fetching from ${GIT_REPOSITORY}")
    FetchContent_Declare(
        ${PACKAGE_NAME}
        GIT_REPOSITORY ${GIT_REPOSITORY}
        GIT_TAG        ${TAG}
    )
    FetchContent_MakeAvailable(${PACKAGE_NAME})
  else()
    message(STATUS "Found package ${PACKAGE_NAME}: ${PACKAGE_NAME}_DIR = ${${PACKAGE_NAME}_DIR}")
  endif()
endfunction()

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -w")

# =====================================================================
#  DEPENDENCIAS EXTERNAS (FetchContent)
# =====================================================================

# Nlohmann JSON
find_or_fetch_package(
  nlohmann_json
  "git@github.com:nlohmann/json.git"
  "3.11.3"
  "v3.11.3"
)

# [FIX MAESTRO] Variable necesaria
if(TARGET nlohmann_json::nlohmann_json)
    get_target_property(JSON_INCLUDE_DIR nlohmann_json::nlohmann_json INTERFACE_INCLUDE_DIRECTORIES)
elseif(DEFINED nlohmann_json_SOURCE_DIR)
    set(JSON_INCLUDE_DIR "${nlohmann_json_SOURCE_DIR}/include")
endif()

# SPDLOG
set(SPDLOG_SYSTEM_INCLUDES OFF CACHE BOOL "Disable libsodium" FORCE)
set(SPDLOG_BUILD_SHARED ON CACHE BOOL "Build shared library" FORCE)
set(SPDLOG_BUILD_PIC ON CACHE BOOL "Build with position independent code" FORCE)
find_or_fetch_package(
  spdlog
  "git@github.com:gabime/spdlog.git"
  "1.16.0"
  "v1.16.0"
)
install(TARGETS spdlog DESTINATION "${CMAKE_INSTALL_LIBDIR}") 

# =====================================================================
#  MQT-DDSIM (FIX SUPER CRITICO)
# =====================================================================
set(Boost_USE_STATIC_LIBS OFF CACHE BOOL "" FORCE)

# [FIX] Inyectar ruta de Boost en CMAKE_CXX_FLAGS para subproyectos rebeldes
if(DEFINED Boost_INCLUDE_DIRS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -I${Boost_INCLUDE_DIRS}")
    message(STATUS "FORCING BOOST INCLUDE IN CXX_FLAGS: ${Boost_INCLUDE_DIRS}")
endif()

find_or_fetch_package(
  mqt-ddsim
  "git@github.com:munich-quantum-toolkit/ddsim.git"
  "1.24.0"
  "v1.24.0"
)

# ZeroMQ (libzmq)
set(WITH_DOCS OFF CACHE BOOL "Disable docs" FORCE)
set(ENABLE_CPACK OFF CACHE BOOL "Disable CPACK" FORCE)
set(WITH_PERF_TOOL OFF CACHE BOOL "Disable performance tool" FORCE)
set(ZMQ_BUILD_TESTS OFF CACHE BOOL "Disable tests" FORCE)
set(ENABLE_DRAFTS ON CACHE BOOL "Enable drafts" FORCE)
set(BUILD_SHARED ON CACHE BOOL "Build shared library" FORCE)
set(BUILD_STATIC OFF CACHE BOOL "Build static library" FORCE)
# FIX: Desactivar libsodium externo
set(WITH_LIBSODIUM OFF CACHE BOOL "Disable external libsodium" FORCE)
set(ENABLE_CURVE ON CACHE BOOL "Enable internal Curve" FORCE)

find_or_fetch_package(
  libzmq
  "git@github.com:zeromq/libzmq.git"
  "4.3.5"
  "v4.3.5"
)

# CppZMQ
set(CPPZMQ_BUILD_TESTS OFF CACHE BOOL "Disable tests" FORCE)
find_or_fetch_package(
  cppzmq
  "git@github.com:zeromq/cppzmq.git"
  "4.11.0"
  "v4.11.0"
)

# CUNQA SIMULATOR
find_or_fetch_package(
  cunqasimulator
  "git@github.com:CESGA-Quantum-Spain/cunqasimulator.git"
  "0.1.1"
  "v0.1.1"
)

# ARGPARSE
FetchContent_Declare(
    argparse
    GIT_REPOSITORY "git@github.com:morrisfranken/argparse.git"
    GIT_TAG "b1479bf9f2f44010ad79efff00bb9bf8ec56dbab"
)
FetchContent_MakeAvailable(argparse)

# AER
FetchContent_Declare(
    aer
    GIT_REPOSITORY "git@github.com:CESGA-Quantum-Spain/qiskit-aer_v0.17.2.git"
    GIT_TAG "717e77a5257c35ce49dfbb4e8ba8c23acbadfe14"
)
FetchContent_GetProperties(aer)
if(NOT aer_POPULATED)
    FetchContent_Populate(aer) 
endif()

add_library(aer_headers INTERFACE)
target_include_directories(aer_headers INTERFACE "${aer_SOURCE_DIR}/src" "${Python_INCLUDE_DIRS}")
if(OpenMP_FOUND)
  target_link_libraries(aer_headers INTERFACE OpenMP::OpenMP_CXX)
endif()
if(pybind11_FOUND)
  target_link_libraries(aer_headers INTERFACE pybind11::headers)
endif()

# =====================================================================
#  DEPENDENCIAS ADICIONALES (Maestro, PyZMQ, Qulacs)
# =====================================================================

include(GNUInstallDirs)

# -- PyZMQ -----------------------------------------------------------
FetchContent_Declare(
    pyzmq
    GIT_REPOSITORY "git@github.com:zeromq/pyzmq.git"
    GIT_TAG        "v25.1.2"
)
set(ZMQ_PREFIX "${libzmq_BINARY_DIR}" CACHE PATH "ZMQ_PREFIX" FORCE)
set(CMAKE_DISABLE_FIND_PACKAGE_Sodium ON CACHE BOOL "" FORCE)
set(ZMQ_DRAFT_API OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(pyzmq)

if(EXISTS "${pyzmq_SOURCE_DIR}/zmq/")
    install(DIRECTORY "${pyzmq_SOURCE_DIR}/zmq/" DESTINATION "${PYTHON_SITE_PACKAGES}/zmq")
endif()
if(TARGET _zmq)
    install(TARGETS "_zmq" DESTINATION "${PYTHON_SITE_PACKAGES}/zmq/backend/cython")
endif()


# -- Maestro Dependencies ---------------------------------------------
find_package(Eigen3 QUIET)
if(NOT Eigen3_FOUND)
  FetchContent_Declare(MaestroEigen GIT_REPOSITORY "https://gitlab.com/libeigen/eigen.git" GIT_TAG "bc3b39870ecb690a623a3f49149a358b95c5781d")
  FetchContent_MakeAvailable(MaestroEigen)
  set(EIGEN5_INCLUDE_DIR "${maestroeigen_SOURCE_DIR}") 
else()
  set(EIGEN5_INCLUDE_DIR "${EIGEN3_INCLUDE_DIR}") 
endif()

FetchContent_Declare(qcsim GIT_REPOSITORY "git@github.com:aromanro/QCSim.git" GIT_TAG "5a458c8b4bddfbbe445de09376b366a97d474266")
FetchContent_GetProperties(qcsim)
if(NOT qcsim_POPULATED)
    FetchContent_Populate(qcsim)
endif()
set(QCSIM_INCLUDE_DIR "${qcsim_SOURCE_DIR}/QCSim")

FetchContent_Declare(maestro-aer GIT_REPOSITORY "git@github.com:InvictusWingsSRL/qiskit-aer.git" GIT_TAG "96e82fdd1c8c1b17d749863ee5095262372e0d7e")
FetchContent_GetProperties(maestro-aer)
if(NOT maestro-aer_POPULATED)
    FetchContent_Populate(maestro-aer)
endif()
set(AER_INCLUDE_DIR "${maestro-aer_SOURCE_DIR}/src")

# -- Maestro ----------------------------------------------------------
FetchContent_Declare(maestro GIT_REPOSITORY "git@github.com:QoroQuantum/maestro.git" GIT_TAG "7ba339fc5595fd18d2fcb0612a6570c3c5e1fd90")
FetchContent_MakeAvailable(maestro)
target_include_directories(maestro PUBLIC "${maestro_SOURCE_DIR}")
install(TARGETS maestro DESTINATION "${CMAKE_INSTALL_LIBDIR}")

# -- Qulacs -----------------------------------------------------------
FetchContent_Declare(qulacs GIT_REPOSITORY "git@github.com:usendon/usendon_qulacs.git" GIT_TAG "228f617b9e31007b54488f467c031ebbf07efcdb")
set(USE_PYTHON OFF CACHE BOOL "Disable Qulacs Python bindings" FORCE)
set(BUILD_QULACS_WITH_MPI OFF)
if(BUILD_QULACS_WITH_MPI)
  set(USE_MPI ON CACHE BOOL "Enable MPI for Qulacs" FORCE)
endif()
FetchContent_MakeAvailable(qulacs)

# =====================================================================
#  PROYECTO
# =====================================================================

include_directories("${CMAKE_CURRENT_SOURCE_DIR}/src/utils/logger" "${CMAKE_CURRENT_SOURCE_DIR}/src")

add_subdirectory(src)
add_subdirectory(cunqa)
add_subdirectory(examples)

if(NOT TARGET uninstall)
  configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
    IMMEDIATE @ONLY)
  add_custom_target(uninstall COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake)
endif()