#include <fstream>
#include <iostream>
#include <thread>
#include <chrono>

#include "aer_adapters/aer_simulator_adapter.hpp"
#include "aer_adapters/aer_computation_adapter.hpp"
#include "quantum_task.hpp"
#include "aer_executor.hpp"

#include "utils/constants.hpp"
#include "utils/json.hpp"
#include "logger.hpp"

namespace cunqa {
namespace sim {

/**
 * @brief Default constructor for the AerExecutor class.
 *
 * This constructor initializes the classical channel, reads the communications
 * file to find the QPU endpoints, connects to them, and sends its own endpoint.
 *
 * @throws std::runtime_error If the communications file cannot be opened.
 */
AerExecutor::AerExecutor() : classical_channel{"executor"}
{
    std::ifstream in(constants::COMM_FILEPATH);

    if (!in.is_open()) {
        throw std::runtime_error("Error opening the communications file.");
    }

    JSON j;
    if (in.peek() != std::ifstream::traits_type::eof())
        in >> j;
    in.close();

    std::string job_id = std::getenv("SLURM_JOB_ID");

    for (const auto& [key, value]: j.items()) {
        if (key.rfind(job_id, 0) == 0) {
            auto qpu_endpoint = value["communications_endpoint"].get<std::string>();
            qpu_ids.push_back(qpu_endpoint);
            classical_channel.connect(qpu_endpoint);
            classical_channel.send_info(classical_channel.endpoint, qpu_endpoint);
        }
    }
}

/**
 * @brief Constructs a new AerExecutor object with a group ID.
 *
 * This constructor initializes the classical channel, reads the communications
 * file to find the QPU endpoints for a specific group, connects to them, and
 * sends its own endpoint.
 *
 * @param group_id The identifier for the group.
 * @throws std::runtime_error If the communications file cannot be opened.
 */
AerExecutor::AerExecutor(const std::string& group_id) : classical_channel{"executor"}
{
    std::ifstream in(constants::COMM_FILEPATH);

    if (!in.is_open()) {
        throw std::runtime_error("Error opening the communications file.");
    }

    JSON j;
    if (in.peek() != std::ifstream::traits_type::eof())
        in >> j;
    in.close();

    for (const auto& [key, value]: j.items()) {
        if (key.rfind(group_id) == key.size() - group_id.size()) {
            auto qpu_endpoint = value["communications_endpoint"].get<std::string>();
            qpu_ids.push_back(qpu_endpoint);
            classical_channel.connect(qpu_endpoint);
            classical_channel.send_info(classical_channel.endpoint, qpu_endpoint);
        }
    }
}

/**
 * @brief Starts the executor.
 *
 * This method runs the main loop of the executor. It continuously listens for
 * quantum tasks from the QPUs, collects them, executes them using the Aer
 * simulator, and sends the results back to the respective QPUs.
 */
void AerExecutor::run()
{
    std::vector<QuantumTask> quantum_tasks;
    std::vector<std::string> qpus_working;
    std::string message;

    while (true) {
        for (const auto& qpu_id : qpu_ids) {
            LOGGER_DEBUG("Waiting for a message from: {}", qpu_id);
            message = classical_channel.recv_info(qpu_id);
            LOGGER_DEBUG("Received message: {}", message);

            if (!message.empty()) {
                qpus_working.push_back(qpu_id);
                quantum_tasks.emplace_back(message);
            }
        }

        AerComputationAdapter qc(quantum_tasks);
        AerSimulatorAdapter aer_sa(qc);
        auto result = aer_sa.simulate(&classical_channel);

        // TODO: Transform results to provide each QPU with its specific results.
        std::string result_str = result.dump();

        for (const auto& qpu : qpus_working) {
            classical_channel.send_info(result_str, qpu);
        }

        qpus_working.clear();
        quantum_tasks.clear();
    }
}

} // End of sim namespace
} // End of cunqa namespace