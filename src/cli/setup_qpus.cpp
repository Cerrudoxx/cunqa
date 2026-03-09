#include <cstdlib>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

#include "qpu.hpp"
#include "backends/simple_backend.hpp"
#include "backends/cc_backend.hpp"
#include "backends/simulators/AER/aer_simple_simulator.hpp"
#include "backends/simulators/AER/aer_cc_simulator.hpp"
#include "backends/simulators/AER/aer_qc_simulator.hpp"
#include "backends/simulators/Munich/munich_simple_simulator.hpp"
#include "backends/simulators/Munich/munich_cc_simulator.hpp"
#include "backends/simulators/Munich/munich_qc_simulator.hpp"
#include "backends/simulators/Maestro/maestro_simple_simulator.hpp"
#include "backends/simulators/Maestro/maestro_cc_simulator.hpp"
#include "backends/simulators/Maestro/maestro_qc_simulator.hpp"
#include "backends/simulators/CUNQA/cunqa_simple_simulator.hpp"
#include "backends/simulators/CUNQA/cunqa_cc_simulator.hpp"
#include "backends/simulators/CUNQA/cunqa_qc_simulator.hpp"
#include "backends/simulators/Qulacs/qulacs_simple_simulator.hpp"
#include "backends/simulators/Qulacs/qulacs_cc_simulator.hpp"
#include "backends/simulators/Qulacs/qulacs_qc_simulator.hpp"

#include "utils/json.hpp"
#include "utils/helpers/murmur_hash.hpp"
#include "utils/constants.hpp" // Necesario para get_user_cunqa_dir()
#include "logger.hpp"

using namespace std::string_literals;
using namespace cunqa;
using namespace cunqa::sim;

// Modificado para aceptar el output_path e inyectarlo en el comando de python
std::string generate_noise_instructions(const JSON& back_path_json, const std::string& family, const std::string& output_path)
{
    std::string backend_path;

    if (back_path_json.contains("backend_path")){
        LOGGER_DEBUG("backend_path provided");
        backend_path=back_path_json.at("backend_path").get<std::string>();
    } else {
        LOGGER_DEBUG("No backend_path provided, defining backend from noise_properties.");
        backend_path = "default";
    }
    std::string command("python "s + std::string(constants::INSTALL_PATH) + "/cunqa/qiskit_deps/noise_instructions.py "s
                                   + back_path_json.at("noise_properties_path").get<std::string>() + " "s
                                   + backend_path + " "s
                                   + back_path_json.at("thermal_relaxation").get<std::string>() + " "s
                                   + back_path_json.at("readout_error").get<std::string>() + " "s
                                   + back_path_json.at("gate_error").get<std::string>() + " "s
                                   + family + " "s
                                   + back_path_json.at("fakeqmio").get<std::string>() + " "s
                                   + output_path); // ¡El output path que le pasamos al parser de Python!
                                   
    LOGGER_DEBUG("Command: {}", command);
    std::system(command.c_str());
    return "";
}

template<typename Simulator, typename Config, typename BackendType>
void turn_ON_QPU(
    const JSON& backend_json, const std::string& mode, 
    const std::string& name, const std::string& family
)
{
    std::unique_ptr<Simulator> simulator = std::make_unique<Simulator>();
    Config config;
    if (!backend_json.empty())
        config = backend_json;
    QPU qpu(std::make_unique<BackendType>(config, std::move(simulator)), mode, name, family);
    qpu.turn_ON();
}

int main(int argc, char *argv[])
{
    std::string mode(argv[1]);
    std::string communications(argv[2]);
    std::string family(argv[3]);
    std::string sim_arg(argv[4]);

    // Variables seguras de Slurm (evitan segfault si se corre en local)
    std::string slurm_job_id = std::getenv("SLURM_JOB_ID") ? std::getenv("SLURM_JOB_ID") : "local_job";
    std::string slurm_procid = std::getenv("SLURM_PROCID") ? std::getenv("SLURM_PROCID") : "0";
    std::string slurm_task_pid = std::getenv("SLURM_TASK_PID") ? std::getenv("SLURM_TASK_PID") : "0";

    if (family == "default")
        family = slurm_job_id;
        
    std::string name = slurm_job_id + "_"s + slurm_task_pid;
    
    auto back_path_json = (argc == 6 ? JSON::parse(std::string(argv[5])) : JSON());
    JSON backend_json;

    if (back_path_json.contains("noise_properties_path")) {
        if (sim_arg != "Aer")
            throw std::runtime_error("Noise is only available with AER at the moment.");
            
        // ==============================================================================
        //  AQUÍ ESTÁ LA CLAVE: Usamos get_user_cunqa_dir() para asegurar permisos
        // ==============================================================================
        std::string fpath = cunqa::constants::get_user_cunqa_dir() + "/tmp_noisy_backend_" + slurm_job_id + ".json";

        if (slurm_procid == "0") {
            generate_noise_instructions(back_path_json, family, fpath); // Pasamos fpath a python
            LOGGER_DEBUG("Correctly created tmp noise intructions file.");
        } else {
            int fd = open(fpath.c_str(), O_RDONLY);
            while (fd == -1 || flock(fd, LOCK_SH) != 0) {
                if (fd != -1) close(fd);
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                fd = open(fpath.c_str(), O_RDONLY);
            }
            close(fd);
        }

        std::ifstream f(fpath);
        backend_json = JSON::parse(f);
    } else if (back_path_json.contains("backend_path")) {
        std::ifstream f(back_path_json.at("backend_path").get<std::string>());
        backend_json = JSON::parse(f);
    }

    switch(murmur::hash(communications)) {
        case murmur::hash("no_comm"): 
            LOGGER_DEBUG("Raising QPU without communications.");
            switch(murmur::hash(sim_arg)) {
                case murmur::hash("Aer"): 
                    LOGGER_DEBUG("QPU going to turn on with AerSimpleSimulator.");
                    turn_ON_QPU<AerSimpleSimulator, SimpleConfig, SimpleBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Munich"):
                    LOGGER_DEBUG("QPU going to turn on with MunichSimpleSimulator.");
                    turn_ON_QPU<MunichSimpleSimulator, SimpleConfig, SimpleBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Maestro"):
                    LOGGER_DEBUG("QPU going to turn on with MaestroSimpleSimulator.");
                    turn_ON_QPU<MaestroSimpleSimulator, SimpleConfig, SimpleBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Cunqa"):
                    LOGGER_DEBUG("QPU going to turn on with CunqaSimpleSimulator.");
                    turn_ON_QPU<CunqaSimpleSimulator, SimpleConfig, SimpleBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Qulacs"):
                    LOGGER_DEBUG("QPU going to turn on with QulacsSimpleSimulator.");
                    turn_ON_QPU<QulacsSimpleSimulator, SimpleConfig, SimpleBackend>(backend_json, mode, name, family);
                    break;
                default:
                    LOGGER_ERROR("Simulator {} do not support simple simulation or does not exist.", sim_arg);
                    return EXIT_FAILURE;
            }
            break;
        case murmur::hash("cc"): 
            LOGGER_DEBUG("Raising QPU with classical communications.");
            switch(murmur::hash(sim_arg)) {
                case murmur::hash("Aer"): 
                    LOGGER_DEBUG("QPU going to turn on with AerCCSimulator.");
                    turn_ON_QPU<AerCCSimulator, CCConfig, CCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Munich"): 
                    LOGGER_DEBUG("QPU going to turn on with MunichCCSimulator.");
                    turn_ON_QPU<MunichCCSimulator, CCConfig, CCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Maestro"):
                    LOGGER_DEBUG("QPU going to turn on with MaestroCCSimulator.");
                    turn_ON_QPU<MaestroCCSimulator, CCConfig, CCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Cunqa"): 
                    LOGGER_DEBUG("QPU going to turn on with CunqaCCSimulator.");
                    turn_ON_QPU<CunqaCCSimulator, CCConfig, CCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Qulacs"): 
                    LOGGER_DEBUG("QPU going to turn on with QulacsCCSimulator.");
                    turn_ON_QPU<QulacsCCSimulator, CCConfig, CCBackend>(backend_json, mode, name, family);
                    break;
                default:
                    LOGGER_ERROR("Simulator {} do not support classical communication simulation or does not exist.", sim_arg);
                    return EXIT_FAILURE;
            }
            break;
        case murmur::hash("qc"):
            LOGGER_DEBUG("Raising QPU with quantum communications.");
            switch(murmur::hash(sim_arg)) {
                case murmur::hash("Aer"): 
                    LOGGER_DEBUG("QPU going to turn on with AerQCSimulator.");
                    turn_ON_QPU<AerQCSimulator, QCConfig, QCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Munich"): 
                    LOGGER_DEBUG("QPU going to turn on with MunichQCSimulator.");
                    turn_ON_QPU<MunichQCSimulator, QCConfig, QCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Maestro"):
                    LOGGER_DEBUG("QPU going to turn on with MaestroQCSimulator.");
                    turn_ON_QPU<MaestroQCSimulator, QCConfig, QCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Cunqa"): 
                    LOGGER_DEBUG("QPU going to turn on with CunqaQCSimulator.");
                    turn_ON_QPU<CunqaQCSimulator, QCConfig, QCBackend>(backend_json, mode, name, family);
                    break;
                case murmur::hash("Qulacs"): 
                    LOGGER_DEBUG("QPU going to turn on with QulacsQCSimulator.");
                    turn_ON_QPU<QulacsQCSimulator, QCConfig, QCBackend>(backend_json, mode, name, family);
                    break;
                default:
                    LOGGER_ERROR("Simulator {} do not support quantum communication simulation or does not exist.", sim_arg);
                    return EXIT_FAILURE;
            }
            break;
        default:
            LOGGER_ERROR("No {} communication method available.", communications);
            return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}