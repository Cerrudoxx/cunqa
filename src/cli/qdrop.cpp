#include <string>
#include <fstream>
#include <iostream>
#include <cstdlib>
#include <cstdint>
#include <unistd.h>
#include <stdexcept>
#include <set>
#include <unordered_set>
#include <ranges>

#include "argparse/argparse.hpp"
#include "utils/constants.hpp"
#include "utils/json.hpp"

using namespace std::literals;

/**
 * @struct CunqaArgs
 * @brief Defines the command-line arguments for the qdrop command.
 */
struct CunqaArgs : public argparse::Args
{
    std::optional<std::vector<std::string>>& ids = arg("Slurm IDs of the QPUs to be dropped.").multi_argument();
    std::optional<std::vector<std::string>>& family = kwarg("fam,family_name", "Family name of the QPUs to be dropped.");
    bool &all = flag("all", "All qraise jobs will be dropped.");
};

/**
 * @brief Reads the qpus.json file.
 * @return A JSON object containing the QPU information.
 */
cunqa::JSON read_qpus_json()
{
    std::ifstream in(cunqa::constants::QPUS_FILEPATH);
    cunqa::JSON j;
    in >> j;
    return j;
}

/**
 * @brief Extracts the unique Slurm job IDs from the qpus.json data.
 * @param jobs A JSON object containing the QPU information.
 * @return A vector of strings containing the unique job IDs.
 */
std::vector<std::string> get_qpus_ids(const cunqa::JSON& jobs)
{
    std::vector<std::string> ids;
    std::string last_id;
    for (auto it = jobs.begin(); it != jobs.end(); ++it) {
        const auto& key = it.key();
        std::size_t pos = key.find('_');
        auto id = (pos == std::string::npos) ? key : key.substr(0, pos);

        if (id != last_id) {
            ids.push_back(id);
            last_id = id;
        }
    }
    return ids;
}

/**
 * @brief Finds the Slurm job IDs associated with a given family name.
 * @param qpus A JSON object containing the QPU information.
 * @param target_families A vector of strings containing the family names to search for.
 * @return A vector of strings containing the matching job IDs.
 */
std::vector<std::string> find_family_id(const cunqa::JSON& qpus, const std::vector<std::string>& target_families) {
    std::vector<std::string> ids;
    for (const auto& target_family : target_families) {
        for (const auto& [key, entry] : qpus.items()) {
            if (entry.is_object()) {
                auto itFam = entry.find("family");
                auto itJob = entry.find("slurm_job_id");
                if (itFam != entry.end() && itJob != entry.end() && itFam->get<std::string>() == target_family) {
                    ids.push_back(itJob->get<std::string>());
                    break;
                }
            }
        }
    }
    return ids;
}

/**
 * @brief Removes Slurm jobs using the scancel command.
 * @param job_ids A vector of strings containing the job IDs to remove.
 * @param all A boolean indicating whether to clear the qpus.json file.
 */
void removeJobs(const std::vector<std::string>& job_ids, bool all = false)
{
    std::string scancel = "scancel ";
    std::string job_ids_str;
    for (const auto& job_id : job_ids) {
        job_ids_str += job_id + " ";
    }
    scancel += job_ids_str;
    std::system(scancel.c_str());
    std::cout << "Removed job(s) with ID(s): \033[1;32m" << job_ids_str << "\033[0m\n";

    if (all) {
        auto left_jobs = read_qpus_json();
        if (!left_jobs.empty()) {
            std::ofstream ofs(cunqa::constants::QPUS_FILEPATH, std::ios::trunc);
            ofs << "{}";
        }
    }
}

/**
 * @brief Main entry point for the qdrop command.
 * @param argc The number of command-line arguments.
 * @param argv An array of command-line arguments.
 * @return 0 on success, -1 or EXIT_FAILURE on failure.
 */
int main(int argc, char* argv[])
{
    auto args = argparse::parse<CunqaArgs>(argc, argv);

    if (args.all) {
        auto ids = get_qpus_ids(read_qpus_json());
        if (!ids.empty()) removeJobs(ids, true);
        else return EXIT_FAILURE;
    } else if (args.ids.has_value() && !args.family.has_value()) {
        auto ids = get_qpus_ids(read_qpus_json());
        std::unordered_set<std::string> keep(args.ids.value().begin(), args.ids.value().end());
        auto filtered_ids = ids | std::views::filter([&](const std::string& id) { return keep.count(id); });
        std::vector<std::string> to_remove(filtered_ids.begin(), filtered_ids.end());

        if (!to_remove.empty())
            removeJobs(to_remove);
        else {
            std::cerr << "\033[1;33mWarning: \033[0mNo qraise jobs are currently running with the specified ID.\n";
            return EXIT_FAILURE;
        }
    } else if (!args.ids.has_value() && args.family.has_value()) {
        auto ids = find_family_id(read_qpus_json(), args.family.value());
        if (!ids.empty())
            removeJobs(ids);
        else {
            std::cerr << "\033[1;33mWarning: \033[0mNo qraise jobs are currently running with the specified family names.\n";
            return EXIT_FAILURE;
        }
    } else {
        std::cerr << "\033[1;31mError: \033[0mYou must specify either the IDs or the family name (with --fam) of the jobs to be removed, or use the --all flag.\n";
        return -1;
    }
    
    return EXIT_SUCCESS;
}