import os, sys

# --- CONFIGURACIÓN CUNQA ---
sys.path.append(os.getenv("HOME"))
from cunqa.qutils import get_QPUs, qraise, qdrop
from cunqa.circuit import CunqaCircuit

# =========================================================================
#  HERRAMIENTA DE VISUALIZACIÓN DISTRIBUIDA (SIN QISKIT)
# =========================================================================

class VisualizadorCunqa:
    def __init__(self):
        self.simbolos = {
            'h': '[H]', 'x': '[X]', 'y': '[Y]', 'z': '[Z]',
            'cx': '[CX]', 'cz': '[CZ]', 'measure': '[M]',
            'id': '---'
        }

    def dibujar(self, circuitos):
        print("\n" + "="*60)
        print(f"   VISUALIZACIÓN DE ARQUITECTURA DISTRIBUIDA CUNQA")
        print("="*60 + "\n")

        # Diccionario para coordinar visualmente las conexiones (Link ID -> Label)
        conexiones = {}
        contador_enlaces = 1

        # 1. PRIMERA PASADA: DETECTAR CONEXIONES PARA ASIGNAR ETIQUETAS
        for cc in circuitos:
            for instr in cc.instructions:
                if instr['name'] == 'measure_and_send':
                    destino = instr.get('circuits', ['?'])[0]
                    # Clave única de conexión: (Origen, Destino)
                    clave = (cc._id, destino)
                    if clave not in conexiones:
                        conexiones[clave] = f"LINK-{contador_enlaces}"
                        contador_enlaces += 1

        # 2. SEGUNDA PASADA: DIBUJAR CADA CIRCUITO
        for cc in circuitos:
            self._dibujar_circuito_individual(cc, conexiones)
            print("\n" + " "*25 + "||")
            print(" "*25 + "|| (Red Cuántica/Clásica)")
            print(" "*25 + "\/" + "\n")

    def _dibujar_circuito_individual(self, cc, conexiones):
        # Crear "pistas" (wires) para cada qubit
        wires = {q: f"q{q}: " for q in range(cc.num_qubits)}
        
        # Estado interno para controlar el espaciado
        max_len = 0
        
        # Iterar instrucciones
        for instr in cc.instructions:
            name = instr['name']
            qubits = instr.get('qubits', [])
            
            # --- LÓGICA DE DIBUJO ---
            bloque_visual = ""
            
            # 1. PUERTAS LOCALES SIMPLES
            if name in self.simbolos:
                sym = self.simbolos[name]
                # Aplicar a los qubits involucrados
                for q in wires:
                    if q in qubits:
                        wires[q] += f"--{sym}--"
                    else:
                        wires[q] += "-" * (len(sym) + 4) # Relleno

            # 2. MEDIR Y ENVIAR (SALIDA)
            elif name == 'measure_and_send':
                target = instr.get('circuits', ['?'])[0]
                link_label = conexiones.get((cc._id, target), "LINK-?")
                
                sym = f"==[M] ==>> {link_label} >>"
                
                for q in wires:
                    if q in qubits:
                        wires[q] += sym
                    else:
                        wires[q] += "-" * len(sym)

            # 3. RECIBIR (ENTRADA - Se procesa junto con la puerta condicionada)
            elif name == 'recv':
                # Normalmente 'recv' es invisible, preparamos el terreno para la siguiente instr
                pass

            # 4. PUERTA REMOTA (CONDICIONADA)
            elif 'remote_conditional_reg' in instr:
                # Intentamos deducir el origen (en una impl real estaría en metadatos, aquí buscamos el link inverso)
                # Buscamos qué link apunta a este circuito 'cc._id'
                origen_label = "LINK-?"
                for (orig, dest), label in conexiones.items():
                    if dest == cc._id:
                        origen_label = label
                        break
                
                gate_base = name  # ej: 'x'
                sym = f"<< {origen_label} <<==[ {gate_base.upper()} ]--"
                
                for q in wires:
                    if q in qubits:
                        wires[q] += sym
                    else:
                        wires[q] += "-" * len(sym)

            # Sincronizar longitudes
            max_len = max(len(w) for w in wires.values())
            for q in wires:
                wires[q] = wires[q].ljust(max_len, '-')

        # IMPRIMIR EL BLOQUE
        print(f"╔══ CIRCUITO: {cc._id} ══════════════════════╗")
        for q in range(cc.num_qubits):
            print(f"║ {wires[q]} ║")
        print(f"╚════════════════════════════════════════════════╝")

# =========================================================================
#  TU EJECUCIÓN
# =========================================================================

# 1. Configuración de Infraestructura
family = qraise(2, "00:10:00", simulator="Aer", classical_comm=True, co_located=True)
qpus = get_QPUs(on_node=False)

try:
    # 2. Definición de Circuitos
    # Circuito 1
    cc_1 = CunqaCircuit(2, 2, id="First") # Ajustado a 2 qubits para visualización limpia
    cc_1.h(0)
    cc_1.measure_and_send(qubit=0, target_circuit="Second") 
    cc_1.measure(1, 1)

    # Circuito 2
    cc_2 = CunqaCircuit(2, 2, id="Second")
    cc_2.remote_c_if("x", qubits=0, param=None, control_circuit="First") 
    cc_2.measure(1, 1)

    # 3. VISUALIZAR
    viz = VisualizadorCunqa()
    viz.dibujar([cc_1, cc_2])

    # 4. EJECUTAR (Opcional)
    jobs = run_distributed([cc_1, cc_2], qpus)
    results = gather(jobs)
    print("\nResultados:", [r.counts for r in results])

finally:
    qdrop(family)