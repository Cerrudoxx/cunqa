"""
    Cointains the class :py:class:`~cunqa.backend.Backend` which serves as a description of the characteristics of the virtual QPUs.

    It can be found as the attribute :py:attr:`~cunqa.qpu.QPU.backend` of the :py:class:`~cunqa.qpu.QPU` class, it is created with
    the corrresponding data when the :py:class:`~cunqa.qpu.QPU` object is instantiated:

        >>> qpu.backend
        <cunqa.backend.Backend object at XXXX>
"""

from typing import  TypedDict

class BackendData(TypedDict):
    """A TypedDict to gather the characteristics of a Backend object.

    Attributes:
        basis_gates: Native gates that the Backend accepts. If other gates are
            used, they must be translated into the native gates.
        coupling_map: Defines the physical connectivity of the qubits,
            specifying in which pairs two-qubit gates can be performed.
        custom_instructions: Any custom instructions that the Backend has
            defined.
        description: A description of the Backend itself.
        gates: A list of specific gates supported by the Backend.
        n_qubits: The number of qubits that form the Backend, which
            determines the maximal number of qubits supported for a quantum
            circuit.
        name: The name assigned to the Backend.
        noise_path: The path to the noise model JSON file, which contains
            the noise instructions needed for the simulator.
        simulator: The name of the simulator that simulates the circuits
            according to the Backend's characteristics.
        version: The version of the Backend.
    """
    basis_gates: "list[str]"
    coupling_map: "list[list[int]]"
    custom_instructions: str
    description: str
    gates: "list[str]"
    n_qubits: int
    name: str
    noise_path: str
    simulator: str
    version: str


class Backend:
    """Defines the backend information of a virtual QPU."""
    def __init__(self, backend_dict: BackendData):
        """Initializes the Backend object.

        Args:
            backend_dict: A dictionary containing all the necessary
                information about the backend.
        """
        for key, value in backend_dict.items():
            setattr(self, key, value)

    def info(self) -> None:
        """Prints a dictionary with the backend configuration."""
        print("--- Backend configuration ---")
        for attribute_name, attribute_value in self.__dict__.items():
            print(f"{attribute_name}: {attribute_value}")