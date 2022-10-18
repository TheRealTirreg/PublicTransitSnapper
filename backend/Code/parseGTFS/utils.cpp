// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#define _USE_MATH_DEFINES
#define Edge tuple<double, double, double, double>

#include <cmath>
#include <iostream>
#include <vector>
#include <string>
#include <tuple>
#include "./utils.h"

using std::vector;
using std::string;
using std::tuple;

// ___________________________________________________________________________
double degrees_to_radians(const double degrees) {
    return degrees * M_PI / 180;
}

// ___________________________________________________________________________
double great_circle_distance(
    const double lat1, const double lon1,
    const double lat2, const double lon2) {
    const double radius = 6371e3;
    const double d_lat = degrees_to_radians(lat2 - lat1);
    const double d_lon = degrees_to_radians(lon2 - lon1);
    const double a = sin(d_lat/2.f) * sin(d_lat/2.f) +
        cos(degrees_to_radians(lat1)) * cos(degrees_to_radians(lat2)) *
        sin(d_lon/2.f) * sin(d_lon/2.f);
    const double c = 2 * atan2(sqrt(a), sqrt(1-a));
    return radius * c;
}

// ___________________________________________________________________________
double great_circle_distance(const Edge edge) {
    return great_circle_distance(
            std::get<0>(edge), std::get<1>(edge),
            std::get<2>(edge), std::get<3>(edge));
}

// ___________________________________________________________________________
tuple<double, double> get_point_on_line(
    const double lineX1, const double lineY1,
    const double lineX2, const double lineY2,
    const double pointX, const double pointY) {
    const double a = pointX - lineX1;
    const double b = pointY - lineY1;
    const double c = lineX2 - lineX1;
    const double d = lineY2 - lineY1;

    const double dot = a * c + b * d;
    const double len_sq = c * c + d * d;
    double param = -1;
    if (len_sq != 0) param = dot / len_sq;  // in case of 0 length line

    // check if point is closer to one of the endpoints or the line itself
    double xx, yy;
    if (param < 0 || (lineX1 == lineX2 && lineY1 == lineY2)) {
        xx = lineX1;
        yy = lineY1;
    } else if (param > 1) {
        xx = lineX2;
        yy = lineY2;
    } else {
        xx = lineX1 + param * c;
        yy = lineY1 + param * d;
    }

    return std::make_tuple(xx, yy);
}

// ___________________________________________________________________________
double distance_line_point(
    const double lineX1, const double lineY1,
    const double lineX2, const double lineY2,
    const double pointX, const double pointY) {

    const auto[lineX, lineY] = get_point_on_line(
        lineX1, lineY1, lineX2, lineY2, pointX, pointY);
    const double dx = pointX - lineX;
    const double dy = pointY - lineY;
    return sqrt(dx * dx + dy * dy);
}

// ___________________________________________________________________________
const vector<string> split_by_delimiter(
    const string& str, const string& delimiter) {
    vector<string> result;
    if (str.length() == 0) return result;
    size_t start = 0;
    size_t end = str.find(delimiter);
    while (end != string::npos) {
        result.push_back(str.substr(start, end - start));
        start = end + delimiter.length();
        end = str.find(delimiter, start);
    }

    result.push_back(str.substr(start));
    return result;
}

// ___________________________________________________________________________
const tuple<string, bool> convert_GTFS_date_to_string(const string& time) {
    const vector<string> tokens = split_by_delimiter(time, ":");
    if (tokens.size() != 3 || tokens[0].length() == 0 ||
        tokens[1].length() == 0 || tokens[2].length() == 0) {
        std::cerr << "Invalid time format: " << time << std::endl;
        exit(1);
    }
    bool overflow = false;
    int hour = std::stoi(tokens[0]);

    // check special case where time has 24 hours or more
    if (hour > 23) {
        hour = hour - 24;
        overflow = true;
    }
    // we can only handle max one additional day right now
    if (hour > 23) {
        std::cerr << "overflow < 24 hrs" << std::endl;
        exit(1);
    }

    const string minute = tokens[1];
    const string second = tokens[2];

    // minus can remove the leading zero, so we need to add it back
    string leading_zero;
    if (hour < 9) leading_zero = "0";

    return make_tuple(leading_zero + std::to_string(hour) +
                      ":" + minute + ":" + second, overflow);
}
