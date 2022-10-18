// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#ifndef UTILS_H_
#define UTILS_H_

#include <vector>
#include <string>
#include <tuple>

// Convert degrees to radians.
double degrees_to_radians(const double degrees);

// Calculate great circle distance between two points with haversine formula.
double great_circle_distance(
    const double lat1, const double lon1,
    const double lat2, const double lon2);

// Calculate great circle distance for an edge with the haversine formula.
double great_circle_distance(
    const std::tuple<double, double, double, double> edge);

// Given a line segment and a point, find the closest point on the line.
std::tuple<double, double> get_point_on_line(
    const double lineX1, const double lineY1,
    const double lineX2, const double lineY2,
    const double pointX, const double pointY);

// Calculate shortest distance between a line segment to a point.
double distance_line_point(
    const double lineX1, const double lineY1,
    const double lineX2, const double lineY2,
    const double pointX, const double pointY);

// Split a string by given delimiter, return a vector of strings.
const std::vector<std::string> split_by_delimiter(
    const std::string& str, const std::string& delimiter);

// GTFS times can hace more than 24 hours.
// Convert to less than 24 with overtime bool.
// Currently only works for less than 48 hours.
const std::tuple<std::string, bool> convert_GTFS_date_to_string(
    const std::string& time);

#endif  // UTILS_H_
