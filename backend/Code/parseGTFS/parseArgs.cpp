// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#include <string.h>
#include <filesystem>
#include <iostream>
#include <vector>
#include <string>
#include <tuple>
#include "./parseArgs.h"

using std::vector;
using std::string;
using std::tuple;

// ___________________________________________________________________________
void print_help_and_exit() {
    std::cerr << "Usage: " << "<gtfs_folder_name> -o <output_folder_name>"
              << std::endl;
    std::cerr << "help or -h to show this message" << std::endl;
    std::cerr << "Empty folder name will use current folder." << std::endl;
    std::cerr << "Need to have these GTFS files in the folder:" << std::endl;
    std::cerr << "shapes.txt trips.txt stops.txt stop_times.txt "
              << "routes.txt calendar.txt calendar_dates.txt" << std::endl;
    exit(1);
}

// ___________________________________________________________________________
void print_folder_usage(
    const string& gtfs_folder_name, const string& output_folder_name) {
    if (gtfs_folder_name.empty()) {
        std::cout << "GTFS   folder: ." << std::endl;
    } else {
        std::cout << "GTFS   folder: " << gtfs_folder_name << std::endl;
    }
    if (output_folder_name.empty()) {
        std::cout << "Output folder: ." << std::endl;
    } else {
        std::cout << "Output folder: " << output_folder_name << std::endl;
    }
}

// ___________________________________________________________________________
void check_gtfs_files_exist(const string& folder_name) {
    vector<string> files_to_check = {
        "shapes.txt", "trips.txt", "stops.txt", "stop_times.txt",
        "routes.txt", "calendar.txt", "calendar_dates.txt"};

    for (const auto& file : files_to_check) {
        if (!std::filesystem::exists(folder_name + file)) {
            std::cerr << "Error: file " << file << " not found in folder "
                      << folder_name << std::endl;
            print_help_and_exit();
        }
    }
}

// ___________________________________________________________________________
const string add_slash(const string& folder_name) {
    if (!folder_name.empty() && folder_name.back() != '/') {
        return folder_name + "/";
    } else {
        return folder_name;
    }
}

// ___________________________________________________________________________
void check_folder_exists(
    const string& gtfs_folder_name, const string& output_folder_name) {
    if (gtfs_folder_name.empty() ||
        std::filesystem::is_directory(gtfs_folder_name)) {
        check_gtfs_files_exist(gtfs_folder_name);
    } else {
        std::cerr << "Error: "<< gtfs_folder_name << " does not exist"
                  << std::endl;
        print_help_and_exit();
    }

    if (!output_folder_name.empty() &&
        !std::filesystem::is_directory(output_folder_name)) {
        std::cerr << "Error: "<< output_folder_name << " does not exist"
                  << std::endl;
        print_help_and_exit();
    }
}

// ___________________________________________________________________________
const tuple<string, string> parse_arguments(int argc, char** argv) {
    string gtfs_folder_name = "";
    string output_folder_name = "";
    switch (argc) {
        case 1:
            break;
        case 2:
            if (strcmp(argv[1], "help") == 0 || strcmp(argv[1], "-h") == 0)
                print_help_and_exit();
            gtfs_folder_name = argv[1];
            break;
        case 3:
            if (strcmp(argv[1], "-o") == 0) {
                output_folder_name = argv[2];
            } else {
                print_help_and_exit();
            }
            break;
        case 4:
            if (strcmp(argv[2], "-o") == 0) {
                gtfs_folder_name = argv[1];
                output_folder_name = argv[3];
                break;
            }
        default:
            print_help_and_exit();
            break;
    }
    print_folder_usage(gtfs_folder_name, output_folder_name);
    gtfs_folder_name = add_slash(gtfs_folder_name);
    output_folder_name = add_slash(output_folder_name);
    check_folder_exists(gtfs_folder_name, output_folder_name);

    return make_tuple(gtfs_folder_name, output_folder_name);
}
