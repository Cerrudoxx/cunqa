#pragma once

#include <string>
#include <thread>
#include <queue>
#include <atomic>
#include <condition_variable>

#include "comm/server.hpp"
#include "backends/backend.hpp"
#include "utils/json.hpp"

using namespace std::string_literals;

namespace cunqa {

/**
 * @class QPU
 * @brief Represents a Quantum Processing Unit (QPU) in the CUNQA simulator.
 *
 * The QPU class encapsulates the functionality of a quantum backend simulator
 * and a communication server. It is responsible for receiving quantum tasks,
 * processing them using the specified backend, and managing the communication
 * with the client.
 */
class QPU {
public:
    /**
     * @brief A unique pointer to the quantum backend simulator.
     *
     * This backend is responsible for executing the quantum circuits.
     */
    std::unique_ptr<sim::Backend> backend;

    /**
     * @brief A unique pointer to the communication server.
     *
     * This server handles the communication with the client, receiving
     * quantum tasks and sending back the results.
     */
    std::unique_ptr<comm::Server> server;

    /**
     * @brief Constructs a new QPU object.
     *
     * @param backend A unique pointer to a backend object that will perform the quantum simulations.
     * @param mode The communication mode for the server (e.g., "tcp", "ipc").
     * @param name The name assigned to this QPU instance.
     * @param family The family or group this QPU belongs to.
     */
    QPU(std::unique_ptr<sim::Backend> backend, const std::string& mode, const std::string& name, const std::string& family);

    /**
     * @brief Starts the QPU.
     *
     * This method initializes the server and starts the threads for receiving data
     * and computing results, effectively making the QPU ready to process tasks.
     */
    void turn_ON();

private:
    /**
     * @brief A queue to hold incoming messages (quantum tasks) from the client.
     */
    std::queue<std::string> message_queue_;

    /**
     * @brief A condition variable to signal when a new message is available in the queue.
     */
    std::condition_variable queue_condition_;

    /**
     * @brief A mutex to protect access to the message queue.
     */
    std::mutex queue_mutex_;

    /**
     * @brief The family or group this QPU belongs to.
     */
    std::string family_;

    /**
     * @brief The name assigned to this QPU instance.
     */
    std::string name_;

    /**
     * @brief Processes quantum tasks from the message queue.
     *
     * This method runs in a separate thread, waiting for tasks to appear in the
     * message queue, processing them using the backend, and sending the
     * results back to the client.
     */
    void compute_result_();

    /**
     * @brief Receives data from the client and places it in the message queue.
     *
     * This method runs in a separate thread, continuously listening for incoming
     * messages from the client and adding them to the message queue.
     */
    void recv_data_();

    /**
     * @brief Serializes the QPU object to a JSON object.
     * @param j The JSON object to serialize to.
     * @param obj The QPU object to serialize.
     */
    friend void to_json(JSON& j, const QPU& obj) {
        JSON backend_json = obj.backend->to_json();
        JSON server_json = *(obj.server);
        j = {
            {"backend", backend_json},
            {"net", server_json},
            {"name", obj.name_},
            {"family", obj.family_},
            {"slurm_job_id", std::getenv("SLURM_JOB_ID")}
        };
    }
};
        
} // End of cunqa namespace