"""
    Contains objects that define and manage quantum emulation jobs.

    The core of this module is the class :py:class:`~cunqa.qjob.QJob`. These objects are created when a quantum job
    is sent to a virtual QPU, as a return of the :py:meth:`~cunqa.qpu.QPU.run` method:

        >>> qpu.run(circuit)
        <cunqa.qjob.QJob object at XXXXXXXX>
        
    Once it is created, the circuit is being simulated at the virtual QPU.
    :py:class:`QJob` is the bridge between sending a circuit with instructions and recieving the results.
    Because of this, usually one wants to save this output in a variable:

        >>> qjob = qpu.run(circuit)

    Another functionality described in the submodule is the function :py:func:`~gather`, 
    which recieves a list of :py:class:`~QJob` objects and returns their results as :py:class:`~cunqa.result.Result`
    objects.

        >>> qjob_1 = qpu_1.run(circuit_1)
        >>> qjob_2 = qpu_2.run(circuit_2)
        >>> results = gather([qjob_1, qjob_2])
    
    For further information on sending and gathering quantum jobs, chekout the `Examples Galery <https://cesga-quantum-spain.github.io/cunqa/examples_gallery.html>`_.


    """

from typing import  Union, Any
import json
from typing import  Optional, Union, Any
from qiskit import QuantumCircuit
from qiskit.qasm2.exceptions import QASM2Error
from qiskit.exceptions import QiskitError

from cunqa.circuit import CunqaCircuit
from cunqa.circuit.converters import convert, _registers_dict
from cunqa.logger import logger
from cunqa.backend import Backend
from cunqa.result import Result
from cunqa.qclient import QClient, FutureWrapper


class QJobError(Exception):
    """Exception for errors that occur during job submission to virtual QPUs."""
    pass

class QJob:
    """Handles jobs sent to virtual QPUs.

    A `QJob` object is created as the output of the `QPU.run` method. It
    encapsulates the circuit to be simulated, simulation instructions, and
    information about the virtual QPU to which the job is sent.

    Attributes:
        qclient (QClient): The client linked to the server that listens at the
            virtual QPU.
    """
    _backend: 'Backend' 
    qclient: 'QClient' #: Client linked to the server that listens at the virtual QPU.
    _updated: bool
    _future: 'FutureWrapper' 
    _result: Optional['Result']
    _circuit_id: str 
    _sending_to: "list[str]"
    _is_dynamic: bool
    _has_cc: bool
    _has_qc: bool

    def __init__(self, qclient: 'QClient', backend: 'Backend', circuit: Union[dict, 'CunqaCircuit', 'QuantumCircuit'], **run_parameters: Any):
        """Initializes the QJob.

        Args:
            qclient: The client linked to the server that listens at the
                virtual QPU.
            backend: An object that gathers necessary information about the
                simulator.
            circuit: The circuit to be run, which can be a `QuantumCircuit`,
                a `CunqaCircuit`, or a dictionary.
            **run_parameters: Any other simulation instructions, such as `shots`,
                `method`, `parameter_binds`, `meas_level`, etc.
        """
        self._backend: 'Backend' = backend
        self._qclient: 'QClient' = qclient
        self._updated: bool = False
        self._future: 'FutureWrapper' = None
        self._result: Optional['Result'] = None
        self._circuit_id: str = ""

        self._convert_circuit(circuit)
        self._configure(**run_parameters)
        logger.debug("QJob configured.")

    @property
    def result(self) -> 'Result':
        """The result of the job.

        If no error occurred during simulation, a `Result` object is returned.
        Otherwise, a `ResultError` will be raised.

        Note:
            This is a blocking call, as it waits for the simulation to finish.
            The program will be blocked until the `QClient` receives the outcome
            of the job from the server.
        """
        try:
            if self._future and self._future.valid():
                if self._result is None or not self._updated:
                    res = self._future.get()
                    self._result = Result(json.loads(res), circ_id=self._circuit_id, registers=self._cregisters)
                    self._updated = True
            else:
                logger.debug("self._future is None or not valid; None is returned.")
        except Exception as error:
            logger.error(f"Error while reading the results: {error}")
            raise SystemExit
        
        if self._backend.simulator == "CunqaSimulator" and self.num_clbits != self.num_qubits:
            logger.warning("For CunqaSimulator, the number of classical bits is required to be equal to the number of qubits. Classical bits may appear to be rewritten.")

        return self._result

    @property
    def time_taken(self) -> str:
        """The time that the job took to execute."""
        if self._future and self._future.valid():
            if self._result:
                try:
                    return self._result.time_taken
                except AttributeError:
                    logger.warning("Time taken is not available.")
                    return ""
            else:
                logger.error(f"QJob not finished. [{QJobError.__name__}].")
                raise SystemExit
        else:
            logger.error(f"No QJob submitted. [{QJobError.__name__}].")
            raise SystemExit

    def submit(self) -> None:
        """Submits a job to the corresponding `QClient` asynchronously.

        Note:
            This is a non-blocking call. Once a job is submitted, the program
            continues while the server receives and simulates the circuit.
        """
        if self._future:
            logger.warning("QJob has already been submitted.")
        else:
            try:
                self._future = self._qclient.send_circuit(self._execution_config)
                logger.debug("Circuit was sent.")
            except Exception as error:
                logger.error(f"An error occurred when submitting the job: [{type(error).__name__}].")
                raise QJobError

    def upgrade_parameters(self, parameters: "list[float | int]") -> None:
        """Upgrades the parameters in a previously submitted parametric circuit job.

        This method checks if the result of the prior simulation has been
        retrieved. If not, it retrieves it but does not store it. Then, it
        sends the new set of parameters to the server to be reassigned to the
        circuit for re-simulation.

        Warning:
            In the current version, parameters will be assigned to all
            parametric gates in the circuit. Only `rx`, `ry`, and `rz` gates
            are considered parametric.

        Args:
            parameters: A list of parameters to assign to the parameterized circuit.
        """
        if self._result is None:
            self._future.get()

        if isinstance(parameters, list):
            if all(isinstance(param, (int, float)) for param in parameters):
                message = f'{{"params":{parameters}}}'.replace("'", '"')
            else:
                logger.error(f"Parameters must be real numbers. [{ValueError.__name__}].")
                raise SystemExit
        
            try:
                self._future = self._qclient.send_parameters(message)
            except Exception as error:
                logger.error(f"An error occurred when sending the new parameters for circuit {self._circuit_id}: [{type(error).__name__}].")
                raise SystemExit
        else:
            logger.error(f"Invalid parameter type. A list was expected, but {type(parameters)} was given. [{TypeError.__name__}].")
            raise SystemExit
        
        self._updated = False

    def _convert_circuit(self, circuit: Union[str, dict, 'CunqaCircuit', 'QuantumCircuit']) -> None:
        """Converts the circuit to a dictionary format."""
        try:
            if isinstance(circuit, dict):
                logger.debug("A circuit dict was provided.")
                self.num_qubits = circuit["num_qubits"]
                self.num_clbits = circuit["num_clbits"]
                self._cregisters = circuit["classical_registers"]
                self._sending_to = circuit.get("sending_to", [])
                self._has_cc = circuit.get("has_cc", False)
                self._has_qc = circuit.get("has_qc", False)
                self._is_dynamic = self._has_cc or self._has_qc or circuit.get("is_dynamic", False)
                self._circuit_id = circuit["id"]
                instructions = circuit['instructions']
            elif isinstance(circuit, CunqaCircuit):
                logger.debug("A CunqaCircuit was provided.")
                self.num_qubits = circuit.num_qubits
                self.num_clbits = circuit.num_clbits
                self._cregisters = circuit.classical_regs
                self._circuit_id = circuit._id
                self._sending_to = circuit.sending_to
                self._is_dynamic = circuit.is_dynamic
                self._has_cc = circuit.has_cc
                self._has_qc = circuit.has_qc
                logger.debug("Translating to dict from CunqaCircuit...")
                instructions = circuit.instructions
            elif isinstance(circuit, QuantumCircuit):
                logger.debug("A QuantumCircuit was provided.")
                self.num_qubits = circuit.num_qubits
                self.num_clbits = sum(c.size for c in circuit.cregs)
                self._cregisters = _registers_dict(circuit)[1]
                self._sending_to = []
                logger.debug("Translating to dict from QuantumCircuit...")
                circuit_json = convert(circuit, "dict")
                instructions = circuit_json["instructions"]
                self._is_dynamic = circuit_json["is_dynamic"]
                self._has_cc = False
                self._has_qc = False
            elif isinstance(circuit, str):
                logger.debug("A QASM2 circuit was provided.")
                qc_from_qasm = QuantumCircuit.from_qasm_str(circuit)
                self.num_qubits = qc_from_qasm.num_qubits
                self._cregisters = _registers_dict(qc_from_qasm)[1]
                self.num_clbits = sum(len(v) for v in self._cregisters.values())
                self._sending_to = []
                logger.debug("Translating to dict from QASM2 string...")
                circuit_json = convert(qc_from_qasm, "dict")
                instructions = circuit_json["instructions"]
                self._is_dynamic = circuit_json["is_dynamic"]
                self._has_cc = False
                self._has_qc = False
            else:
                logger.error(f"Circuit must be a dict, `CunqaCircuit`, or QASM2 string, but {type(circuit)} was provided. [{TypeError.__name__}].")
                raise QJobError

            self._circuit = instructions
            
        except KeyError as error:
            logger.error(f"The format of the circuit dict is incorrect. Could not find 'num_clbits', 'classical_registers', or 'instructions'. [{type(error).__name__}].")
            raise QJobError
        except QASM2Error as error:
            logger.error(f"Error while translating to QASM2: [{type(error).__name__}].")
            raise QJobError
        except QiskitError as error:
            logger.error(f"The format of the circuit is incorrect: [{type(error).__name__}].")
            raise QJobError
        except Exception as error:
            logger.error(f"An error occurred with the provided circuit dict: [{type(error).__name__}].")
            raise QJobError

    def _configure(self, **run_parameters: Any) -> None:
        """Configures the execution parameters for the job."""
        try:
            run_config = {
                "shots": 1024,
                "method": "automatic",
                "avoid_parallelization": False,
                "num_clbits": self.num_clbits,
                "num_qubits": self.num_qubits,
                "seed": 123123
            }

            if not run_parameters:
                logger.debug("No run parameters provided; using defaults.")
            elif isinstance(run_parameters, dict):
                run_config.update(run_parameters)
            else:
                logger.warning("Error reading `run_parameters`; using defaults.")
            
            exec_config = {
                "id": self._circuit_id,
                "config": run_config,
                "instructions": self._circuit,
                "sending_to": self._sending_to,
                "is_dynamic": self._is_dynamic,
                "has_cc": self._has_cc
            }
            self._execution_config = json.dumps(exec_config)
            logger.debug("QJob created.")

        except KeyError as error:
            logger.error(f"The format of the circuit is incorrect. Could not find 'instructions'. [{type(error).__name__}].")
            raise QJobError
        except Exception as error:
            logger.error(f"An error occurred when generating the simulation configuration: [{type(error).__name__}].")
            raise QJobError

def gather(qjobs: "list['QJob']") -> "list['Result']":
    """Gets the results of several `QJob` objects.

    This is a blocking call that retrieves results sequentially. Since jobs
    are run simultaneously, the total time will be dominated by the longest-
    running job.

    Warning:
        The order of jobs must be preserved when submitting to the same
        virtual QPU.

    Args:
        qjobs: A list of `QJob` objects to get the results from.

    Returns:
        A list of `Result` objects.
    """
    if isinstance(qjobs, list):
        if all(isinstance(q, QJob) for q in qjobs):
            return [q.result for q in qjobs]
        else:
            logger.error(f"All objects in the list must be of type `QJob`. [{TypeError.__name__}].")
            raise SystemExit
    else:
        logger.error(f"`qjobs` must be a list, but {type(qjobs)} was provided. [{TypeError.__name__}].")
        raise SystemError
