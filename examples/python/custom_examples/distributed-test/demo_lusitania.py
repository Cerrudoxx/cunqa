import sys
import time

# --- IMPORTACIONES CORRECTAS (CUNQA EX MODULE) ---
from cunqa.qutils import qraise, qdrop
from cunqa import get_QPUs
from cunqa.circuit import CunqaCircuit

# --- CÁLCULOS PARA LUSITANIA (16 Cores / 32GB RAM) ---
# Objetivo: Maximizar uso sin romper el nodo (Out of Memory)
NUM_NODOS = 2
QUBITS_POR_NODO = 30       # 30q = ~17.2 GB de RAM requerida
MEMORIA_A_SOLICITAR = 24   # Pedimos 24GB (Dejamos 8GB de margen al SO)
CORES_A_SOLICITAR = 15     # Pedimos 15 Cores (Dejamos 1 al SO)
TIEMPO_MAX = "00:45:00"    # 30 qubits tardan un poco más en simularse

def main():
    total_qubits = NUM_NODOS * QUBITS_POR_NODO
    
    print(f"\n{'='*70}")
    print(f"🚀 CUNQA LUSITANIA MAX: {total_qubits} QUBITS ({QUBITS_POR_NODO} x {NUM_NODOS} Nodos)")
    print(f"   Hardware: Partition Lusitania (32GB RAM/Nodo)")
    print(f"   Memoria Simulada: ~34.4 GB (Statevector total)")
    print(f"{'='*70}")

    # 1. SOLICITAR INFRAESTRUCTURA
    # ---------------------------------------------------------
    print(f"\n[1/4] Solicitando recursos optimizados...")
    print(f"   -> Reservando {NUM_NODOS} nodos con {MEMORIA_A_SOLICITAR}GB RAM y {CORES_A_SOLICITAR} Cores cada uno.")
    
    family = None
    try:
        family = qraise(
            n=NUM_NODOS,            # Total de QPUs
            n_nodes=NUM_NODOS,      # Nodos físicos distintos
            qpus_per_node=1,        # 1 QPU gigante por nodo
            mem_per_qpu=MEMORIA_A_SOLICITAR, # 24GB
            cores=CORES_A_SOLICITAR,# 15 Cores
            t=TIEMPO_MAX,
            partition="lusitania",
            co_located=False        # Distribuido real
        )
    except Exception as e:
        print(f"❌ Error en qraise: {e}")
        print("   (Es posible que no haya 2 nodos libres ahora mismo. Prueba más tarde)")
        sys.exit(1)

    try:
        # 2. CONEXIÓN
        # ---------------------------------------------------------
        print(f"[2/4] Esperando arranque de workers...")
        qpus = get_QPUs(on_node=False, family=family)
        
        if len(qpus) < NUM_NODOS:
            raise RuntimeError(f"Fallo de conexión. QPUs encontradas: {len(qpus)}")

        print(f"✅ Infraestructura ONLINE:")
        for i, qpu in enumerate(qpus):
            print(f"   - Worker {i}: {qpu.name}")

        # 3. ALGORITMO (Carga Pesada)
        # ---------------------------------------------------------
        print(f"\n[3/4] Generando estados cuánticos de {QUBITS_POR_NODO} qubits...")
        print("   (Esto creará vectores de estado de 1GB+ en memoria)")
        
        # Circuito A (Nodo 1): Superposición masiva
        qc_a = CunqaCircuit(QUBITS_POR_NODO)
        for i in range(QUBITS_POR_NODO): 
            qc_a.h(i)
        qc_a.measure_all()

        # Circuito B (Nodo 2): Entrelazamiento local pesado
        qc_b = CunqaCircuit(QUBITS_POR_NODO)
        qc_b.h(0)
        for i in range(QUBITS_POR_NODO - 1):
            qc_b.cnot(i, i+1) # CNOT en cadena para usar RAM intensamente
        qc_b.measure_all()

        # 4. EJECUCIÓN PARALELA
        # ---------------------------------------------------------
        print(f"\n[4/4] Ejecutando simulación distribuida...")
        t_start = time.time()
        
        # Lanzamos los trabajos
        # Nota: Con 30 qubits, esto tardará unos segundos/minutos por shot
        # Reducimos shots para que no sea eterno en la prueba
        SHOTS_PRUEBA = 100 
        
        print(f"   -> Procesando {SHOTS_PRUEBA} shots en paralelo...")
        job_a = qpus[0].run(qc_a, shots=SHOTS_PRUEBA)
        job_b = qpus[1].run(qc_b, shots=SHOTS_PRUEBA)
        
        res_a = job_a.result()
        res_b = job_b.result()
        
        t_end = time.time()
        
        # RESULTADOS
        print(f"\n{'='*70}")
        print(f"RESULTADO FINAL (Tiempo: {t_end - t_start:.2f}s)")
        print(f"{'='*70}")
        
        # Simplemente mostramos el nº de estados para no inundar la pantalla
        print(f"🔹 Nodo A (30q): Simulación completada.")
        print(f"🔹 Nodo B (30q): Simulación completada.")
        print(f"🎉 Has usado ~34GB de RAM agregada entre los dos nodos.")

    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 5. LIMPIEZA
        if family:
            print(f"\n🧹 Liberando recursos...")
            try:
                qdrop(family)
                print("   Recursos liberados.")
            except:
                print("⚠️ Ejecuta 'qdrop --all' manualmente.")

if __name__ == "__main__":
    main()
