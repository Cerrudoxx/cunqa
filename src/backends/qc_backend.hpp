#pragma once

#include <vector>

#include "backend.hpp"
#include "quantum_task.hpp"
#include "simulators/simulator_strategy.hpp"

#include "utils/constants.hpp"
#include "utils/json.hpp"
#include "logger.hpp"


namespace cunqa {
namespace sim {

/**
 * @struct QCConfig
 * @brief Configuration for the QCBackend.
 *
 * This struct holds all the configuration parameters for a QCBackend instance,
 * including its name, version, number of qubits, and noise model. It also provides
 * serialization and deserialization functions for JSON.
 */
struct QCConfig {
    std::string name = "QCBackend"; ///< The name of the backend.
    std::string version = "0.0.1"; ///< The version of the backend.
    int n_qubits = 32; ///< The number of qubits in the backend.
    std::string description = "A backend with quantum communication capabilities."; ///< A description of the backend.
    std::vector<std::vector<int>> coupling_map; ///< The coupling map of the qubits.
    std::vector<std::string> basis_gates = constants::BASIS_GATES; ///< The basis gates supported by the backend.
    std::string custom_instructions; ///< Custom instructions supported by the backend.
    std::vector<std::string> gates; ///< A list of all gates supported by the backend.
    JSON noise_model = {}; ///< The noise model to be used for simulations.
    std::string noise_properties_path; ///< The path to the noise properties file.
    std::string noise_path; ///< The path to the noise model file.

    /**
     * @brief Deserializes a QCConfig object from a JSON object.
     * @param j The JSON object to deserialize from.
     * @param obj The QCConfig object to deserialize to.
     */
    friend void from_json(const JSON& j, QCConfig &obj) {
        j.at("name").get_to(obj.name);
        j.at("version").get_to(obj.version);
        j.at("n_qubits").get_to(obj.n_qubits);
        j.at("description").get_to(obj.description);
        j.at("coupling_map").get_to(obj.coupling_map);
        j.at("basis_gates").get_to(obj.basis_gates);
        j.at("custom_instructions").get_to(obj.custom_instructions);
        j.at("gates").get_to(obj.gates);
        j.at("noise_model").get_to(obj.noise_model);
        j.at("noise_properties_path").get_to(obj.noise_properties_path);
        j.at("noise_path").get_to(obj.noise_path);
    }

    /**
     * @brief Serializes a QCConfig object to a JSON object.
     * @param j The JSON object to serialize to.
     * @param obj The QCConfig object to serialize.
     */
    friend void to_json(JSON& j, const QCConfig& obj) {
        j = {
            {"name", obj.name},
            {"version", obj.version},
            {"n_qubits", obj.n_qubits},
            {"description", obj.description},
            {"coupling_map", obj.coupling_map},
            {"basis_gates", obj.basis_gates},
            {"custom_instructions", obj.custom_instructions},
            {"gates", obj.gates},
            {"noise_model", obj.noise_path},
            {"noise_properties_path", obj.noise_properties_path}
        };
    }
};

/**
 * @class QCBackend
 * @brief A final class representing a quantum backend with quantum communication capabilities.
 *
 * This class inherits from the Backend interface and provides a concrete
 * implementation of a backend that supports quantum communication. It uses a
 * simulator strategy to execute quantum tasks.
 */
class QCBackend final : public Backend {
public:
    QCConfig qc_config; ///< The configuration for this backend.

    /**
     * @brief Constructs a new QCBackend object.
     * @param qc_config The configuration for the backend.
     * @param simulator A unique pointer to a simulator strategy.
     */
    QCBackend(const QCConfig& qc_config, std::unique_ptr<SimulatorStrategy<QCBackend>> simulator):
        qc_config{qc_config},
        simulator_{std::move(simulator)}
    {
        config = qc_config;
        config["noise_model"] = qc_config.noise_model;
    }

    /**
     * @brief Default copy constructor.
     */
    QCBackend(QCBackend& cc_backend) = default;

    /**
     * @brief Executes a quantum task using the assigned simulator strategy.
     * @param quantum_task The quantum task to execute.
     * @return The result of the execution as a JSON object.
     */
    inline JSON execute(const QuantumTask& quantum_task) const override {
        LOGGER_DEBUG("Executing quantum task.");
        return simulator_->execute(*this, quantum_task);
    }

    /**
     * @brief Serializes the backend's configuration to a JSON object.
     * @return The backend's configuration as a JSON object.
     */
    JSON to_json() const override {
        JSON config_json = config;
        const auto simulator_name = simulator_->get_name();
        config_json["simulator"] = simulator_name;
        return config_json;
    }

private:
    std::unique_ptr<SimulatorStrategy<QCBackend>> simulator_; ///< The simulator strategy used by this backend.
};

} // End of sim namespace
} // End of cunqa namespace