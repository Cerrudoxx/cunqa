
#include <string>
#include <queue>
#include <memory>
#include <algorithm>
#include <unordered_map>
#include "zmq.hpp"

#include "classical_channel/classical_channel.hpp"
#include "utils/helpers/net_functions.hpp"

#include "utils/json.hpp"
#include "logger.hpp"

namespace cunqa {
namespace comm {

/**
 * @struct ClassicalChannel::Impl
 * @brief Implementation of the ClassicalChannel class using ZeroMQ.
 *
 * This struct contains the private members and methods for the ZeroMQ-based
 * implementation of the classical channel. It manages the ZeroMQ context,
 * sockets, and message queues.
 */
struct ClassicalChannel::Impl
{
    std::string zmq_endpoint;
    std::string zmq_id;

    zmq::context_t zmq_context;
    std::unordered_map<std::string, zmq::socket_t> zmq_sockets;
    zmq::socket_t zmq_comm_server;
    std::unordered_map<std::string, std::queue<std::string>> message_queue;

    /**
     * @brief Constructs a new Impl object.
     * @param id The identifier for the channel.
     */
    Impl(const std::string& id)
    {
        auto IP = get_IP_address();
        zmq_endpoint = "tcp://" + IP + ":*";

        zmq::socket_t qpu_server_socket_(zmq_context, zmq::socket_type::router);
        qpu_server_socket_.bind(zmq_endpoint);
        
        char endpoint_buf[256];
        size_t sz = sizeof(endpoint_buf);
        zmq_getsockopt(qpu_server_socket_, ZMQ_LAST_ENDPOINT, endpoint_buf, &sz);
        zmq_endpoint = std::string(endpoint_buf);
        zmq_id = id.empty() ? zmq_endpoint : id;

        zmq_comm_server = std::move(qpu_server_socket_);
    }

    /**
     * @brief Default destructor for the Impl object.
     */
    ~Impl() = default;

    /**
     * @brief Connects to another endpoint.
     * @param endpoint The endpoint to connect to.
     * @param id An optional identifier for the connection.
     */
    void connect(const std::string& endpoint, const std::string& id = "")
    {   
        auto client_id = id.empty() ? endpoint : id;
        if (zmq_sockets.find(client_id) == zmq_sockets.end()) {
            zmq::socket_t tmp_client_socket(zmq_context, zmq::socket_type::dealer);
            tmp_client_socket.setsockopt(ZMQ_IDENTITY, zmq_id.c_str(), zmq_id.size());
            zmq_sockets[client_id] = std::move(tmp_client_socket);
            zmq_sockets[client_id].connect(endpoint);
        }
    }

    /**
     * @brief Connects to another endpoint, with an option to force the endpoint.
     * @param endpoint The endpoint to connect to.
     * @param force_endpoint A boolean indicating whether to force the endpoint.
     */
    void connect(const std::string& endpoint, const bool force_endpoint)
    {   
        if (zmq_sockets.find(endpoint) == zmq_sockets.end()) {
            zmq::socket_t tmp_client_socket(zmq_context, zmq::socket_type::dealer);
            std::string connexion_id = force_endpoint ? zmq_endpoint : zmq_id;
            tmp_client_socket.setsockopt(ZMQ_IDENTITY, connexion_id.c_str(), connexion_id.size());
            zmq_sockets[endpoint] = std::move(tmp_client_socket);
            zmq_sockets[endpoint].connect(endpoint);
        }
    }

    /**
     * @brief Sends data to a target.
     * @param data The data to send.
     * @param target The target to send the data to.
     */
    void send(const std::string& data, const std::string& target)
    {
        if (zmq_sockets.find(target) == zmq_sockets.end()) {
            LOGGER_ERROR("No connection established with endpoint {} while trying to send: {}", target, data);
            throw std::runtime_error("Error with endpoint connection.");
        }
        zmq::message_t message(data.begin(), data.end());

        LOGGER_DEBUG("Sending circuit to {}", target);
        zmq_sockets[target].send(message, zmq::send_flags::none);
    }
    
    /**
     * @brief Receives data from an origin.
     * @param origin The origin of the data.
     * @return The received data as a string.
     */
    std::string recv(const std::string& origin)
    {
        if (!message_queue[origin].empty()) {
            std::string stored_data = message_queue[origin].front();
            message_queue[origin].pop();
            return stored_data;
        } else {
            while (true) {
                zmq::message_t id;
                zmq::message_t message;
                
                LOGGER_DEBUG("{} is waiting to receive a circuit from {}", zmq_id, origin);
                zmq_comm_server.recv(id, zmq::recv_flags::none);
                zmq_comm_server.recv(message, zmq::recv_flags::none);
                std::string id_str(static_cast<char*>(id.data()), id.size());
                std::string data(static_cast<char*>(message.data()), message.size());

                if (id_str == origin) {
                    return data;
                } else {
                    message_queue[id_str].push(data);
                }
            }
        }
    }
};

ClassicalChannel::ClassicalChannel() : pimpl_{std::make_unique<Impl>("")}
{ 
    endpoint = pimpl_->zmq_endpoint;
}

ClassicalChannel::ClassicalChannel(const std::string& id) : pimpl_{std::make_unique<Impl>(id)}
{ 
    endpoint = pimpl_->zmq_endpoint;
}

ClassicalChannel::~ClassicalChannel() = default;

void ClassicalChannel::publish(const std::string& suffix)
{
    JSON communications_endpoint = {{"communications_endpoint", endpoint}};
    write_on_file(communications_endpoint, constants::COMM_FILEPATH, suffix);
}

void ClassicalChannel::connect(const std::string& endpoint, const std::string& id)
{
    pimpl_->connect(endpoint, id);
}

void ClassicalChannel::connect(const std::string& endpoint, const bool force_endpoint)
{
    pimpl_->connect(endpoint, force_endpoint);
}

void ClassicalChannel::connect(const std::vector<std::string>& endpoints, const bool force_endpoint)
{
    for (const auto& ep : endpoints) {
        pimpl_->connect(ep, force_endpoint);
    }
}

void ClassicalChannel::send_info(const std::string& data, const std::string& target) { pimpl_->send(data, target); }
std::string ClassicalChannel::recv_info(const std::string& origin) { return pimpl_->recv(origin); }

void ClassicalChannel::send_measure(const int& measurement, const std::string& target) { pimpl_->send(std::to_string(measurement), target); }
int ClassicalChannel::recv_measure(const std::string& origin) { return std::stoi(pimpl_->recv(origin)); }

} // End of comm namespace
} // End of cunqa namespace
