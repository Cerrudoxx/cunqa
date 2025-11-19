#pragma once

#include "quantum_task.hpp"
#include "utils/json.hpp"

namespace cunqa {
namespace sim {

/**
 * @class SimulatorStrategy
 * @brief An abstract base class for simulator strategies.
 *
 * The SimulatorStrategy class defines the interface for different simulation
 * strategies that can be used by the backends. It is a template class that
 * allows for different types of backends to be used with the strategies.
 *
 * @tparam T The type of the backend that the strategy will be used with.
 */
template <typename T>
class SimulatorStrategy {
public:
    /**
     * @brief Virtual destructor for the SimulatorStrategy class.
     */
    virtual ~SimulatorStrategy() = default;

    /**
     * @brief Gets the name of the simulator strategy.
     *
     * This is a pure virtual function that must be implemented by derived classes.
     *
     * @return The name of the simulator strategy.
     */
    virtual inline std::string get_name() const = 0;

    /**
     * @brief Executes a quantum task on a given backend.
     *
     * This is a pure virtual function that must be implemented by derived classes.
     *
     * @param backend The backend to execute the task on.
     * @param circuit The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    virtual JSON execute(const T& backend, const QuantumTask& circuit) = 0;
};

} // End of sim namespace
} // End of cunqa namespace