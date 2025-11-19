#pragma once

#include <iostream>
#include <fstream>
#include <string_view>
#include <memory>

namespace cunqa {
namespace comm {

/**
 * @class FutureWrapper
 * @brief A wrapper class for handling asynchronous results from a client.
 *
 * The FutureWrapper class provides a future-like interface for retrieving
 * results from a client. It allows for blocking until the result is available.
 *
 * @tparam T The type of the client.
 */
template <typename T>
class FutureWrapper {
public:
    /**
     * @brief Constructs a new FutureWrapper object.
     * @param client A pointer to the client.
     */
    FutureWrapper(T* client) : client_{client} {};

    /**
     * @brief Gets the result, blocking until it is available.
     * @return The result as a string.
     */
    inline std::string get() { return client_->recv_results(); };

    /**
     * @brief Checks if the future is valid.
     * @return Always returns true.
     */
    inline bool valid() { return true; };

private:
    T* client_;
};

/**
 * @class Client
 * @brief A class representing a client for communication.
 *
 * The Client class manages the communication with a server, allowing for
 * sending circuits and parameters and receiving results. It uses the pimpl
 * idiom to hide implementation details.
 */
class Client {
public:
    /**
     * @brief Default constructor for the Client class.
     */
    Client();

    /**
     * @brief Destructor for the Client class.
     */
    ~Client();

    /**
     * @brief Connects to a server endpoint.
     * @param endpoint The endpoint to connect to.
     */
    void connect(const std::string& endpoint);

    /**
     * @brief Sends a circuit to the server.
     * @param circuit The circuit to send.
     * @return a FutureWrapper for retrieving the result.
     */
    FutureWrapper<Client> send_circuit(const std::string& circuit);

    /**
     * @brief Sends parameters to the server.
     * @param parameters The parameters to send.
     * @return a FutureWrapper for retrieving the result.
     */
    FutureWrapper<Client> send_parameters(const std::string& parameters);

    /**
     * @brief Receives results from the server.
     * @return The received results as a string.
     */
    std::string recv_results();

    /**
     * @brief Disconnects from the server.
     * @param endpoint The endpoint to disconnect from.
     */
    void disconnect(const std::string& endpoint = "");

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // End of comm namespace
} // End of cunqa namespace