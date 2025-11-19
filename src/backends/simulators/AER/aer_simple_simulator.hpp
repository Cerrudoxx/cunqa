#pragma once

#include "quantum_task.hpp"
#include "backends/simple_backend.hpp"
#include "backends/simulators/simulator_strategy.hpp"

#include "utils/json.hpp"
#include "logger.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerSimpleSimulator
 * @brief A final class representing a simple simulator based on the Aer simulator.
 *
 * This class inherits from the SimulatorStrategy interface and provides a concrete
 * implementation of a simple simulator using the Aer backend.
 */
class AerSimpleSimulator final : public SimulatorStrategy<SimpleBackend> {
public:
    /**
     * @brief Default constructor for the AerSimpleSimulator class.
     */
    AerSimpleSimulator() = default;

    /**
     * @brief Constructs a new AerSimpleSimulator object.
     * @param group_id The identifier for the group.
     */
    AerSimpleSimulator(const std::string& group_id) {};

    /**
     * @brief Destructor for the AerSimpleSimulator class.
     */
    ~AerSimpleSimulator() override;

    /**
     * @brief Gets the name of the simulator.
     * @return The name of the simulator, "AerSimulator".
     */
    inline std::string get_name() const override { return "AerSimulator"; }

    /**
     * @brief Executes a quantum task on a SimpleBackend using the Aer simulator.
     * @param backend The SimpleBackend to execute the task on.
     * @param circuit The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    JSON execute(const SimpleBackend& backend, const QuantumTask& circuit) override;
};

} // End of sim namespace
} // End of cunqa namespace