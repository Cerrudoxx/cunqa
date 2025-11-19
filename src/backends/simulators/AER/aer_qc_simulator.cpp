#include "aer_qc_simulator.hpp"

#include <string>
#include <cstdlib>
#include <sys/file.h>
#include <unistd.h>

namespace cunqa {
namespace sim {

/**
 * @brief Default constructor for the AerQCSimulator class.
 *
 * This constructor initializes the classical channel, publishes its endpoint,
 * receives the executor's endpoint, connects to it, and writes the endpoint to a file.
 */
AerQCSimulator::AerQCSimulator()
{
    classical_channel.publish();
    auto executor_endpoint = classical_channel.recv_info("executor");
    std::string id_ = "executor";
    classical_channel.connect(executor_endpoint, id_);
    write_executor_endpoint(executor_endpoint);
}

/**
 * @brief Constructs a new AerQCSimulator object with a group ID.
 *
 * This constructor initializes the classical channel with a group ID, publishes its
 * endpoint, receives the executor's endpoint, connects to it, and writes the
 * endpoint to a file.
 *
 * @param group_id The identifier for the group.
 */
AerQCSimulator::AerQCSimulator(const std::string& group_id)
{
    classical_channel.publish(group_id);
    auto executor_endpoint = classical_channel.recv_info("executor");
    std::string id_ = "executor";
    classical_channel.connect(executor_endpoint, id_);
    write_executor_endpoint(executor_endpoint, group_id);
}

/**
 * @brief Executes a quantum task on a QCBackend using the Aer simulator.
 *
 * This method converts the quantum task to a string, sends it to the executor
 * via the classical channel, waits for the results, and returns them as a JSON object.
 *
 * @param backend The QCBackend to execute the task on.
 * @param quantum_task The quantum task to execute.
 * @return The result of the execution as a JSON object.
 */
JSON AerQCSimulator::execute([[maybe_unused]] const QCBackend& backend, const QuantumTask& quantum_task)
{
    auto circuit = to_string(quantum_task);
    LOGGER_DEBUG("Sending circuit to executor: {}", circuit);

    classical_channel.send_info(circuit, "executor");
    if (!circuit.empty()) {
        auto results = classical_channel.recv_info("executor");
        return JSON::parse(results);
    }
    return JSON();
}

/**
 * @brief Writes the executor endpoint to a file.
 *
 * This method opens a file, acquires a lock, reads the existing JSON content,
 * adds the new executor endpoint, and writes the updated JSON back to the file.
 *
 * @param endpoint The endpoint to write.
 * @param group_id The identifier for the group.
 * @throws std::runtime_error If an error occurs while writing to the file.
 */
void AerQCSimulator::write_executor_endpoint(const std::string endpoint, const std::string& group_id)
{
    try {
        int file = open(constants::COMM_FILEPATH.c_str(), O_RDWR | O_CREAT, 0666);
        if (file == -1) {
            std::cerr << "Error opening the file" << std::endl;
            return;
        }
        flock(file, LOCK_EX);

        JSON j;
        std::ifstream file_in(constants::COMM_FILEPATH);

        if (file_in.peek() != std::ifstream::traits_type::eof())
            file_in >> j;
        file_in.close();

        // These two SLURM variables form the ID of the process
        std::string local_id = std::getenv("SLURM_TASK_PID");
        std::string job_id = std::getenv("SLURM_JOB_ID");
        auto task_id = (group_id.empty()) ? job_id + "_" + local_id : job_id + "_" + local_id + "_" + group_id;
        
        j[task_id]["executor_endpoint"] = endpoint;

        std::ofstream file_out(constants::COMM_FILEPATH, std::ios::trunc);
        file_out << j.dump(4);
        file_out.close();

        flock(file, LOCK_UN);
        close(file);
    } catch(const std::exception& e) {
        std::string msg("Error writing JSON simultaneously using locks.\nSystem error message: ");
        throw std::runtime_error(msg + e.what());
    }
}

} // End namespace sim
} // End namespace cunqa