import numpy as np
from qiskit import QuantumCircuit
import os, sys

sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs, gather
from cunqa.circuit import CunqaCircuit



def build_grover_circuit():
    print("Creando el circuito de grover.")
    
    qc = QuantumCircuit(2)
    
    qc.h([0, 1])
    qc.cz(0, 1)

    qc.h([0, 1])
    qc.z([0, 1])
    qc.cz(0, 1)
    qc.h([0, 1])

    qc.measure_all()
    
    print("Circuito creado")
    
    return qc

def main():
    
    qpus = get_QPUs(on_node=False)

    for q in qpus:
        print(f"QPU {q.id}, backend: {q.backend.name}, simulator: {q.backend.simulator}, version: {q.backend.version}.")

    grover_qc = build_grover_circuit()
    
    print("Comenzando ejecucion")
    
    qjobs = []
    for _ in range(1):
        for qpu in qpus:
            qjobs.append(qpu.run(grover_qc, shots=1024))
            
    print("Ejecucion finalizada")
    
    results = gather(qjobs)
    
    for result in results:
        print("Result: ", result.counts)
        print("Time taken: ", result.time_taken)
    
if __name__ == "__main__":
    main()
