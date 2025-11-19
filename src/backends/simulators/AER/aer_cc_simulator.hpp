#pragma once

#include "quantum_task.hpp"
#include "backends/cc_backend.hpp"
#include "backends/simulators/simulator_strategy.hpp"
#include "classical_channel/classical_channel.hpp"

#include "utils/json.hpp"
#include "logger.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerCCSimulator
 * @brief A final class representing a classical communication simulator based on Aer.
 *
 * This class inherits from the SimulatorStrategy interface and provides a concrete
 * implementation of a simulator that supports classical communication using the Aer
 * backend. It manages a classical channel for communication.
 */
class AerCCSimulator final : public SimulatorStrategy<CCBackend> {
public:
    /**
     * @brief Default constructor for the AerCCSimulator class.
     */
    AerCCSimulator();

    /**
     * @brief Constructs a new AerCCSimulator object.
     * @param group_id The identifier for the group.
     */
    AerCCSimulator(const std::string& group_id);

    /**
     * @brief Default destructor for the AerCCSimulator class.
     */
    ~AerCCSimulator() = default;

    /**
     * @brief Gets the name of the simulator.
     * @return The name of the simulator, "AerSimulator".
     */
    inline std::string get_name() const override { return "AerSimulator"; }

    /**
     * @brief Executes a quantum task on a CCBackend using the Aer simulator.
     * @param backend The CCBackend to execute the task on.
     * @param circuit The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    JSON execute(const CCBackend& backend, const QuantumTask& circuit) override;

private:
    comm::ClassicalChannel classical_channel; ///< The classical channel for communication.
};


} // End namespace sim
} // End namespace cunqa