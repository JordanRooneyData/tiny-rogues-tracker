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
    std::string csv_path = "report.csv";
    std::string character;
    int mode = 0;
    bool no_pause = false;
};

struct RouteSpec {
    std::string key;
    std::string label;
    std::string final_label;
    std::vector<int> completion_boss_ids;
    std::vector<int> entry_boss_ids;
    std::string source;
};

struct RunInfo {
    int class_id = -1;
    int cinder = 0;
    int floor_zero_based = -1;
    std::set<int> bosses;
};

struct SaveCandidate {
    fs::path path;
    std::string time_of_save;
    size_t run_count = 0;
    size_t cinder_history_count = 0;
    bool non_blank = false;
};

struct Row {
    int death_best = -1;
    int win_plus_best = -1;
    int best_floor = -1;
    int c16_death = 0;
    int c16_win_plus = 0;
    int runs = 0;
    std::map<std::string,int> route_best;
    std::map<std::string,int> route_c16;
};

static std::string get_env(const char* name) {
    const char* v = std::getenv(name);
    return v ? std::string(v) : std::string();
}

static json read_json(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("Could not open: " + path);
    json j;
    try { f >> j; }
    catch (const std::exception& e) { throw std::runtime_error("Malformed or unsupported JSON save/mapping: " + path + " (" + e.what() + ")"); }
    return j;
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

static bool history_entry_meaningful(const json& h) {
    if (!h.is_object()) return false;
    if (as_int(h, "highestUsedCinderThisRun", -1) >= 0) return true;
    if (as_int(h, "deathKills", 0) > 0) return true;
    if (as_int(h, "megaDeathKills", 0) > 0) return true;
    if (h.contains("cinderHistoryFlat") && h["cinderHistoryFlat"].is_array() && !h["cinderHistoryFlat"].empty()) return true;
    return false;
}

static bool save_has_meaningful_data(const json& save) {
    bool has_runs = save.contains("RunRecords") && save["RunRecords"].is_array() && !save["RunRecords"].empty();
    bool has_cinders = false;
    if (save.contains("CinderStreakHistory") && save["CinderStreakHistory"].is_array()) {
        for (const auto& h : save["CinderStreakHistory"]) if (history_entry_meaningful(h)) { has_cinders = true; break; }
    }
    return has_runs || has_cinders;
}

static bool parse_save_candidate(const fs::path& p, SaveCandidate& candidate) {
    try {
        if (!fs::is_regular_file(p)) return false;
        auto name = p.filename().string();
        if (name.rfind("Public_Slot", 0) != 0 || name.find("_Save") == std::string::npos || p.extension() != ".json") return false;
        json save = read_json(p.string());
        if (!save.is_object() || !save.contains("RunRecords") || !save["RunRecords"].is_array() ||
            !save.contains("CinderStreakHistory") || !save["CinderStreakHistory"].is_array()) return false;
        candidate.path = p;
        candidate.time_of_save = save.value("TimeOfSave", std::string("unknown"));
        candidate.run_count = save["RunRecords"].size();
        candidate.cinder_history_count = save["CinderStreakHistory"].size();
        candidate.non_blank = save_has_meaningful_data(save);
        return true;
    } catch (...) {
        return false;
    }
}

static void add_unique_path(std::vector<fs::path>& paths, const fs::path& candidate) {
    if (candidate.empty()) return;
    for (const auto& existing : paths) if (existing == candidate) return;
    paths.push_back(candidate);
}

static std::vector<fs::path> candidate_save_folders() {
    std::vector<fs::path> folders;
#ifdef _WIN32
    const fs::path tiny_rogues_suffix = fs::path("AppData") / "LocalLow" / "RubyDev" / "Tiny Rogues";
    auto user = get_env("USERPROFILE");
    if (!user.empty()) add_unique_path(folders, fs::path(user) / tiny_rogues_suffix);
    const fs::path users_root = fs::path("C:/Users");
    std::error_code ec;
    if (fs::exists(users_root, ec) && fs::is_directory(users_root, ec)) {
        for (const auto& entry : fs::directory_iterator(users_root, fs::directory_options::skip_permission_denied, ec)) {
            if (ec) break;
            if (!entry.is_directory(ec)) continue;
            add_unique_path(folders, entry.path() / tiny_rogues_suffix);
        }
    }
#else
    auto home = get_env("HOME");
    if (!home.empty()) add_unique_path(folders, fs::path(home));
#endif
    add_unique_path(folders, fs::current_path());
    return folders;
}

static std::vector<SaveCandidate> saves_in_folder(const fs::path& folder) {
    std::vector<SaveCandidate> saves;
    if (!fs::exists(folder) || !fs::is_directory(folder)) return saves;
    auto add = [&](const fs::path& p) {
        SaveCandidate c;
        if (!parse_save_candidate(p, c)) return;
        for (const auto& existing : saves) if (existing.path == c.path) return;
        saves.push_back(c);
    };
    for (const auto& name : {"Public_Slot1_Save1.json", "Public_Slot1_Save2.json", "Public_Slot1_Save3.json"}) add(folder / name);
    std::error_code ec;
    for (const auto& entry : fs::directory_iterator(folder, fs::directory_options::skip_permission_denied, ec)) {
        if (ec) break;
        add(entry.path());
    }
    std::sort(saves.begin(), saves.end(), [](const SaveCandidate& a, const SaveCandidate& b) {
        if (a.non_blank != b.non_blank) return a.non_blank > b.non_blank;
        std::error_code ea, eb;
        auto ta = fs::last_write_time(a.path, ea);
        auto tb = fs::last_write_time(b.path, eb);
        if (!ea && !eb && ta != tb) return ta > tb;
        return a.path.string() < b.path.string();
    });
    return saves;
}

static std::vector<SaveCandidate> collect_save_candidates() {
    std::vector<SaveCandidate> candidates;
    for (const auto& folder : candidate_save_folders()) {
        for (const auto& save : saves_in_folder(folder)) {
            bool seen = false;
            for (const auto& existing : candidates) if (existing.path == save.path) { seen = true; break; }
            if (!seen) candidates.push_back(save);
        }
    }
    std::sort(candidates.begin(), candidates.end(), [](const SaveCandidate& a, const SaveCandidate& b){
        if (a.non_blank != b.non_blank) return a.non_blank > b.non_blank;
        return a.path.string() < b.path.string();
    });
    return candidates;
}

static std::string select_save_from_candidates(const std::vector<SaveCandidate>& candidates, bool no_pause) {
    std::vector<SaveCandidate> non_blank;
    for (const auto& c : candidates) if (c.non_blank) non_blank.push_back(c);
    if (non_blank.empty()) return "";
    if (non_blank.size() == 1 || no_pause) return non_blank.front().path.string();
    while (true) {
        std::cout << "Multiple non-blank Tiny Rogues saves were found. Pick the save to read:\n";
        for (size_t i = 0; i < non_blank.size(); ++i) {
            std::cout << "  " << (i + 1) << ") " << non_blank[i].path.string()
                      << " | saved: " << non_blank[i].time_of_save
                      << " | runs: " << non_blank[i].run_count << "\n";
        }
        std::cout << "Enter 1-" << non_blank.size() << ", R retry, or Q exit: ";
        std::string line; std::getline(std::cin, line);
        std::transform(line.begin(), line.end(), line.begin(), [](unsigned char c){ return std::toupper(c); });
        if (line == "Q") std::exit(0);
        if (line == "R") return "";
        try { size_t choice = static_cast<size_t>(std::stoul(line)); if (choice >= 1 && choice <= non_blank.size()) return non_blank[choice - 1].path.string(); } catch (...) {}
        std::cout << "Invalid choice.\n";
    }
}

static std::string lookup_name(const json& ids, const std::string& section, int id, const std::string& fallback_prefix) {
    std::string key = std::to_string(id);
    if (ids.contains(section) && ids[section].contains(key) && ids[section][key].contains("name")) return ids[section][key]["name"].get<std::string>();
    return fallback_prefix + " " + key;
}

static bool contains_any(const std::set<int>& haystack, const std::vector<int>& needles) {
    for (int n : needles) if (haystack.count(n)) return true;
    return false;
}

static std::string join_ints(const std::vector<int>& values) {
    if (values.empty()) return "-";
    std::ostringstream ss;
    for (size_t i = 0; i < values.size(); ++i) { if (i) ss << ","; ss << values[i]; }
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
    for (const auto& key : order) {
        if (!ids.contains("routes") || !ids["routes"].contains(key) || !ids["routes"][key].is_object()) continue;
        const auto& r = ids["routes"][key];
        RouteSpec spec;
        spec.key = key;
        spec.label = r.value("label", key);
        spec.completion_boss_ids = json_int_vector(r.value("completion_boss_ids", json::array()));
        spec.entry_boss_ids = json_int_vector(r.value("entry_boss_ids", json::array()));
        spec.source = r.value("source", std::string());
        spec.final_label = spec.label;
        if (!spec.completion_boss_ids.empty()) spec.final_label = lookup_name(ids, "bosses", spec.completion_boss_ids.front(), spec.label);
        if (!spec.completion_boss_ids.empty()) routes.push_back(spec);
    }
    return routes;
}

static std::vector<RunInfo> parse_runs(const json& save) {
    if (!save.contains("RunRecords") || !save["RunRecords"].is_array()) throw std::runtime_error("Unsupported save: missing RunRecords array");
    if (!save.contains("CinderStreakHistory") || !save["CinderStreakHistory"].is_array()) throw std::runtime_error("Unsupported save: missing CinderStreakHistory array");
    std::vector<RunInfo> runs;
    for (const auto& r : save["RunRecords"]) {
        if (!r.is_object() || !r.contains("PlayedClass")) continue;
        RunInfo info;
        info.class_id = r["PlayedClass"].get<int>();
        info.cinder = as_int(r, "CinderLevel", 0);
        info.floor_zero_based = as_int(r, "FloorReached", -1);
        if (r.contains("bossesKilled") && r["bossesKilled"].is_array()) {
            for (const auto& b : r["bossesKilled"]) if (b.is_number_integer()) info.bosses.insert(b.get<int>());
        }
        runs.push_back(info);
    }
    return runs;
}

static int display_floor(const RunInfo& r) { return r.floor_zero_based < 0 ? -1 : r.floor_zero_based + 1; }
static bool is_death_clear(const RunInfo& r) { return r.bosses.count(18) > 0; }
static bool is_route_clear(const RunInfo& r, const RouteSpec& route) { return contains_any(r.bosses, route.completion_boss_ids); }
static bool is_win_plus(const RunInfo& r, const std::vector<RouteSpec>& routes) { for (const auto& route : routes) if (is_route_clear(r, route)) return true; return false; }

static std::string val_or_dash(int v) { return v < 0 ? std::string("—") : std::to_string(v); }

static std::set<int> all_character_ids(const json& save, const json& ids, const std::vector<RunInfo>& runs) {
    std::set<int> class_ids;
    if (ids.contains("characters") && ids["characters"].is_object()) {
        for (auto it = ids["characters"].begin(); it != ids["characters"].end(); ++it) { try { class_ids.insert(std::stoi(it.key())); } catch (...) {} }
    }
    const auto& streaks = save["CinderStreakHistory"];
    for (size_t i = 0; i < streaks.size(); ++i) class_ids.insert(static_cast<int>(i));
    for (const auto& r : runs) class_ids.insert(r.class_id);
    return class_ids;
}

static std::map<int, Row> compute_rows(const json& save, const std::set<int>& class_ids, const std::vector<RunInfo>& runs, const std::vector<RouteSpec>& routes) {
    std::map<int, Row> rows;
    const auto& streaks = save["CinderStreakHistory"];
    for (int cid : class_ids) {
        auto& row = rows[cid];
        for (const auto& route : routes) { row.route_best[route.key] = -1; row.route_c16[route.key] = 0; }
        // Reconciliation rule: RunRecords are authoritative for route outcomes and counts. CinderStreakHistory is used only as historical Death-clear best when deathKills proves a Death clear and no duplicate run identity exists to reconcile.
        if (cid >= 0 && cid < static_cast<int>(streaks.size()) && streaks[cid].is_object()) {
            int streak_best = as_int(streaks[cid], "highestUsedCinderThisRun", -1);
            int death_kills = as_int(streaks[cid], "deathKills", 0);
            if (death_kills > 0 && streak_best >= 0) row.death_best = std::max(row.death_best, streak_best);
        }
    }
    for (const auto& r : runs) {
        auto& row = rows[r.class_id];
        row.runs++;
        row.best_floor = std::max(row.best_floor, display_floor(r));
        if (is_death_clear(r)) { row.death_best = std::max(row.death_best, r.cinder); if (r.cinder == 16) row.c16_death++; }
        bool plus = false;
        for (const auto& route : routes) {
            if (is_route_clear(r, route)) {
                plus = true;
                row.route_best[route.key] = std::max(row.route_best[route.key], r.cinder);
                if (r.cinder == 16) row.route_c16[route.key]++;
            }
        }
        if (plus) { row.win_plus_best = std::max(row.win_plus_best, r.cinder); if (r.cinder == 16) row.c16_win_plus++; }
    }
    return rows;
}

static std::string matrix_outcome(const RunInfo& r, const std::vector<RouteSpec>& routes) {
    if (is_win_plus(r, routes)) return "Win+";
    int f = display_floor(r);
    if (f < 1) f = 1;
    return "Floor " + std::to_string(f);
}

static int resolve_character_value(const std::string& arg, const json& ids, const std::set<int>& class_ids) {
    try { return std::stoi(arg); } catch (...) {}
    std::string lowered = arg;
    std::transform(lowered.begin(), lowered.end(), lowered.begin(), [](unsigned char c){ return std::tolower(c); });
    for (int cid : class_ids) {
        std::string name = lookup_name(ids, "characters", cid, "Class ID");
        std::string n = name; std::transform(n.begin(), n.end(), n.begin(), [](unsigned char c){ return std::tolower(c); });
        if (n == lowered) return cid;
    }
    throw std::runtime_error("Unknown character value: " + arg);
}

static int choose_character(const json& ids, const std::set<int>& class_ids, const std::map<int, Row>& rows) {
    std::vector<int> ordered(class_ids.begin(), class_ids.end());
    while (true) {
        std::cout << "\nPick one character for the floor x cinder matrix:\n";
        for (size_t i = 0; i < ordered.size(); ++i) {
            auto it = rows.find(ordered[i]);
            int runs = it == rows.end() ? 0 : it->second.runs;
            std::cout << "  " << (i + 1) << ") " << lookup_name(ids, "characters", ordered[i], "Class ID") << " (runs: " << runs << ")\n";
        }
        std::cout << "Enter 1-" << ordered.size() << ", B back, M main menu, or Q exit: ";
        std::string line; std::getline(std::cin, line);
        std::string u = line; std::transform(u.begin(), u.end(), u.begin(), [](unsigned char c){ return std::toupper(c); });
        if (u == "Q") std::exit(0);
        if (u == "B" || u == "M") return -1;
        try { size_t n = std::stoul(line); if (n >= 1 && n <= ordered.size()) return ordered[n - 1]; } catch (...) {}
        std::cout << "Invalid choice.\n";
    }
}

static std::string view1_text(const json& ids, const std::set<int>& class_ids, const std::map<int, Row>& rows) {
    std::ostringstream out;
    out << "View 1 — Best records by character\n";
    out << "----------------------------------\n";
    out << std::left << std::setw(20) << "Character" << std::right << std::setw(8) << "Death" << std::setw(8) << "Win+" << std::setw(8) << "Eden" << std::setw(8) << "Amon" << std::setw(14) << "PrimalDeath" << std::setw(8) << "Runs" << std::setw(12) << "Best Floor" << "\n";
    out << std::string(86, '-') << "\n";
    for (int cid : class_ids) {
        const auto& row = rows.at(cid);
        out << std::left << std::setw(20) << lookup_name(ids, "characters", cid, "Class ID").substr(0, 19) << std::right
            << std::setw(8) << val_or_dash(row.death_best)
            << std::setw(8) << val_or_dash(row.win_plus_best)
            << std::setw(8) << val_or_dash(row.route_best.at("heaven"))
            << std::setw(8) << val_or_dash(row.route_best.at("hell"))
            << std::setw(14) << val_or_dash(row.route_best.at("law"))
            << std::setw(8) << row.runs
            << std::setw(12) << val_or_dash(row.best_floor) << "\n";
    }
    return out.str();
}

static std::string view2_text(const json& ids, const std::set<int>& class_ids, const std::map<int, Row>& rows) {
    std::ostringstream out;
    out << "View 2 — Cinder 16 clear counts by character\n";
    out << "--------------------------------------------\n";
    out << std::left << std::setw(20) << "Character" << std::right << std::setw(11) << "Death C16" << std::setw(10) << "Win+ C16" << std::setw(10) << "Eden C16" << std::setw(10) << "Amon C16" << std::setw(18) << "PrimalDeath C16" << "\n";
    out << std::string(79, '-') << "\n";
    for (int cid : class_ids) {
        const auto& row = rows.at(cid);
        out << std::left << std::setw(20) << lookup_name(ids, "characters", cid, "Class ID").substr(0, 19) << std::right
            << std::setw(11) << row.c16_death
            << std::setw(10) << row.c16_win_plus
            << std::setw(10) << row.route_c16.at("heaven")
            << std::setw(10) << row.route_c16.at("hell")
            << std::setw(18) << row.route_c16.at("law") << "\n";
    }
    return out.str();
}

static std::string matrix_text(int cid, const json& ids, const std::vector<RunInfo>& runs, const std::vector<RouteSpec>& routes) {
    std::vector<std::string> outcomes;
    outcomes.push_back("Win+");
    std::set<int> floors;
    for (const auto& r : runs) if (r.class_id == cid && !is_win_plus(r, routes)) floors.insert(std::max(1, display_floor(r)));
    for (int f : floors) outcomes.push_back("Floor " + std::to_string(f));
    if (outcomes.size() == 1) for (int f = 1; f <= 12; ++f) outcomes.push_back("Floor " + std::to_string(f));
    std::map<std::string, std::map<int,int>> matrix;
    for (const auto& o : outcomes) for (int c = 0; c <= 16; ++c) matrix[o][c] = 0;
    for (const auto& r : runs) if (r.class_id == cid && r.cinder >= 0 && r.cinder <= 16) matrix[matrix_outcome(r, routes)][r.cinder]++;
    std::ostringstream out;
    out << "View 3 — Character floor x cinder matrix: " << lookup_name(ids, "characters", cid, "Class ID") << "\n";
    out << "--------------------------------------------------------\n";
    out << std::left << std::setw(12) << "Outcome";
    for (int c = 0; c <= 16; ++c) out << std::right << std::setw(4) << c;
    out << "\n" << std::string(80, '-') << "\n";
    for (const auto& o : outcomes) {
        out << std::left << std::setw(12) << o.substr(0, 11);
        for (int c = 0; c <= 16; ++c) out << std::right << std::setw(4) << matrix[o][c];
        out << "\n";
    }
    out << "\nWin+ is terminal and mutually exclusive in this matrix: Eden, Amon, and PrimalDeath kills use the Win+ row instead of a normal floor row.\n";
    return out.str();
}

static std::string notes_text(const json& save, const json& ids, const std::vector<RunInfo>& runs, const std::vector<RouteSpec>& routes) {
    std::set<int> all_bosses_seen;
    std::set<int> cinders;
    for (const auto& r : runs) { cinders.insert(r.cinder); for (int b : r.bosses) all_bosses_seen.insert(b); }
    std::ostringstream out;
    out << "\nRoute decoding and validation notes\n";
    out << "-----------------------------------\n";
    out << "Save time: " << save.value("TimeOfSave", std::string("unknown")) << "\n";
    out << "Run records: " << runs.size() << "; CinderStreakHistory entries: " << save["CinderStreakHistory"].size() << "\n";
    out << "Recent cinder levels: " << join_ints(std::vector<int>(cinders.begin(), cinders.end())) << "\n";
    out << "Death clear: bossesKilled contains Death boss ID 18. Win+ requires a final route boss kill (Eden/Amon/PrimalDeath); reaching Bahamut/Tiamat/Geryon or their floor alone is not Win+.\n";
    out << "FloorReached is zero-based in the save; this report displays in-game floor as FloorReached + 1.\n";
    out << "Reconciliation: RunRecords are used for per-run route counts. CinderStreakHistory only supplements historical Death bests where deathKills proves clears absent from RunRecords; it is not double-counted as extra runs.\n";
    for (const auto& route : routes) {
        out << route.final_label << ": completion boss IDs " << join_names_for_ids(ids, route.completion_boss_ids);
        if (!route.entry_boss_ids.empty()) out << "; route-entry/reached-not-clear IDs " << join_names_for_ids(ids, route.entry_boss_ids);
        out << ".\n";
    }
    out << "Observed boss IDs in raw runs: " << join_ints(std::vector<int>(all_bosses_seen.begin(), all_bosses_seen.end())) << "\n";
    out << "Unresolved character mappings: ";
    bool any_unresolved = false;
    if (ids.contains("characters")) {
        for (auto it = ids["characters"].begin(); it != ids["characters"].end(); ++it) {
            std::string status = it.value().value("status", std::string());
            if (status.find("unresolved") != std::string::npos) { if (any_unresolved) out << ", "; out << it.key(); any_unresolved = true; }
        }
    }
    if (!any_unresolved) out << "none";
    out << "\nThis tool is read-only. It never writes to the Tiny Rogues save file. It writes only report files you choose.\n";
    return out.str();
}

static std::string build_report(const json& save, const json& ids, const std::string& save_path, int matrix_cid) {
    auto runs = parse_runs(save);
    auto routes = load_routes(ids);
    auto class_ids = all_character_ids(save, ids, runs);
    auto rows = compute_rows(save, class_ids, runs, routes);
    std::ostringstream out;
    out << "Tiny Rogues Tracker v2\n";
    out << "======================\n\n";
    out << "Save: " << save_path << "\n";
    out << "ID mapping: " << ids.value("provenance", json::object()).value("status", std::string("unknown")) << "\n\n";
    out << view1_text(ids, class_ids, rows) << "\n";
    out << view2_text(ids, class_ids, rows) << "\n";
    out << matrix_text(matrix_cid, ids, runs, routes);
    out << notes_text(save, ids, runs, routes);
    return out.str();
}

static void write_csv(const std::string& path, const json& save, const json& ids) {
    auto runs = parse_runs(save);
    auto routes = load_routes(ids);
    auto class_ids = all_character_ids(save, ids, runs);
    auto rows = compute_rows(save, class_ids, runs, routes);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("Could not write CSV: " + path);
    out << "view,character_id,character,death,win_plus,eden,amon,primal_death,runs,best_floor\n";
    for (int cid : class_ids) {
        const auto& row = rows[cid];
        std::string name = lookup_name(ids, "characters", cid, "Class ID");
        out << "best," << cid << ",\"" << name << "\"," << val_or_dash(row.death_best) << "," << val_or_dash(row.win_plus_best) << "," << val_or_dash(row.route_best.at("heaven")) << "," << val_or_dash(row.route_best.at("hell")) << "," << val_or_dash(row.route_best.at("law")) << "," << row.runs << "," << val_or_dash(row.best_floor) << "\n";
    }
    for (int cid : class_ids) {
        const auto& row = rows[cid];
        std::string name = lookup_name(ids, "characters", cid, "Class ID");
        out << "cinder16_counts," << cid << ",\"" << name << "\"," << row.c16_death << "," << row.c16_win_plus << "," << row.route_c16.at("heaven") << "," << row.route_c16.at("hell") << "," << row.route_c16.at("law") << ",," << "\n";
    }
}

static void write_reports(const Args& args, const json& save, const json& ids, const std::string& save_path, int matrix_cid) {
    std::string report = build_report(save, ids, save_path, matrix_cid);
    std::ofstream txt(args.report_path);
    if (!txt) throw std::runtime_error("Could not write report: " + args.report_path);
    txt << report;
    write_csv(args.csv_path, save, ids);
}

static void prompt_after_screen() {
    std::cout << "\nEnter B back, M main menu, or Q exit: ";
    std::string line; std::getline(std::cin, line);
    std::transform(line.begin(), line.end(), line.begin(), [](unsigned char c){ return std::toupper(c); });
    if (line == "Q") std::exit(0);
}

static int default_matrix_character(const std::set<int>& class_ids, const std::map<int, Row>& rows) {
    for (int cid : class_ids) { auto it = rows.find(cid); if (it != rows.end() && it->second.runs > 0) return cid; }
    return class_ids.empty() ? 0 : *class_ids.begin();
}

static void run_interactive(const Args& args, const json& save, const json& ids, const std::string& save_path) {
    auto runs = parse_runs(save);
    auto routes = load_routes(ids);
    auto class_ids = all_character_ids(save, ids, runs);
    auto rows = compute_rows(save, class_ids, runs, routes);
    int report_matrix_cid = default_matrix_character(class_ids, rows);
    write_reports(args, save, ids, save_path, report_matrix_cid);
    while (true) {
        std::cout << "\nTiny Rogues Tracker v2 — mode picker\n";
        std::cout << "Save: " << save_path << "\n";
        std::cout << "  1) Best records by character\n";
        std::cout << "  2) Cinder 16 clear counts by character\n";
        std::cout << "  3) Character floor x cinder matrix\n";
        std::cout << "Enter 1-3, Q exit: ";
        std::string line; std::getline(std::cin, line);
        std::transform(line.begin(), line.end(), line.begin(), [](unsigned char c){ return std::toupper(c); });
        if (line == "Q") return;
        if (line == "1") { std::cout << "\n" << view1_text(ids, class_ids, rows); prompt_after_screen(); }
        else if (line == "2") { std::cout << "\n" << view2_text(ids, class_ids, rows); prompt_after_screen(); }
        else if (line == "3") { int cid = choose_character(ids, class_ids, rows); if (cid >= 0) { std::cout << "\n" << matrix_text(cid, ids, runs, routes); prompt_after_screen(); } }
        else std::cout << "Invalid choice.\n";
    }
}

static Args parse_args(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        if (s == "--save" && i + 1 < argc) a.save_path = argv[++i];
        else if (s == "--ids" && i + 1 < argc) a.ids_path = argv[++i];
        else if (s == "--report" && i + 1 < argc) a.report_path = argv[++i];
        else if (s == "--csv" && i + 1 < argc) a.csv_path = argv[++i];
        else if (s == "--character" && i + 1 < argc) a.character = argv[++i];
        else if (s == "--mode" && i + 1 < argc) a.mode = std::stoi(argv[++i]);
        else if (s == "--no-pause") a.no_pause = true;
        else if (s == "--help" || s == "-h") {
            std::cout << "Usage: TinyRoguesTracker.exe [--save Public_Slot1_Save1.json] [--ids ids.json] [--report report.txt] [--csv report.csv] [--mode 1|2|3] [--character Druid|21] [--no-pause]\n";
            std::exit(0);
        }
    }
    return a;
}

int main(int argc, char** argv) {
    try {
        Args args = parse_args(argc, argv);
        while (args.save_path.empty()) {
            args.save_path = select_save_from_candidates(collect_save_candidates(), args.no_pause);
            if (!args.save_path.empty()) break;
            if (args.no_pause) break;
            std::cout << "No non-blank Tiny Rogues save found. A blank save parses but has empty RunRecords and no meaningful CinderStreakHistory.\n";
            std::cout << "Enter R retry or Q exit: ";
            std::string line; std::getline(std::cin, line);
            std::transform(line.begin(), line.end(), line.begin(), [](unsigned char c){ return std::toupper(c); });
            if (line == "Q") return 2;
        }
        if (args.save_path.empty()) {
            std::cerr << "Could not auto-locate a non-blank Tiny Rogues save. Drag/drop Public_Slot*_Save*.json onto this exe or run with --save PATH.\n";
            if (!args.no_pause) { std::cout << "Press Enter to exit..."; std::cin.get(); }
            return 2;
        }
        json save = read_json(args.save_path);
        if (!save_has_meaningful_data(save)) throw std::runtime_error("Selected save parses but appears blank: empty RunRecords and no meaningful CinderStreakHistory.");
        json ids = read_json(args.ids_path);
        auto runs = parse_runs(save);
        auto routes = load_routes(ids);
        if (routes.size() < 3) throw std::runtime_error("Unsupported ids.json: route mappings for Eden/Amon/Primal Death are incomplete");
        auto class_ids = all_character_ids(save, ids, runs);
        auto rows = compute_rows(save, class_ids, runs, routes);
        int matrix_cid = args.character.empty() ? default_matrix_character(class_ids, rows) : resolve_character_value(args.character, ids, class_ids);

        if (!args.no_pause && args.mode == 0 && args.character.empty()) {
            run_interactive(args, save, ids, args.save_path);
            return 0;
        }

        if (args.mode == 1) std::cout << view1_text(ids, class_ids, rows);
        else if (args.mode == 2) std::cout << view2_text(ids, class_ids, rows);
        else if (args.mode == 3) std::cout << matrix_text(matrix_cid, ids, runs, routes);
        else std::cout << build_report(save, ids, args.save_path, matrix_cid);
        write_reports(args, save, ids, args.save_path, matrix_cid);
        std::cout << "\nWrote " << args.report_path << " and " << args.csv_path << "\n";
        if (!args.no_pause) { std::cout << "Press Enter to exit..."; std::cin.get(); }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << "\n";
        if (argc <= 1) { std::cout << "Press Enter to exit..."; std::cin.get(); }
        return 1;
    }
}
