#pragma once

#include <iostream>
#include <memory>
#include <queue>
#include <string>

#include "backends/simple_backend.hpp"
#include "utils/json.hpp"

namespace cunqa {
namespace comm {

/**
 * @class ServerException
 * @brief An exception class for server-related errors.
 */
class ServerException : public std::exception {
    std::string message;
public:
    /**
     * @brief Constructs a new ServerException object.
     * @param msg The error message.
     */
    explicit ServerException(const std::string& msg) : message(msg) { }

    /**
     * @brief Gets the error message.
     * @return A C-style string containing the error message.
     */
    const char* what() const noexcept override {
        return message.c_str();
    }
};

/**
 * @class Server
 * @brief A class representing a server for communication.
 *
 * The Server class manages the communication with clients, allowing for
 * receiving data and sending results. It uses the pimpl idiom to hide
 * implementation details.
 */
class Server {
public:
    std::string mode; ///< The communication mode (e.g., "tcp", "ipc").
    std::string nodename; ///< The name of the node where the server is running.
    std::string endpoint; ///< The endpoint of the server.

    /**
     * @brief Constructs a new Server object.
     * @param mode The communication mode.
     */
    Server(const std::string& mode);

    /**
     * @brief Destructor for the Server class.
     */
    ~Server();

    /**
     * @brief Accepts a new client connection.
     */
    void accept();

    /**
     * @brief Receives data from a client.
     * @return The received data as a string.
     */
    std::string recv_data();

    /**
     * @brief Sends a result to a client.
     * @param result The result to send.
     */
    void send_result(const std::string& result);

    /**
     * @brief Closes the server connection.
     */
    void close();

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;

    /**
     * @brief Serializes a Server object to a JSON object.
     * @param j The JSON object to serialize to.
     * @param obj The Server object to serialize.
     */
    friend void to_json(JSON& j, const Server& obj) {
        j = {   
            {"mode", obj.mode}, 
            {"nodename", obj.nodename}, 
            {"endpoint", obj.endpoint}
        };
    }

    /**
     * @brief Deserializes a Server object from a JSON object.
     * @param j The JSON object to deserialize from.
     * @param obj The Server object to deserialize to.
     */
    friend void from_json(const JSON& j, Server& obj) {
        j.at("mode").get_to(obj.mode);
        j.at("nodename").get_to(obj.nodename);
        j.at("endpoint").get_to(obj.endpoint);
    }
};

} // End of comm namespace
} // End of cunqa namespace

