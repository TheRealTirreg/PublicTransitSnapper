// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#define Edge tuple<double, double, double, double>

#include <gtest/gtest.h>
#include <cstdio>
#include <fstream>
#include <map>
#include <string>
#include "./parseGTFS.h"

using std::map;
using std::vector;
using std::string;

// ___________________________________________________________________________
TEST(parseGTFSTest, write_to_file) {
    json j = {{"test", "test"}};
    write_to_file(j, "test.json", "test_files/jsons/");
    std::ifstream file("test_files/jsons/test.json");
    string content((std::istreambuf_iterator<char>(file)),
                   (std::istreambuf_iterator<char>()));
    string expected = "{\"test\":\"test\"}";
    ASSERT_STREQ(content.c_str(), expected.c_str());
    std::remove("test_files/jsons/test.json");
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_routes_file_dicts) {
    generate_routes_file_dicts("test_files/", "test_files/jsons/");

    std::ifstream file1("test_files/jsons/route_id_to_route_information.json");
    string content((std::istreambuf_iterator<char>(file1)),
                   (std::istreambuf_iterator<char>()));

    std::ifstream file2(
        "test_files/jsons/route_id_to_route_information.solution");
    string solution((std::istreambuf_iterator<char>(file2)),
                   (std::istreambuf_iterator<char>()));

    ASSERT_STREQ(content.c_str(), solution.c_str());
    std::remove("test_files/jsons/route_id_to_route_information.json");
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_shapes_file_dicts) {
    // also tests generate_edges_for_graph
    generate_shapes_file_dicts("test_files/", "test_files/jsons/");

    std::ifstream file1("test_files/jsons/edges_for_graph.json");
    string content((std::istreambuf_iterator<char>(file1)),
                   (std::istreambuf_iterator<char>()));

    std::ifstream file2("test_files/jsons/edges_for_graph.solution");
    string solution((std::istreambuf_iterator<char>(file2)),
                   (std::istreambuf_iterator<char>()));

    ASSERT_STREQ(content.c_str(), solution.c_str());
    std::remove("test_files/jsons/edges_for_graph.json");
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_trips_calendar_calendar_dates_file_dicts) {
    // also tests generate_service_id_information_map
    // and        generate_service_id_to_date_and_exception

    string gtfs = "test_files/"; string output = "test_files/jsons/";
    const auto[shape_id_to_list_edge_ids_map, edges_list_by_edge_id] =
            generate_shapes_file_dicts(gtfs, output);

    generate_trips_calendar_calendar_dates_file_dicts(
        shape_id_to_list_edge_ids_map, edges_list_by_edge_id,
        gtfs, output);

    std::ifstream file1(
        "test_files/jsons/shape_id_to_trip_service_route_ids.json");
    string content((std::istreambuf_iterator<char>(file1)),
                   (std::istreambuf_iterator<char>()));

    std::ifstream file2(
        "test_files/jsons/shape_id_to_trip_service_route_ids.solution");
    string solution((std::istreambuf_iterator<char>(file2)),
                   (std::istreambuf_iterator<char>()));

    ASSERT_STREQ(content.c_str(), solution.c_str());
    std::remove("test_files/jsons/shape_id_to_trip_service_route_ids.json");
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_stops_file_dicts) {
    generate_stops_file_dicts("test_files/", "test_files/jsons/");
    {
        std::ifstream file1(
            "test_files/jsons/stop_id_to_stop_information.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2(
            "test_files/jsons/stop_id_to_stop_information.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove("test_files/jsons/stop_id_to_stop_information.json");
    }
    {
        std::ifstream file1(
            "test_files/jsons/stop_name_to_list_of_stop_ids.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2(
            "test_files/jsons/stop_name_to_list_of_stop_ids.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove("test_files/jsons/stop_name_to_list_of_stop_ids.json");
    }
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_stop_times_file_dicts) {
    string gtfs = "test_files/"; string output = "test_files/jsons/";
    const auto[shape_id_to_list_edge_ids_map, edges_list_by_edge_id] =
        generate_shapes_file_dicts(gtfs, output);
    const auto[trip_id_to_route_id_map, trip_id_to_shape_id_and_calendar_map] =
        generate_trips_calendar_calendar_dates_file_dicts(
                shape_id_to_list_edge_ids_map, edges_list_by_edge_id,
                gtfs, output);
    std::remove("test_files/jsons/shape_id_to_trip_service_route_ids.json");
    generate_stop_times_file_dicts(gtfs, output, trip_id_to_route_id_map);
    {
        std::ifstream file1(
            "test_files/jsons/stop_id_to_trips_with_departure_time.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2(
            "test_files/jsons/stop_id_to_trips_with_departure_time.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove(((string) "test_files/jsons/stop_id_to"
                     + "_trips_with_departure_time.json").c_str());
    }
    {
        std::ifstream file1((string) "test_files/jsons/trip_id_to_route_id"
                            + "_and_list_of_stop_times_and_stop_id.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2((string) "test_files/jsons/trip_id_to_route_id"
                            + "_and_list_of_stop_times_and_stop_id.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove(((string) "test_files/jsons/trip_id_to_route_id_"
                     + "and_list_of_stop_times_and_stop_id.json").c_str());
    }
}

// ___________________________________________________________________________
TEST(parseGTFSTest, generate_trips_with_stops_and_times) {
    string gtfs = "test_files/"; string output = "test_files/jsons/";
    const auto[shape_id_to_list_edge_ids_map, edges_list_by_edge_id] =
        generate_shapes_file_dicts(gtfs, output);
    std::remove("test_files/jsons/edges_for_graph.json");

    const auto[trip_id_to_route_id_map, trip_id_to_shape_id_and_calendar_map] =
        generate_trips_calendar_calendar_dates_file_dicts(
            shape_id_to_list_edge_ids_map,
            edges_list_by_edge_id,
            gtfs, output);
    std::remove("test_files/jsons/stop_id_to_trips_with_departure_time.json");
    std::remove("test_files/jsons/shape_id_to_trip_service_route_ids.json");

    const auto stop_id_to_information_json = generate_stops_file_dicts(
        gtfs, output);
    std::remove("test_files/jsons/stop_id_to_stop_information.json");
    std::remove("test_files/jsons/stop_name_to_list_of_stop_ids.json");

    const auto trip_id_to_stops_json = generate_stop_times_file_dicts(
        gtfs, output, trip_id_to_route_id_map);

    std::remove("test_files/jsons/stop_id_to_trips_with_departure_time.json");
    std::remove(((string) "test_files/jsons/trip_id_to_route_id_"
                 + "and_list_of_stop_times_and_stop_id.json").c_str());

    generate_trips_with_stops_and_times(
        shape_id_to_list_edge_ids_map, edges_list_by_edge_id,
        trip_id_to_shape_id_and_calendar_map, trip_id_to_stops_json,
        stop_id_to_information_json, output);
    {
        std::ifstream file1(
            "test_files/jsons/trips_with_stops_and_times.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2(
            "test_files/jsons/trips_with_stops_and_times.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove("test_files/jsons/trips_with_stops_and_times.json");
    }
    {
        std::ifstream file1(
            "test_files/jsons/map_hash_to_edge_id_to_trip_segment_id.json");
        string content((std::istreambuf_iterator<char>(file1)),
                    (std::istreambuf_iterator<char>()));

        std::ifstream file2(
            "test_files/jsons/map_hash_to_edge_id_to_trip_segment_id.solution");
        string solution((std::istreambuf_iterator<char>(file2)),
                    (std::istreambuf_iterator<char>()));

        ASSERT_STREQ(content.c_str(), solution.c_str());
        std::remove(((string) "test_files/jsons/map_hash_to_edge"
                     + "_id_to_trip_segment_id.json").c_str());
    }
}
