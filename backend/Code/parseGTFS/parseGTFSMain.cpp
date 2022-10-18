// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#define TIME_MEASUREMENT_DECL \
    high_resolution_clock::time_point t1; \
    high_resolution_clock::time_point t2; uint64_t duration;
#define START_TIME_MEASUREMENT(x) \
    std::cout << "Processing " << x << " ..." << std::endl; \
    t1 = high_resolution_clock::now();
#define STOP_TIME_MEASUREMENT(x) \
    t2 = high_resolution_clock::now(); \
    duration = duration_cast<microseconds>(t2 - t1).count(); \
    std::cout << x << " done in " << duration / 1000000.f \
              << " seconds!" << std::endl;

#include <iostream>
#include <string>
#include <chrono>
#include "./parseArgs.h"
#include "./parseGTFS.h"

using std::chrono::duration_cast;
using std::chrono::high_resolution_clock;
using std::chrono::microseconds;
using std::string;

// Generate all necessary json files from GTFS data.
// Need to specify the path to the GTFS data.
void generate_all_dicts(
    const string& gtfs_folder, const string& output_folder) {
    TIME_MEASUREMENT_DECL
    std::cout << "Starting Generation of JSON files!" << std::endl;

    START_TIME_MEASUREMENT("routes.txt")
    generate_routes_file_dicts(gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("routes.txt")

    START_TIME_MEASUREMENT("calendar.txt, calendar_dates.txt")
    generate_service_id_to_service_information_dict(gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("calendar.txt, calendar_dates.txt")

    START_TIME_MEASUREMENT("shapes.txt")
    const auto[shape_id_to_list_edge_ids_map, edges_list_by_edge_id] =
        generate_shapes_file_dicts(gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("shapes.txt")

    START_TIME_MEASUREMENT("trips.txt")
    const auto[trip_id_to_route_id_map, trip_id_to_shape_id_and_service_id] =
        generate_trips_calendar_calendar_dates_file_dicts(
            shape_id_to_list_edge_ids_map,
            edges_list_by_edge_id,
            gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("trips.txt")

    START_TIME_MEASUREMENT("stops.txt")
    const auto stop_id_to_information_json = generate_stops_file_dicts(
        gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("stops.txt")

    START_TIME_MEASUREMENT("stop_times.txt")
    const auto trip_id_to_stops_json = generate_stop_times_file_dicts(
        gtfs_folder, output_folder, trip_id_to_route_id_map);
    STOP_TIME_MEASUREMENT("stop_times.txt")

    START_TIME_MEASUREMENT("trips_with_stops_and_times")
    generate_trips_with_stops_and_times(
        shape_id_to_list_edge_ids_map, edges_list_by_edge_id,
        trip_id_to_shape_id_and_service_id, trip_id_to_stops_json,
        stop_id_to_information_json, output_folder);
    STOP_TIME_MEASUREMENT("trips_with_stops_and_times")
}

int main(int argc, char *argv[]) {
    const auto[gtfs_folder, output_folder] = parse_arguments(argc, argv);
    TIME_MEASUREMENT_DECL
    START_TIME_MEASUREMENT("all dictionaries")
    generate_all_dicts(gtfs_folder, output_folder);
    STOP_TIME_MEASUREMENT("all dictionaries")
    return (0);
}
