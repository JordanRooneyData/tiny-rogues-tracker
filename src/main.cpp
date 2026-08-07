#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

using json = nlohmann::json;
namespace fs = std::filesystem;

struct Args {
    std::string save_path;
    std::string ids_path = "ids.json";
    std::string report_path = "report.txt";
    bool no_pause = false;
};

struct RouteSpec {
    std::string key;
    std::string label;
    std::string name;
    std::vector<int> completion_boss_ids;
    std::vector<int> entry_boss_ids;
    std::string source;
};

static std::string get_env(const char* name) {
    const char* v = std::getenv(name);
    return v ? std::string(v) : std::string();
}

static bool looks_like_tiny_rogues_save(const fs::path& p) {
    try {
        if (!fs::is_regular_file(p)) return false;
        auto name = p.filename().string();
        if (name.find("Save") == std::string::npos || p.extension() != ".json") return false;
        std::ifstream f(p);
        if (!f) return false;
        std::string head(4096, '\0');
        f.read(head.data(), static_cast<std::streamsize>(head.size()));
        head.resize(static_cast<size_t>(f.gcount()));
        return head.find("RunRecords") != std::string::npos && head.find("CinderStreakHistory") != std::string::npos;
    } catch (...) {
        return false;
    }
}

static std::vector<fs::path> candidate_roots() {
    std::vector<fs::path> roots;
#ifdef _WIN32
    auto user = get_env("USERPROFILE");
    auto appdata = get_env("APPDATA");
    if (!user.empty()) {
        // The normal Steam/Unity location, supplied by the user:
        // C:\Users\jorda\AppData\LocalLow\RubyDev\Tiny Rogues
        roots.push_back(fs::path(user) / "AppData" / "LocalLow" / "RubyDev" / "Tiny Rogues");
        roots.push_back(fs::path(user) / "AppData" / "LocalLow");
        roots.push_back(fs::path(user) / "AppData" / "Local");
        roots.push_back(fs::path(user) / "Documents");
    }
    if (!appdata.empty()) roots.push_back(fs::path(appdata));
#else
    auto home = get_env("HOME");
    if (!home.empty()) roots.push_back(fs::path(home));
#endif
    roots.push_back(fs::current_path());
    return roots;
}

static std::string auto_locate_save() {
    for (const auto& root : candidate_roots()) {
        if (!fs::exists(root)) continue;
        if (fs::is_directory(root)) {
            for (const auto& name : {"Public_Slot1_Save1.json", "Public_Slot1_Save2.json", "Public_Slot1_Save3.json"}) {
                fs::path direct = root / name;
                if (looks_like_tiny_rogues_save(direct)) return direct.string();
            }
        }
        std::error_code ec;
        fs::recursive_directory_iterator it(root, fs::directory_options::skip_permission_denied, ec), end;
        size_t visited = 0;
        for (; it != end && !ec; it.increment(ec)) {
            if (++visited > 250000) break;
            const auto& p = it->path();
            if (looks_like_tiny_rogues_save(p)) return p.string();
        }
    }
    return "";
}

static json read_json(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("Could not open: " + path);
    json j;
    f >> j;
    return j;
}

static std::string lookup_name(const json& ids, const std::string& section, int id, const std::string& fallback_prefix) {
    std::string key = std::to_string(id);
    if (ids.contains(section) && ids[section].contains(key) && ids[section][key].contains("name")) {
        return ids[section][key]["name"].get<std::string>();
    }
    return fallback_prefix + " " + key;
}

static int as_int(const json& j, const std::string& key, int fallback=0) {
    if (!j.is_object() || !j.contains(key) || !j[key].is_number_integer()) return fallback;
    return j[key].get<int>();
}

static std::vector<int> json_int_vector(const json& j) {
    std::vector<int> out;
    if (!j.is_array()) return out;
    for (const auto& v : j) if (v.is_number_integer()) out.push_back(v.get<int>());
    return out;
}

static bool contains_any(const std::set<int>& haystack, const std::vector<int>& needles) {
    for (int n : needles) if (haystack.count(n)) return true;
    return false;
}

static std::string join_ints(const std::vector<int>& values) {
    if (values.empty()) return "-";
    std::ostringstream ss;
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) ss << ",";
        ss << values[i];
    }
    return ss.str();
}

static std::string join_names_for_ids(const json& ids, const std::vector<int>& values) {
    if (values.empty()) return "-";
    std::ostringstream ss;
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) ss << ", ";
        ss << lookup_name(ids, "bosses", values[i], "Boss ID") << " (" << values[i] << ")";
    }
    return ss.str();
}

static std::vector<RouteSpec> load_routes(const json& ids) {
    std::vector<RouteSpec> routes;
    const std::vector<std::string> order = {"heaven", "hell", "law"};
    if (!ids.contains("routes") || !ids["routes"].is_object()) return routes;
    for (const auto& key : order) {
        if (!ids["routes"].contains(key) || !ids["routes"][key].is_object()) continue;
        const auto& r = ids["routes"][key];
        RouteSpec spec;
        spec.key = key;
        spec.label = r.value("label", key);
        spec.name = r.value("name", spec.label);
        spec.source = r.value("source", std::string());
        spec.completion_boss_ids = json_int_vector(r.value("completion_boss_ids", json::array()));
        spec.entry_boss_ids = json_int_vector(r.value("entry_boss_ids", json::array()));
        if (!spec.completion_boss_ids.empty()) routes.push_back(spec);
    }
    return routes;
}

static std::string build_report(const json& save, const json& ids, const std::string& save_path) {
    const auto runs = save.value("RunRecords", json::array());
    const auto streaks = save.value("CinderStreakHistory", json::array());
    const auto routes = load_routes(ids);

    std::set<int> class_ids;
    for (size_t i = 0; i < streaks.size(); ++i) class_ids.insert(static_cast<int>(i));
    for (const auto& r : runs) if (r.contains("PlayedClass")) class_ids.insert(r["PlayedClass"].get<int>());

    struct Row {
        int death_max = 0;
        int death_kills = 0;
        int mega_death_kills = 0;
        int recent_runs = 0;
        int recent_max_cinder = -1;
        int recent_max_floor = -1;
        std::map<std::string,int> route_max;
        std::map<std::string,int> route_kills;
    };
    std::map<int, Row> rows;
    std::set<int> cinders;
    std::set<int> all_bosses_seen;

    for (int cid : class_ids) {
        if (cid >= 0 && cid < static_cast<int>(streaks.size()) && streaks[cid].is_object()) {
            rows[cid].death_max = as_int(streaks[cid], "highestUsedCinderThisRun", 0);
            rows[cid].death_kills = as_int(streaks[cid], "deathKills", 0);
            rows[cid].mega_death_kills = as_int(streaks[cid], "megaDeathKills", 0);
        }
        for (const auto& route : routes) {
            rows[cid].route_max[route.key] = -1;
            rows[cid].route_kills[route.key] = 0;
        }
    }

    for (const auto& r : runs) {
        if (!r.is_object() || !r.contains("PlayedClass")) continue;
        int cid = r["PlayedClass"].get<int>();
        int cinder = as_int(r, "CinderLevel", 0);
        int floor = as_int(r, "FloorReached", -1);
        cinders.insert(cinder);
        auto& row = rows[cid];
        row.recent_runs++;
        row.recent_max_cinder = std::max(row.recent_max_cinder, cinder);
        row.recent_max_floor = std::max(row.recent_max_floor, floor);

        std::set<int> bosses;
        if (r.contains("bossesKilled") && r["bossesKilled"].is_array()) {
            for (const auto& b : r["bossesKilled"]) {
                if (!b.is_number_integer()) continue;
                int bid = b.get<int>();
                bosses.insert(bid);
                all_bosses_seen.insert(bid);
            }
        }
        for (const auto& route : routes) {
            if (contains_any(bosses, route.completion_boss_ids)) {
                row.route_kills[route.key]++;
                row.route_max[route.key] = std::max(row.route_max[route.key], cinder);
            }
        }
    }

    std::ostringstream out;
    out << "Tiny Rogues Tracker v2\n";
    out << "======================\n\n";
    out << "Save: " << save_path << "\n";
    out << "Save time: " << save.value("TimeOfSave", std::string("unknown")) << "\n";
    out << "Run records: " << runs.size() << "\n";
    out << "CinderStreakHistory entries: " << streaks.size() << "\n";
    out << "Recent cinder levels: " << join_ints(std::vector<int>(cinders.begin(), cinders.end())) << "\n";
    out << "ID mapping: " << ids.value("provenance", json::object()).value("status", std::string("unknown")) << "\n\n";

    out << std::left << std::setw(18) << "Character" << std::right
        << std::setw(8) << "Death" << std::setw(8) << "Heaven" << std::setw(8) << "Hell" << std::setw(8) << "Law"
        << std::setw(8) << "Runs" << std::setw(8) << "Floor" << "\n";
    out << std::string(66, '-') << "\n";
    for (int cid : class_ids) {
        const auto& row = rows[cid];
        std::string name = lookup_name(ids, "characters", cid, "Class ID");
        auto route_val = [&](const std::string& key) {
            auto it = row.route_max.find(key);
            return (it == row.route_max.end() || it->second < 0) ? 0 : it->second;
        };
        out << std::left << std::setw(18) << name.substr(0, 17) << std::right
            << std::setw(8) << row.death_max
            << std::setw(8) << route_val("heaven")
            << std::setw(8) << route_val("hell")
            << std::setw(8) << route_val("law")
            << std::setw(8) << row.recent_runs
            << std::setw(8) << (row.recent_max_floor < 0 ? 0 : row.recent_max_floor)
            << "\n";
    }

    out << "\nRoute decoding\n";
    out << "--------------\n";
    out << "Death: uses CinderStreakHistory highestUsedCinderThisRun/deathKills, backed by boss ID 18 (" << lookup_name(ids, "bosses", 18, "Boss ID") << ").\n";
    for (const auto& route : routes) {
        out << route.label << ": completion boss IDs " << join_names_for_ids(ids, route.completion_boss_ids);
        if (!route.entry_boss_ids.empty()) out << "; entry/paired boss IDs " << join_names_for_ids(ids, route.entry_boss_ids);
        out << ".\n";
        if (!route.source.empty()) out << "  Source: " << route.source << "\n";
    }
    out << "\nObserved boss IDs in recent runs: " << join_ints(std::vector<int>(all_bosses_seen.begin(), all_bosses_seen.end())) << "\n";
    out << "\nThis tool is read-only. It never writes to the Tiny Rogues save file. It writes only the report path you choose.\n";
    return out.str();
}

static Args parse_args(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        if (s == "--save" && i + 1 < argc) a.save_path = argv[++i];
        else if (s == "--ids" && i + 1 < argc) a.ids_path = argv[++i];
        else if (s == "--report" && i + 1 < argc) a.report_path = argv[++i];
        else if (s == "--no-pause") a.no_pause = true;
        else if (s == "--help" || s == "-h") {
            std::cout << "Usage: TinyRoguesTracker.exe [--save Public_Slot1_Save1.json] [--ids ids.json] [--report report.txt] [--no-pause]\n";
            std::exit(0);
        }
    }
    return a;
}

int main(int argc, char** argv) {
    try {
        Args args = parse_args(argc, argv);
        if (args.save_path.empty()) {
            args.save_path = auto_locate_save();
        }
        if (args.save_path.empty()) {
            std::cerr << "Could not auto-locate a Tiny Rogues save. Drag/drop Public_Slot*_Save*.json onto this exe or run with --save PATH.\n";
            if (!args.no_pause) { std::cout << "Press Enter to exit..."; std::cin.get(); }
            return 2;
        }
        json save = read_json(args.save_path);
        json ids = read_json(args.ids_path);
        std::string report = build_report(save, ids, args.save_path);
        std::cout << report;
        std::ofstream out(args.report_path);
        if (!out) throw std::runtime_error("Could not write report: " + args.report_path);
        out << report;
        std::cout << "\nWrote " << args.report_path << "\n";
        if (!args.no_pause) { std::cout << "Press Enter to exit..."; std::cin.get(); }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << "\n";
        if (argc <= 1) { std::cout << "Press Enter to exit..."; std::cin.get(); }
        return 1;
    }
}
