// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#ifndef PARSEGTFS_H_
#define PARSEGTFS_H_

#define Edge tuple<double, double, double, double>
#define Point tuple<double, double>
#define TimeOt tuple<string, bool>

#include <gtest/gtest.h>
#include <map>
#include <vector>
#include <string>
#include <tuple>

#include "nlohmann/json.hpp"
using nlohmann::json;
using std::map;
using std::vector;
using std::string;
using std::tuple;

// Write json object to file.
void write_to_file(
    const json& json, const string& filename, const string& folder_name);

// Generate edge for bulding graph. List is ordered by edge_id.
// [([start_lat, start_lon, end_lat, end_lon], distance, shapes_tuple), ...]
void generate_edges_for_graph(
    const vector<Edge>& edges_list_by_edge_id,
    const vector<vector<tuple<string, uint32_t>>>&
        shapes_and_sequence_list_by_edge_id,
    const string& output_folder);

// Generate the edges for graph.
// Return map of shape_id to edge_id and list of edge_corrds ordered by edge_id.
// {"shape_id" : [edge1_id, edge2_id, ...]}, [edge1, edge2, ...]
const tuple<map<string, vector<uint32_t>>, vector<Edge>>
    generate_shapes_file_dicts(
        const string& gtfs_folder, const string& output_folder);

// Generate dicts from the stop_times file.
// trip_id => list of stop_times and stop_id,
//     {"trip_id": [(arrival_time, departure_time, stop_id), ...]}
// stop_id => list of trips with departure_time,
//     {"stop_id": [(trip_id, departure_time), ...]}
const map<string, vector<tuple<TimeOt, TimeOt, string>>>
    generate_stop_times_file_dicts(
        const string& gtfs_folder,
        const string& output_folder,
        const map<string, string> trip_id_to_route_id_map);

// Generate dicts from the stop_times file.
// stop_id => stop information,
//     {"stop_id" : (stop_name, stop_lat, stop_lon)}
// stop_name => list of stop_ids,
//     {"stop_name" : [stop_id1, stop_id2, ...]}
const json generate_stops_file_dicts(
    const string& gtfs_folder, const string& output_folder);

// With calendar file generate dicts.
// service_id => active weekdays and start/end date,
//     {"service_id" : (weekdays, (start_date, end_date))}
const map<string, tuple<vector<int>, string, string>>
    generate_service_id_information_map(const string& gtfs_folder);

// Generate dicts from calendar_dates file.
// service_id => list of extra dates and remove dates,
//     {"service_id" : (list_of_extra_dates, list_of_remove_dates)}
const map<string, tuple<vector<string>, vector<string>>>
    generate_service_id_to_date_and_exception(const string& gtfs_folder);

// I don't know what this does.
void generate_service_id_to_service_information_dict(
    const string& gtfs_folder, const string& output_folder);

// writes a JSON shape_id_to_trip_service_route_ids
// and generates two maps for future use:
// trip_id_to_route_id_map: {string trip_id: string route_id}
// and trip_id_to_shape_id_and_calendar_map: {string trip_id: (
//                                string shape_id,
//                                [int active weekdays],
//                                (string start_date, string end_date),
//                                [string extra_dates],
//                                [string removed_dates],
//                  )}
/// !!! Assumes calendar_dates.txt is sorted by service_id !!!
const tuple<const map<string, string>, const map<string, tuple<string, string>>>
    generate_trips_calendar_calendar_dates_file_dicts(
        const map<string, vector<uint32_t>>& shape_id_to_list_edge_ids_map,
        const vector<Edge>& edges_list_by_edge_id,
        const string& gtfs_folder, const string& output_folder);

// Generate dicts from routes file.
// route_id => route information
// {"route_id" : (agency_id, route_short_name, route_long_name,
//                route_description, route_type, route_color,
//                route_text_color)}
void generate_routes_file_dicts(
    const string& gtfs_folder, const string& output_folder);

// Generate list of stops consisting only of their location
// Returns [(stop1_lat, stop1_lon), (stop2_lat, stop2_lon), ...]
const vector<Point> get_list_of_stop_locations(
    const vector<string>& stops_info_list,
    const json& stop_id_to_stop_information_json);

// Generate list of stop ids
// Returns [stop_id1, stop_id2, ...]
const vector<string> get_list_of_stop_ids(
    const vector<tuple<tuple<string, bool>,
    tuple<string, bool>, string>>& stops_info_list);

// Generate a hash, by putting shape_id and all stop_ids into a string.
// "shape_id", ["stop_id1", "stop_id2", ...] =>
//      "shape_idstop_id1stop_id2..." => hash
size_t generate_shape_id_stop_ids_hash(
    const string& shape_id, const vector<string>& stop_ids);

// Take a list of stop locations, the polyline (by edge_ids)
// of the shape and edge_ids.
// Generate map of edges_id from polyline to trip_segment_ids.
// {edge_id: [trip_segment_id1, trip_segment_id2, ...]}
// due to json limitations, edge_id is a string.
const map<string, vector<uint32_t>> generate_edge_id_to_trip_segments_map(
    const vector<Point>& stop_locations,
    const vector<Edge>& polyline,
    const vector<uint32_t>& edge_ids);

// Take a list of edges of the polyline and a list stop location
// Generate Split the polyline into trip segments with stops
// return a list of polyline of the trip segments.
// Note that trip segments are only between stops.
vector<vector<Point>> generate_trip_segments_split_by_stops(
    const vector<Edge>& polyline,
    const vector<Point>& stop_locations);

// Return a hash value for a map from edge_id_to_trip_segment_id.
// also changes hash_to_edge_id_to_trip_segment_id_map.
// if the edge_id_to_trip_segment_id_map was not generated before add it.
// This is necessary to reduce the size of the json file. Trips that have
// the same shape_id and stop_ids, will also have the same edges.
size_t generate_hash_of_edge_id_to_trip_segement_id_map(
    const string& shape_id,
    const vector<string>& stop_ids,
    const json& stop_id_to_stop_information_json,
    const vector<Edge>& polyline,
    const vector<uint32_t>& edge_ids,
    map<size_t, tuple<map<string, vector<uint32_t>>, vector<vector<Point>>>>&
        hash_to_edge_id_to_trip_segment_id_map);

// Generate list of edges. Polyline contains list of edge_ids.
// Returns [(edge1_start, edge1_end), (edge2_start, edge2_end), ...])
const vector<Edge> get_polyline_from_edge_ids(
    const vector<uint32_t>& edge_ids_list,
    const vector<Edge>& edges_list_by_edge_id);

// Generate the trips with stops and times dict.
// This can be used to generate the trips with stops and times object in python.
// {"trip_id" : [hash_map_id_to_trip_segments, start_date, end_date,
//               [extra_dates], [removed_dates], [active_weekdays]]}
// the hash value is mapped to map_id_to_trip_segments.
// map_id_to_trip_segments is a dict with string as key, not tuple of doubles
// {"edge_id": trip_segment_id}
void generate_trips_with_stops_and_times(
    const map<string, vector<uint32_t>>& shape_id_to_list_edge_ids_map,
    const vector<Edge>& edges_list_by_edge_id,
    const map<string, tuple<string, string>>&
        trip_id_to_shape_id_and_calendar_map,
    const map<string, vector<
                tuple<tuple<string, bool>, tuple<string, bool>, string>>>&
        trip_id_to_stops_json,
    const json& stop_id_to_stop_information_json, const string& output_file);

#endif  // PARSEGTFS_H_
