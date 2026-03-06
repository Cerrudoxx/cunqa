import argparse
import os
import sys
from runner import Runner
from results_handler import ResultsHandler

# --- IMPORTACIONES CUNQA ---
from cunqa import get_QPUs
from cunqa.qutils import qraise, qdrop

def main():
    parser = argparse.ArgumentParser(description="Run QFT algorithm on CUNQA (Distributed)")
    parser.add_argument("n", type=str, help="Number of qubits or range (e.g., '4' or '4-7')")
    parser.add_argument("num_iterations", type=str, help="Number of repetitions/circuits to run per batch")
    
    # Parámetros de Infraestructura CUNQA
    parser.add_argument("--nodes", type=int, default=2, help="Number of HPC nodes to reserve")
    parser.add_argument("--qpus-per-node", type=int, default=1, help="QPUs per node")
    parser.add_argument("--cores", type=int, default=1, help="Cores per virtual QPU") 
    parser.add_argument("--mem-per-qpu", type=int, default=4, help="RAM per QPU in GB")

    # Flags de monitoreo (Ignorados pero mantenidos por compatibilidad)
    parser.add_argument("--no-ram", action='store_false', dest='ram', default=True, help="Ignored")
    parser.add_argument("--no-cpu", action='store_false', dest='cpu', default=True, help="Ignored")
    
    args = parser.parse_args()

    # Parsear rango de qubits
    if '-' in args.n:
        start, end = map(int, args.n.split('-'))
        if start >= end:
            print("Error: Invalid range of qubits.")
            sys.exit(1)
        qubits_list = range(start, end + 1)
    else:
        n = int(args.n)
        if n <= 2:
            print("Error: Number of qubits must be greater than 2.")
            sys.exit(1)
        qubits_list = [n]

    # Parsear iteraciones
    if '-' in args.num_iterations:
        start, end = map(int, args.num_iterations.split('-'))
        iterations_list = []
        current = start
        while current <= end:
            iterations_list.append(current)
            current *= 2
    else:
        num_iterations = int(args.num_iterations)
        iterations_list = [num_iterations]

    # Configurar directorio
    results_dir = f"results_cunqa_{args.nodes}nodes_{args.qpus_per_node}qpn"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    times_file_name = f'QFT_data_cunqa_N{args.nodes}'
    results_handler = ResultsHandler(times_file_name, results_dir)

    # ---------------------------------------------------------
    # 1. LEVANTAR INFRAESTRUCTURA CUNQA
    # ---------------------------------------------------------
    n_total_qpus = args.nodes * args.qpus_per_node
    print(f"\n>>> Iniciando CUNQA: {n_total_qpus} QPUs en {args.nodes} Nodos...")
    print(f">>> Configuración: {args.mem_per_qpu} GB RAM/QPU | {args.cores} Cores/QPU")
    
    try:
        family = qraise(
            n=n_total_qpus,
            t="00:30:00",
            n_nodes=args.nodes,
            qpus_per_node=args.qpus_per_node,
            cores=args.cores,
            mem_per_qpu=args.mem_per_qpu,  # <--- AHORA USA EL ARGUMENTO
            co_located=True,
            partition="lusitania"
        )
        
        qpus = get_QPUs(on_node=False, family=family)
        print(f">>> Recursos listos: {len(qpus)} QPUs activas.")

        # ---------------------------------------------------------
        # 2. BUCLE DE EXPERIMENTOS
        # ---------------------------------------------------------
        for n in qubits_list:
            for num_iterations in iterations_list:
                print(f"\n--- Running QFT ({n} qubits) - Distributed Batch: {num_iterations} ---")
                
                # Runner simplificado
                runner = Runner(n, num_iterations, qpus)
                
                results = runner.run()
                
                results_handler.display_timing_table(results)
                results_handler.save_to_csv(results)

    except Exception as e:
        print(f"ERROR CRÍTICO EN CUNQA: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n>>> Liberando recursos CUNQA...")
        try:
            qdrop(family)
        except:
            qdrop("--all")

if __name__ == "__main__":
    main()