import sys
import time
import os
import subprocess
import json
from cunqa import get_QPUs
from cunqa.circuit import CunqaCircuit

# --- CONFIGURACIÓN LUSITANIA MAX ---
NUM_NODOS = 2
QUBITS_POR_NODO = 30
TIEMPO_MAX = "00:45:00"
SBATCH_FILE = "manual_launch.sbatch"

def generar_sbatch():
    """Genera el SBATCH corregido (mem=0 para usar toda la RAM)."""
    script_content = f"""#!/bin/bash
#SBATCH --job-name=cunqa_manual
#SBATCH --nodes={NUM_NODOS}
#SBATCH --ntasks={NUM_NODOS}
#SBATCH --cpus-per-task=16
#SBATCH --mem=0
#SBATCH --partition=lusitania
#SBATCH --time={TIEMPO_MAX}
#SBATCH --output=salida_manual_%j.txt
#SBATCH --error=error_manual_%j.txt

module purge
module load python/python-cunqa-ex

# Borramos configuración antigua para evitar lecturas falsas
rm -f $HOME/.cunqa/qpus.json

echo ">>> INICIANDO SETUP_QPUS..."
# Lanzamos setup_qpus en segundo plano (&) para que el script no se bloquee
srun --ntasks={NUM_NODOS} --ntasks-per-node=1 \\
     setup_qpus hpc no_comm default Aer &

SRUN_PID=$!

# Esperamos un poco para asegurar arranque
sleep 5

# Mantenemos el trabajo vivo esperando al proceso srun
wait $SRUN_PID
"""
    with open(SBATCH_FILE, "w") as f:
        f.write(script_content)

def esperar_arranque_job(job_id):
    """Bloquea la ejecución hasta que el trabajo esté RUNNING."""
    print(f"[2/4] Esperando a que el trabajo {job_id} entre en ejecución...")
    sys.stdout.flush()
    
    while True:
        # Consultamos squeue
        res = subprocess.run(["squeue", "-j", job_id, "-h", "-o", "%t"], 
                           capture_output=True, text=True)
        state = res.stdout.strip()
        
        if not state:
            # Si no sale nada, el trabajo murió o terminó muy rápido
            print("\n⚠️ El trabajo ha desaparecido de la cola (¿Falló o terminó?).")
            return False
            
        if state == "R": # Running
            print(f"\n✅ ¡El trabajo {job_id} está EJECUTÁNDOSE (RUNNING)!")
            time.sleep(10) # Damos 10s de cortesía para que setup_qpus arranque
            return True
            
        if state == "PD": # Pending
            print(".", end="", flush=True)
            time.sleep(5)
        else:
            print(f"[{state}]", end="", flush=True)
            time.sleep(5)

def main():
    print(f"\n{'='*70}")
    print(f"🚀 CUNQA LUSITANIA: ESTRATEGIA MANUAL (CON ESPERA INTELIGENTE)")
    print(f"{'='*70}")

    # 1. Generar y Lanzar
    generar_sbatch()
    print(f"[1/4] Enviando solicitud a SLURM...")
    
    result = subprocess.run(["sbatch", SBATCH_FILE], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error sbatch: {result.stderr}")
        sys.exit(1)
        
    job_id = result.stdout.strip().split()[-1]
    print(f"   -> Trabajo ID: {job_id}")

    try:
        # 2. Esperar a la cola (Fase PENDING -> RUNNING)
        if not esperar_arranque_job(job_id):
            raise RuntimeError("El trabajo falló antes de arrancar.")

        # 3. Conectar QPUs (Fase RUNNING -> ONLINE)
        print(f"[3/4] Buscando QPUs activas...")
        qpus = []
        # Intentamos durante 2 minutos (por si setup_qpus tarda)
        for i in range(24): 
            try:
                qpus = get_QPUs(on_node=False)
                # Solo nos vale si encontramos TODAS las QPUs
                if len(qpus) >= NUM_NODOS:
                    break
            except Exception:
                pass
            print(f"   Intento {i+1}/24: Buscando...", end="\r")
            time.sleep(5)
        print("") # Salto de línea

        if len(qpus) < NUM_NODOS:
            print("\n❌ TIMEOUT: El trabajo corre, pero las QPUs no responden.")
            print("   Posible causa: Error de librería o red en el nodo remoto.")
            raise RuntimeError("QPUs no encontradas.")

        print(f"✅ CONEXIÓN ESTABLECIDA:")
        for i, qpu in enumerate(qpus):
            print(f"   - QPU {i}: {qpu.name} @ {qpu.ip}")

        # 4. Simulación
        print(f"\n[4/4] Ejecutando Simulación Distribuida ({QUBITS_POR_NODO}q x {NUM_NODOS})...")
        
        qc_a = CunqaCircuit(QUBITS_POR_NODO)
        for i in range(QUBITS_POR_NODO): qc_a.h(i)
        qc_a.measure_all()
        
        qc_b = CunqaCircuit(QUBITS_POR_NODO)
        for i in range(QUBITS_POR_NODO): qc_b.x(i)
        qc_b.measure_all()
        
        t_start = time.time()
        # Nota: Usamos shot=10 para prueba rápida, subir si funciona
        job_a = qpus[0].run(qc_a, shots=10) 
        job_b = qpus[1].run(qc_b, shots=10)
        
        res_a = job_a.result()
        res_b = job_b.result()
        
        print(f"\n{'='*70}")
        print(f"RESULTADOS FINALES ({time.time() - t_start:.2f}s)")
        print(f"{'='*70}")
        print(f"🔹 Nodo A: OK ({len(res_a.get_counts())} estados)")
        print(f"🔹 Nodo B: OK ({len(res_b.get_counts())} estados)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        # Intentamos mostrar por qué falló
        print("--- Log de Error del Trabajo ---")
        os.system(f"cat error_manual_{job_id}.txt 2>/dev/null")

    finally:
        print(f"\n🧹 Cancelando trabajo {job_id}...")
        subprocess.run(["scancel", job_id], stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
