"""
    Contains map-like callables to distribute circuits in virtual QPUS, needed when communications among circuits are present.

    Submitting circuits with classical or quantum communications
    ---------------------------------------------------------

    When having classical or quantum communications among circuits, method :py:func:`~cunqa.qpu.QPU.run` is obsolete, circuits must be sent as an ensemble in order to ensure correct functioning of the communication protocols.

    So, once the virtual QPUs that allow the desired type of communications are raised and circuits have been defined using :py:class:`~cunqa.circuit.CunqaCircuit`,
    they can be sent using the :py:meth:`~run_distributed` function:

    >>> circuit1 = CunqaCircuit(1, "circuit_1")
    >>> circuit2 = CunqaCircuit(1, "circuit_2")
    >>> circuit1.h(0)
    >>> circuit1.measure_and_send(0, "circuit_2")
    >>> circuit2.remote_c_if("x", 0, "circuit_1")
    >>>
    >>> qpus = get_QPUs()
    >>>
    >>> qjobs = run_distributed([circuit1, circuit2], qpus)
    >>> results = gather(qjobs)


    Mapping circuits to virtual QPUs in optimization problems
    ---------------------------------------------------------

    **Variational Quantum Algorithms** [#]_ require from numerous executions of parametric cirucits, while in each step of the optimization process new parameters are assigned to them.
    This implies that, after parameters are updated, a new circuit must be created, transpiled and then sent to the quantum processor or simulator.
    For simplifying this process, we have :py:class:`~QJobMapper` and :py:class:`~QPUCircuitMapper` classes. Both classes are thought to be used for Scipy optimizers [#]_ as the *workers* argument in global optimizers.

    QJobMapper
    ==========
    :py:class:`~QJobMapper` takes a list of existing :py:class:`~cunqa.qjob.QJob` objects, then, the class can be called passing a set of **parameters** and a **cost function**.
    This callable updates the each existing :py:class:`~cunqa.qjob.QJob` object with such **parameters** through the :py:meth:`~cunqa.qjob.QJob.upgrade_parameters` method.
    Then, it gathers the results of the executions and returns the **value of the cost function** for each.
    
    QPUCircuitMapper
    ===============
    On the other hand, :py:class:`~QPUCircuitMapper` is instanciated with a circuit and instructions for its execution, toguether with a list of the :py:class:`~cunqa.qpu.QPU` objects.
    The difference with :py:class:`~QJobMapper` is that here the method :py:meth:`~cunqa.qpu.QPU.run` is mapped to each QPU, passing it the circuit with the given parameters assigned so that for this case several :py:class:`~cunqa.qjob.QJob` objects are created.

    Examples utilizing both classes can be found in the `Examples gallery <https://cesga-quantum-spain.github.io/cunqa/_examples/Optimizers_II_mapping.html>`_. These examples focus on optimization of VQAs, using a global optimizer called Differential Evolution [#]_.

    References:
    ~~~~~~~~~~~

    .. [#] `Variational Quantum Algorithms arXiv <https://arxiv.org/abs/2012.09265>`_ .

    .. [#] `scipy.optimize documentation <https://docs.scipy.org/doc/scipy/reference/optimize.html>`_.

    .. [#] Differential Evolution initializes a population of inidividuals that evolute from generation to generation in order to collectively find the lowest value to a given cost function. This optimizer has shown great performance for VQAs [`Reference <https://arxiv.org/abs/2303.12186>`_]. It is well implemented at Scipy by the `scipy.optimize.differential_evolution <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html#scipy.optimize.differential_evolution>`_ function.



"""
from cunqa.logger import logger
from cunqa.qjob import gather
from cunqa.circuit import CunqaCircuit
from cunqa.qpu import QPU
from cunqa.qjob import QJob

from qiskit import QuantumCircuit
from qiskit.exceptions import QiskitError
from qiskit.qasm2 import QASM2Error
import numpy as np
from typing import  Optional, Union, Any

import time
import copy


def run_distributed(circuits: "list[Union[dict, 'CunqaCircuit']]", qpus: "list['QPU']", **run_args: Any) -> "list[QJob]":
    """Sends circuits to several virtual QPUs, allowing for classical or
    quantum communications among them.

    Each circuit is sent to a corresponding QPU in order, so both lists must
    be of the same size. Because this function is intended for executions
    that require communications, only `CunqaCircuit` objects or instruction
    sets are accepted. The provided arguments will be the same for all
    `QJob` objects created.

    Warning:
        If `transpile`, `initial_layout`, or `opt_level` are passed as
        `run_args`, they will be ignored, as transpilation is not supported
        in the current version when communications are present.

    Args:
        circuits: A list of circuits to be run, either as `CunqaCircuit`
            objects or dictionaries.
        qpus: A list of `QPU` objects associated with the virtual QPUs
            where the circuits will be run.
        **run_args: Any other run arguments and parameters.

    Returns:
        A list of `QJob` objects.
    """

    distributed_qjobs = []
    circuit_jsons = []

    remote_controlled_gates = ["measure_and_send", "remote_c_if", "recv", "qsend", "qrecv", "expose", "rcontrol"]
    correspondence = {}

    #Check wether the circuits are valid and extract jsons
    for circuit in circuits:
        if isinstance(circuit, CunqaCircuit):
            info_circuit_copy = copy.deepcopy(circuit.info) # To modify the info without modifying the attribute info of the circuit
            circuit_jsons.append(info_circuit_copy)

        elif isinstance(circuit, dict):
            circuit_jsons.append(circuit)
        else:
            logger.error(f"Objects of the list `circuits` must be  <class 'cunqa.circuit.CunqaCircuit'> or jsons, but {type(circuit)} was given. [{TypeError.__name__}].")
            raise SystemExit # User's level
    
    #check wether there are enough qpus and create an allocation dict that for every circuit id has the info of the QPU to which it will be sent
    if len(circuit_jsons) > len(qpus):
        logger.error(f"There are not enough QPUs: {len(circuit_jsons)} circuits were given, but only {len(qpus)} QPUs [{ValueError.__name__}].")
        raise SystemExit # User's level
    else:
        if len(circuit_jsons) < len(qpus):
            logger.warning("More QPUs provided than the number of circuits. Last QPUs will remain unused.")
        for circuit, qpu in zip(circuit_jsons, qpus):
            correspondence[circuit["id"]] = qpu._id
        

    # Check whether the QPUs are valid
    # TODO: check only makes sense if we have selected mpi option at compilation time. For the moment it remains commented.
    # if not all(qpu._family == qpus[0]._family for qpu in qpus):
    #     logger.debug(f"QPUs of different families were provided.")
    #     if not all(re.match(r"^tcp://", qpu._endpoint) for qpu in qpus):
    #         names = set()
    #         for qpu in qpus:
    #             names.add(qpu._family)
    #         logger.error(f"QPU objects provided are from different families ({list(names)}). For this version, classical communications beyond families are only supported with zmq communication type.")
    #         raise SystemExit # User's level
    
    logger.debug(f"Run arguments provided for simulation: {run_args}")
    
    #translate circuit ids in comm instruction to qpu endpoints
    for circuit in circuit_jsons:
        for instr in circuit["instructions"]:
            if instr["name"] in remote_controlled_gates:
                instr["qpus"] =  [correspondence[instr["circuits"][0]]]
                instr.pop("circuits")
        for i in range(len(circuit["sending_to"])):
            circuit["sending_to"][i] = correspondence[circuit["sending_to"][i]]
        circuit["id"] = correspondence[circuit["id"]]

    warn = False
    run_parameters = {}
    for k,v in run_args.items():
        if k == "transpile" or k == "initial_layout" or k == "opt_level":
            if not warn:
                logger.warning("Transpilation instructions are not supported for this version. Default `transpilation=False` is set.")
        else:
            run_parameters[k] = v

    # no need to capture errors bacuse they are captured at `QPU.run`
    for circuit, qpu in zip(circuit_jsons, qpus):
        distributed_qjobs.append(qpu.run(circuit, **run_parameters))

    return distributed_qjobs


class QJobMapper:
    """Maps the `QJob.upgrade_parameters` method to a set of jobs.

    This class is designed for optimization algorithms where a parametric
    circuit needs to be updated with new parameters. It takes a list of
    `QJob` objects and can be called with a set of parameters and a cost
    function to evaluate the results.

    Attributes:
        qjobs (list[QJob]): The list of jobs that are mapped.
    """
    qjobs: "list['QJob']"

    def __init__(self, qjobs: "list['QJob']"):
        """Initializes the QJobMapper.

        Args:
            qjobs: A list of `QJob` objects to be mapped.
        """
        self.qjobs = qjobs
        logger.debug(f"QJobMapper initialized with {len(qjobs)} QJobs.")

    def __call__(self, func, population):
        """Maps a function to the results of assigning a population to the jobs.

        Args:
            func (callable): The function to be applied to the results of the
                jobs.
            population (list[list[int or float]]): A list of vectors to be
                mapped to the jobs.

        Returns:
            A list of the outputs of the function applied to the results of
            each job for the given population.
        """
        qjobs_ = []
        for i, params in enumerate(population):
            qjob = self.qjobs[i]
            logger.debug(f"Updating parameters for QJob {qjob}...")
            qjob.upgrade_parameters(params.tolist())
            qjobs_.append(qjob)

        logger.debug("Gathering results...")
        results = gather(qjobs_)

        return [func(result) for result in results]


class QPUCircuitMapper:
    """Maps the `QPU.run` method to a list of QPUs.

    This class is initialized with a list of `QPU` objects, a circuit, and
    simulation instructions. When called, it assigns a set of parameters to
    the circuit and sends it to each QPU.

    Attributes:
        qpus (list[QPU]): The `QPU` objects to which the circuit is mapped.
        circuit (QuantumCircuit): The circuit to which parameters are assigned.
        transpile (bool, optional): Whether transpilation should be done before
            sending each circuit.
        initial_layout (list[int], optional): The initial mapping of virtual
            qubits to physical qubits for transpilation.
        run_parameters (Any, optional): Any other run instructions for the
            simulation.
    """
    qpus: "list['QPU']"
    circuit: 'QuantumCircuit'
    transpile: Optional[bool]
    initial_layout: Optional["list[int]"]
    run_parameters: Optional[Any]

    def __init__(self, qpus: "list['QPU']", circuit: Union[dict, 'QuantumCircuit', 'CunqaCircuit'], transpile: Optional[bool] = False, initial_layout: Optional["list[int]"] = None, **run_parameters: Any):
        """Initializes the QPUCircuitMapper.

        Args:
            qpus: A list of `QPU` objects to be used.
            circuit: The circuit to be run on the QPUs.
            transpile (bool): If `True`, transpilation will be done with
                respect to the backend. Defaults to `False`.
            initial_layout (list[int], optional): The initial mapping of
                virtual qubits to physical qubits for transpilation.
            **run_parameters: Any other simulation instructions.
        """
        self.qpus = qpus

        if not isinstance(circuit, QuantumCircuit):
            logger.error(f"The parametric circuit must be a QuantumCircuit, but {type(circuit)} was provided. [{TypeError.__name__}].")
            raise SystemExit

        self.circuit = circuit
        self.transpile = transpile
        self.initial_layout = initial_layout
        self.run_parameters = run_parameters
        
        logger.debug(f"QPUMapper initialized with {len(qpus)} QPUs.")

    def __call__(self, func, population):
        """Maps a function to the results of circuits sent to the QPUs.

        Args:
            func (callable): The function to be mapped to the QPUs. It must
                take a `Result` object as an argument.
            population (list[list[float or int]]): A population of vectors to
                be mapped to the circuits.

        Returns:
            A list of the results of the function applied to the output of the
            circuits.
        """
        qjobs = []
        try:
            tick = time.time()
            for i, params in enumerate(population):
                qpu = self.qpus[i % len(self.qpus)]
                circuit_assembled = self.circuit.assign_parameters(params)

                logger.debug(f"Sending QJob to QPU {qpu._id}...")
                qjobs.append(qpu.run(circuit_assembled, transpile=self.transpile, initial_layout=self.initial_layout, **self.run_parameters))

            logger.debug(f"Gathering {len(qjobs)} results...")
            results = gather(qjobs)
            tack = time.time()
            median = sum(res.time_taken for res in results) / len(results)

            print("Mean simulation time: ", median)
            print("Total distribution and gathering time: ", tack - tick)

            return [func(result) for result in results]
        
        except QiskitError as error:
            logger.error(f"An error occurred while assigning parameters to the QuantumCircuit. Check if the size is correct. [{type(error).__name__}]: {error}.")
            raise SystemExit
        except Exception as error:
            logger.error(f"An error occurred with the circuit: [{type(error).__name__}]: {error}")
            raise SystemExit