"""
    Holds functions to manage and get infomation about the virtual QPUs displayed by the user.

    Connecting to virtual QPUs
    ==========================
    The most important function of the submodule, and one of the most important of :py:mod:`cunqa` is the :py:func:`get_QPUs`
    function, since it creates the objects that allow sending circuits and receiving the results of the simulations from the
    virtual QPUs already deployed:

        >>> from cunqa import get_QPUs
        >>> get_QPUs()
        [<cunqa.qpu.QPU object at XXXX>, <cunqa.qpu.QPU object at XXXX>, <cunqa.qpu.QPU object at XXXX>]

    The function allows to filter by `family` name or by choosing the virtual QPUs available at the `local` node.

    When each :py:class:`~cunqa.qpu.QPU` is instanciated, the corresponding :py:class:`QClient` is created.
    Nevertheless, it is not until the first job is submited that the client actually connects to the correspoding server.
    Other properties and information gathered in the :py:class:`~cunqa.qpu.QPU` class are shown on its documentation.

    Q-raising and Q-dropping at pyhton
    ==================================
    This submodule allows to raise and drop virtual QPUs, with no need to work in the command line.
    One must provide the neccesary information, analogous to the ``qraise`` command:

        >>> qraise(n = 4, # MANDATORY, number of QPUs to be raised
        >>> ...    t = "2:00:00", # MANDATORY, maximum time until they are automatically dropped
        >>> ...    classical_comm = True, # allow classical communications
        >>> ...    simulator = "Aer", # choosing Aer simulator
        >>> ...    co_located = True, # allowing co-located mode, QPUs can be accessed from any node
        >>> ...    family = "my_family_of_QPUs" # assigning a name to the group of QPUs
        >>> ...    )
        '<job id>'

    The function :py:func:`qraise` returns a string specifying the id of the `SLURM <https://slurm.schedmd.com/documentation.html>`_
    job that deploys the QPUs.

    Once we are finished with our work, we should drop the virtual QPUs in order to release classical resources.
    Knowing the `job id` or the `family` name of the group of virtual QPUs:

        >>> qdrop('<job id>')

    If no argument is passed to :py:func:`qdrop`, all QPUs deployed by the user are dropped.

    .. warning::
        The :py:func:`qraise` function can only be used when the python program is being run at a login node, otherwise an error will be raised.
        This is because SLURM jobs can only be submmited from login nodes, but not from compute sessions or running jobs.

    .. note::
        Even if we did not raise the virtual QPUs by the :py:func:`qraise` function, we can still use :py:func:`qdrop` to cancel them.
        In the same way, if we raise virtual QPUs by the python function, we can still drop them by terminal commands.
    

    Obtaining information about virtual QPUs
    ========================================

    In some cases we might be interested on checking availability of virtual QPUs or getting information about them, but before creating
    the :py:class:`~cunqa.qpu.QPU` objects.

    - To check if certain virtual QPUs are raised, :py:func:`are_QPUs_raised` should be used:
         
        >>> are_QPUs_raised(family = 'my_family_of_QPUs')
        True
        
    - In order to know what nodes have available virtual QPUs deployed:

        >>> nodes_with_QPUs()
        ['c7-3', 'c7-4']

    - For obtaining information about QPUs in the local node or in other nodes:

        >>> info_QPUs(on_node = True)
        [{'QPU':'<id>',
          'node':'<node name>',
          'family':'<family name>',
          'backend':{···}
          }]
"""
import os
import sys
import time
from typing import Union, Optional
from subprocess import run
from json import load
import json

from cunqa.qclient import QClient
from cunqa.backend import Backend
from cunqa.logger import logger
from cunqa.qpu import QPU
from cunqa.constants import QPUS_FILEPATH

class QRaiseError(Exception):
    """Exception for errors that occur during the qraise Slurm command."""
    pass
               
def qraise(n, t, *,
           classical_comm=False,
           quantum_comm=False,
           simulator=None,
           backend=None,
           fakeqmio=False,
           family=None,
           co_located=True,
           cores=None,
           mem_per_qpu=None,
           n_nodes=None,
           node_list=None,
           qpus_per_node=None) -> Union[tuple, str]:
    """Raises virtual QPUs and returns the job ID associated with the Slurm job.

    This function allows QPUs to be raised from the Python API, similar to the
    `qraise` command-line tool.

    Args:
        n (int): The number of virtual QPUs to be raised in the job.
        t (str): The maximum time that classical resources will be reserved
            for the job. The format is 'D-HH:MM:SS'.
        classical_comm (bool): If `True`, the virtual QPUs will allow
            classical communications.
        quantum_comm (bool): If `True`, the virtual QPUs will allow quantum
            communications.
        simulator (str, optional): The name of the desired simulator to use.
            Defaults to Aer.
        backend (str, optional): The path to a file containing backend
            information.
        fakeqmio (bool): If `True`, `n` virtual QPUs with the FakeQmio backend
            will be raised.
        family (str, optional): A name to identify the group of virtual QPUs
            being raised.
        co_located (bool): If `True`, co-located mode is set; otherwise, HPC
            mode is set.
        cores (str, optional): The number of cores per virtual QPU.
        mem_per_qpu (str, optional): The memory to allocate for each virtual
            QPU in GB (e.g., "4G").
        n_nodes (str, optional): The number of nodes for the Slurm job.
        node_list (str, optional): A list of nodes on which the virtual QPUs
            will be deployed.
        qpus_per_node (str, optional): The number of virtual QPUs to be
            deployed on each node.
    
    Returns:
        The Slurm job ID of the deployed job. If `family` was provided, a
        tuple of (`family`, `job_id`) is returned.

    Raises:
        QRaiseError: If an error occurs while raising the QPUs.
    """
    logger.debug("Setting up the requested QPUs...")

    SLURMD_NODENAME = os.getenv("SLURMD_NODENAME")

    if SLURMD_NODENAME == None:
        command = f"qraise -n {n} -t {t}"
    else: 
        logger.warning("Be careful, you are deploying QPUs from an interactive session.")
        HOSTNAME = os.getenv("HOSTNAME")
        command = f"qraise -n {n} -t {t}"

    try:
        # Add specified flags
        if fakeqmio:
            command = command + " --fakeqmio"
        if classical_comm:
            command = command + " --classical_comm"
        if quantum_comm:
            command = command + " --quantum_comm"
        if simulator is not None:
            command = command + f" --simulator={str(simulator)}"
        if family is not None:
            command = command + f" --family_name={str(family)}"
        if co_located:
            command = command + " --co-located"
        if cores is not None:
            command = command + f" --cores={str(cores)}"
        if mem_per_qpu is not None:
            command = command + f" --mem-per-qpu={str(mem_per_qpu)}G"
        if n_nodes is not None:
            command = command + f" --n_nodes={str(n_nodes)}"
        if node_list is not None:
            command = command + f" --node_list={str(node_list)}"
        if qpus_per_node is not None:
            command = command + f" --qpus_per_node={str(qpus_per_node)}"
        if backend is not None:
            command = command + f" --backend={str(backend)}"

        if not os.path.exists(QPUS_FILEPATH):
           with open(QPUS_FILEPATH, "w") as file:
                file.write("{}")

        print(f"Command: {command}")

        output = run(command, capture_output=True, shell=True, text=True).stdout #run the command on terminal and capture its output on the variable 'output'
        logger.info(output)
        job_id = ''.join(e for e in str(output) if e.isdecimal()) #sees the output on the console (looks like 'Submitted sbatch job 136285') and selects the number
        
        cmd_getstate = ["squeue", "-h", "-j", job_id, "-o", "%T"]
        
        i = 0
        while True:
            state = run(cmd_getstate, capture_output=True, text=True, check=True).stdout.strip()
            if state == "RUNNING":
                try:     
                    with open(QPUS_FILEPATH, "r") as file:
                        data = json.load(file)
                except json.JSONDecodeError:
                    continue
                count = sum(1 for key in data if key.startswith(job_id))
                if count == n:
                    break
            # We do this to prevent an overload to the Slurm deamon through the 
            if i == 500:
                time.sleep(2)
            else:
                i += 1

        # Wait for QPUs to be raised, so that get_QPUs can be executed inmediately
        print("QPUs ready to work \U00002705")

        return (family, str(job_id)) if family is not None else str(job_id)
    
    except Exception as error:
        raise QRaiseError(f"Unable to raise requested QPUs [{error}].")

def qdrop(*families: Union[tuple, str]):
    """Drops the virtual QPU families corresponding to the input family names.

    If no families are provided, all virtual QPUs deployed by the user will be
    dropped.

    Args:
        *families: The family names of the groups of virtual QPUs to be
            dropped.
    """
    cmd = ['qdrop']
    if not families:
        cmd.append('--all')
    else:
        for family in families:
            if isinstance(family, str):
                cmd.append(family)
            elif isinstance(family, tuple):
                cmd.append(family[1])
            else:
                logger.error("Invalid type provided for qdrop.")
                raise SystemExit
    run(cmd)

def nodes_with_QPUs() -> "list[str]":
    """Provides information about the nodes where virtual QPUs are available.

    Returns:
        A list of the corresponding node names.
    """
    try:
        with open(QPUS_FILEPATH, "r") as f:
            qpus_json = load(f)
        return list({info["net"]["node_name"] for info in qpus_json.values()})
    except Exception as error:
        logger.error(f"An exception occurred: [{type(error).__name__}].")
        raise SystemExit

def info_QPUs(on_node: bool = True, node_name: Optional[str] = None) -> "list[dict]":
    """Provides information about the virtual QPUs available.

    Args:
        on_node (bool): If `True`, information is shown for the local node.
        node_name (str, optional): Filters the information by a specific node.

    Returns:
        A list of dictionaries containing information about the virtual QPUs.
    """
    try:
        with open(QPUS_FILEPATH, "r") as f:
            qpus_json = load(f)
        if not qpus_json:
            logger.warning("No QPUs were found.")
            return [{}]
        
        if node_name:
            targets = [{k: v} for k, v in qpus_json.items() if v["net"].get("node_name") == node_name]
        elif on_node:
            local_node = os.getenv("SLURMD_NODENAME")
            logger.debug(f"User is at {'node ' + local_node if local_node else 'a login node'}.")
            targets = [{k: v} for k, v in qpus_json.items() if v["net"].get("node_name") == local_node]
        else:
            targets = [{k: v} for k, v in qpus_json.items()]
        
        info = []
        for t in targets:
            key = list(t.keys())[0]
            info.append({
                "QPU": key,
                "node": t[key]["net"]["node_name"],
                "family": t[key]["family"],
                "backend": {
                    "name": t[key]["backend"]["name"],
                    "simulator": t[key]["backend"]["simulator"],
                    "version": t[key]["backend"]["version"],
                    "description": t[key]["backend"]["description"],
                    "n_qubits": t[key]["backend"]["n_qubits"],
                    "basis_gates": t[key]["backend"]["basis_gates"],
                    "coupling_map": t[key]["backend"]["coupling_map"],
                    "custom_instructions": t[key]["backend"]["custom_instructions"]
                }
            })
        return info
    except Exception as error:
        logger.error(f"An exception occurred: [{type(error).__name__}].")
        raise

def get_QPUs(on_node: bool = True, family: Optional[Union[tuple, str]] = None) -> "list['QPU']":
    """Returns `QPU` objects corresponding to the virtual QPUs raised by the user.

    Args:
        on_node (bool): If `True`, filters by the virtual QPUs available on the
            local node.
        family (str or tuple, optional): Filters virtual QPUs by their family
            name.

    Returns:
        A list of `QPU` objects.
    """
    if isinstance(family, tuple):
        family = family[0]

    try:
        with open(QPUS_FILEPATH, "r") as f:
            qpus_json = load(f)
        if not qpus_json:
            logger.error("No QPUs were found.")
            raise SystemExit
    except Exception as error:
        logger.error(f"An exception occurred: [{type(error).__name__}].")
        raise SystemExit
    
    logger.debug("File accessed correctly.")

    local_node = os.getenv("SLURMD_NODENAME")
    logger.debug(f"User is at {'node ' + local_node if local_node else 'a login node'}.")

    if on_node:
        if family:
            targets = {k: v for k, v in qpus_json.items() if v["net"].get("node_name") == local_node and v.get("family") == family}
        else:
            targets = {k: v for k, v in qpus_json.items() if v["net"].get("node_name") == local_node}
    else:
        if family:
            targets = {k: v for k, v in qpus_json.items() if (v["net"].get("node_name") == local_node or v["net"].get("mode") == "co_located") and v.get("family") == family}
        else:
            targets = {k: v for k, v in qpus_json.items() if v["net"].get("node_name") == local_node or v["net"].get("mode") == "co_located"}
    
    qpus = [QPU(id=id, qclient=QClient(), backend=Backend(info['backend']), name=info["name"], family=info["family"], endpoint=info["net"]["endpoint"]) for id, info in targets.items()]

    if qpus:
        logger.debug(f"{len(qpus)} QPU objects were created.")
        return qpus
    else:
        logger.error(f"No QPUs were found with the specified characteristics: on_node={on_node}, family_name={family}.")
        raise SystemExit


