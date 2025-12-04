#include <string>
#include <fstream>
#include <regex>
#include <any>
#include <filesystem>
#include <iostream>
#include <cstdlib>

#include "argparse/argparse.hpp"
#include "utils/constants.hpp"
#include "qraise/utils_qraise.hpp"
#include "qraise/args_qraise.hpp"
#include "qraise/noise_model_conf_qraise.hpp"
#include "qraise/simple_conf_qraise.hpp"
#include "qraise/cc_conf_qraise.hpp"
#include "qraise/qc_conf_qraise.hpp"
#include "qraise/infrastructure_conf_qraise.hpp"
#include "logger.hpp"

using namespace std::literals;
using namespace cunqa;

namespace {

/**
 * @brief Writes the SBATCH header to the sbatch file.
 * @param sbatchFile The output file stream for the sbatch file.
 * @param args The command-line arguments.
 */
void write_sbatch_header(std::ofstream& sbatchFile, const CunqaArgs& args)
{
    sbatchFile << "#!/bin/bash\n";
    sbatchFile << "#SBATCH --job-name=qraise\n";

    int n_tasks = args.qc ? args.n_qpus * args.cores_per_qpu + args.n_qpus : args.n_qpus;
    sbatchFile << "#SBATCH --ntasks=" << n_tasks << "\n";

    if (!args.qc)
        sbatchFile << "#SBATCH -c " << args.cores_per_qpu << "\n";

    sbatchFile << "#SBATCH -N " << args.number_of_nodes.value() << "\n";
    
    if (args.qpus_per_node.has_value()) {
        if (args.n_qpus < args.qpus_per_node) {
            LOGGER_ERROR("Fewer QPUs than selected qpus_per_node.");
            LOGGER_ERROR("\tNumber of QPUs: {}\n\tQPUs per node: {}", args.n_qpus, args.qpus_per_node.value());
            LOGGER_ERROR("Aborted.");
            std::system("rm qraise_sbatch_tmp.sbatch");
            return;
        } else {
            sbatchFile << "#SBATCH --ntasks-per-node=" << args.qpus_per_node.value() << "\n";
        }
    }

    if (args.node_list.has_value()) {
        if (args.number_of_nodes.value() != args.node_list.value().size()) {
            LOGGER_ERROR("The number of node names does not match the total number of nodes.");
            LOGGER_ERROR("\tNumber of nodes: {}\n\tNumber of node names: {}", args.number_of_nodes.value(), args.node_list.value().size());
            LOGGER_ERROR("Aborted.");
            return;
        } else {
            sbatchFile << "#SBATCH --nodelist=";
            for (size_t i = 0; i < args.node_list.value().size(); ++i) {
                if (i > 0) sbatchFile << ",";
                sbatchFile << args.node_list.value()[i];
            }
            sbatchFile << "\n";
        }
    }

    if (args.mem_per_qpu.has_value() && (args.mem_per_qpu.value() / args.cores_per_qpu > DEFAULT_MEM_PER_CORE)) {
        LOGGER_ERROR("Too much memory per QPU. Please decrease --mem-per-qpu or increase --cores-per-qpu.");
        return;
    }

    if (!args.qc) {
        if (args.mem_per_qpu.has_value() && check_mem_format(args.mem_per_qpu.value())) {
            sbatchFile << "#SBATCH --mem-per-cpu=" << args.mem_per_qpu.value() / args.cores_per_qpu << "G\n";
        } else if (args.mem_per_qpu.has_value() && !check_mem_format(args.mem_per_qpu.value())) {
            LOGGER_ERROR("Memory format is incorrect. It must be: xG (where x is the number of Gigabytes).");
            return;
        } else if (!args.mem_per_qpu.has_value()) {
            sbatchFile << "#SBATCH --mem-per-cpu=" << DEFAULT_MEM_PER_CORE << "G\n";
        }
    } else {
        if (args.mem_per_qpu.has_value() && check_mem_format(args.mem_per_qpu.value())) {
            sbatchFile << "#SBATCH --mem=" << args.mem_per_qpu.value() * args.n_qpus + args.n_qpus << "G\n";
        } else {
            sbatchFile << "#SBATCH --mem=" << DEFAULT_MEM_PER_CORE * args.cores_per_qpu * args.n_qpus + args.n_qpus << "G\n";
        }
    }

    if (check_time_format(args.time))
        sbatchFile << "#SBATCH --time=" << args.time << "\n";
    else {
        LOGGER_ERROR("Time format is incorrect. It must be: hh:mm:ss.");
        return;
    }

    if (!check_simulator_name(args.simulator)) {
        LOGGER_ERROR("Incorrect simulator name ({}).", args.simulator);
        return;
    }

    sbatchFile << "#SBATCH --output=qraise_%j\n\n";
    sbatchFile << "unset SLURM_MEM_PER_CPU SLURM_CPU_BIND_LIST SLURM_CPU_BIND\n";
    sbatchFile << "EPILOG_PATH=" << std::string(constants::CUNQA_PATH) << "/epilog.sh\n";
}

/**
 * @brief Writes the run command to the sbatch file.
 * @param sbatchFile The output file stream for the sbatch file.
 * @param args The command-line arguments.
 * @param mode The execution mode ("co_located" or "hpc").
 */
void write_run_command(std::ofstream& sbatchFile, const CunqaArgs& args, const std::string& mode)
{
    std::string run_command;
    if (args.noise_properties.has_value() || args.fakeqmio.has_value()) {
        LOGGER_DEBUG("noise_properties json path provided.");
        if (args.simulator == "Munich" || args.simulator == "Cunqa") {
            LOGGER_WARN("Personalized noise models are only supported for AerSimulator. Switching simulator from {} to Aer.", args.simulator);
        }
        if (args.cc || args.qc) {
            LOGGER_ERROR("Personalized noise models are not supported for classical/quantum communication schemes.");
            return;
        }
        if (args.backend.has_value()) {
            LOGGER_WARN("Backend will be redefined according to the provided noise properties.");
        }
        run_command = get_noise_model_run_command(args, mode);
    } else if ((!args.noise_properties.has_value() || !args.fakeqmio.has_value()) && (args.no_thermal_relaxation || args.no_gate_error || args.no_readout_error)) {
        LOGGER_ERROR("noise_properties flags were provided, but neither --noise_properties nor --fakeqmio were included.");
        return;
    } else {
        if (args.cc) {
            LOGGER_DEBUG("Classical communications enabled.");
            run_command = get_cc_run_command(args, mode);
        } else if (args.qc) {
            LOGGER_DEBUG("Quantum communications enabled.");
            run_command = get_qc_run_command(args, mode);
        } else {
            LOGGER_DEBUG("No communications.");
            run_command = get_simple_run_command(args, mode);
        }
    }

    LOGGER_DEBUG("Run command: {}", run_command);
    sbatchFile << run_command;
}

}
namespace fs = std::filesystem;

/**
 * @brief Main entry point for the qraise command.
 * @param argc The number of command-line arguments.
 * @param argv An array of command-line arguments.
 * @return 0 on success, -1 on failure.
 */
int main(int argc, char* argv[])
{
    auto args = argparse::parse<CunqaArgs>(argc, argv, true);

    if (args.infrastructure.has_value()) {
        LOGGER_DEBUG("Raising infrastructure with path: {}", args.infrastructure.value());
        std::ofstream sbatchFile("qraise_sbatch_tmp.sbatch");
        write_sbatch_file_from_infrastructure(sbatchFile, args);
        sbatchFile.close();
    } else {
        std::string mode = args.co_located ? "co_located" : "hpc";
        std::string family = args.family_name;
        if (exists_family_name(family, constants::QPUS_FILEPATH)) {
            LOGGER_ERROR("QPUs with the same family name '{}' already exist.", family);
            return -1;
        }

        std::ofstream sbatchFile("qraise_sbatch_tmp.sbatch");
        write_sbatch_header(sbatchFile, args);
        write_run_command(sbatchFile, args, mode);
        sbatchFile.close();
    }

    std::system("sbatch qraise_sbatch_tmp.sbatch");
    std::system("rm qraise_sbatch_tmp.sbatch");
    
    return 0;
}