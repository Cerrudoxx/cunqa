#pragma once

#include <nlohmann/json.hpp>

namespace cunqa {
    /**
     * @brief A type alias for the nlohmann::json class.
     */
    using JSON = nlohmann::json;

    /**
     * @brief Writes a JSON object to a file.
     *
     * This function writes a JSON object to a file, optionally appending a suffix
     * to the key. It uses file locking to prevent race conditions.
     *
     * @param local_data The JSON object to write.
     * @param filename The name of the file to write to.
     * @param suffix An optional suffix to append to the key.
     */
    void write_on_file(JSON local_data, const std::string &filename, const std::string& suffix = "");

    /**
     * @brief Removes a key-value pair from a JSON file.
     *
     * This function removes a key-value pair from a JSON file. It uses file
     * locking to prevent race conditions.
     *
     * @param filename The name of the file to modify.
     * @param key The key to remove.
     */
    void remove_from_file(const std::string &filename, const std::string &key);
}

