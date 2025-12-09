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

find_package(Python COMPONENTS Interpreter Development REQUIRED)
message(STATUS "Found Python: ${Python_EXECUTABLE} (Version: ${Python_VERSION})")

# Asume 'module load pybind11' o que está en path
find_package(pybind11 CONFIG REQUIRED)
message(STATUS "Found Pybind11: ${pybind11_DIR} (Version: ${pybind11_VERSION})")

# Definimos la versión para uso interno si es necesario
set(PYBIND11_PYTHON_VERSION "${Python_VERSION_MAJOR}.${Python_VERSION_MINOR}" CACHE STRING "")

find_package(Threads REQUIRED)
find_package(MPI REQUIRED)
find_package(OpenMP REQUIRED)
find_package(Boost REQUIRED)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)

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
    message(STATUS "Found package ${PACKAGE_NAME}")
  endif()
endfunction()

# Compiler flags: save current and silence warnings for dependencies
set(_old_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
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

# MQT-DDSIM
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

# Restaurar flags originales
set(CMAKE_CXX_FLAGS "${_old_CXX_FLAGS}")

include_directories("${CMAKE_CURRENT_SOURCE_DIR}/src/utils/logger" "${CMAKE_CURRENT_SOURCE_DIR}/src")

add_subdirectory(src)
add_subdirectory(cunqa)
add_subdirectory(examples)

# Target uninstall
if(NOT TARGET uninstall)
  configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
    IMMEDIATE @ONLY)

  add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake)
endif()
