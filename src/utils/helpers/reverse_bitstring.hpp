#pragma once

#include <string>
#include <map>

#include "logger.hpp"

namespace cunqa {

/**
 * @brief Reverses a string.
 * @param bitstring The string to reverse.
 * @return The reversed string.
 */
inline std::string reverse_string(const std::string& bitstring)
{
    return {bitstring.rbegin(), bitstring.rend()};
}

/**
 * @brief Reverses the keys of a map, which are assumed to be bitstrings.
 * @param counts A reference to a map of bitstring keys and size_t values.
 */
inline void reverse_bitstring_keys_json(std::map<std::string, std::size_t>& counts)
{
    std::map<std::string, std::size_t> modified_counts;

    for (const auto& [key, inner] : counts) {
        modified_counts[reverse_string(key)] = inner;
    }
    counts = modified_counts;
}

/**
 * @brief Reverses the keys of the "counts" object within a JSON object.
 * @param result A reference to a JSON object containing a "counts" object.
 */
inline void reverse_bitstring_keys_json(JSON& result)
{
    JSON counts = result.at("counts").get<JSON>();
    JSON modified_counts;

    for (const auto& [key, inner] : counts.items()) {
        modified_counts[reverse_string(key)] = inner;
    }
    result.at("counts") = modified_counts;
}

} //End namespace cunqa