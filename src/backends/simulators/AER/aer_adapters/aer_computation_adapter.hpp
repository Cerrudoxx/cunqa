#pragma once

#include "quantum_task.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerComputationAdapter
 * @brief An adapter class for managing quantum computations for the Aer simulator.
 *
 * The AerComputationAdapter class encapsulates a collection of quantum tasks
 * that are to be executed by the Aer simulator. It provides constructors for
 * creating an adapter from a single quantum task or a vector of them.
 */
class AerComputationAdapter
{
public:
    /**
     * @brief Default constructor for the AerComputationAdapter class.
     */
    AerComputationAdapter() = default;

    /**
     * @brief Constructs a new AerComputationAdapter object from a single quantum task.
     * @param quantum_task The quantum task to be included in the adapter.
     */
    AerComputationAdapter(const QuantumTask& quantum_task) :
        quantum_tasks{quantum_task}
    { }

    /**
     * @brief Constructs a new AerComputationAdapter object from a vector of quantum tasks.
     * @param quantum_tasks The vector of quantum tasks to be included in the adapter.
     */
    AerComputationAdapter(const std::vector<QuantumTask>& quantum_tasks) :
        quantum_tasks{quantum_tasks}
    { }

    std::vector<QuantumTask> quantum_tasks; ///< A vector of quantum tasks.
};


} // End of sim namespace
} // End of cunqa namespace