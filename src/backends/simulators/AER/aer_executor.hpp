#pragma once

#include <string>
#include "classical_channel/classical_channel.hpp"

namespace cunqa {
namespace sim {

/**
 * @class AerExecutor
 * @brief A class responsible for executing quantum tasks in a distributed manner using the Aer simulator.
 *
 * The AerExecutor class manages the communication and execution of quantum tasks
 * that involve multiple QPUs. It uses a classical channel to communicate with
 * other executors and QPUs.
 */
class AerExecutor {
public:
    /**
     * @brief Default constructor for the AerExecutor class.
     */
    AerExecutor();

    /**
     * @brief Constructs a new AerExecutor object.
     * @param group_id The identifier for the group.
     */
    AerExecutor(const std::string& group_id);

    /**
     * @brief Default destructor for the AerExecutor class.
     */
    ~AerExecutor() = default;

    /**
     * @brief Starts the executor.
     *
     * This method runs the main loop of the executor, which listens for tasks,
     * executes them, and communicates with other nodes.
     */
    void run();

private:
    comm::ClassicalChannel classical_channel; ///< The classical channel for communication.
    std::vector<std::string> qpu_ids; ///< A list of QPU identifiers.
};

} // End of sim namespace
} // End of cunqa namespace