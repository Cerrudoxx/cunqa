#include "aer_simple_simulator.hpp"
#include "aer_adapters/aer_computation_adapter.hpp"
#include "aer_adapters/aer_simulator_adapter.hpp"

namespace cunqa {
namespace sim {

/**
 * @brief Destructor for the AerSimpleSimulator class.
 */
AerSimpleSimulator::~AerSimpleSimulator() = default;

/**
 * @brief Executes a quantum task on a SimpleBackend using the Aer simulator.
 *
 * This method creates an AerComputationAdapter and an AerSimulatorAdapter to
 * perform the simulation. It checks if the quantum task is dynamic and calls
 * the appropriate simulate method on the AerSimulatorAdapter.
 *
 * @param backend The SimpleBackend to execute the task on.
 * @param quantum_task The quantum task to execute.
 * @return The result of the execution as a JSON object.
 */
JSON AerSimpleSimulator::execute(const SimpleBackend& backend, const QuantumTask& quantum_task)
{
    AerComputationAdapter aer_ca(quantum_task);
    AerSimulatorAdapter aer_sa(aer_ca);

    if (quantum_task.is_dynamic)
        return aer_sa.simulate();
    else
        return aer_sa.simulate(&backend);
}

} // End namespace sim
} // End namespace cunqa