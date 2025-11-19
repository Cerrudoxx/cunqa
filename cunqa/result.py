"""
    Contains the :py:class:`~cunqa.result.Result` class, which gathers the information about the output of a simulations, also other functions
    to manage them.

    Once we have submmited a :py:class:`~cunqa.qjob.QJob`, for obtaining its results we call for its propperty :py:attr:`QJob.result`:

        >>> qjob.result
        <cunqa.result.Result object at XXXX>
    
    This object has two main attributes for out interest: the counts distribution from the simulation and the time that the simulation took in seconds:

        >>> result = qjob.result
        >>> result.counts
        {'000':34, '111':66}
        >>> result.time_taken
        0.056
    

"""
from cunqa.logger import logger
from typing import Union, Optional
import numpy as np

class ResultError(Exception):
    """Exception for errors received from a simulation."""
    pass

class Result:
    """Describes the result of a simulation.

    Attributes:
        _result (dict): The raw dictionary output of the simulation.
        _id (str): The circuit identifier.
        _registers (dict): A dictionary specifying the classical registers
            defined for the circuit.
    """
    _result: dict
    _id: str
    _registers: dict
    
    def __init__(self, result: dict, circ_id: str, registers: dict):
        """Initializes the Result.

        Args:
            result: The dictionary given as the output of the simulation.
            circ_id: The circuit identifier.
            registers: A dictionary specifying the classical registers,
                necessary for correctly formatting the counts bitstrings.
        """
        self._result = {}
        self._id = circ_id
        self._registers = registers
        
        if not result:
            logger.error(f"Empty object passed, result is None. [{ValueError.__name__}].")
            raise ValueError
        elif "ERROR" in result:
            message = result["ERROR"]
            logger.error(f"Error during simulation. Check QPU availability, run arguments, and circuit syntax: {message}")
            raise ResultError
        else:
            self._result = result

    def __str__(self):
        """Returns a string representation of the result."""
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        GREEN = "\033[32m"
        return f"{YELLOW}{self._id}:{RESET} {{'counts': {self.counts}, \n\t 'time_taken': {GREEN}{self.time_taken} s{RESET}}}"

    @property
    def result(self) -> dict:
        """The raw output of the simulation."""
        return self._result
    
    @property
    def counts(self) -> dict:
        """The distribution of counts from the simulation sampling."""
        try:
            if "results" in self._result:
                counts = self._result["results"][0]["data"]["counts"]
            elif "counts" in self._result:
                counts = self._result["counts"]
            else:
                logger.error("Could not find 'counts' in the result.")
                raise ResultError
            
            if len(self._registers) > 1:
                counts = _convert_counts(counts, self._registers)
            return counts
        except Exception as error:
            logger.error(f"An error occurred with counts [{type(error).__name__}]: {error}.")
            raise

    @property
    def time_taken(self) -> str:
        """The time the simulation took, in seconds."""
        try:
            if "results" in self._result:
                return self._result["results"][0]["time_taken"]
            elif "time_taken" in self._result:
                return self._result["time_taken"]
            else:
                raise ResultError
        except Exception as error:
            logger.error(f"An error occurred with time_taken [{type(error).__name__}]: {error}.")
            raise

def _divide(string: str, lengths: "list[int]") -> str:
    """Divides a bitstring into groups of given lengths, separated by spaces.

    Args:
        string: The string to be divided.
        lengths: The lengths of the resulting substrings.

    Returns:
        A new string with groups separated by spaces.
    """
    parts = []
    init = 0
    try:
        if not lengths:
            return string
        for length in lengths:
            parts.append(string[init:init + length])
            init += length
        return ' '.join(parts)
    except Exception as error:
        logger.error(f"Failed to divide the string: [{type(error).__name__}].")
        raise SystemExit

def _convert_counts(counts: dict, registers: dict) -> dict:
    """Converts counts from hexadecimal to binary strings and divides the bitstrings.

    Args:
        counts: A dictionary of counts to be converted.
        registers: A dictionary of classical registers.

    Returns:
        A new counts dictionary with keys as binary strings, correctly
        separated by spaces according to the classical registers.
    """
    if not isinstance(registers, dict):
        logger.error(f"`registers` must be a dict, but {type(registers)} was provided. [TypeError].")
        raise ResultError
    
    lengths = [len(v) for v in registers.values()]
    logger.debug(f"Dividing strings into {len(lengths)} classical registers.")

    if not isinstance(counts, dict):
        logger.error(f"`counts` must be a dict, but {type(counts)} was provided. [TypeError].")
        raise ResultError
    
    return {_divide(k, lengths): v for k, v in counts.items()}

