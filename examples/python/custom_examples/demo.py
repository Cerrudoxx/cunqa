import os, sys
sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs
from cunqa.circuit import CunqaCircuit

# 1. Obtener QPUs disponibles (Co-located)
qpus = get_QPUs(on_node=False)

for q in qpus:
    print(f"QPU {q.id}, backend: {q.backend.name}, simulator: {q.backend.simulator}, version: {q.backend.version}.")

# 2. Definir Circuito (Estado de Bell)
qc = CunqaCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# 3. Ejecutar 
qpu = qpus[0]
qjob = qpu.run(qc, shots=100) # Esta llamada no bloquea

# 4. Obtener resultados (Bloqueante)
counts = qjob.result.counts
tiempo = qjob.time_taken

print(f"Resultados: {counts}")
print(f"Tiempo: {tiempo}s")