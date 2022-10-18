// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

// Output file names
#define EDGES_FOR_GRAPH_FILE \
    "edges_for_graph.json"
#define TRIP_ID_TO_ROUTE_ID_AND_LIST_OF_STOP_TIMES_AND_STOP_ID_FILE \
    "trip_id_to_route_id_and_list_of_stop_times_and_stop_id.json"
#define STOP_ID_TO_TRIPS_WITH_DEPARTURE_TIME_FILE \
    "stop_id_to_trips_with_departure_time.json"
#define STOP_ID_TO_STOP_INFORMATION_FILE \
    "stop_id_to_stop_information.json"
#define STOP_NAME_TO_LIST_OF_STOP_IDS_FILE \
    "stop_name_to_list_of_stop_ids.json"
#define SHAPE_ID_TO_TRIP_SERVICE_ROUTE_IDS_FILE \
    "shape_id_to_trip_service_route_ids.json"
#define ROUTE_ID_TO_ROUTE_INFORMATION_FILE \
    "route_id_to_route_information.json"
#define TRIPS_WITH_STOPS_AND_TIMES_FILE \
    "trips_with_stops_and_times.json"
#define MAP_HASH_TO_EDGE_ID_TO_TRIP_SEGMENT_ID \
    "map_hash_to_edge_id_to_trip_segment_id.json"
#define SERVICE_ID_TO_SERVICE_INFORMATION \
    "service_id_to_service_information.json"

// Default values for generation
#define ROUTE_COLOR_DEFAULT "777777"
#define ROUTE_TEXT_COLOR_DEFAULT "FFFFFF"
#define STOP_OFFSET_SLACK 0.00010
#define METERS_TO_DEGREES 0.000008993
#define MAX_DISTANCE_STOP_TO_EDGE 0.00025

#define Point tuple<double, double>
#define Edge tuple<double, double, double, double>
#define DateOt tuple<string, bool>

#define CSV_READER(x, y) \
    io::CSVReader<x, io::trim_chars<>, io::double_quote_escape<',', '"'>> \
    in(gtfs_folder + y);

#include <fstream>
#include <iostream>
#include <map>
#include <vector>
#include <string>
#include <tuple>
#include <utility>
#include "./utils.h"
#include "./parseGTFS.h"
#include "nlohmann/json.hpp"
#include "csv-parser/csv.h"

using std::string;
using std::vector;
using std::map;
using std::tuple;
using std::get;
using std::stod;
using std::make_tuple;
using nlohmann::json;

// ___________________________________________________________________________
void write_to_file(
    const json& json, const string& filename, const string& folder_name) {
    std::cout << "Writing to file: " << folder_name << filename \
              << " ..." << std:: endl;
    std::ofstream file;
    file.open(folder_name + filename);
    file << json;
    file.close();
    std::cout << "Done writing file!" << std::endl;
}

// ___________________________________________________________________________
void generate_edges_for_graph(
    const vector<Edge>& edges_list_by_edge_id,
    const vector<vector<tuple<string, uint32_t>>>&
        shapes_and_sequence_list_by_edge_id,
    const string& output_folder) {

    vector<tuple<Edge, double, vector<tuple<string, uint32_t>>>> graph_edges;

    for (size_t i = 0; i < edges_list_by_edge_id.size(); i++) {
        const Edge& edge = edges_list_by_edge_id[i];
        const double edge_length = great_circle_distance(edge);
        const vector<tuple<string, uint32_t>>& shapes_and_sequence =
            shapes_and_sequence_list_by_edge_id[i];
        graph_edges.push_back(
            make_tuple(edges_list_by_edge_id.at(i),
                       edge_length, shapes_and_sequence));
    }
    json j = graph_edges;
    write_to_file(j, EDGES_FOR_GRAPH_FILE, output_folder);
}

// ___________________________________________________________________________
const tuple<map<string, vector<uint32_t>>, vector<Edge>>
    generate_shapes_file_dicts(const string& gtfs_folder,
                               const string& output_folder) {
    CSV_READER(3, "shapes.txt");
    in.read_header(io::ignore_extra_column,
        "shape_id", "shape_pt_lat", "shape_pt_lon");

    vector<Edge> edges_list_by_edge_id;
    map<Edge, uint32_t> edge_to_edge_ids_map;
    map<string, vector<uint32_t>> shape_id_to_list_edge_ids_map;
    vector<vector<tuple<string, uint32_t>>> shapes_and_sequence_by_edge_id;

    uint32_t edge_id = 0; uint32_t shape_pt_sequence = 1;
    string last_shape_id = ""; string last_lat = ""; string last_lon = "";

    string shape_id; string shape_pt_lat; string shape_pt_lon;

    while (in.read_row(shape_id, shape_pt_lat, shape_pt_lon)) {
        // Only edges if the shape is the same
        // thus always ignore the first points, since no edge can be made
        if (!(last_shape_id.empty() && last_lat.empty() && last_lon.empty()) &&
             (shape_id == last_shape_id)) {
            // make edge from last point to current point
            Edge edge = make_tuple(stod(last_lat), stod(last_lon),
                                   stod(shape_pt_lat), stod(shape_pt_lon));
            // calculate the length of the edge

            // get the edge_id of current edge
            uint32_t current_edge_id;
            if (edge_to_edge_ids_map.count(edge) == 0) {
                // if edge is unseen, generate edge_id and add to list of edges
                current_edge_id = edge_id;
                edge_to_edge_ids_map.insert(make_pair(edge, edge_id++));
                edges_list_by_edge_id.push_back(edge);

                // add edge information to shapes_and_sequence_by_edge_id
                // at the location of edge_id
                shapes_and_sequence_by_edge_id.push_back(
                    {make_tuple(shape_id, shape_pt_sequence++)});
            } else {
                // otherwise the edge already has an edge_id
                current_edge_id = edge_to_edge_ids_map.at(edge);
                // append edge information to existing list
                shapes_and_sequence_by_edge_id.at(current_edge_id).push_back(
                        make_tuple(shape_id, shape_pt_sequence++));
            }

            // add current edge_id to list of corresponding shape_id
            shape_id_to_list_edge_ids_map[shape_id].push_back(current_edge_id);

        } else if (shape_id != last_shape_id) {
            // if shape_id is different, reset the sequence number
            shape_pt_sequence = 1;
        }
        last_shape_id = shape_id;
        last_lat = shape_pt_lat;
        last_lon = shape_pt_lon;
    }

    generate_edges_for_graph(
        edges_list_by_edge_id, shapes_and_sequence_by_edge_id, output_folder);

    // {"shape_id" : [edge1_id, edge2_id, ...]}
    // [edge1, edge2, ...]
    return make_tuple(shape_id_to_list_edge_ids_map, edges_list_by_edge_id);
}

// ___________________________________________________________________________
const map<string, vector<tuple<DateOt, DateOt, string>>>
    generate_stop_times_file_dicts(
        const string& gtfs_folder,
        const string& output_folder,
        const map<string, string> trip_id_to_route_id_map) {
    CSV_READER(4, "stop_times.txt")
    in.read_header(io::ignore_extra_column,
        "trip_id", "arrival_time", "departure_time", "stop_id");

    map<string, tuple<string, vector<tuple<DateOt, DateOt, string>>>>
        trip_id_to_info_map;

    map<string, vector<tuple<DateOt, DateOt, string>>>
        trip_id_to_info_no_route_id_map;

    json j1; string trip_id; string arrival_time;
    string departure_time; string stop_id;

    while (in.read_row(trip_id, arrival_time, departure_time, stop_id)) {
        j1[stop_id].push_back(make_tuple(trip_id, departure_time));

        if (trip_id_to_info_map.count(trip_id) == 0) {
            if (trip_id_to_route_id_map.count(trip_id) == 0) {
                continue;
            }
            get<0>(trip_id_to_info_map[trip_id]) =
                trip_id_to_route_id_map.at(trip_id);
        }
        tuple<DateOt, DateOt, string> info =
            make_tuple(convert_GTFS_date_to_string(arrival_time),
                       convert_GTFS_date_to_string(departure_time), stop_id);

        std::get<1>(trip_id_to_info_map.at(trip_id)).push_back(info);

        trip_id_to_info_no_route_id_map[trip_id].push_back(info);
    }
    write_to_file(j1, STOP_ID_TO_TRIPS_WITH_DEPARTURE_TIME_FILE, output_folder);
    json j2 = trip_id_to_info_map;
    write_to_file(j2,
                  TRIP_ID_TO_ROUTE_ID_AND_LIST_OF_STOP_TIMES_AND_STOP_ID_FILE,
                  output_folder);

    return trip_id_to_info_no_route_id_map;
}

// ___________________________________________________________________________
const json generate_stops_file_dicts(const string& gtfs_folder,
                                     const string& output_folder) {
    CSV_READER(4, "stops.txt")
    in.read_header(io::ignore_extra_column,
        "stop_id", "stop_name", "stop_lat", "stop_lon");

    json j1; json j2;
    string stop_id; string stop_name; double stop_lat; double stop_lon;
    while (in.read_row(stop_id, stop_name, stop_lat, stop_lon)) {
        j1[stop_id] = make_tuple(stop_name, stop_lat, stop_lon);
        if (j2.count(stop_name) == 0) j2[stop_name] = vector<string>();
        j2[stop_name].push_back(stop_id);
    }

    // {"stop_id" : ("stop_name", stop_lat, stop_lon)}
    write_to_file(j1, STOP_ID_TO_STOP_INFORMATION_FILE, output_folder);
    write_to_file(j2, STOP_NAME_TO_LIST_OF_STOP_IDS_FILE, output_folder);

    return j1;
}

// ___________________________________________________________________________
const map<string, tuple<vector<string>, vector<string>>>
    generate_service_id_to_date_and_exception(const string& gtfs_folder) {
    CSV_READER(3, "calendar_dates.txt")
    in.read_header(io::ignore_extra_column,
        "service_id", "date", "exception_type");

    // first tuple entry is extra_dates and second is removed_dates
    map<string, tuple<vector<string>, vector<string>>> service_id_to_info;

    string calendar_service_id; string date; string exception_type;
    while (in.read_row(calendar_service_id, date, exception_type)) {
        // add date to extra_dates if exception_type is 1
        if (exception_type == "1") {
            get<0>(service_id_to_info[calendar_service_id]).push_back(date);
        // add date to removed_dates if exception_type is 2
        } else if (exception_type == "2") {
            get<1>(service_id_to_info[calendar_service_id]).push_back(date);
        } else {
            throw std::runtime_error("Invalid exception_type.");
        }
    }

    return service_id_to_info;
}

// ___________________________________________________________________________
void generate_service_id_to_service_information_dict(
    const string& gtfs_folder, const string& output_folder) {

    // generate service_id >> extra_dates and removed_dates map
    const map<string, tuple<vector<string>, vector<string>>>
        service_id_calendar_dates_map =
            generate_service_id_to_date_and_exception(gtfs_folder);

    CSV_READER(10, "calendar.txt")
    in.read_header(io::ignore_extra_column,
        "service_id", "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday", "start_date", "end_date");

    json j;
    string service_id; string monday; string tuesday; string wednesday;
    string thursday; string friday; string saturday; string sunday;
    string start_date; string end_date;
    while (in.read_row(service_id, monday, tuesday, wednesday, thursday,
                       friday, saturday, sunday, start_date, end_date)) {
        // add days on which the service_id is active to the list/vector
        vector<int> weekdays = vector<int>();
        if (std::stoi(monday)) weekdays.push_back(0);
        if (std::stoi(tuesday)) weekdays.push_back(1);
        if (std::stoi(wednesday)) weekdays.push_back(2);
        if (std::stoi(thursday)) weekdays.push_back(3);
        if (std::stoi(friday)) weekdays.push_back(4);
        if (std::stoi(saturday)) weekdays.push_back(5);
        if (std::stoi(sunday)) weekdays.push_back(6);

        // get extra and removed dates of trip
        // for some services this is empty
        vector<string> extra_dates; vector<string> removed_dates;
        if (service_id_calendar_dates_map.count(service_id) != 0) {
            const auto[extra, removed] =
                service_id_calendar_dates_map.at(service_id);
            extra_dates = extra;
            removed_dates = removed;
        }

        j[service_id] = make_tuple(weekdays, start_date, end_date,
                                   extra_dates, removed_dates);
    }

    write_to_file(j, SERVICE_ID_TO_SERVICE_INFORMATION, output_folder);
}

// ___________________________________________________________________________
const tuple<const map<string, string>,
            const map<string, tuple<string, string>>>
    generate_trips_calendar_calendar_dates_file_dicts(
        const map<string, vector<uint32_t>>& shape_id_to_list_edge_ids_map,
        const vector<Edge>& edges_list_by_edge_id,
        const string& gtfs_folder, const string& output_folder) {
    CSV_READER(4, "trips.txt")
    in.read_header(io::ignore_extra_column,
        "route_id", "service_id", "trip_id", "shape_id");

    // generate map trip_id => route_id
    map<string, string> trip_id_to_route_id_map;

    map<string, tuple<string, string>> trip_id_to_shape_id_and_service_id;

    json j1;
    string route_id; string service_id; string trip_id; string shape_id;
    while (in.read_row(route_id, service_id, trip_id, shape_id)) {
        // save first edge of shape in the json at the first position
        if (j1[shape_id].empty()) {
            if (shape_id_to_list_edge_ids_map.count(shape_id) == 0) {
                continue;
            }
            uint32_t edge_id = shape_id_to_list_edge_ids_map.at(shape_id).at(0);
            j1[shape_id].push_back(edges_list_by_edge_id.at(edge_id));
        }

        // generate shape_id_to_service_id_map
        j1[shape_id].push_back(make_tuple(trip_id, service_id, route_id));

        // generate trip_id_to_route_id_map
        if (trip_id_to_route_id_map.count(trip_id) == 0)
            trip_id_to_route_id_map.insert(make_pair(trip_id, route_id));

        trip_id_to_shape_id_and_service_id[trip_id] =
            make_tuple(shape_id, service_id);
    }

    write_to_file(j1, SHAPE_ID_TO_TRIP_SERVICE_ROUTE_IDS_FILE, output_folder);

    return make_tuple(trip_id_to_route_id_map,
                      trip_id_to_shape_id_and_service_id);
}

// ___________________________________________________________________________
void generate_routes_file_dicts(const string& gtfs_folder,
                                const string& output_folder) {
    try {
        CSV_READER(5, "routes.txt")
        in.read_header(io::ignore_extra_column,
            "route_id", "route_short_name",
            "route_type", "route_color", "route_text_color");

        json j;
        string route_id; string route_short_name;
        string route_type; string route_color;
        string route_text_color;

        while (in.read_row(route_id, route_short_name,
                        route_type, route_color, route_text_color)) {
            // route color and text color are optional, we need them for drawing
            if (route_color.empty())
                route_color = ROUTE_COLOR_DEFAULT;
            if (route_text_color.empty())
                route_text_color = ROUTE_TEXT_COLOR_DEFAULT;

            j[route_id] = make_tuple(route_short_name, std::stoi(route_type),
                                    route_color, route_text_color);
        }

        write_to_file(j, ROUTE_ID_TO_ROUTE_INFORMATION_FILE, output_folder);
    } catch (const io::error::missing_column_in_header& e) {
        CSV_READER(3, "routes.txt")
        in.read_header(io::ignore_extra_column,
            "route_id", "route_short_name",
            "route_type");
        json j;
        string route_id; string route_short_name; string route_type;
        string route_color = ROUTE_COLOR_DEFAULT;
        string route_text_color = ROUTE_TEXT_COLOR_DEFAULT;

        while (in.read_row(route_id, route_short_name, route_type)) {
            // route color and text color are optional, we need them for drawing
            if (route_color.empty())
                route_color = ROUTE_COLOR_DEFAULT;
            if (route_text_color.empty())
                route_text_color = ROUTE_TEXT_COLOR_DEFAULT;

            j[route_id] = make_tuple(route_short_name, std::stoi(route_type),
                                    route_color, route_text_color);
        }

        write_to_file(j, ROUTE_ID_TO_ROUTE_INFORMATION_FILE, output_folder);
    }
}

// ___________________________________________________________________________
const vector<Point> get_list_of_stop_locations(
    const vector<string>& stops_info_list,
    const json& stop_id_to_stop_information_json) {
    vector<Point> stop_locations;

    for (const auto& stop_id : stops_info_list) {
        if (stop_id_to_stop_information_json.count(stop_id) == 0) {
            std::cout << "Error in get_list_of_stop_locations\n"
                      << "stop_id " << stop_id
                      << " not found in stop_id_to_stop_information_json"
                      << std::endl;
            continue;
        }
        const tuple<string, double, double> stop_information =
            stop_id_to_stop_information_json[stop_id];

        const auto&[stop_name, stop_lat, stop_lon] = stop_information;

        stop_locations.push_back(make_tuple(stop_lat, stop_lon));
    }

    return stop_locations;
}

// ___________________________________________________________________________
const vector<string> get_list_of_stop_ids(
    const vector<tuple<DateOt, DateOt, string>>& stops_info_list) {

    vector<string> stop_ids;

    for (const auto&[arrival_time, departure_time, stop_id] : stops_info_list) {
        stop_ids.push_back(stop_id);
    }

    return stop_ids;
}

// ___________________________________________________________________________
size_t generate_shape_id_stop_ids_hash(
    const string& shape_id, const vector<string>& stop_ids) {

    string shape_id_shop_ids_string = shape_id;

    for (const auto& stop_id : stop_ids) {
        shape_id_shop_ids_string += stop_id;
    }

    return std::hash<string>{}(shape_id_shop_ids_string);
}

// ___________________________________________________________________________
const map<string, vector<uint32_t>> generate_edge_id_to_trip_segments_map(
    const vector<Point>& stop_locations,
    const vector<Edge>& polyline,
    const vector<uint32_t>& edge_ids) {

    map<string, vector<uint32_t>> edge_id_to_trip_segment_id_map;

    size_t start_id = 0;

    vector<double> distances;
    for (size_t id_stop = 0; id_stop < stop_locations.size(); id_stop++) {
        const auto[stop_lat, stop_lon] = stop_locations[id_stop];

        double min_distance = 1000000000;
        for (size_t idx = 0; idx < polyline.size(); idx++) {
            const auto[edge_start_lat, edge_start_lon,
                       edge_end_lat, edge_end_lon] = polyline[idx];

            const double distance = distance_line_point(
                edge_start_lat, edge_start_lon,
                edge_end_lat, edge_end_lon,
                stop_lat, stop_lon);
            if (distance < min_distance) {
                min_distance = distance;
            }
        }
        distances.push_back(min_distance + STOP_OFFSET_SLACK);
    }

    for (size_t ts_id = 0; ts_id < stop_locations.size(); ts_id++) {
        const auto[stop_lat, stop_lon] = stop_locations[ts_id];
        double old_distance = 1000000000;
        size_t edge_nr = polyline.size() - 1;

        // find the edge that is closest to the stop
        // to avoid problems with loops, etc.
        // we start from the beginning and loop through the edges
        for (size_t idx = start_id; idx < polyline.size(); idx++) {
            const auto[edge_start_lat, edge_start_lon,
                       edge_end_lat, edge_end_lon] = polyline[idx];

            const double distance = distance_line_point(
                edge_start_lat, edge_start_lon,
                edge_end_lat, edge_end_lon,
                stop_lat, stop_lon);

            if ((old_distance > distances[ts_id] && ts_id != 0) ||
                distance <= old_distance) {
                old_distance = distance;
            } else {
                // we have found the closest edge, stop searching
                edge_nr = idx - 1;
                break;
            }
        }

        size_t end_id = edge_nr + 1;
        // skip the first stop, since there is not time for the edge
        if (ts_id > 0) {
            for (size_t i = start_id; i < end_id; i++) {
                // json keys need to be strings...
                const string edge_id = std::to_string(edge_ids[i]);
                edge_id_to_trip_segment_id_map[edge_id].push_back(ts_id - 1);
            }
        }
        start_id = edge_nr;
    }

    return edge_id_to_trip_segment_id_map;
}

// ___________________________________________________________________________
vector<vector<Point>> generate_trip_segments_split_by_stops(
    const vector<Edge>& polyline,
    const vector<Point>& stop_locations) {

    vector<vector<Point>> trip_segments_polyline;
    vector<double> distances;
    for (size_t id_stop = 0; id_stop < stop_locations.size(); id_stop++) {
        const auto[stop_lat, stop_lon] = stop_locations[id_stop];

        double min_distance = 1000000000;
        for (size_t idx = 0; idx < polyline.size(); idx++) {
            const auto[edge_start_lat, edge_start_lon,
                       edge_end_lat, edge_end_lon] = polyline[idx];

            const double distance = distance_line_point(
                edge_start_lat, edge_start_lon,
                edge_end_lat, edge_end_lon,
                stop_lat, stop_lon);
            if (distance < min_distance) {
                min_distance = distance;
            }
        }
        distances.push_back(min_distance + STOP_OFFSET_SLACK);
    }

    size_t last_edge_nr = 0;
    Point last_point_on_line;

    for (size_t id_stop = 0; id_stop < stop_locations.size(); id_stop++) {
        const auto[stop_lat, stop_lon] = stop_locations[id_stop];

        vector<Point> points_in_trip_segment;

        // only if we have a previous stop, add stop projected onto shape
        if (id_stop > 0) points_in_trip_segment.push_back(last_point_on_line);

        double old_distance = 1000000000;
        size_t edge_nr = polyline.size() - 1;
        for (size_t idx = last_edge_nr; idx < polyline.size(); idx++) {
            const auto[edge_start_lat, edge_start_lon,
                       edge_end_lat, edge_end_lon] = polyline[idx];

            const double distance = distance_line_point(
                edge_start_lat, edge_start_lon,
                edge_end_lat, edge_end_lon,
                stop_lat, stop_lon);

            if ((old_distance > distances[id_stop] && id_stop != 0) ||
                distance <= old_distance) {
                // we only need to add the end points
                // the start of the next edge is the same as current end
                points_in_trip_segment.push_back(
                    make_tuple(edge_end_lat, edge_end_lon));
                old_distance = distance;
            } else {
                // we have found the closest edge, stop searching
                edge_nr = idx - 1;
                break;
            }
        }

        // project the stop location onto the closest edge
        const auto[edge_start_lat, edge_start_lon,
                   edge_end_lat, edge_end_lon] = polyline[edge_nr];
        Point point_on_line = get_point_on_line(
            edge_start_lat, edge_start_lon, edge_end_lat, edge_end_lon,
            stop_lat, stop_lon);

        // points in front of the first stop can be discarded
        // points after the last stop can be discarded
        if (id_stop > 0) {
            points_in_trip_segment.push_back(point_on_line);
            trip_segments_polyline.push_back(points_in_trip_segment);
        }

        last_edge_nr = edge_nr;
        last_point_on_line = point_on_line;
    }

    return trip_segments_polyline;
}

// ___________________________________________________________________________
size_t generate_hash_of_edge_id_to_trip_segement_id_map(
    const string& shape_id, const vector<string>& stop_ids,
    const json& stop_id_to_stop_information_json,
    const vector<Edge>& polyline, const vector<uint32_t>& edge_ids,
    map<size_t, tuple<map<string, vector<uint32_t>>, vector<vector<Point>>>>&
        hash_of_edge_id_to_trip_segment_id_map) {
    // first generate a hash of the shape_id and stop_ids
    const size_t hash = generate_shape_id_stop_ids_hash(shape_id, stop_ids);

    // check if we have already had this hash before
    if (hash_of_edge_id_to_trip_segment_id_map.count(hash) == 0) {
        // if not add hash to map
        const vector<Point> stop_locations =
            get_list_of_stop_locations(
                stop_ids, stop_id_to_stop_information_json);

        hash_of_edge_id_to_trip_segment_id_map.insert(
            make_pair(hash, make_tuple(
                generate_edge_id_to_trip_segments_map(
                    stop_locations, polyline, edge_ids),
                generate_trip_segments_split_by_stops(
                    polyline, stop_locations))));
    }

    return hash;
}

// ___________________________________________________________________________
const vector<Edge> get_polyline_from_edge_ids(
    const vector<uint32_t>& edge_ids_list,
    const vector<Edge>& edges_list_by_edge_id) {

    const uint32_t num_edges = edge_ids_list.size();
    vector<Edge> polyline;
    polyline.reserve(num_edges);

    for (const auto edge_id : edge_ids_list) {
        polyline.push_back(edges_list_by_edge_id.at(edge_id));
    }

    return polyline;
}

// ___________________________________________________________________________
void generate_trips_with_stops_and_times(
    // {"shape_id" : [edge1_id, edge2_id, ...]}
    const map<string, vector<uint32_t>>& shape_id_to_list_edge_ids_map,
    // [edge1, edge2, ...]
    const vector<Edge>& edges_list_by_edge_id,
    // {"trip_id" : ("shape_id", "service_id")
    const map<string, tuple<string, string>>&
        trip_id_to_shape_id_and_calendar_map,
    // {"trip_id" : [(arrival_time, departure_time, stop_id), ...]}
    const map<string, vector<tuple<DateOt, DateOt, string>>>&
        trip_id_to_stops_json,
    // {"stop_id" : ("stop_name", stop_lat, stop_lon)}
    const json& stop_id_to_stop_information_json, const string& output_file) {

    json j;

    map<size_t, tuple<map<string, vector<uint32_t>>, vector<vector<Point>>>>
        map_hash_to_edge_id_to_trip_segment_id;

    // variables for progress measurement
    size_t counter = 0;
    const uint32_t num_trips = trip_id_to_shape_id_and_calendar_map.size();
    const uint32_t num_trips_modulo = num_trips / 10;

    for (const auto&[trip_id, shape_id_and_service_id] :
            trip_id_to_shape_id_and_calendar_map) {
        // add some time measurement, for every 1% of the file
        if (num_trips_modulo > 0 && counter++ % num_trips_modulo == 0) {
            std::cout << "Processing trip " << counter - 1
                      << " of " << num_trips << std::endl;
        }

        const auto&[shape_id, service_id] = shape_id_and_service_id;

        // check if trip actually has stops
        // should always be the case with GTFS standard
        if (trip_id_to_stops_json.count(trip_id) == 0) {
            std::cout << "Error in generate_trips_with_stops_and_time\n"
                      << "trip_id: " << trip_id
                      << " not found in trip_id_to_stops_json"
                      << std::endl;
            continue;
        }

        const vector<tuple<DateOt, DateOt, string>>& list_stop_info =
            trip_id_to_stops_json.at(trip_id);

        const vector<string> stop_ids_list =
            get_list_of_stop_ids(list_stop_info);

        // get the polyline (list of edges) for the shape of the trip
        // check if shape_id has polyline
        // should always be the case with GTFS standard
        if (shape_id_to_list_edge_ids_map.count(shape_id) == 0) {
            std::cout << "Error in generate_trips_with_stops_and_time\n"
                      << "trip_id: " << trip_id << " shape_id: " << shape_id
                      << " not found in shape_id_to_list_edge_ids_map"
                      << std::endl;
            continue;
        }

        const vector<uint32_t>& edge_ids =
            shape_id_to_list_edge_ids_map.at(shape_id);

        const vector<Edge> polyline =
            get_polyline_from_edge_ids(edge_ids, edges_list_by_edge_id);

        const size_t hash_value =
            generate_hash_of_edge_id_to_trip_segement_id_map(
                shape_id, stop_ids_list, stop_id_to_stop_information_json,
                polyline, edge_ids, map_hash_to_edge_id_to_trip_segment_id);

        j[trip_id] = make_tuple(hash_value, service_id);
    }

    write_to_file(j, TRIPS_WITH_STOPS_AND_TIMES_FILE, output_file);
    json j1 = map_hash_to_edge_id_to_trip_segment_id;
    write_to_file(j1, MAP_HASH_TO_EDGE_ID_TO_TRIP_SEGMENT_ID, output_file);
}
