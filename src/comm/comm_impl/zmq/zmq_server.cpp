#include "zmq.hpp"

#include "comm/server.hpp"
#include "logger.hpp"
#include "utils/helpers/net_functions.hpp"

namespace cunqa {
namespace comm {

/**
 * @struct Server::Impl
 * @brief Implementation of the Server class using ZeroMQ.
 *
 * This struct contains the private members and methods for the ZeroMQ-based
 * implementation of the server. It manages the ZeroMQ context, socket, and
 * routing ID queue.
 */
struct Server::Impl {
    zmq::context_t context_;
    zmq::socket_t socket_;
    std::queue<uint32_t> rid_queue_;

    std::string zmq_endpoint;

    /**
     * @brief Constructs a new Impl object.
     * @param mode The communication mode.
     */
    Impl(const std::string& mode) :
        socket_{context_, zmq::socket_type::server}
    {
        try {
            std::string ip = (mode == "hpc" ? "127.0.0.1" : get_IP_address());
            socket_.bind("tcp://" + ip + ":*");
            
            char endpoint_buf[256];
            size_t sz = sizeof(endpoint_buf);
            zmq_getsockopt(socket_, ZMQ_LAST_ENDPOINT, endpoint_buf, &sz);
            zmq_endpoint = std::string(endpoint_buf);
            LOGGER_DEBUG("Server bound to {}", zmq_endpoint);

        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Error binding to endpoint: {}", e.what());
            throw;
        }
    }

    /**
     * @brief Receives data from a client.
     * @return The received data as a string.
     */
    std::string recv()
    { 
        try {
            zmq::message_t message;
            auto size = socket_.recv(message, zmq::recv_flags::none);
            std::string data(static_cast<char*>(message.data()), size.value());
            
            rid_queue_.push(message.routing_id());
            return data;
        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Error receiving data: {}", e.what());
            return "CLOSE";
        }
    }

    /**
     * @brief Sends data to a client.
     * @param result The data to send.
     */
    void send(const std::string& result)
    {
        try {
            zmq::message_t message(result.begin(), result.end());
            message.set_routing_id(rid_queue_.front());
            rid_queue_.pop();
            
            socket_.send(message, zmq::send_flags::none);
        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Error sending result: {}", e.what());
            throw;
        }
    }

    /**
     * @brief Closes the server socket.
     */
    void close()
    {
        socket_.close();
    }
};

Server::Server(const std::string& mode) :
    mode{mode},
    nodename{get_nodename()},
    pimpl_{std::make_unique<Impl>(mode)}
{ 
    endpoint = pimpl_->zmq_endpoint;
}

Server::~Server() = default;

void Server::accept()
{
    // ZMQ does not need to accept connections like Asio.
}

std::string Server::recv_data()
{ 
    return pimpl_->recv();
}

void Server::send_result(const std::string& result)
{ 
    try {
        pimpl_->send(result);
    } catch (const std::exception& e) {
        throw ServerException(e.what());
    }
}

void Server::close()
{
    pimpl_->close();
}

} // End of comm namespace
} // End of cunqa namespace
