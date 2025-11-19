#pragma once

#include <string>
#include <vector>
#include <memory>

namespace cunqa {
namespace comm {

/**
 * @class ClassicalChannel
 * @brief Manages classical communication between different components of the simulator.
 *
 * The ClassicalChannel class provides an interface for sending and receiving
 * information and measurements between different nodes in a distributed quantum
 * computation. It uses the pimpl idiom to hide implementation details.
 */
class ClassicalChannel {
public:
    std::string endpoint; ///< The endpoint of the classical channel.

    /**
     * @brief Default constructor for the ClassicalChannel class.
     */
    ClassicalChannel();

    /**
     * @brief Constructs a new ClassicalChannel object with a specific identifier.
     * @param id The identifier for the channel.
     */
    ClassicalChannel(const std::string& id);

    /**
     * @brief Destructor for the ClassicalChannel class.
     */
    ~ClassicalChannel();

    /**
     * @brief Publishes the endpoint of the channel.
     * @param suffix An optional suffix to append to the endpoint.
     */
    void publish(const std::string& suffix = "");

    /**
     * @brief Connects to another endpoint.
     * @param endpoint The endpoint to connect to.
     * @param id An optional identifier for the connection.
     */
    void connect(const std::string& endpoint, const std::string& id = "");

    /**
     * @brief Connects to another endpoint, with an option to force the endpoint.
     * @param endpoint The endpoint to connect to.
     * @param force_endpoint A boolean indicating whether to force the endpoint.
     */
    void connect(const std::string& endpoint, const bool force_endpoint);

    /**
     * @brief Connects to multiple endpoints.
     * @param endpoints A vector of endpoints to connect to.
     * @param force_endpoint A boolean indicating whether to force the endpoints.
     */
    void connect(const std::vector<std::string>& endpoints, const bool force_endpoint);

    /**
     * @brief Sends information to a target.
     * @param data The data to send.
     * @param target The target to send the data to.
     */
    void send_info(const std::string& data, const std::string& target);

    /**
     * @brief Receives information from an origin.
     * @param origin The origin of the information.
     * @return The received information as a string.
     */
    std::string recv_info(const std::string& origin);

    /**
     * @brief Sends a measurement to a target.
     * @param measurement The measurement to send.
     * @param target The target to send the measurement to.
     */
    void send_measure(const int& measurement, const std::string& target);

    /**
     * @brief Receives a measurement from an origin.
     * @param origin The origin of the measurement.
     * @return The received measurement as an integer.
     */
    int recv_measure(const std::string& origin);
    
private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};  

} // End of comm namespace
} // End of cunqa namespace