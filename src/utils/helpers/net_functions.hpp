#pragma once

#include <iostream>
#include <fstream>
#include <string>
#include <set>
#include <vector>
#include <cstring>
#include <dirent.h>

#include <ifaddrs.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netpacket/packet.h>
#include <net/if_arp.h>

#include "logger.hpp"
#include "utils/constants.hpp"

using namespace std::string_literals;

/**
 * @brief Safely casts an unsigned integer type to another unsigned integer type.
 * @tparam TO The target unsigned integer type.
 * @tparam FROM The source unsigned integer type.
 * @param value The value to cast.
 * @return The casted value.
 */
template<typename TO, typename FROM>
TO legacy_size_cast(FROM value)
{
    static_assert(std::is_unsigned_v<FROM> && std::is_unsigned_v<TO>,
                  "Only unsigned types can be cast here!");
    return static_cast<TO>(value);
}

/**
 * @brief Gets the hostname of the current machine.
 * @return The hostname as a string.
 */
inline std::string get_hostname(){
    char hostname[HOST_NAME_MAX];
    gethostname(hostname, HOST_NAME_MAX);
    return hostname;
}

/**
 * @brief Gets the nodename from the SLURM environment.
 * @return The nodename as a string, or "login" if not found.
 */
inline std::string get_nodename(){
    auto nodename = std::getenv("SLURMD_NODENAME");
    return nodename ? nodename : "login"s;
}

/**
 * @brief Reads a line from a file.
 * @param path The path to the file.
 * @param out A reference to a string to store the line.
 * @return True if the line was read successfully, false otherwise.
 */
inline bool read_line(const std::string& path, std::string& out) {
    std::ifstream f(path);
    if (!f.is_open()) return false;
    std::getline(f, out);
    while (!out.empty() && (out.back() == '\n' || out.back() == '\r')) out.pop_back();
    return true;
}

/**
 * @brief Reads an integer from a file.
 * @param path The path to the file.
 * @return The integer value, or -1 if an error occurred.
 */
inline int read_int(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return -1;
    int v = -1;
    f >> v;
    return f.fail() ? -1 : v;
}

/**
 * @brief Gets the ARP hardware address type for a network interface.
 * @param head A pointer to the head of the ifaddrs list.
 * @param ifname The name of the network interface.
 * @return The ARP hardware address type, or -1 if not found.
 */
inline int arphrd_from_ifaddrs(struct ifaddrs* head, const std::string& ifname) {
    for (auto p = head; p; p = p->ifa_next) {
        if (p->ifa_addr && p->ifa_addr->sa_family == AF_PACKET && ifname == p->ifa_name) {
            auto* sll = reinterpret_cast<sockaddr_ll*>(p->ifa_addr);
            return sll->sll_hatype;
        }
    }
    return -1;
}

/**
 * @brief Lists the names of files in a directory.
 * @param path The path to the directory.
 * @return A vector of strings containing the file names.
 */
inline std::vector<std::string> list_names(const std::string& path) {
    std::vector<std::string> v;
    DIR* d = opendir(path.c_str());
    if (!d) return v;
    for (auto e = readdir(d); e; e = readdir(d)) {
        std::string n = e->d_name;
        if (n != "." && n != "..") v.push_back(n);
    }
    closedir(d);
    return v;
}

/**
 * @brief Gets the speed of an Ethernet interface in Mbps.
 * @param ifname The name of the network interface.
 * @return The speed in Mbps, or -1 if not available.
 */
inline long speed_eth_mbps(const std::string& ifname) {
    int v = read_int("/sys/class/net/" + ifname + "/speed");
    return (v > 0) ? v : -1;
}

/**
 * @brief Checks if a network interface is an InfiniBand HCA.
 * @param ifname The name of the network interface.
 * @param hca A reference to a string to store the HCA name.
 * @return True if it is an InfiniBand HCA, false otherwise.
 */
inline bool ib_hca(const std::string& ifname, std::string& hca) {
    auto v = list_names("/sys/class/net/" + ifname + "/device/infiniband");
    if (v.empty()) return false;
    hca = v.front();
    return true;
}

/**
 * @brief Gets the speed of an InfiniBand interface in Mbps.
 * @param ifname The name of the network interface.
 * @return The speed in Mbps, or -1 if not available.
 */
inline long speed_ib_mbps(const std::string& ifname) {
    std::string hca;
    if (!ib_hca(ifname, hca)) return -1;
    int port = read_int("/sys/class/net/" + ifname + "/dev_port");
    if (port <= 0) port = 1;
    std::string rate;
    if (!read_line("/sys/class/infiniband/" + hca + "/ports/" + std::to_string(port) + "/rate", rate)) return -1;
    double val = 0.0;
    char unit[16] = {0};
    if (sscanf(rate.c_str(), " %lf %15s", &val, unit) != 2) return -1;
    std::string u(unit);
    for (auto& c : u) c = tolower(c);
    if (u.find("gb") != std::string::npos) return static_cast<long>(val * 1000.0 + 0.5);
    if (u.find("mb") != std::string::npos) return static_cast<long>(val + 0.5);
    return -1;
}

/**
 * @brief Gets the link speed of a network interface in Mbps.
 * @param head A pointer to the head of the ifaddrs list.
 * @param ifname The name of the network interface.
 * @return The link speed in Mbps, or -1 if not available.
 */
inline long link_speed_mbps(struct ifaddrs* head, const std::string& ifname) {
    long s = speed_eth_mbps(ifname);
    if (s > 0) return s;
    if (arphrd_from_ifaddrs(head, ifname) == ARPHRD_INFINIBAND) {
        s = speed_ib_mbps(ifname);
        if (s > 0) return s;
    }
    return -1;
}

/**
 * @brief Checks if a network interface is operationally up.
 * @param ifname The name of the network interface.
 * @return True if the interface is up, false otherwise.
 */
inline bool oper_up(const std::string& ifname) {
    std::string st;
    if (read_line("/sys/class/net/" + ifname + "/operstate", st)) return st == "up";
    return read_int("/sys/class/net/" + ifname + "/carrier") == 1;
}

/**
 * @brief Checks if a network interface is administratively up.
 * @param head A pointer to the head of the ifaddrs list.
 * @param ifname The name of the network interface.
 * @return True if the interface is up, false otherwise.
 */
inline bool admin_up(struct ifaddrs* head, const std::string& ifname) {
    for (auto p = head; p; p = p->ifa_next) {
        if (p->ifa_name && ifname == p->ifa_name) return (p->ifa_flags & IFF_UP);
    }
    return false;
}

/**
 * @brief Gets the first IPv4 address of a network interface.
 * @param head A pointer to the head of the ifaddrs list.
 * @param ifname The name of the network interface.
 * @param ip_out A reference to a string to store the IP address.
 * @return True if an IPv4 address was found, false otherwise.
 */
inline bool get_first_ipv4(struct ifaddrs* head, const std::string& ifname, std::string& ip_out) {
    char buf[INET_ADDRSTRLEN];
    for (auto p = head; p; p = p->ifa_next) {
        if (p->ifa_addr && p->ifa_name && ifname == p->ifa_name && p->ifa_addr->sa_family == AF_INET) {
            auto* sa = reinterpret_cast<sockaddr_in*>(p->ifa_addr);
            if ((ntohl(sa->sin_addr.s_addr) & 0xFF000000u) != 0x7F000000u) {
                if (inet_ntop(AF_INET, &sa->sin_addr, buf, sizeof(buf))) {
                    ip_out = buf;
                    return true;
                }
            }
        }
    }
    return false;
}

/**
 * @brief Gets the IP address of the fastest available network interface.
 * @return The IP address as a string, or an empty string if not found.
 */
inline std::string get_IP_address() {
    struct ifaddrs* ifaddr = nullptr;
    if (getifaddrs(&ifaddr) == -1) { perror("getifaddrs"); return ""; }

    std::set<std::string> seen;
    std::string best_if, best_ip;
    long best_mbps = -1;

    for (auto p=ifaddr; p; p=p->ifa_next) {

        // If has been added, skip
        if (!p->ifa_name) continue;
        std::string ifname = p->ifa_name;
        if (!seen.insert(ifname).second) continue;

        // Check if it is UP, if not skip
        if (!admin_up(ifaddr, ifname)) continue;
        if (!oper_up(ifname)) continue;

        // Obtain IPv4 and safe if it is the fastest
        std::string ip;
        if (!get_first_ipv4(ifaddr, ifname, ip)) continue;
        long mbps = link_speed_mbps(ifaddr, ifname);
        if (mbps <= 0) continue;
        if (mbps > best_mbps) { best_mbps = mbps; best_if = ifname; best_ip = ip; }
    }

    freeifaddrs(ifaddr);

    if (best_mbps > 0 && !best_ip.empty()) return best_ip;
    else return "";
}
