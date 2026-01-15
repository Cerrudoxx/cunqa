import os
import csv
from datetime import datetime

class ResultsHandler:
    def __init__(self, file_name: str, results_dir: str):
        self.file_name = os.path.join(results_dir, file_name + '.csv')
        self.results_dir = results_dir
        self._ensure_csv_headers()

    def _ensure_csv_headers(self) -> None:
        if not os.path.isfile(self.file_name):
            with open(self.file_name, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                # Solo cabeceras relevantes
                csv_writer.writerow(['n', 'iterations_number', 't_grover', 'std_grover'])

    def save_to_csv(self, data: dict) -> None:
        with open(self.file_name, mode='a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([data['n'], data['iterations_number'], data['t_grover'], data['std_grover']])
        
        print(f"Datos guardados en {self.file_name}")

    def display_timing_table(self, data: dict) -> None:
        print("-" * 40)
        print("RESULTADOS:")
        print(f"  Qubits:              {data['n']}")
        print(f"  Tiempo Medio:        {data['t_grover']:.6f} s")
        print(f"  Desviación Típica:   {data['std_grover']:.6f} s")
        print("-" * 40)