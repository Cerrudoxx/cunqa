import numpy as np
import os, sys
import math
import time

# Aseguramos acceso a la librería CUNQA
sys.path.append(os.getenv("HOME"))

from cunqa import get_QPUs, gather
from cunqa.qutils import qraise, qdrop
from qiskit import QuantumCircuit, transpile

def build_circuit(theta):
    """Crea un circuito simple con una rotación Ry(theta)."""
    qc = QuantumCircuit(1)
    qc.ry(theta, 0)
    qc.measure_all()
    return qc

def run_experiment(total_points, n_qpus_requested):
    label = f"Sweep_{n_qpus_requested}QPUs"
    print(f"\n{'='*60}")
    print(f"  EJECUTANDO: {label} ({total_points} puntos)")
    print(f"{'='*60}")
    
    # 1. Definir el espacio de búsqueda
    angulos = np.linspace(0, np.pi, total_points).tolist()
    
    # 2. Levantar Infraestructura
    try:
        family = qraise(n_qpus_requested, "00:10:00", simulator="Aer", co_located=True, partition="lusitania")
    except Exception as e:
        print(f"[ERROR] Fallo al levantar QPUs: {e}")
        return float('nan')
    
    start_time = time.time()
    
    try:
        qpus = get_QPUs(on_node=False, family=family)
        print(f"-> {len(qpus)} QPUs activas. Distribuyendo carga...")
        
        qjobs = []
        
        # 3. Distribución de Carga (Round-Robin)
        # Enviamos todos los circuitos repartiéndolos entre las QPUs disponibles
        for i, angle in enumerate(angulos):
            # Seleccionamos QPU de forma cíclica (0, 1, 0, 1...)
            qpu_index = i % len(qpus)
            qpu = qpus[qpu_index]
            
            # Creamos y transpilamos el circuito para este ángulo
            qc = build_circuit(angle)
            qc_t = transpile(qc, basis_gates=['u3', 'cx', 'measure'], optimization_level=0)
            
            # Enviamos el trabajo (Asíncrono/No bloqueante)
            job = qpu.run(qc_t, shots=1024)
            qjobs.append(job)
            
        print(f"-> {len(qjobs)} trabajos enviados. Esperando resultados...")
        
        # 4. Sincronización
        gather(qjobs)
        
        # 5. Procesamiento (solo para verificar que tenemos datos)
        resultados_validos = 0
        for job in qjobs:
            try:
                # Accedemos a counts para asegurar que la lectura es correcta
                _ = job.result.counts
                resultados_validos += 1
            except Exception as e:
                print(f"[WARN] Fallo leyendo un resultado: {e}")

        print(f"-> {resultados_validos}/{total_points} circuitos completados exitosamente.")

    except Exception as e:
        print(f"[ERROR CRÍTICO] {e}")
        return float('nan')
    
    finally:
        qdrop(family)
        print("-> Recursos liberados.")
        
    total_time = time.time() - start_time
    return total_time

def main():
    # --- CONFIGURACIÓN ---
    total_puntos = 40       # Número de circuitos a evaluar
    qpus_lista = [1, 2, 4]  # Escalar número de QPUs para ver el Speedup
    
    results = []
    
    print("INICIANDO BENCHMARK ROBUSTO DE BARRIDO DE PARÁMETROS...")
    
    for n_qpus in qpus_lista:
        t_total = run_experiment(total_puntos, n_qpus)
        
        if not math.isnan(t_total):
            # Throughput = Circuitos por segundo
            throughput = total_puntos / t_total
            results.append((n_qpus, t_total, throughput))
            
        # Pausa de seguridad
        time.sleep(3)

    # --- INFORME ---
    print("\n\n")
    print("#######################################################")
    print(f"#      RESULTADOS DEL BARRIDO ({total_puntos} CIRCUITOS)       #")
    print("#######################################################")
    print(f"{'QPUS':<10} | {'TIEMPO TOTAL (s)':<18} | {'VELOCIDAD (circs/s)':<20}")
    print("-" * 54)
    
    base_speed = 0
    for i, (qpus, t, speed) in enumerate(results):
        if i == 0: base_speed = speed
        factor = speed / base_speed if base_speed > 0 else 0
        print(f"{qpus:<10} | {t:.4f}{' '*12} | {speed:.2f} (x{factor:.1f})")
    print("-" * 54)

if __name__ == "__main__":
    main()