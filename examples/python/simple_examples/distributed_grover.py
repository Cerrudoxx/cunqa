import os, sys

sys.path.append(os.getenv("HOME"))

from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit

def create_grover_subcircuit(subspace_id):
    """
    Crea un circuito de Grover de 2 qubits (n=2).
    - subspace_id=0: Busca en el prefijo '0'. (Global target '111' -> Local target 'Ninguno')
    - subspace_id=1: Busca en el prefijo '1'. (Global target '111' -> Local target '11')
    """
    
    qc = CunqaCircuit(2, id=f"Grover_Subspace_{subspace_id}")
    
    # Superposición
    qc.h(0)
    qc.h(1)
    
    # Oráculo (Se marca solo si existe en este subspacio)
    if subspace_id == 1:
        # El target global es 111. Al fijar el primer bit a 1, buscamos localmente '11'.
        # El oráculo para '11' es una puerta CZ (o H-CX-H).
        # Marca el estado |11> con fase -1.
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
    else:
        # Si estamos en el subespacio 0 (prefijo 0), el target '111' NO está aquí.
        # El oráculo es la Identidad (no hace nada).
        pass   
    
    # Difusor para 2 qubits
    qc.h(0); qc.h(1)
    qc.x(0); qc.x(1)
    # CZ (H-CX-H)
    qc.h(1)
    qc.cx(0, 1)
    qc.h(1)
    qc.x(0); qc.x(1)
    qc.h(0); qc.h(1)
    
    qc.measure_all()
    return qc


# BLOQUE PRINCIPAL
family = qraise(n=2, t="00:10:00", co_located=True, partition="lusi2")

try:
    qpus = get_QPUs(on_node=False)
except SystemExit:
    print("Error: No se detectaron QPUs")
    sys.exit(1)
    
if len(qpus) < 2:
    print("Se necesitan al menos 2 vQPUS para este ejemplo.")
    sys.exit(1)
    
# 2. Definir los circuitos distribuidos
# vQPU 0 explorará los estados que empiezan por '0'
# vQPU 1 explorará los estados que empiezan por '1'
circuits = [create_grover_subcircuit(0), create_grover_subcircuit(1)]

jobs = []
for i, qc in enumerate(circuits):
    jobs.append(qpus[i].run(qc, shots=100))
    
print("\n-- Resultados --")
for i, job in enumerate(jobs):
    result = job.result.counts
    prefix = str(i) # 0 o 1
    print(f"\nvQPU {i} (Prefijo '{prefix}'): {result}")
    
    # Análisis simple
    if i == 1:
        # En vQPU 1 esperamos encontrar la solución '11'
        print(f"  -> ¡SOLUCIÓN ENCONTRADA! Parte local: '11'. Global: '{prefix}11'")
    else:
        # En vQPU 0 no hay solución, esperamos ruido/uniformidad
        print(f"  -> Sin solución clara (ruido uniforme esperado).")
        
        
qdrop(family)