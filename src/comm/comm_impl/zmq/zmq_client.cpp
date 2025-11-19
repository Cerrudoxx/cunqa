#include "zmq.hpp"
#include <iostream>
#include <string>

#include "comm/client.hpp"
#include "logger.hpp"

namespace cunqa {
namespace comm {

/**
 * @struct Client::Impl
 * @brief Implementation of the Client class using ZeroMQ.
 *
 * This struct contains the private members and methods for the ZeroMQ-based
 * implementation of the client. It manages the ZeroMQ context and socket.
 */
struct Client::Impl {
    /**
     * @brief Constructs a new Impl object.
     */
    Impl() :
        socket_{context_, zmq::socket_type::client}
    { }

    /**
     * @brief Destructor for the Impl object.
     */
    ~Impl()
    {
        socket_.close();
    }

    /**
     * @brief Connects to a server endpoint.
     * @param endpoint The endpoint to connect to.
     */
    void connect(const std::string& endpoint)
    {
        try {
            socket_.connect(endpoint);
            LOGGER_DEBUG("Client successfully connected to server at {}.", endpoint);
        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Unable to connect to endpoint {}. Error: {}", endpoint, e.what());
        } catch (const std::exception& e) {
            LOGGER_ERROR("Error connecting to an external QPU node: {}", e.what());
            throw;
        }
    }

    /**
     * @brief Sends data to the server.
     * @param data The data to send.
     */
    void send(const std::string& data)
    {
        try {
            zmq::message_t message(data.begin(), data.end());
            socket_.send(message, zmq::send_flags::none);
            LOGGER_DEBUG("Circuit sent: {}", data);
        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Error sending the circuit: {}", e.what());
        }
    }

    /**
     * @brief Receives data from the server.
     * @return The received data as a string.
     */
    std::string recv()
    {
        try {
            zmq::message_t reply;
            auto size = socket_.recv(reply, zmq::recv_flags::none);
            std::string result(static_cast<char*>(reply.data()), size.value());
            LOGGER_DEBUG("Result correctly received: {}", result);
            return result;
        } catch (const zmq::error_t& e) {
            LOGGER_ERROR("Error receiving the result: {}", e.what());
        }

        return "{}";
    }

    /**
     * @brief Disconnects from the server.
     * @param endpoint The endpoint to disconnect from.
     */
    void disconnect(const std::string& endpoint)
    {
        if (!endpoint.empty()) {
            socket_.disconnect(endpoint);
        } else {
            socket_.close();
            socket_ = zmq::socket_t(context_, zmq::socket_type::client);
        }
    }

    zmq::context_t context_;
    zmq::socket_t socket_;
};

Client::Client() :
    pimpl_{std::make_unique<Impl>()}
{ }

Client::~Client() = default;

void Client::connect(const std::string& endpoint) {
    pimpl_->connect(endpoint);
}

FutureWrapper<Client> Client::send_circuit(const std::string& circuit)
{ 
    pimpl_->send(circuit);
    return FutureWrapper<Client>(this); 
}

FutureWrapper<Client> Client::send_parameters(const std::string& parameters)
{ 
    pimpl_->send(parameters);
    return FutureWrapper<Client>(this); 
}

std::string Client::recv_results() {
    return pimpl_->recv();
}

void Client::disconnect(const std::string& endpoint) {
    pimpl_->disconnect(endpoint);
}

} // End of comm namespace
} // End of cunqa namespace