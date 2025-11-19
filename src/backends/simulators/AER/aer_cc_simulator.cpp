#include "aer_cc_simulator.hpp"
#include "aer_adapters/aer_computation_adapter.hpp"
#include "aer_adapters/aer_simulator_adapter.hpp"

namespace cunqa {
namespace sim {

/**
 * @brief Default constructor for the AerCCSimulator class.
 *
 * This constructor initializes the classical channel and publishes its endpoint.
 */
AerCCSimulator::AerCCSimulator()
{
    classical_channel.publish();
}

/**
 * @brief Constructs a new AerCCSimulator object with a group ID.
 *
 * This constructor initializes the classical channel with a group ID and publishes its endpoint.
 *
 * @param group_id The identifier for the group.
 */
AerCCSimulator::AerCCSimulator(const std::string& group_id)
{
    classical_channel.publish(group_id);
}

/**
 * @brief Executes a quantum task on a CCBackend using the Aer simulator.
 *
 * This method connects to other QPUs via the classical channel, creates an
 * AerComputationAdapter and an AerSimulatorAdapter, and then performs the
 * simulation. It handles both dynamic and non-dynamic circuits.
 *
 * @param backend The CCBackend to execute the task on.
 * @param quantum_task The quantum task to execute.
 * @return The result of the execution as a JSON object.
 */
JSON AerCCSimulator::execute(const CCBackend& backend, const QuantumTask& quantum_task)
{
    std::vector<std::string> connect_with = quantum_task.sending_to;
    classical_channel.connect(connect_with, false);

    AerComputationAdapter aer_ca(quantum_task);
    AerSimulatorAdapter aer_sa(aer_ca);
    if (quantum_task.is_dynamic) {
        return aer_sa.simulate(&classical_channel);
    } else {
        return aer_sa.simulate(&backend);
    }
}

} // End namespace sim
} // End namespace cunqa