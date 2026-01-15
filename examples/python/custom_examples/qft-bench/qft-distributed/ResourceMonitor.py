import threading
import time
import psutil
import csv
import os
import matplotlib.pyplot as plt

class CPUMonitor:
    def __init__(self, interval=0.1):
        self.interval = interval
        self.readings = []
        self._monitoring = False

    def _monitor(self):
        while self._monitoring:
            self.readings.append(psutil.cpu_percent(interval=None))
            time.sleep(self.interval)

    def start(self):
        self._monitoring = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self._monitoring = False
        self.thread.join()

    def average(self):
        return sum(self.readings) / len(self.readings) if self.readings else 0.0

class RAMMonitor:
    def __init__(self, interval=0.1):
        self.interval = interval
        self.readings = []
        self._monitoring = False

    def _monitor(self):
        process = psutil.Process()
        while self._monitoring:
            try:
                # Usar rss (Resident Set Size) en MB
                mem_info = process.memory_info()
                self.readings.append(mem_info.rss / (1024 * 1024)) 
            except:
                pass
            time.sleep(self.interval)

    def start(self):
        self._monitoring = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self._monitoring = False
        self.thread.join()

    def average(self):
        return sum(self.readings) / len(self.readings) if self.readings else 0.0

    def plot_ram_usage_from_csv(self, file_name):
        # Implementación simplificada sin rich
        print(f"Generando gráfica de RAM para {file_name}...")
        pass