import os, sys
import math

sys.path.append(os.getenv("HOME"))
from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit

# --- CONFIGURACIÓN ---
N_TOTAL = 15          # Total de qubits
K_BITS = 2            # Bits para dividir (Prefijo)
N_LOCAL = N_TOTAL - K_BITS  # 13 qubits por vQPU
N_VQPUS = 2**K_BITS   # 4 vQPUs

# Definimos el Target Global: '11...1'
TARGET_GLOBAL = '1' * N_TOTAL 

def add_mcz_gate(qc, n_qubits):
    """
    Aplica una puerta Multi-Controlled Z (MCZ).
    Usa qc.multicontrol para compatibilidad con CUNQA.
    """
    ctrl_qubits = list(range(n_qubits - 1))
    target_qubit = n_qubits - 1
    
    # MCZ = H en target -> MCX -> H en target
    qc.h(target_qubit)
    
    # Usamos multicontrol explícito
    qc.multicontrol(
        base_gate="x", 
        num_ctrl_qubits=len(ctrl_qubits), 
        qubits=ctrl_qubits + [target_qubit]
    )
    
    qc.h(target_qubit)

def create_grover_large(subspace_id):
    """
    Crea el subcircuito para la vQPU 'subspace_id' con bucle de iteraciones.
    """
    # 1. Definir variables de control
    prefix_bin = format(subspace_id, f'0{K_BITS}b')
    target_prefix = TARGET_GLOBAL[:K_BITS]  # <--- AQUÍ ESTABA EL ERROR (Faltaba esta definición)
    
    qc = CunqaCircuit(N_LOCAL, id=f"Grover_Chunk_{prefix_bin}")
    
    # 2. Superposición Inicial
    for q in range(N_LOCAL):
        qc.h(q)
    
    # 3. BUCLE DE GROVER (Vital para N=13)
    # Iteraciones ≈ (pi/4) * sqrt(2^13) ≈ 69
    num_iterations = 69
    
    for _ in range(num_iterations):
        # A. Oráculo Distribuido
        if prefix_bin == target_prefix:
            # Solo la vQPU con el prefijo correcto aplica la marca
            add_mcz_gate(qc, N_LOCAL)
        else:
            pass # Identidad (no marcamos nada)

        # B. Difusor (Inversión sobre la media)
        for q in range(N_LOCAL):
            qc.h(q)
            qc.x(q)
        
        add_mcz_gate(qc, N_LOCAL)
        
        for q in range(N_LOCAL):
            qc.x(q)
            qc.h(q)
    
    # 4. Medición final
    qc.measure_all()
    return qc

# --- BLOQUE PRINCIPAL ---

print(f"Solicitando {N_VQPUS} vQPUs para N={N_TOTAL}...")
# Aseguramos memoria suficiente para simular 13 qubits + overhead
family = qraise(n=N_VQPUS, t="00:30:00", co_located=True, partition="lusi2", mem_per_qpu=2)

try:
    qpus = get_QPUs(on_node=False)
except SystemExit:
    sys.exit("Error: No se detectaron QPUs")

if len(qpus) < N_VQPUS:
    sys.exit(f"Faltan vQPUs. Tienes {len(qpus)}, necesitas {N_VQPUS}.")

# Generar circuitos
circuits = []
for i in range(N_VQPUS):
    circuits.append(create_grover_large(i))

print("Enviando trabajos (esto tomará unos minutos debido a las 69 iteraciones)...")
jobs = []
shots = 1000 

for i, qc in enumerate(circuits):
    jobs.append(qpus[i].run(qc, shots=shots))

print("\n-- Resultados Distribuidos --")
for i, job in enumerate(jobs):
    counts = job.result.counts
    prefix = format(i, f'0{K_BITS}b')
    
    # Buscamos el estado '11...1' local (13 unos)
    target_local = '1' * N_LOCAL
    hits = counts.get(target_local, 0)
    
    # Umbral de detección: >10% de los shots (con 69 iteraciones debería ser cerca del 99%)
    if hits > (shots * 0.1): 
        print(f"✅ vQPU {i} (Prefijo {prefix}): ¡Candidato detectado!")
        print(f"   -> Hits: {hits}/{shots}")
        print(f"   -> SOLUCIÓN GLOBAL: {prefix}{target_local}")
    else:
        print(f"❌ vQPU {i} (Prefijo {prefix}): Ruido (Máx freq: {max(counts.values()) if counts else 0})")

qdrop(family)