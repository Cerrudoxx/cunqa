#!/bin/bash

echo "Lanzando ejemplos con comunicación clásica"
for script in examples/python/cc_examples/0{1,2,3,4,5}-*.py examples/python/cc_examples/distributed_raw.py; do
    python "$script"
    if [ $? -ne 0 ]; then
        echo "Error: $(basename $script) no terminó correctamente"
        exit 1
    fi
    echo "$(basename $script) ejecutado"
done

echo "Lanzando ejemplos con comunicación cuántica"
for script in examples/python/qc_examples/0{1,2,3,4}-*.py; do
    python "$script"
    if [ $? -ne 0 ]; then
        echo "Error: $(basename $script) no terminó correctamente"
        exit 1
    fi
    echo "$(basename $script) ejecutado"
done

echo "Lanzando ejemplos simples"
for script in examples/python/simple_examples/*.py; do
    python "$script"
    if [ $? -ne 0 ]; then  
        echo "Error: $(basename $script) no terminó correctamente"
        exit 1
    fi
    echo "$(basename $script) ejecutado"
done