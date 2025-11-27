#!/bin/bash

rm -rf ~/share/*

cmake --build build/ --target uninstall

rm -rf build/
