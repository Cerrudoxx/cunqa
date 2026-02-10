import os, sys
sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs
from cunqa.circuit import CunqaCircuit
from cunqa.qjob import gather

# Obtener QPUs disponibles (Co-located)
qpus = get_QPUs(on_node=False)

for q in qpus:
    print(f"QPU {q.id}, backend: {q.backend.name}, simulator: {q.backend.simulator}, version: {q.backend.version}.")

qc = CunqaCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# Ejecutar (SCATTER: 50 shots a cada QPU en paralelo, 100 en total)
jobs = [q.run(qc, shots=50) for q in qpus] 

# Obtener resultados (GATHER: Bloqueante y Sincronizado)
results = gather(jobs) 

# Mostrar el conteo de cada QPU
print(f"Resultados por QPU: {[res.counts for res in results]}")

# Mostrar la combinación de ambas QPUs
total_counts = {}
for res in results:
    for bitstring, count in res.counts.items():
        # Si la clave ya existe, suma. Si no, inicializa.
        total_counts[bitstring] = total_counts.get(bitstring, 0) + count

# Mostrar combinados
print("Resultados Combinados:", total_counts)

# print(f"Tiempo: {tiempo}s") # El tiempo ahora es individual por job, habría que sumarlo o promediarlo si se requiere.