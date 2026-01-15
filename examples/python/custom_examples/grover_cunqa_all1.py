import sys
import os
import math
import numpy as np

# Añadimos el path si es necesario
sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs, gather
from cunqa.circuit import CunqaCircuit

def apply_toffoli_decomposed(qc, c1, c2, target):
    """
    Implementación manual de una puerta Toffoli (CCX) usando 
    solo puertas H, CX y RZ, soportadas por el backend C++.
    """
    # H sobre el target
    qc.h(target)
    
    # Secuencia de descomposición estándar
    qc.cx(c2, target)
    qc.rz(-np.pi/4, target) # Tdg
    qc.cx(c1, target)
    qc.rz(np.pi/4, target)  # T
    qc.cx(c2, target)
    qc.rz(-np.pi/4, target) # Tdg
    qc.cx(c1, target)
    qc.rz(np.pi/4, target)  # T
    
    qc.h(target)
    
    # Corrección de fase en los controles
    qc.cx(c1, c2)
    qc.rz(-np.pi/4, c2)     # Tdg
    qc.cx(c1, c2)
    qc.rz(np.pi/4, c2)      # T
    qc.rz(np.pi/4, c1)      # T

def build_grover_3qubits():
    n = 3
    print(f"Creando Grover para {n} qubits (Descomposición Manual).")
    
    qc = CunqaCircuit(n)
    
    # 1. Superposición
    for i in range(n):
        qc.h(i)
    
    # Iteraciones (para N=3, pi/4 * sqrt(8) approx 2 iteraciones)
    optimal_num_iterations = 2 
    
    for _ in range(optimal_num_iterations):
        # --- Oráculo para |111> (CCZ) ---
        # CCZ = H(t) + CCX + H(t)
        qc.h(2)
        apply_toffoli_decomposed(qc, 0, 1, 2)
        qc.h(2)
        
        # --- Difusor ---
        for i in range(n):
            qc.h(i)
            qc.x(i)
        
        # CCZ de nuevo
        qc.h(2)
        apply_toffoli_decomposed(qc, 0, 1, 2)
        qc.h(2)
        
        for i in range(n):
            qc.x(i)
            qc.h(i)
    
    qc.measure_all()
    return qc

def main():
    qpus = get_QPUs(on_node=False)
    
    # Usamos 3 qubits
    grover_qc = build_grover_3qubits()
    
    print("Enviando ejecución al clúster...")
    
    qjobs = []
    for qpu in qpus:
        # Lanzamos 1 job por QPU
        qjobs.append(qpu.run(grover_qc, shots=1024))
            
    print("Esperando resultados (esto puede tardar unos segundos)...")
    results = gather(qjobs)
    
    for result in results:
        print(f"Resultados: {result.counts}")
        
        # Verificamos si encontró |111>
        hits = 0
        target = '111'
        for k, v in result.counts.items():
            if k.endswith(target):
                hits = v
        print(f"Aciertos para |{target}>: {hits}/1024")

if __name__ == "__main__":
    main()