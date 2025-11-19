#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>

#include "json.hpp"

namespace {

/**
 * @brief Opens a file and returns a file descriptor.
 * @param filename The name of the file to open.
 * @return The file descriptor.
 */
int open_file(const std::string& filename)
{
    int fd = open(filename.c_str(), O_RDWR | O_CREAT, 0666);
    if (fd == -1) {
        perror("open");
        throw std::runtime_error("Failed to open file: " + filename);
    }
    return fd;
}

/**
 * @brief Acquires a write lock on a file.
 * @param fd The file descriptor.
 * @return The flock structure representing the lock.
 */
struct flock lock(const int& fd)
{
    struct flock fl;
    fl.l_type = F_WRLCK;
    fl.l_whence = SEEK_SET;
    fl.l_start = 0;
    fl.l_len = 0; // Lock the entire file

    if (fcntl(fd, F_SETLKW, &fl) == -1) {
        perror("fcntl - lock");
        throw std::runtime_error("Failed to acquire file lock");
    }
    return fl;
}

/**
 * @brief Releases a lock on a file.
 * @param fd The file descriptor.
 * @param fl The flock structure representing the lock.
 */
void unlock(const int& fd, struct flock& fl)
{
    if (fsync(fd) == -1) {
        perror("fsync");
    }

    fl.l_type = F_UNLCK;
    if (fcntl(fd, F_SETLK, &fl) == -1)
        perror("fcntl - unlock");
}

/**
 * @brief Reads a JSON object from a file.
 * @param fd The file descriptor.
 * @return The JSON object.
 */
cunqa::JSON read_json(const int& fd)
{
    lseek(fd, 0, SEEK_SET);
    std::string content;
    char buf[4096];
    ssize_t n;
    while ((n = read(fd, buf, sizeof(buf))) > 0) {
        content.append(buf, n);
    }
    if (n == -1) {
        perror("read");
        throw std::runtime_error("Failed to read file");
    }

    return content.empty() ? cunqa::JSON::object() : cunqa::JSON::parse(content, nullptr, false);
}

/**
 * @brief Writes a JSON object to a file.
 * @param fd The file descriptor.
 * @param j The JSON object to write.
 */
void write_json(const int& fd, const cunqa::JSON& j)
{
    std::string output = j.dump(4);
    if (ftruncate(fd, 0) == -1) {
        perror("ftruncate");
        throw std::runtime_error("Failed to truncate file");
    }

    lseek(fd, 0, SEEK_SET);
    ssize_t written = write(fd, output.c_str(), output.size());
    if (written < 0 || static_cast<size_t>(written) != output.size()) {
        perror("write");
        throw std::runtime_error("Failed to write complete JSON");
    }
}

} // End of anonymous namespace


namespace cunqa {

void write_on_file(JSON local_data, const std::string &filename, const std::string &suffix)
{
    int fd = -1;
    try {
        fd = open_file(filename);
        auto fl = lock(fd);
        auto j = read_json(fd);

        const char *pid_env = std::getenv("SLURM_TASK_PID");
        const char *job_env = std::getenv("SLURM_JOB_ID");
        std::string local_id = pid_env ? pid_env : "UNKNOWN";
        std::string job_id = job_env ? job_env : "UNKNOWN";
        std::string task_id = suffix.empty() ? (job_id + "_" + local_id) : (job_id + "_" + local_id + "_" + suffix);
        j[task_id] = local_data;

        write_json(fd, j);
        unlock(fd, fl);
        close(fd);
    } catch (const std::exception &e) {
        if (fd != -1) close(fd);
        std::string msg = "Error writing JSON with POSIX (fcntl) locks.\nSystem message: ";
        throw std::runtime_error(msg + e.what());
    }
}

void remove_from_file(const std::string &filename, const std::string &rm_key)
{
    int fd = -1;
    try {
        fd = open_file(filename);
        auto fl = lock(fd);
        auto j = read_json(fd);

        JSON out = JSON::object();
        for (auto it = j.begin(); it != j.end(); ++it) {
            if (it.key().rfind(rm_key, 0) != 0) {
                out[it.key()] = it.value();
            }
        }

        write_json(fd, out);
        unlock(fd, fl);
        close(fd);
    } catch (const std::exception &e) {
        if (fd != -1) close(fd);
        std::string msg = "Error writing JSON with POSIX (fcntl) locks.\nSystem message: ";
        throw std::runtime_error(msg + e.what());
    }
}

} // End of cunqa namespace