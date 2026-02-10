import os, sys
import numpy as np

sys.path.append(os.getenv("HOME"))

from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit
from cunqa.mappers import run_distributed
from cunqa.qjob import gather

qpus = get_QPUs(on_node=False)

cc_1 = CunqaCircuit(2,2,id="Uno")
cc_1.h(0)
cc_1.measure_and_send(qubit=0, target_circuit="Dos")
# cc_1.measure(0,0)
# cc_1.measure(1,1)
cc_1.measure_all()

cc_2 = CunqaCircuit(2,2,id="Dos")
cc_2.remote_c_if("x", qubits=0, param=None, control_circuit="Uno")
cc_2.measure_and_send(qubit=1,target_circuit="Tres")
# cc_2.measure(0,0)
# cc_2.measure(1,1)
cc_2.measure_all()

cc_3 = CunqaCircuit(2,2,id="Tres")
cc_3.remote_c_if("x", qubits=0, param=None, control_circuit="Dos")
# cc_3.measure(0,0)
# cc_3.measure(1,1)
cc_3.measure_all()

circuits = [cc_1, cc_2, cc_3]

distr_jobs = run_distributed(circuits, qpus, shots=20)

result_list = gather(distr_jobs)

for result in result_list:
    print(result)
    
