#pragma once

#include <vector>
#include <string>
#include "utils/json.hpp"

namespace cunqa {

/**
 * @class QuantumTask
 * @brief Represents a quantum task to be executed by a QPU.
 *
 * The QuantumTask class encapsulates all the information needed to execute a
 * quantum circuit, including the circuit itself, configuration options, and
 * metadata such as whether the circuit is dynamic or involves classical
 * communication.
 */
class QuantumTask {
public:
    /**
     * @brief The quantum circuit to be executed, represented as a JSON object.
     */
    JSON circuit;

    /**
     * @brief Configuration options for the quantum task, represented as a JSON object.
     */
    JSON config;

    /**
     * @brief A list of destination identifiers for the task's output.
     */
    std::vector<std::string> sending_to;

    /**
     * @brief A flag indicating whether the circuit is dynamic (contains c_if gates or classical communication).
     */
    bool is_dynamic = false;

    /**
     * @brief A flag indicating whether the circuit involves classical communication.
     */
    bool has_cc = false;

    /**
     * @brief The unique identifier for the quantum task.
     */
    std::string id;

    /**
     * @brief Default constructor for the QuantumTask class.
     */
    QuantumTask() = default;

    /**
     * @brief Constructs a new QuantumTask object from a JSON string.
     * @param quantum_task A JSON string representing the quantum task.
     */
    QuantumTask(const std::string& quantum_task);

    /**
     * @brief Constructs a new QuantumTask object from JSON objects for the circuit and config.
     * @param circuit The quantum circuit.
     * @param config The configuration for the task.
     */
    QuantumTask(const JSON& circuit, const JSON& config): circuit(circuit), config(config) {};

    /**
     * @brief Updates the quantum circuit and related properties from a JSON string.
     * @param quantum_task A JSON string representing the new quantum task details.
     */
    void update_circuit(const std::string& quantum_task);
    
private:
    /**
     * @brief Updates the parameters of the quantum circuit.
     * @param params A vector of doubles representing the new parameters.
     */
    void update_params_(const std::vector<double> params);
};

/**
 * @brief Converts a QuantumTask object to its string representation.
 * @param data The QuantumTask object to convert.
 * @return A string representation of the QuantumTask object.
 */
std::string to_string(const QuantumTask& data);

} // End of cunqa namespace