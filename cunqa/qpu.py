"""
    Contains the description of the :py:class:`~cunqa.qpu.QPU` class.

    These :py:class:`QPU` objects are the python representation of the virtual QPUs deployed.
    Each one has its :py:class:`QClient` object that communicates with the server of the corresponding virtual QPU.
    Through these objects we are able to send circuits and recieve results from simulations.

    Virtual QPUs
    ============
    Each virtual QPU is described by three elements:

        - **Server**: classical resources intended to communicate with the python API to recieve circuits or quantum tasks and to send results of the simulations.
        - **Backend**: characteristics that define the QPU that is emulated: coupling map, basis gates, noise model, etc.
        - **Simulator**: classical resources intended to simulate circuits accordingly to the backend characteristics.
    
    .. image:: /_static/virtualqpuequal.png
        :align: center
        :width: 400px
        :height: 200px

    In order to stablish communication with the server, in the python API :py:class:`QPU` objects are created, each one of them associated with a virtual QPU.
    Each object will have a :py:class:`QClient` C++ object through which the communication with the classical resoruces is performed.
    
    .. image:: /_static/client-server-comm.png
        :align: center
        :width: 150
        :height: 300px

        
    Connecting to virtual QPUs
    ==========================

    The submodule :py:mod:`~cunqa.qutils` gathers functions for obtaining information about the virtual QPUs available;
    among them, the :py:func:`~cunqa.qutils.get_QPUs` function returns a list of :py:class:`QPU` objects with the desired filtering:

    >>> from cunqa import get_QPUs
    >>> get_QPUs()
    [<cunqa.qpu.QPU object at XXXX>, <cunqa.qpu.QPU object at XXXX>, <cunqa.qpu.QPU object at XXXX>]

    When each :py:class:`QPU` is instanciated, the corresponding :py:class:`QClient` is created.
    Nevertheless, it is not until the first job is submited that the client actually connects to the correspoding server.
    Other properties and information gathered in the :py:class:`QPU` class are shown on its documentation.

    Interacting with virtual QPUs
    =============================

    Once we have the :py:class:`QPU` objects created, we can start interacting with them.
    The most important method of the class is :py:meth:`QPU.run`, which allows to send a circuit to the virtual QPU for its simulation,
    returning a :py:class:`~cunqa.qjob.QJob` object associated to the quantum task:

        >>> qpus = get_QPUs()
        >>> qpu = qpus[0]
        >>> qpu.run(circuit)
        <cunqa.qjob.QJob object at XXXX>

    This method takes several arguments for specifications of the simulation such as `shots` or `transpilation`.
    For a larger description of its functionalities checkout its documentation.

"""

import os
from typing import  Union, Any, Optional
import inspect

from qiskit import QuantumCircuit

from cunqa.qclient import QClient
from cunqa.circuit import CunqaCircuit
from cunqa.circuit.converters import _is_parametric
from cunqa.backend import Backend
from cunqa.qjob import QJob
from cunqa.logger import logger
from cunqa.transpile import transpiler, TranspileError

class QPU:
    """Represents a virtual QPU deployed for user interaction.

    This class contains the necessary data for connecting to the virtual QPU's
    server to communicate circuits and results. This communication is
    established through the `QPU.qclient`.

    Attributes:
        _id (int): The ID assigned to the object.
        _qclient (QClient): The client for communicating with the server.
        _backend (Backend): The backend characteristics of the QPU.
        _name (str): The name of the QPU.
        _family (str): The family to which the QPU belongs.
        _endpoint (str): The server endpoint of the QPU.
        _connected (bool): The connection status of the client.
    """
    _id: int
    _qclient: 'QClient'
    _backend: 'Backend'
    _name: str
    _family: str
    _endpoint: str
    _connected: bool

    def __init__(self, id: int, qclient: 'QClient', backend: Backend, name: str, family: str, endpoint: str):
        """Initializes the QPU.

        This is typically done by the `get_QPUs` function, which loads the
        `id`, `family`, and `endpoint`, and instantiates the `qclient` and
        `backend` objects.

        Args:
            id: The ID string assigned to the object.
            qclient: The client for communicating with the server endpoint.
            backend: The object providing the backend characteristics.
            name: The name assigned to the QPU.
            family: The name of the family to which the QPU belongs.
            endpoint: The server endpoint of the QPU.
        """
        self._id = id
        self._qclient = qclient
        self._backend = backend
        self._name = name
        self._family = family
        self._endpoint = endpoint
        self._connected = False
        logger.debug(f"Object for QPU {id} created correctly.")

    @property
    def id(self) -> int:
        """The ID string assigned to the object."""
        return self._id
    
    @property
    def name(self) -> str:
        """The name of the QPU."""
        return self._name
    
    @property
    def backend(self) -> Backend:
        """The backend characteristics of the QPU."""
        return self._backend

    def run(self, circuit: Union[dict, 'CunqaCircuit', 'QuantumCircuit'], transpile: bool = False, initial_layout: Optional["list[int]"] = None, opt_level: int = 1, **run_parameters: Any) -> 'QJob':
        """Sends a circuit to the corresponding virtual QPU.

        If `transpile` is set to `False`, it is assumed that the user has
        already performed the transpilation.

        Args:
            circuit: The circuit to be simulated.
            transpile: If `True`, transpilation will be performed with respect
                to the backend. Defaults to `False`.
            initial_layout: The initial mapping of virtual qubits to physical
                qubits for transpilation.
            opt_level: The optimization level for transpilation. Defaults to 1.
            **run_parameters: Any other simulation instructions, such as `shots`
                and `method`.

        Returns:
            A `QJob` object related to the submitted job.
        """

        # Disallow execution of distributed circuits
        if inspect.stack()[1].function != "run_distributed": # Checks if the run() is called from run_distributed()
            if isinstance(circuit, CunqaCircuit):
                if circuit.has_cc or circuit.has_qc:
                    logger.error("Distributed circuits can't run using QPU.run(), try run_distributed() instead.")
                    raise SystemExit
            elif isinstance(circuit, dict):
                if ('has_cc' in circuit and circuit["has_cc"]) or ('has_qc' in circuit and circuit["has_qc"]):
                    logger.error("Distributed circuits can't run using QPU.run(), try run_distributed() instead.")
                    raise SystemExit

        # Handle connection to QClient
        if not self._connected:
            self._qclient.connect(self._endpoint)
            self._connected = True
            logger.debug(f"QClient connection stabished for QPU {self._id} to endpoint {self._endpoint}.")
            self._connected = True

        # Transpilation if requested
        if transpile:
            try:
                #logger.debug(f"About to transpile: {circuit}")
                circuit = transpiler(circuit, self._backend, initial_layout = initial_layout, opt_level = opt_level)
                logger.debug("Transpilation done.")
            except Exception as error:
                logger.error(f"Transpilation failed [{type(error).__name__}].")
                raise TranspileError # I capture the error in QPU.run() when creating the job

        try:
            qjob = QJob(self._qclient, self._backend, circuit, **run_parameters)
            qjob.submit()
            logger.debug(f"Qjob submitted to QPU {self._id}.")
        except Exception as error:
            logger.error(f"Error when submitting QJob [{type(error).__name__}].")
            raise SystemExit

        return qjob
