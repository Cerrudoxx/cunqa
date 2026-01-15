import sys
import time
from cunqa.qutils import qraise, qdrop
from cunqa import get_QPUs
from cunqa.circuit import CunqaCircuit

# --- CONFIGURACIÓN MÍNIMA DE DEPURACIÓN ---
# Si esto falla, el cluster nos odia.
NUM_NODOS = 2
QUBITS_POR_NODO = 5   # Ridículamente bajo para que sea instantáneo
MEMORIA_GB = 2        # 2 GB (Cualquier nodo tiene esto)
CORES = 1             # 1 Core (Cualquier nodo tiene esto)
TIEMPO = "00:10:00"

def main():
    print(f"\n{'='*60}")
    print(f"🕵️  CUNQA DEBUG: PRUEBA DE CONECTIVIDAD MÍNIMA")
    print(f"{'='*60}")

    # 1. SOLICITUD
    print(f"\n[1/4] Pidiendo 2 Nodos 'Baratos' (1 Core, 2GB RAM)...")
    
    family = None
    try:
        family = qraise(
            n=NUM_NODOS,
            n_nodes=NUM_NODOS,
            qpus_per_node=1,
            mem_per_qpu=MEMORIA_GB,
            cores=CORES,           # Solo 1 core para no estresar a SLURM
            t=TIEMPO,
            partition="lusitania",
            co_located=False
        )
        print(f"   -> Familia ID: {family}")
    except Exception as e:
        sys.exit(f"❌ Error al lanzar qraise: {e}")

    try:
        # 2. CONEXIÓN
        print(f"[2/4] Buscando QPUs (Timeout 60s)...")
        
        # Bucle de reintento manual por si tardan en arrancar
        for i in range(12):
            try:
                qpus = get_QPUs(on_node=False, family=family)
                if len(qpus) >= NUM_NODOS:
                    break
            except:
                pass
            print(f"   ... esperando ({i*5}s)", end="\r")
            time.sleep(5)
        print("") # Salto de línea

        if len(qpus) < NUM_NODOS:
            raise RuntimeError("Timeout: Las QPUs no conectaron. Revisa 'squeue'.")

        print(f"✅ ¡CONEXIÓN EXITOSA! La red funciona.")
        for q in qpus: print(f"   - {q.name}")

        # 3. EJECUCIÓN TEST
        print(f"\n[3/4] Lanzando circuito de prueba (5 qubits)...")
        qc = CunqaCircuit(QUBITS_POR_NODO)
        qc.h(0)
        qc.measure_all()
        
        # Ejecución rápida
        jobs = [q.run(qc, shots=10) for q in qpus]
        results = [j.result() for j in jobs]
        
        print(f"\n{'='*60}")
        print(f"RESULTADO: ¡TODO FUNCIONA!")
        print(f"{'='*60}")
        print(f"Si lees esto, el entorno distribuido está SANO.")
        print(f"El fallo anterior era por pedir demasiada RAM/CPU.")

    except Exception as e:
        print(f"\n❌ ERROR DE EJECUCIÓN: {e}")

    finally:
        # 4. LIMPIEZA
        if family:
            print("\n🧹 Limpiando...")
            try:
                qdrop(family)
            except:
                pass

if __name__ == "__main__":
    main()
