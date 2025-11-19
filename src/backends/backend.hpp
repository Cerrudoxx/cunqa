#pragma once

#include <string>
#include <iostream>
#include <fstream>
#include <memory>
#include <optional>

#include "quantum_task.hpp"

#include "utils/json.hpp"

namespace cunqa {
namespace sim {

/**
 * @class Backend
 * @brief An abstract base class for quantum backend simulators.
 *
 * The Backend class defines the interface for all quantum backends in the CUNQA
 * simulator. It provides a common interface for executing quantum tasks and
 * serializing the backend's configuration to JSON.
 */
class Backend {
public:
    /**
     * @brief Virtual destructor for the Backend class.
     */
    virtual ~Backend() = default;

    /**
     * @brief Executes a quantum task.
     *
     * This is a pure virtual function that must be implemented by derived classes.
     * It takes a QuantumTask object and returns the result of the execution as a
     * JSON object.
     *
     * @param quantum_task The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    virtual inline JSON execute(const QuantumTask& quantum_task) const = 0;

    /**
     * @brief Serializes the backend's configuration to a JSON object.
     *
     * This is a pure virtual function that must be implemented by derived classes.
     *
     * @return The backend's configuration as a JSON object.
     */
    virtual JSON to_json() const = 0;

    /**
     * @brief The configuration of the backend, represented as a JSON object.
     */
    JSON config;
};

} // End of sim namespace
} // End of cunqa namespace