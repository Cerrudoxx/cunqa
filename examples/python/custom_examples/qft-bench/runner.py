import math
import statistics
import time
import numpy as np
from datetime import datetime

# --- CUNQA IMPORTS ---
from cunqa.circuit import CunqaCircuit
from cunqa import gather

class Runner:
    """Clase para ejecutar QFT en CUNQA distribuido (Versión Ligera)."""
    
    def __init__(self, n: int, num_iterations: int, qpus: list):
        self.n = n
        self.num_iterations = num_iterations
        self.qpus = qpus
        self.qc = self._build_circuit_cunqa()

    def _build_circuit_cunqa(self) -> CunqaCircuit:
        qc = CunqaCircuit(self.n)
        for i in range(self.n):
            qc.h(i)
            for j in range(i + 1, self.n):
                theta = np.pi / (2 ** (j - i))
                qc.cp(theta, j, i)
        
        for i in range(self.n // 2):
            qc.swap(i, self.n - 1 - i)
            
        qc.measure_all()
        return qc

    def _run_distributed_batch(self, num_executions: int) -> list[float]:
        jobs = []
        # Envío
        for i in range(num_executions):
            qpu = self.qpus[i % len(self.qpus)]
            job = qpu.run(self.qc, shots=1024)
            jobs.append(job)
            
        # Espera
        _ = gather(jobs)
        
        # Recogida
        times = []
        for job in jobs:
            try:
                t_str = job.time_taken
                t_val = float(t_str) 
                times.append(t_val * 1e9) # nanosegundos
            except:
                times.append(0.0)
        return times

    def run(self) -> dict:
        print(f"Comienza ejecución distribuida: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Lógica de iteraciones
        n_iterations_in = 10
        first_batch = min(n_iterations_in, self.num_iterations)
        
        t_batch = self._run_distributed_batch(first_batch)
        
        t_mean_ns = statistics.mean(t_batch) if t_batch else 0
        std_mean_ns = statistics.stdev(t_batch) if len(t_batch) > 1 else 0

        # Cálculo de iteraciones
        if t_mean_ns > 0:
            optimal_iterations = (math.ceil((2 * 1.96 * std_mean_ns) / (0.05 * t_mean_ns)) ** 2)
        else:
            optimal_iterations = self.num_iterations

        final_iterations = min(optimal_iterations, 1000) 
        print(f"Iteraciones calculadas: {final_iterations}")

        remaining = final_iterations - first_batch
        if remaining > 0:
            t_batch_2 = self._run_distributed_batch(remaining)
            t_batch.extend(t_batch_2)

        t_final_mean = statistics.mean(t_batch) / 1e9 if t_batch else 0
        std_final = statistics.stdev(t_batch) / 1e9 if len(t_batch) > 1 else 0

        print(f"Termina ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return {
            'n': self.n,
            'iterations_number': final_iterations,
            't_grover': t_final_mean,
            'std_grover': std_final
        }