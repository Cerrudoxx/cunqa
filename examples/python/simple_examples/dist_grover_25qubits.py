import os, sys
import math

sys.path.append(os.getenv("HOME"))
from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit

# --- CONFIGURACIÓN PARA 25 QUBITS ---
N_TOTAL = 25          # Total de qubits (¡Reto aceptado!)
K_BITS = 2            # Dividimos en 4 vQPUs (2^2)
N_LOCAL = N_TOTAL - K_BITS  # 25 - 2 = 23 qubits por vQPU
N_VQPUS = 2**K_BITS   # 4 vQPUs

# Definimos el Target Global: '11...1' (25 unos)
TARGET_GLOBAL = '1' * N_TOTAL 

def add_mcz_gate(qc, n_qubits):
    """
    Aplica una puerta Multi-Controlled Z (MCZ).
    """
    ctrl_qubits = list(range(n_qubits - 1))
    target_qubit = n_qubits - 1
    
    # MCZ = H en target -> MCX -> H en target
    qc.h(target_qubit)
    
    # Puerta multicontrolada (X con N-1 controles)
    qc.multicontrol(
        base_gate="x", 
        num_ctrl_qubits=len(ctrl_qubits), 
        qubits=ctrl_qubits + [target_qubit]
    )
    
    qc.h(target_qubit)

def create_grover_large(subspace_id):
    """
    Crea el subcircuito local de 23 qubits.
    """
    # 1. Variables de control
    prefix_bin = format(subspace_id, f'0{K_BITS}b')
    target_prefix = TARGET_GLOBAL[:K_BITS]
    
    qc = CunqaCircuit(N_LOCAL, id=f"Grover_Chunk_{prefix_bin}")
    
    # 2. Superposición Inicial
    for q in range(N_LOCAL):
        qc.h(q)
    
    # 3. CÁLCULO DE ITERACIONES
    # Para N=23 local, las iteraciones son aprox (pi/4) * sqrt(2^23)
    # sqrt(8,388,608) ≈ 2896.3
    # Iteraciones ≈ 0.785 * 2896 ≈ 2274
    num_iterations = int((math.pi / 4) * math.sqrt(2**N_LOCAL))
    
    # Imprimimos esto solo una vez para que el usuario sepa qué esperar
    if subspace_id == 0:
        print(f"[INFO] Generando circuito con {num_iterations} iteraciones de Grover por vQPU...")
    
    # --- BUCLE DE GROVER ---
    for _ in range(num_iterations):
        # A. Oráculo Distribuido
        if prefix_bin == target_prefix:
            add_mcz_gate(qc, N_LOCAL)
        else:
            pass # Identidad

        # B. Difusor
        for q in range(N_LOCAL):
            qc.h(q)
            qc.x(q)
        
        add_mcz_gate(qc, N_LOCAL)
        
        for q in range(N_LOCAL):
            qc.x(q)
            qc.h(q)
    # -----------------------
    
    # 4. Medición
    qc.measure_all()
    return qc

# --- BLOQUE PRINCIPAL ---

print(f"Solicitando {N_VQPUS} vQPUs para N={N_TOTAL} (N_local={N_LOCAL})...")
# Aumentamos el tiempo a 2 horas por seguridad
# family = qraise(n=N_VQPUS, t="02:00:00", co_located=True, partition="lusi2", mem_per_qpu=1)

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

print("\n--- INICIANDO EJECUCIÓN ---")
print("ADVERTENCIA: Esto tardará bastante (20-40 mins aprox). No cierres la terminal.")
jobs = []
shots = 1000 

for i, qc in enumerate(circuits):
    # run() es asíncrono, enviamos los 4 a la vez
    jobs.append(qpus[i].run(qc, shots=shots))

print("\nEsperando resultados...")
# Al pedir job.result, el script se bloqueará hasta que termine
results_collected = [job.result for job in jobs] 

print("\n-- Resultados Distribuidos --")
for i, result in enumerate(results_collected):
    counts = result.counts
    prefix = format(i, f'0{K_BITS}b')
    
    # Buscamos el estado '1...1' local (23 unos)
    target_local = '1' * N_LOCAL
    hits = counts.get(target_local, 0)
    
    if hits > (shots * 0.1): 
        print(f"✅ vQPU {i} (Prefijo {prefix}): ¡Candidato detectado!")
        print(f"   -> Hits: {hits}/{shots}")
        print(f"   -> SOLUCIÓN GLOBAL: {prefix}{target_local}")
        print(f"   -> Tiempo de ejecución: {result.time_taken:.2f}s")
    else:
        # Mostramos tiempo también para ver cuánto tardaron las que fallaron
        t_taken = getattr(result, 'time_taken', 0.0)
        print(f"❌ vQPU {i} (Prefijo {prefix}): Ruido. (Tiempo: {t_taken:.2f}s)")

#qdrop(family)