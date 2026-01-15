import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ZGate
import os, sys
import math
import time

# Añadimos path para CUNQA
sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs, gather
from cunqa.qutils import qraise, qdrop

# --- 1. CONSTRUCCIÓN DEL CIRCUITO DE GROVER ---
def build_grover_circuit(n):
    # Cálculo de iteraciones óptimas
    optimal_num_iterations = math.floor(math.pi / (4 * math.asin(math.sqrt(1 / 2**n))))
    
    qc = QuantumCircuit(n)
    
    # Superposición
    qc.h(range(n))
    
    for _ in range(optimal_num_iterations):
        # Oráculo
        if n > 1:
            mcz = ZGate().control(n-1)
            qc.append(mcz, list(range(n)))
        else:
            qc.z(0)
        
        # Difusión
        qc.h(range(n))
        qc.x(range(n)) 
        
        if n > 1:
            mcz = ZGate().control(n-1)
            qc.append(mcz, list(range(n)))
        else:
            qc.z(0)
            
        qc.x(range(n))
        qc.h(range(n))
    
    qc.measure_all()
    
    # Transpilación para backend C++
    basis_gates = ['cx', 'h', 'x', 'z', 'rx', 'ry', 'rz', 'measure']
    qc_transpiled = transpile(qc, basis_gates=basis_gates, optimization_level=2)
    
    return qc_transpiled

# --- 2. LÓGICA DE EXPERIMENTO CON CHUNKING ---
def run_experiment_chunked(n_qubits, n_qpus_requested, total_shots, label):
    print(f"\n{'='*70}")
    print(f"  INICIANDO: {label}")
    print(f"  Objetivo: {total_shots} shots repartidos entre {n_qpus_requested} QPUs")
    print(f"{'='*70}")
    
    # 1. Levantar Infraestructura
    family = qraise(n_qpus_requested, "00:10:00", simulator="Aer", co_located=True, partition="lusitania")
    
    final_time_metric = 0.0
    
    try:
        qpus = get_QPUs(on_node=False, family=family)
        print(f"-> {len(qpus)} QPUs activas.")

        # 2. Dividir la carga (Chunking)
        shots_per_qpu = total_shots // n_qpus_requested
        remainder = total_shots % n_qpus_requested
        
        # Lista con los shots para cada QPU
        chunks = [shots_per_qpu + (1 if i < remainder else 0) for i in range(n_qpus_requested)]
        print(f"-> Distribución de chunks: {chunks}")

        grover_qc = build_grover_circuit(n_qubits)
        
        qjobs = []
        
        # CORRECCIÓN: Definimos la variable correctamente aquí
        start_time = time.time()
        
        # 3. Lanzamiento Paralelo
        for i, qpu in enumerate(qpus):
            if chunks[i] > 0:
                job = qpu.run(grover_qc, shots=chunks[i])
                qjobs.append(job)
            
        print("-> Trabajos enviados. Esperando resultados...")
        gather(qjobs)
        
        end_time = time.time() # Paramos el cronómetro
        
        # 4. Agregación de Resultados y Tiempos
        total_counts = {}
        max_job_time = 0.0
        
        print("\n--- Desglose por Chunk ---")
        for i, qjob in enumerate(qjobs):
            # Recopilar tiempos reportados por CUNQA (simulación pura)
            t_val_str = qjob.time_taken
            try:
                t_val = float(t_val_str)
                if t_val > max_job_time: max_job_time = t_val
            except:
                pass
            
            # Recopilar y sumar conteos
            counts = qjob.result.counts
            print(f"  QPU {i} ({chunks[i]} shots): {t_val_str}s -> {counts}")
            
            for state, count in counts.items():
                total_counts[state] = total_counts.get(state, 0) + count

        # El tiempo efectivo de simulación es el del job más lento
        final_time_metric = max_job_time
        
        print(f"\n-> CONTEO TOTAL AGREGADO: {total_counts}")
        print(f"-> Tiempo del chunk más lento (Simulación): {final_time_metric:.4f} s")
        # CORRECCIÓN: Usamos la variable start_time correcta
        print(f"-> Tiempo Wall-clock total (Real): {end_time - start_time:.4f} s")

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        final_time_metric = float('nan')
    
    finally:
        qdrop(family)
        print("-> Recursos liberados.")
        
    return final_time_metric

# --- 3. MAIN ---
def main():
    # --- CONFIGURACIÓN ---
    n_qubits = 14          # Complejidad fija
    total_shots_global = 10000 # Carga de trabajo total fija
    
    # Lista de QPUs a probar
    qpus_lista = [1, 2, 4, 5] 
    
    results = []
    
    print("INICIANDO BENCHMARK DE CHUNKING (SHOT SPLITTING)...")
    
    for n_qpus in qpus_lista:
        label = f"Split_{total_shots_global}shots_{n_qpus}QPUs"
        
        # Ejecutamos
        time_taken = run_experiment_chunked(n_qubits, n_qpus, total_shots_global, label)
        
        if not math.isnan(time_taken):
            results.append({
                "qpus": n_qpus,
                "time": time_taken
            })
            
        time.sleep(2)

    # --- INFORME FINAL ---
    print("\n\n")
    print("#######################################################")
    print(f"#      RESULTADOS: PROCESANDO {total_shots_global} SHOTS       #")
    print("#######################################################")
    print(f"{'QPUS':<10} | {'TIEMPO SIMULACIÓN (s)':<25} | {'SPEEDUP':<10}")
    print("-" * 55)
    
    base_time = 0
    for i, r in enumerate(results):
        if i == 0: base_time = r['time']
        
        # Speedup ideal basado en tiempos de simulación reportados
        if r['time'] > 0:
            speedup = base_time / r['time']
        else:
            speedup = 0.0
            
        print(f"{r['qpus']:<10} | {r['time']:.5f}{' '*19} | {speedup:.2f}x")
    
    print("-" * 55)

if __name__ == "__main__":
    main()