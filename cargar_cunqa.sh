#!/bin/bash

module load python/python-cunqa-ex gcc/gcc-11.2.0 cmake/cmake-3.23 openblas/openblas-0.3.24 openmpi/openmpi-4.1.2-gcc11.2.0 libraries/libffi-devel-8.1

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/lusitania_apps/python/python-3.10.6/lib