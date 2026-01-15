import os, sys
import numpy as np
import time

# Añadimos path para CUNQA
sys.path.append(os.getenv("HOME"))

from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit
from cunqa.mappers import run_distributed
from cunqa.qjob import gather

# --- 1. Construcción del Circuito Distribuido ---
def build_distributed_qpe(n_ancilla, theta):
    """
    Construye dos circuitos entrelazados para estimar la fase 'theta'.
    QPU 1: Qubits de ancilla (lectura).
    QPU 2: Qubit del registro (estado propio).
    """
    # Creamos dos circuitos lógicos separados
    ancilla_c = CunqaCircuit(n_ancilla, id="ancilla_node")
    register_c = CunqaCircuit(1, id="register_node") # Solo 1 qubit para el autovalor

    # Inicializamos el estado propio |1> aplicando X
    # (Para una puerta Rz, |1> es autovector con fase e^{-i*lambda/2})
    register_c.x(0) 

    # Superposición en ancillas
    for i in range(n_ancilla):
        ancilla_c.h(i)

    # --- FASE DE CONTROL REMOTO (LO INTERESANTE) ---
    # Aplicamos rotaciones controladas donde el Control está en 'ancilla_c'
    # y el Target está en 'register_c'.
    for i in range(n_ancilla):
        # 'expose' permite que 'register_c' sea visible para 'ancilla_c'
        with ancilla_c.expose(n_ancilla - 1 - i, register_c) as remote_control:
            # Calculamos el ángulo: 2^k * theta
            # Nota: Usamos Rz, cuyo autovalor es exp(-i*phi/2). 
            param = (2**i) * (2 * np.pi * theta)
            
            # CRZ distribuida: Control local, Target remoto
            register_c.crz(param, remote_control, 0)

    # --- QFT INVERSA (Solo local en ancilla) ---
    # No requiere comunicación entre QPUs, solo swaps locales
    if (n_ancilla % 2) == 0:
        swap_range = int(n_ancilla / 2)
    else:
        swap_range = int((n_ancilla - 1) / 2)

    for i in range(swap_range):
        ancilla_c.swap(i, n_ancilla - 1 - i)

    for i in range(n_ancilla):
        for j in range(i):
            angle  = (-np.pi) / (2**(i - j)) 
            ancilla_c.crz(angle, n_ancilla - 1 - j, n_ancilla - 1 - i)
        ancilla_c.h(n_ancilla - 1 - i)

    # Medimos solo las ancillas para obtener la fase
    ancilla_c.measure_all()
    
    # Retornamos la lista de circuitos interdependientes
    return [ancilla_c, register_c]

# --- 2. Decodificación de Resultados ---
def estimate_phase_from_counts(counts):
    # Buscamos el resultado más frecuente
    most_frequent = max(counts, key=counts.get)
    
    # Convertimos de binario fraccionario a decimal
    # 0.j1 j2 j3 ... = j1/2 + j2/4 + j3/8 ...
    estimated = 0.0
    for i, bit in enumerate(most_frequent):
        if bit == '1':
            estimated += 1 / (2 ** (i + 1))
    return estimated, most_frequent

# --- 3. Ejecución ---
def main():
    print(">>> INICIANDO QPE DISTRIBUIDO <<<")
    
    # Parámetros del problema
    n_ancilla = 10           # Usamos pocos qubits para prueba rápida
    target_phase = 0.125     # Fase objetivo (1/8)
    shots = 500
    
    # 1. Despliegue de Recursos con Comunicación Cuántica habilitada
    # quantum_comm=True habilita simulacion de ebits/telegates
    print("Levantando 2 QPUs con canal cuántico...")
    family = qraise(2, "00:10:00", simulator="Aer", quantum_comm=True, co_located=True, partition="lusitania")
    
    try:
        # Recuperamos las QPUs asignadas
        qpus = get_QPUs(on_node=False, family=family)
        print(f"-> Recursos listos: {[q.name for q in qpus]}")
        
        # Construimos los circuitos distribuidos
        circuits = build_distributed_qpe(n_ancilla, target_phase)
        
        print(f"-> Ejecutando QPE distribuido para theta={target_phase}...")
        
        # Usamos 'run_distributed' que gestiona la orquestación de la comunicación
        start_t = time.time()
        distr_jobs = run_distributed(circuits, qpus, shots=shots)
        
        # Esperamos resultados
        results = gather(distr_jobs)
        total_time = time.time() - start_t
        
        # El resultado de interés está en el circuito 0 (ancilla)
        ancilla_res = results[0]
        
        print(f"\n--- Resultados (Tiempo: {total_time:.2f}s) ---")
        print(f"Counts (Ancilla): {ancilla_res.counts}")
        
        est_val, bitstring = estimate_phase_from_counts(ancilla_res.counts)
        print(f"Bitstring más frecuente: {bitstring}")
        print(f"Fase Estimada: {est_val:.4f} (Esperada: {target_phase:.4f})")
        
        error = abs(est_val - target_phase)
        if error < 1e-2:
            print("¡ÉXITO! La fase se ha recuperado correctamente en modo distribuido.")
        else:
            print("WARN: La precisión es baja (aumenta n_ancilla para mejorar).")

    except Exception as e:
        print(f"ERROR: {e}")
        
    finally:
        qdrop(family)
        print("-> Recursos liberados.")

if __name__ == "__main__":
    main()
