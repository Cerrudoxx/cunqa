#pragma once

#include <regex>
#include <string>
#include <bitset>
#include <chrono>
#include <vector>

#include "utils/helpers/reverse_bitstring.hpp"

#include "logger.hpp"

using namespace std::string_literals;
using namespace AER;

namespace cunqa {
namespace sim {

/**
 * @brief Converts a QuantumTask object to a format compatible with the AER simulator.
 *
 * This function takes a QuantumTask object and modifies its configuration and
 * circuit to be compatible with the AER simulator. It adjusts the configuration
 * options and replaces "clbits" with "memory" in the circuit instructions.
 *
 * @param quantum_task The QuantumTask object to convert.
 * @return A new QuantumTask object compatible with the AER simulator.
 */
QuantumTask quantum_task_to_AER(const QuantumTask& quantum_task)
{
    JSON new_config = {
        {"method", quantum_task.config.at("method")},
        {"shots", quantum_task.config.at("shots")},
        {"memory_slots", quantum_task.config.at("num_clbits")},
        // TODO: Tune the different options of the AER simulator
    };

    if (quantum_task.config.contains("parallel_shots")) {
        new_config["_parallel_shots"] = quantum_task.config.at("parallel_shots").get<int>();
    }

    if (quantum_task.config.at("avoid_parallelization").get<bool>()) {
        LOGGER_DEBUG("Thread parallelization canceled");
        new_config["max_parallel_threads"] = 1;
    }

    // JSON Object because if not it generates an array
    JSON new_circuit = {
        {"config", new_config},
        {"instructions", JSON::parse(std::regex_replace(quantum_task.circuit.dump(),
                       std::regex("clbits"), "memory"))}
    };

    return QuantumTask(new_circuit, new_config);
}

/**
 * @brief Converts the standard results from the Aer simulator to the desired format.
 *
 * This function takes a JSON object containing the results from an Aer simulator
 * execution and converts the hexadecimal keys in the "counts" data to binary
 * strings, matching the Qiskit/AER convention.
 *
 * @param res The JSON object containing the results to convert.
 * @param num_clbits The number of classical bits.
 */
void convert_standard_results_Aer(JSON& res, const int& num_clbits)
{
    JSON counts = res.at("results")[0].at("data").at("counts").get<JSON>();
    JSON modified_counts;

    for (const auto& [key, inner] : counts.items()) {
        // Remove "0x" prefix if present
        std::string hex_key = key;
        if (hex_key.rfind("0x", 0) == 0) {
            hex_key = hex_key.substr(2);
        }

        // Use std::bitset<100> for binary conversion (supports up to 100 bits)
        std::bitset<100> bits(0);
        size_t hex_len = hex_key.length();

        // Convert hex to binary manually
        for (size_t i = 0; i < hex_len; ++i) {
            char c = hex_key[hex_len - 1 - i];
            int value = 0;
            if (c >= '0' && c <= '9') value = c - '0';
            else if (c >= 'a' && c <= 'f') value = 10 + (c - 'a');
            else if (c >= 'A' && c <= 'F') value = 10 + (c - 'A');
            for (int j = 0; j < 4; ++j) {
                if ((value >> j) & 1) {
                    size_t bit_pos = i * 4 + j;
                    if (bit_pos < 100) bits.set(bit_pos);
                }
            }
        }

        // Get binary string with num_clbits bits, reversed to match Qiskit/AER convention
        std::string binary_string;
        for (int i = num_clbits - 1; i >= 0; --i) {
            binary_string += bits[i] ? '1' : '0';
        }

        modified_counts[binary_string] = inner;
    }

    res.at("results")[0].at("data").at("counts") = modified_counts;
}

} // End of sim namespace
} // End of cunqa namespace