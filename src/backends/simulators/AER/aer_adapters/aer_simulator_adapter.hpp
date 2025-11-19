#pragma once

#include <vector>

#include "quantum_task.hpp"
#include "classical_channel/classical_channel.hpp"
#include "backends/backend.hpp"
#include "aer_computation_adapter.hpp"

#include "utils/json.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerSimulatorAdapter
 * @brief An adapter class for simulating quantum computations using the Aer simulator.
 *
 * The AerSimulatorAdapter class provides an interface to the Aer simulator,
 * allowing for the execution of quantum computations defined in an
 * AerComputationAdapter. It supports simulation with or without a classical
 * channel for communication.
 */
class AerSimulatorAdapter
{
public:
    /**
     * @brief Default constructor for the AerSimulatorAdapter class.
     */
    AerSimulatorAdapter() = default;

    /**
     * @brief Constructs a new AerSimulatorAdapter object.
     * @param qc A reference to an AerComputationAdapter containing the quantum tasks to be simulated.
     */
    AerSimulatorAdapter(AerComputationAdapter& qc) : qc{qc} {}

    /**
     * @brief Simulates the quantum computation using a specific backend.
     * @param backend A pointer to the backend to be used for the simulation.
     * @return The results of the simulation as a JSON object.
     */
    JSON simulate(const Backend* backend);

    /**
     * @brief Simulates the quantum computation, optionally using a classical channel.
     * @param classical_channel A pointer to a classical channel for communication. Defaults to nullptr.
     * @return The results of the simulation as a JSON object.
     */
    JSON simulate(comm::ClassicalChannel* classical_channel = nullptr);

    AerComputationAdapter qc; ///< The AerComputationAdapter containing the quantum tasks.
};


} // End of sim namespace
} // End of cunqa namespace