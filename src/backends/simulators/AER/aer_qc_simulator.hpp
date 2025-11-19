#pragma once

#include "quantum_task.hpp"
#include "backends/qc_backend.hpp"
#include "backends/simulators/simulator_strategy.hpp"
#include "classical_channel/classical_channel.hpp"

#include "utils/json.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerQCSimulator
 * @brief A final class representing a quantum circuit simulator with quantum communication capabilities based on Aer.
 *
 * This class inherits from the SimulatorStrategy interface and provides a concrete
 * implementation of a simulator that supports quantum communication using the Aer
 * backend. It manages a classical channel for communication.
 */
class AerQCSimulator final : public SimulatorStrategy<QCBackend> {
public:
    /**
     * @brief Default constructor for the AerQCSimulator class.
     */
    AerQCSimulator();

    /**
     * @brief Constructs a new AerQCSimulator object.
     * @param group_id The identifier for the group.
     */
    AerQCSimulator(const std::string& group_id);

    /**
     * @brief Default destructor for the AerQCSimulator class.
     */
    ~AerQCSimulator() = default;

    /**
     * @brief Gets the name of the simulator.
     * @return The name of the simulator, "AerQCSimulator".
     */
    inline std::string get_name() const override { return "AerQCSimulator"; }

    /**
     * @brief Executes a quantum task on a QCBackend using the Aer simulator.
     * @param backend The QCBackend to execute the task on.
     * @param circuit The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    JSON execute([[maybe_unused]] const QCBackend& backend, const QuantumTask& circuit) override;

private:
    /**
     * @brief Writes the executor endpoint to a file.
     * @param endpoint The endpoint to write.
     * @param group_id The identifier for the group.
     */
    void write_executor_endpoint(const std::string endpoint, const std::string& group_id = "");

    comm::ClassicalChannel classical_channel; ///< The classical channel for communication.
};

} // End namespace sim
} // End namespace cunqa