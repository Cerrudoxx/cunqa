#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <cstdlib>

#include "quantum_task.hpp"
#include "utils/json.hpp"
#include "utils/constants.hpp"

#include "logger.hpp"

namespace cunqa {

/**
 * @brief Converts a QuantumTask object to its string representation.
 *
 * This function serializes a QuantumTask object into a JSON string format.
 * If the circuit in the QuantumTask is empty, it returns an empty string.
 *
 * @param data The QuantumTask object to convert.
 * @return A string representation of the QuantumTask object.
 */
std::string to_string(const QuantumTask& data)
{
    if (data.circuit.empty())
        return "";
    std::string circ_str = "{\"id\": \"" + data.id + "\",\n\"config\": " + data.config.dump() + ",\n\"instructions\": " + data.circuit.dump() + ",\n\"sending_to\":[";

    bool first_target = true;
    for (const auto& target : data.sending_to) {
        if (!first_target) {
            circ_str += ", ";
        }
        first_target = false;
        circ_str += "\"" + target + "\"";
    }
    circ_str += "],\n\"is_dynamic\":";
    circ_str += data.is_dynamic ? "true}\n" : "false}\n";

    return circ_str;
}

/**
 * @brief Constructs a new QuantumTask object from a JSON string.
 *
 * This constructor initializes a QuantumTask object by parsing a JSON string.
 *
 * @param quantum_task A JSON string representing the quantum task.
 */
QuantumTask::QuantumTask(const std::string& quantum_task) { update_circuit(quantum_task); }

/**
 * @brief Updates the quantum circuit and related properties from a JSON string.
 *
 * This method parses a JSON string to update the circuit, configuration, and other
 * properties of the QuantumTask. It also handles classical communication details
 * by resolving QPU endpoints from a communications file.
 *
 * @param quantum_task A JSON string representing the new quantum task details.
 */
void QuantumTask::update_circuit(const std::string& quantum_task)
{
    auto quantum_task_json = quantum_task.empty() ? JSON() : JSON::parse(quantum_task);
    std::vector<std::string> no_communications = {};

    if (quantum_task_json.contains("instructions") && quantum_task_json.contains("config")) {
        circuit = quantum_task_json.at("instructions").get<std::vector<JSON>>();
        config = quantum_task_json.at("config").get<JSON>();
        sending_to = (quantum_task_json.contains("sending_to") ? quantum_task_json.at("sending_to").get<std::vector<std::string>>() : no_communications);
        is_dynamic = (quantum_task_json.contains("is_dynamic") ? quantum_task_json.at("is_dynamic").get<bool>() : false);
        has_cc = (quantum_task_json.contains("has_cc") ? quantum_task_json.at("has_cc").get<bool>() : false);
        id = quantum_task_json.at("id");

        if (has_cc) {
            std::ifstream communications_file(constants::COMM_FILEPATH);
            // TODO: Manage behavior when the file is not properly opened

            JSON communications;
            communications_file >> communications;

            for (auto& instruction : circuit) {
                if (instruction.contains("qpus")) {
                    std::vector<std::string> qpuid = instruction.at("qpus").get<std::vector<std::string>>();
                    JSON qpu_communications = communications.at(qpuid[0]).get<JSON>();
                    std::string communications_endpoint = qpu_communications.contains("executor_endpoint") ? qpu_communications.at("executor_endpoint").get<std::string>() : qpu_communications.at("communications_endpoint").get<std::string>();
                    instruction.at("qpus") = {communications_endpoint};
                }
            }
            std::vector<std::string> aux_connects_with = sending_to;
            int counter = 0;
            for (auto& qpuid : aux_connects_with) {
                JSON qpu = communications.at(qpuid).get<JSON>();
                sending_to[counter] = qpu.at("communications_endpoint").get<std::string>();
                counter++;
            }
        }

    } else if (quantum_task_json.contains("params"))
        update_params_(quantum_task_json.at("params"));
}

/**
 * @brief Updates the parameters of the quantum circuit.
 *
 * This method updates the parameters of the quantum gates in the circuit. It iterates
 * through the instructions and updates the parameters for gates that support them.
 *
 * @param params A vector of doubles representing the new parameters.
 * @throws std::runtime_error If the circuit is not set before calling this method or if an error occurs during the update.
 */
void QuantumTask::update_params_(const std::vector<double> params)
{
    if (circuit.empty())
        throw std::runtime_error("Circuit not sent before updating parameters.");

    try {
        int counter = 0;
        
        for (auto& instruction : circuit) {
            std::string name = instruction.at("name");
            switch (cunqa::constants::INSTRUCTIONS_MAP.at(name)) {
                // One parameter gates
                case cunqa::constants::RX:
                case cunqa::constants::RY:
                case cunqa::constants::RZ:
                    instruction.at("params")[0] = params[counter];
                    counter = counter + 1;
                    break;
                // Two parameter gates
                case cunqa::constants::R:
                    instruction.at("params")[0] = params[counter];
                    instruction.at("params")[1] = params[counter + 1];
                    counter = counter + 2;
                    break;
                // Three parameter gates
                case cunqa::constants::U:
                case cunqa::constants::CU:
                    instruction.at("params")[0] = params[counter];
                    instruction.at("params")[1] = params[counter + 1];
                    instruction.at("params")[2] = params[counter + 2];
                    counter = counter + 3;
                    break;
                default:
                    break;
            }
        }

    } catch (const std::exception& e) {
        LOGGER_ERROR("Error updating parameters. (check correct size).");
        throw std::runtime_error("Error updating parameters:" + std::string(e.what()));
    }
}

} // End of cunqa namespace