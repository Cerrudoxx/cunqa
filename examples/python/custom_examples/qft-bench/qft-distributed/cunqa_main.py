import argparse
import os
import sys
from runner import DistributedRunner
from results_handler import ResultsHandler

# --- IMPORTACIONES CUNQA ---
from cunqa import get_QPUs
from cunqa.qutils import  qraise, qdrop

def main():
    parser = argparse.ArgumentParser(description="Run Distributed QFT on CUNQA (Memory Scalable)")
    # Ahora 'n' es el TOTAL de qubits (ej: 32, 40, etc.)
    parser.add_argument("n", type=int, help="Total number of qubits to simulate")
    parser.add_argument("num_iterations", type=int, help="Number of shots/executions")
    
    parser.add_argument("--nodes", type=int, default=2, help="Number of HPC nodes (must be >= 2 for distributed)")
    parser.add_argument("--mem-per-qpu", type=int, default=16, help="RAM per QPU node in GB (e.g. 16 for half node)")
    parser.add_argument("--cores", type=int, default=15, help="Cores per QPU") 

    # Ignorados (compatibilidad)
    parser.add_argument("--qpus-per-node", type=int, default=1, help="Ignored in fully distributed mode")
    parser.add_argument("--no-ram", action='store_false', dest='ram', default=True)
    parser.add_argument("--no-cpu", action='store_false', dest='cpu', default=True)
    
    args = parser.parse_args()

    if args.nodes < 2:
        print("ERROR: Para computación distribuida real necesitas al menos 2 nodos.")
        sys.exit(1)

    # Configurar directorio
    results_dir = f"results_dist_QFT_n{args.n}"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    times_file_name = f'QFT_distributed_n{args.n}'
    results_handler = ResultsHandler(times_file_name, results_dir)

    # ---------------------------------------------------------
    # 1. ESTRATEGIA DE REPARTO (PARTITIONING)
    # ---------------------------------------------------------
    # Si pides 32 qubits -> Creamos 2 QPUs de 16 qubits cada una.
    # Así cada una solo gasta RAM de 16 qubits (MBs) en lugar de 32 qubits (GBs).
    qubits_per_qpu = args.n // args.nodes
    if args.n % args.nodes != 0:
        print("Advertencia: El número de qubits no es divisible exactamente por los nodos. Redondeando.")
    
    print(f"\n>>> MODO DISTRIBUIDO: {args.n} Qubits Totales")
    print(f"    - Reparto: {args.nodes} QPUs de ~{qubits_per_qpu} qubits cada una.")
    print(f"    - RAM Total Usada: ~{args.nodes} x (RAM de {qubits_per_qpu} qubits).")
    
    try:
        # Levantamos 1 QPU por nodo, pero configurada para comunicarse
        family = qraise(
            n=args.nodes,             # Total de QPUs (1 por nodo)
            t="00:30:00",
            n_nodes=args.nodes,       # Nodos físicos
            qpus_per_node=1,          # 1 QPU por nodo (para tener toda la RAM)
            cores=args.cores,
            mem_per_qpu=args.mem_per_qpu, 
            co_located=False,         # IMPORTANTE: False para forzar red real si es necesario
            partition="lusitania"
        )
        
        qpus = get_QPUs(on_node=False, family=family)
        print(f">>> Infraestructura lista: {len(qpus)} QPUs distribuidas.")
        
        # ---------------------------------------------------------
        # 2. EJECUCIÓN DISTRIBUIDA
        # ---------------------------------------------------------
        print(f"\n--- Ejecutando QFT Distribuida ({args.n} Qubits) ---")
        
        # Usamos el nuevo Runner Distribuido
        runner = DistributedRunner(args.n, args.num_iterations, qpus)
        results = runner.run()
        
        results_handler.display_timing_table(results)
        results_handler.save_to_csv(results)

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n>>> Liberando recursos...")
        try:
            qdrop(family)
        except:
            qdrop("--all")

if __name__ == "__main__":
    main()