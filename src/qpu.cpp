#include <string>
#include <iostream>

#include "utils/constants.hpp"
#include "qpu.hpp"
#include "logger.hpp"

using namespace std::string_literals;

namespace cunqa {

/**
 * @brief Constructs a new QPU object.
 *
 * Initializes the QPU with a specific backend, communication mode, name, and family.
 *
 * @param backend A unique pointer to a backend object that will perform the quantum simulations.
 * @param mode The communication mode for the server (e.g., "tcp", "ipc").
 * @param name The name assigned to this QPU instance.
 * @param family The family or group this QPU belongs to.
 */
QPU::QPU(std::unique_ptr<sim::Backend> backend, const std::string& mode, const std::string& name, const std::string& family) :
    backend{std::move(backend)},
    server{std::make_unique<comm::Server>(mode)},
    name_{name},
    family_{family}
{ }

/**
 * @brief Starts the QPU.
 *
 * This method launches two threads: one for receiving data and one for computing results.
 * It also writes the QPU's configuration to a file and then waits for the threads to complete.
 */
void QPU::turn_ON()
{
    std::thread listen([this](){this->recv_data_();});
    std::thread compute([this](){this->compute_result_();});

    JSON qpu_config = *this;
    write_on_file(qpu_config, constants::QPUS_FILEPATH, family_);

    //LOGGER_DEBUG("QPU info written");

    listen.join();
    compute.join();
}

/**
 * @brief Processes quantum tasks from the message queue.
 *
 * This method runs in a loop, waiting for tasks to appear in the message queue.
 * When a task is available, it processes it using the backend and sends the result
 * back to the client. It handles exceptions that may occur during the process.
 */
void QPU::compute_result_()
{
    QuantumTask quantum_task_;
    while (true)
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        queue_condition_.wait(lock, [this] { return !message_queue_.empty(); });

        while (!message_queue_.empty())
        {
            try {
                std::string message = message_queue_.front();
                message_queue_.pop();
                lock.unlock();
                
                quantum_task_.update_circuit(message);
                auto result = backend->execute(quantum_task_);
                server->send_result(result.dump());

            } catch(const comm::ServerException& e) {
                LOGGER_ERROR("An error occurred while sending the result, possibly due to a client-side issue.");
                LOGGER_ERROR("Error message: {}", e.what());
            } catch(const std::exception& e) {
                LOGGER_ERROR("An error occurred while sending the result, but the server will continue iterating.");
                LOGGER_ERROR("Error message: {}", e.what());
                server->send_result("{\"ERROR\":\""s + std::string(e.what()) + "\"}"s);
            }
            lock.lock();
        }
    }
}

/**
 * @brief Receives data from the client and places it in the message queue.
 *
 * This method runs in a loop, accepting client connections and receiving data.
 * Received messages are pushed to the message queue, and the condition variable is
 * notified. It handles a "CLOSE" message to re-accept connections.
 */
void QPU::recv_data_()
{
    server->accept();
    while (true) {
        try {
            auto message = server->recv_data();
                {
                std::lock_guard<std::mutex> lock(queue_mutex_);
                if (message.compare("CLOSE"s) == 0) {
                    server->accept();
                    continue;
                }
                else
                    message_queue_.push(message);
            }
            queue_condition_.notify_one();
        } catch (const std::exception& e) {
            LOGGER_INFO("An error occurred while receiving the circuit, but the server will continue iterating.");
            LOGGER_ERROR("Official error message: {}", e.what());
            throw;
        }
    }
}


} // End of cunqa namespace

