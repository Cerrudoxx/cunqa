#!/bin/bash

cd examples/python

#Comunicacion cuantica
qraise -n 4 -t 00:10:00 --co-located --quantum_comm

sleep 5

python qc_examples/01-teledata_simple_example.py
echo "1 ejemplo completado"

python qc_examples/02-teledata-alternative-example.py
echo "2 ejemplos completado"

python qc_examples/03-telegate_example.py
echo "3 ejemplos completado"

python qc_examples/04-qdistributed_QPE.py
echo "4 ejemplos completado"

qdrop --all
sleep 5


#Comunicacion clasica
qraise -n 4 -t 00:10:00 --co-located --classical_comm
sleep 5

python cc_examples/01-the_easy_one.py
echo "5 ejemplos completado"

python cc_examples/02-the_cyclic_one.py
echo "6 ejemplos completado"

python cc_examples/03-the_better_cyclic_one.py
echo "7 ejemplos completado"

python cc_examples/04-distr_QPE.py
echo "8 ejemplos completado"

python cc_examples/05-ibm-cut-bell-pairs-telegate.py
echo "9 ejemplos completado"

qdrop --all
sleep 5

#Ejemplos simples
qraise -n 4 -t 00:10:00 --co-located 
sleep 5

python simple_examples/cif_example.py
echo "10 ejemplos completado"

python simple_examples/circuit_sum_and_union.py
echo "11 ejemplos completado"

python simple_examples/cloud_example.py
echo "12 ejemplos completado"

python simple_examples/co-located_example.py
echo "13 ejemplos completado"

python simple_examples/example_qraise.py
echo "14 ejemplos completado"

python simple_examples/hpc_example.py
echo "15 ejemplos completado"

python simple_examples/update_parameters.py
echo "16 ejemplos completado"

qdrop --all
sleep 5

#Prueba qraise
qraise -n 2 -t 00:05:00 --co-located --partition=lusi2
sleep 5
echo "qraise en particion lusi2 completado"

qraise -n 2 -t 00:05:00 --co-located --partition=qcomputaex
sleep 5
echo "qraise en particion qcomputaex completado"

qdrop --all