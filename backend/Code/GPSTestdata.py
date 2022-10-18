"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, split, snap
from typing import List, Tuple, Dict
from math import cos, pi, floor
import Utilities as Utils
from random import sample


def calculate_polyline_length(polyline: List[Tuple[float, float]]) -> Tuple[float, list]:
    """
    Calculates the full length of a given polyline
    by calculating the distance from point to point.

    Input:
        polyline: List of Coordinates (lat, lon). Each coordinate is connected to its neighbors in the list.

    Returns:
        Total distance in kilometers
        List of individual distances between each given coordinate

    >>> freiburg_technische_fakultaet = (48.011757, 7.835033)
    >>> freiburg_elsaesser_strasse = (48.009848, 7.831772)
    >>> freiburg_berliner_allee_kurve_1 = (48.008026, 7.828907)
    >>> freiburg_berliner_allee_kurve_2 = (48.007710, 7.828768)
    >>> freiburg_berliner_allee_station = (48.007387, 7.829476)

    >>> polyline = [
    ...     freiburg_technische_fakultaet,
    ...     freiburg_elsaesser_strasse,
    ...     freiburg_berliner_allee_kurve_1,
    ...     freiburg_berliner_allee_kurve_2,
    ...     freiburg_berliner_allee_station
    ... ]

    >>> d = calculate_polyline_length(polyline)
    >>> from math import isclose
    >>> isclose(d[0], 0.716, rel_tol=0.01)
    True
    >>> r = [0.322341, 0.294058, 0.036627, 0.063750]
    >>> all(isclose(x, y, rel_tol=0.01) for x, y in zip(d[1], r))
    True
    """
    num_coordinates = len(polyline)
    distances = []

    for i in range(num_coordinates - 1):
        distances.append(
            Utils.great_circle_distance(polyline[i][0], polyline[i][1], polyline[i + 1][0], polyline[i + 1][1]) / 1000
        )

    return sum(distances), distances


def add_meters_to_coordinates(point: Tuple[float, float], dy, dx) -> Tuple[float, float]:
    """
    Adds an offset in meters to a given coordinate

    Input:
        point: (lat, lon) as a GPS coordinate (degrees)
        dy: offset that will be added to the latitude (in meters)
        dx: offset that will be added to the longitude (in meters)

    Returns:
        Point with the calculated offset.

    >>> freiburg_technische_fakultaet = (48.011757, 7.835033)
    >>> add_meters_to_coordinates(freiburg_technische_fakultaet, 10, 100)
    (48.011846831528416, 7.833609515722384)
    >>> add_meters_to_coordinates(freiburg_technische_fakultaet, 1000, -100)
    (48.0207401528412, 7.836456484277616)
    >>> add_meters_to_coordinates(freiburg_technische_fakultaet, -123, 0)
    (48.010652072200536, 7.835033)
    """
    r_earth = 6378137  # meters
    return point[0] + (180 / pi) * (dy / r_earth), point[1] + (180 / pi) * (dx / r_earth) / cos(point[0])


def get_point_on_polyline_segment(
        line: Tuple[Tuple[float, float], Tuple[float, float]],
        percentage: float,
        step=0.0005
) -> Tuple[float, float]:
    """
    Calculates the position of a device travelling on a line.

    Input:
        line: ((lat1, lon1), (lat2, lon2)) end points of the line
        percentage: specifies, how far the device has gone on the line.
            needs to be a value between 0 and 1
        step: the lower the value, the more accurate the location.
            This is especially important for longer line segments.
            default: 0.0005

    Returns:
        Point on percentage of the line.

    >>> freiburg_technische_fakultaet = (48.011757, 7.835033)
    >>> freiburg_elsaesser_strasse = (48.009848, 7.831772)

    >>> get_point_on_polyline_segment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.3)
    (48.01146429837473, 7.834533)
    >>> get_point_on_polyline_segment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.5)
    (48.01087889512419, 7.833533)
    >>> get_point_on_polyline_segment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.9)
    (48.01029349187366, 7.832533)
    """
    if percentage == 0:  # no movement
        return line[0]
    assert 0 < percentage < 1, "percentage needs to be a value between 0 and 1"

    y1, x1 = line[0]
    y2, x2 = line[1]
    y, x = line[0]      # y and x need to be initialized in case no loop runs

    if abs(y2 - y1) <= abs(x2 - x1):
        a = floor((x2 - x1) / step * percentage) + 1
        if a == 0:
            return y, x
        sgn = a // abs(a)
        for i in range(abs(a) + 1):
            x = x1 + i * step * sgn
            y = (y1 - y2) / (x1 - x2) * (x - x1) + y1
    else:
        a = floor((y2 - y1) / step * percentage) + 1
        if a == 0:
            return y, x
        sgn = a // abs(a)
        for i in range(abs(a) + 1):
            y = y1 + i * step * sgn
            x = (x1 - x2) / (y1 - y2) * (y - y1) + x1

    return y, x


def generate_points_along_line(
        polyline: List[Tuple[float, float]],
        num_signals: float,
        individual_polyline_lengths: List[float],
        avg_travelling_distance_meters: int
) -> Tuple[List[Tuple[float, float]], List[Tuple[Tuple[float, float], Tuple[float, float]]]]:
    """
    Generates a list of geolocation points along a given polyline

    Input:
        polyline: List of Coordinates (lat, lon). Each coordinate is connected to its neighbors in the list.
        num_signals: states how many points the output list will have
        individual_polyline_lengths: List of the lengths of each polyline segment (in km)
        avg_travelling_distance_meters_per_second: the average travelling distance of the device along the line (in m)

    >>> freiburg_technische_fakultaet = (48.011757, 7.835033)
    >>> freiburg_elsaesser_strasse = (48.009848, 7.831772)
    >>> freiburg_berliner_allee_kurve_1 = (48.008026, 7.828907)
    >>> freiburg_berliner_allee_kurve_2 = (48.007710, 7.828768)
    >>> freiburg_berliner_allee_station = (48.007387, 7.829476)

    >>> polyline = [
    ...     freiburg_technische_fakultaet,
    ...     freiburg_elsaesser_strasse,
    ...     freiburg_berliner_allee_kurve_1,
    ...     freiburg_berliner_allee_kurve_2,
    ...     freiburg_berliner_allee_station
    ... ]

    >>> avg_speed = 14  # m/s
    >>> signal_every_n_seconds = 5  # s

    >>> total_distance_in_km, individual_polyline_lengths = calculate_polyline_length(polyline)
    >>> total_time = (total_distance_in_km * 1000) // avg_speed
    >>> num_signals = total_time / signal_every_n_seconds
    >>> avg_travelling_distance = avg_speed * signal_every_n_seconds

    >>> from math import isclose
    >>> isclose(total_distance_in_km * 1000, 716.7778718160419, rel_tol=0.001)  # test in meters
    True
    >>> total_time == 51.0  # seconds (for 716.7778718160419m) with average speed of 14 m/s
    True
    >>> num_signals == 10.2  # => floor(10.2) = 10 GPS signals, as there is one signal every 5 seconds
    True
    >>> avg_travelling_distance == 70  # m/s
    True

    >>> points, edges = generate_points_along_line(
    ...                       polyline,num_signals,individual_polyline_lengths, avg_travelling_distance)
    >>> points == [(48.011757, 7.835033), (48.01146429837473, 7.834533), (48.01117159674946, 7.834033),
    ...     (48.01058619349892, 7.833033), (48.01029349187366, 7.832533), (48.009848, 7.831772),
    ...     (48.009530024432806, 7.831272), (48.00889407329843, 7.830272), (48.008576097731236, 7.829772),
    ...     (48.008026, 7.828907), (48.00725378531074, 7.8297680000000005)]
    True
    >>> edges == [((48.011757, 7.835033), (48.009848, 7.831772)), ((48.011757, 7.835033), (48.009848, 7.831772)),
    ...     ((48.011757, 7.835033), (48.009848, 7.831772)), ((48.011757, 7.835033), (48.009848, 7.831772)),
    ...     ((48.011757, 7.835033), (48.009848, 7.831772)), ((48.009848, 7.831772), (48.008026, 7.828907)),
    ...     ((48.009848, 7.831772), (48.008026, 7.828907)), ((48.009848, 7.831772), (48.008026, 7.828907)),
    ...     ((48.009848, 7.831772), (48.008026, 7.828907)), ((48.008026, 7.828907), (48.00771, 7.828768)),
    ...     ((48.00771, 7.828768), (48.007387, 7.829476))]
    True
    """
    current_polyline_part = 0
    points = [polyline[0]]  # initialize with start of polyline (starting point)
    edges = [(polyline[0], polyline[1])]  # initialize with first edge of polyline
    path_travelled_on_polyline_segment = 0

    for signal in range(int(num_signals)):
        # get length of current polyline segment
        length_polyline_segment = individual_polyline_lengths[current_polyline_part]

        # calculate path travelled on current polyline segment
        path_travelled_on_polyline_segment += avg_travelling_distance_meters / 1000

        # if the device has moved past a polyline segment,
        # go to the next segments until the next signal
        if length_polyline_segment < path_travelled_on_polyline_segment:
            overflow = abs(length_polyline_segment - path_travelled_on_polyline_segment)
            current_polyline_part += 1

            # skip short polyline segments in case they are shorter than the overflow
            while individual_polyline_lengths[current_polyline_part] < overflow:
                overflow -= individual_polyline_lengths[current_polyline_part]
                current_polyline_part += 1

            # get new length of current polyline segment
            length_polyline_segment = individual_polyline_lengths[current_polyline_part]

            # reset path_travelled_on_polyline_segment
            path_travelled_on_polyline_segment = overflow

        # get percentage of how much of the polyline segment has been travelled
        percentage = 1 - ((
            length_polyline_segment - path_travelled_on_polyline_segment) / length_polyline_segment)

        current_edge = (polyline[current_polyline_part], polyline[current_polyline_part + 1])

        # add new point to points
        points.append(get_point_on_polyline_segment(
            line=current_edge,
            percentage=percentage
        ))

        # remember the edges that a point belongs to
        edges.append(current_edge)

    return points, edges


def noisify_points(
        points: List[Tuple[float, float]],
        avg_gps_accuracy_in_meters: int = 18
) -> List[Tuple[float, float]]:
    """
    Takes a list of points and moves each points away a couple of meters
    Uses normal distribution to calculate the x and y offsets

    Input:
        points: List of GPS points
        avg_gps_accuracy_in_meters: the standard deviation from the accurate position

    Output:
        List of points where each point is close to its original point from the input list

    Testing is not possible because the function uses random numbers
    """
    mu = 0
    sigma = avg_gps_accuracy_in_meters
    num_points = len(points)
    x_deviations = np.random.normal(mu, sigma, num_points)
    y_deviations = np.random.normal(mu, sigma, num_points)
    noisified_points = []
    for i, point in enumerate(points):
        noisified_points.append(add_meters_to_coordinates(point, y_deviations[i], x_deviations[i]))
    return noisified_points


def gen_timestamps(
        trip, shape_points, points, points_edges, stops_info,
        date: datetime = datetime.now(), add_noise: bool = False,
        noise_stop: int = 0, noise_point: int = 0):
    """
    Generate plausible times for each point.
    Calculate how much of a route the train has travelled and
    get a time from it, might not be the most accurate

    normal distribution of variation in seconds can be added.
    For stop, all points between this stop and the next stop will have the same delay
        we only allow delay for stops, vehicles never leave before the scheduled time
    For point, each point will have a different delay / earliness

    >>> trip = "1.TA.91-10-A-j22-1.1.H"
    >>> shape = "shp_0_573"
    >>> shape_points = get_polyline(shape, "../GTFS/doctest_files/shapes.txt")
    >>> total_distance_in_km, individual_polyline_lengths = calculate_polyline_length(shape_points)
    >>> total_time = (total_distance_in_km * 1000) // 14
    >>> num_signals = total_time / 5
    >>> avg_travelling_distance_meters_per_second = 14 * 5
    >>> points, e = generate_points_along_line(
    ...                 shape_points, num_signals,
    ...                 individual_polyline_lengths, avg_travelling_distance_meters_per_second)
    >>> stop_info = get_stopinfo(
    ...                 trip, "../GTFS/doctest_files/stop_times.txt", "../GTFS/doctest_files/stops.txt")
    >>> ts = gen_timestamps(trip, shape_points, points, e, stop_info)
    >>> len(ts) == len(points) and ts == sorted(ts)
    True

    >>> trip = "1.TA.91-10-A-j22-1.2.H"
    >>> shape = "shp_0_42"
    >>> shape_points = get_polyline(shape, "../GTFS/doctest_files/shapes.txt")
    >>> total_distance_in_km, individual_polyline_lengths = calculate_polyline_length(shape_points)
    >>> total_time = (total_distance_in_km * 1000) // 14
    >>> num_signals = total_time / 5
    >>> avg_travelling_distance_meters_per_second = 14 * 5
    >>> points, e = generate_points_along_line(
    ...                 shape_points, num_signals,
    ...                 individual_polyline_lengths, avg_travelling_distance_meters_per_second)
    >>> stop_info = get_stopinfo(
    ...                 trip, "../GTFS/doctest_files/stop_times.txt", "../GTFS/doctest_files/stops.txt")
    >>> ts = gen_timestamps(trip, shape_points, points, e, stop_info)
    >>> len(ts) == len(points) and ts == sorted(ts)
    True
    """
    if add_noise:
        # at stops, never have negative delay, vehicles always leave on time or later
        stops_noise = list(map(lambda x: max(x, 0), np.random.normal(0, noise_stop, len(stops_info))))
        # on points, simulate faster and slower segments, e.g. due to traffic or traffic lights
        points_noise = list(np.random.normal(0, noise_point, len(points)))

    # generate edges from polyline
    edges, edges_length = [], []
    for edge in zip(shape_points[:-1], shape_points[1:]):
        edges.append(edge)
        edges_length.append(Utils.distance_wrapper(*edge))

    # find the minimum distances from stop to the polyline
    stop_min_distances = []
    for stop_info in stops_info:
        stop_location, _, _ = stop_info
        min_distance = None
        for edge in edges:
            distance = LineString(edge).distance(Point(stop_location))
            if min_distance is None or distance < min_distance:
                min_distance = distance

        stop_min_distances.append(min_distance + 0.0001)

    last_edge_id = 0
    edge_travelled_percentage, last_departure_time = None, None
    map_edges_to_time_length = {}

    # Go through all stops and find the edge that is closest. Go through edges in order
    # so that streets that are used multiple times by a shape match correctly.
    for id_stop, stop_info in enumerate(stops_info):
        stop_location, arrival_time, departure_time = stop_info

        # get the edge that is closest to the stop
        old_distance = 1000000000
        edge_nr = last_edge_id + len(edges[last_edge_id:]) - 1
        for idx in range(len(edges[last_edge_id:])):
            distance = LineString(edges[last_edge_id + idx]).distance(Point(stop_location))
            if (old_distance > stop_min_distances[id_stop] and id_stop != 0) or distance <= old_distance:
                old_distance = distance
            else:
                edge_nr = last_edge_id + idx - 1
                break

        last_edge_travelled_percentage = edge_travelled_percentage
        # this is the closest edge to the stop location
        edge = edges[edge_nr]
        edge_line_string = LineString(edge)
        # project the point onto the edge, then the distance to the start of the edge can be calculated
        if edge_line_string.length == 0:
            edge_travelled_percentage = 0
        else:
            edge_travelled_percentage = nearest_points(
                edge_line_string, Point(stop_location))[0].distance(Point(edge[0])) / edge_line_string.length

        # for the first stop, just skip most calculation, since there is no time for the edge
        if id_stop > 0:
            time_delta = Utils.time_difference_calculator(*last_departure_time, *arrival_time)
            time_from_start = timedelta(0)

            lengths = edges_length[last_edge_id:edge_nr + 1]

            # if start or end edge, do not use whole length of edge, stops may be on an edge
            lengths = [lengths[0] * last_edge_travelled_percentage] + \
                lengths[1:-1] + [lengths[-1] * edge_travelled_percentage]
            total_distance = sum(lengths)

            # generate the dict that maps edges to a start and stop time of the edge, as well as the length of the edge
            for i, (edge_coordinates, edge_length) in enumerate(zip(edges[last_edge_id:edge_nr + 1], lengths)):
                if i == 0:
                    percentage = last_edge_travelled_percentage
                elif i == len(edges[last_edge_id:edge_nr + 1]) - 1:
                    percentage = edge_travelled_percentage
                else:
                    percentage = 0

                # avoid division by zero
                if total_distance == 0:
                    current_edge_duration = timedelta(0)
                else:
                    current_edge_duration = edge_length / total_distance * time_delta

                # predicted times for start and end of edge
                edge_time_start = last_departure_time[0] + time_from_start, last_departure_time[1]
                edge_time_end = last_departure_time[0] + time_from_start + current_edge_duration, last_departure_time[1]

                if add_noise:
                    noise = timedelta(seconds=stops_noise[id_stop])
                else:
                    noise = timedelta(0)
                elem_to_add = (id_stop - 1, edge_time_start, edge_time_end, percentage, noise)
                if edge_coordinates in map_edges_to_time_length:
                    map_edges_to_time_length[edge_coordinates].append(elem_to_add)
                else:
                    map_edges_to_time_length[edge_coordinates] = [elem_to_add]

                time_from_start += current_edge_duration

        # there can be edges before the first stop, just give them the arrival time of the first stop
        elif id_stop == 0:
            for i, edge_coordinates in enumerate(edges[last_edge_id:edge_nr + 1]):
                edge_time_start, edge_time_end = arrival_time, arrival_time

                if add_noise:
                    noise = timedelta(seconds=stops_noise[id_stop])
                else:
                    noise = timedelta(0)
                elem_to_add = (id_stop - 1, edge_time_start, edge_time_end, 0, noise)
                if edge_coordinates in map_edges_to_time_length:
                    map_edges_to_time_length[edge_coordinates].append(elem_to_add)
                else:
                    map_edges_to_time_length[edge_coordinates] = [elem_to_add]

        last_departure_time = departure_time
        # remove edges that we have already looked at
        last_edge_id = edge_nr

    leftover_edges = edges[last_edge_id + 1:]
    if leftover_edges:
        for edge in leftover_edges:

            if add_noise:
                noise = timedelta(seconds=stops_noise[-1])
            else:
                noise = timedelta(0)
            elem_to_add = (len(stop_info) - 1, last_departure_time, last_departure_time, 0, noise)
            if edge in map_edges_to_time_length:
                map_edges_to_time_length[edge].append(elem_to_add)
            else:
                map_edges_to_time_length[edge] = [elem_to_add]

    year, month, day = date.year, date.month, date.day
    times = []
    next_day = False

    # now go through all generated points, and for each point find the closest edge
    # then calculate the time of the point based on how far along the edge it is
    for i, (test_point, edge_point) in enumerate(zip(points, points_edges)):
        edge_line_string = LineString(edge_point)
        # project the point onto the edge, then the distance to the start of the edge can be calculated
        if edge_line_string.length == 0:
            edge_travelled_percentage = 0
        else:
            edge_travelled_percentage = nearest_points(
                edge_line_string, Point(test_point))[0].distance(Point(edge_point[0])) / edge_line_string.length

        time_delta = Utils.time_difference_calculator(*map_edges_to_time_length[edge_point][0][1],
                                                      *map_edges_to_time_length[edge_point][0][2])
        probable_time = map_edges_to_time_length[edge_point][0][1][0].replace(year=year, month=month, day=day) + \
            time_delta * edge_travelled_percentage
        td = timedelta(0)
        if map_edges_to_time_length[edge_point][0][1][1] and map_edges_to_time_length[edge_point][0][2][1]:
            td = timedelta(days=1)
        elif probable_time.date() != date.date():
            next_day = True
        elif probable_time.date() == date.date() and next_day:
            td = timedelta(days=1)
        probable_time = map_edges_to_time_length[edge_point][0][1][0].replace(year=year, month=month, day=day) + \
            time_delta * edge_travelled_percentage
        if add_noise:
            stop_noise = map_edges_to_time_length[edge_point][0][4]
            point_noise = timedelta(seconds=points_noise[i])
            probable_time += stop_noise + point_noise
        times.append(probable_time + td)

    return times


def get_stopinfo(
        trip: str,
        stop_times_file=r"../GTFS/doctest_files/stop_times.txt",
        stops_file=r"../GTFS/doctest_files/stops.txt"
):
    """
    go through the files and get all the info for stop, location and time
    >>> d = [
    ...    ((47.187458038, 7.4941325188), (datetime(1900, 1, 1, 13, 22), False), (datetime(1900, 1, 1, 13, 22), False)),
    ...    ((47.190280914, 7.5012917519), (datetime(1900, 1, 1, 13, 23), False), (datetime(1900, 1, 1, 13, 23), False)),
    ...    ((47.195011139, 7.5111823082), (datetime(1900, 1, 1, 13, 26), False), (datetime(1900, 1, 1, 13, 26), False)),
    ...    ((47.199813843, 7.5311789513), (datetime(1900, 1, 1, 13, 27), False), (datetime(1900, 1, 1, 13, 27), False)),
    ...    ((47.202091217, 7.5346822739), (datetime(1900, 1, 1, 13, 28), False), (datetime(1900, 1, 1, 13, 28), False)),
    ...    ((47.204524994, 7.5422730446), (datetime(1900, 1, 1, 13, 31), False), (datetime(1900, 1, 1, 13, 31), False))
    ... ]
    >>> get_stopinfo("1.TA.92-8-L-j22-1.1.H") == d
    True
    """
    stop_times_list = []
    stops_to_get = set()
    with open(stop_times_file) as stop_times_csv:
        reader = csv.DictReader(stop_times_csv, delimiter=",", quotechar='"')
        for line in reader:
            current_trip_id = str(line["trip_id"])
            if current_trip_id != trip:
                continue

            stop_times_list.append((
                str(line["stop_id"]),
                Utils.convert_gtfs_date_to_datetime(line["arrival_time"]),
                Utils.convert_gtfs_date_to_datetime(line["departure_time"])
            ))
            stops_to_get.add(str(line["stop_id"]))

    stop_coords = {}
    with open(stops_file) as stops_csv:
        reader = csv.DictReader(stops_csv, delimiter=",", quotechar='"')
        for line in reader:
            if len(stops_to_get) == len(stop_coords):
                break
            stop_id = line["stop_id"]
            if stop_id in stops_to_get:
                stop_coords[stop_id] = (float(line["stop_lat"]), float(line["stop_lon"]))

    ret = []
    for stop_id, arrival_tuple, departure_tuple in stop_times_list:
        ret.append((stop_coords[stop_id], arrival_tuple, departure_tuple))

    return ret


def get_polyline(shape_id, shapes_input_file):
    """
    get polyline from shape name
    """
    # get pandas dataframe of input file
    df = pd.read_csv(shapes_input_file, header=0, usecols=[0, 1, 2])

    # make and return list of tuples of GPS-coordinates of the randomized shape
    polyline_df = df[df["shape_id"] == shape_id]
    polyline = polyline_df[["shape_pt_lat", "shape_pt_lon"]].values.tolist()
    # print("polyline:", [tuple(coord) for coord in polyline])
    return [tuple(coord) for coord in polyline]


def generate_noisified_gps_data_return_dicts(
        path_to_gtfs,
        trip,
        shape_id,
        avg_speed=14,
        signal_every_n_seconds=5,
        avg_gps_accuracy_in_meters=16,
        timestamp_date=datetime.now()
) -> Tuple[List[Tuple[float, float]], Dict[Tuple[float, float], int]]:
    """
    Generates a List of Coordinates (polyline) that are close to the given polyline.
    Simulates the GPS-coordinates from a moving device.

    Input:
        path_to_gtfs: path to the gtfs file
        trip: trip_id of the trip to generate data for
        shape_id: shape_id of the trip to generate data for
        avg_speed: The average speed of the simulated device.
            default: 11m/s (~40km/h)
        signal_every_n_seconds: Every n seconds, the device will send a new (noisy) GPS signal.
            default: 5s
        avg_gps_accuracy_in_meters: The larger the number,
            the farther away the noisified points will be from the original line
            default: 18m
        timestamp_date: date on which the test data is generated for
            it is not checked whether the trip is actually active on that date
        gen_dataset: GenerationDataSet object where information about the trips is stored

    Returns:
        A Tuple:
            0. A list of points that are close to the given polyline
            1. A dict {(lat, lon): timestamp} with (lat, lon) ∈ the list of points from 0.
                and timestamp being the estimated time the public transit vehicle is at the (lat, lon) point

    Testing (pseudo-)non-deterministic functions is not sensible
    """
    _, points, timestamps = generate_noisified_gps_data(
        path_to_gtfs, trip, shape_id, avg_speed, signal_every_n_seconds, avg_gps_accuracy_in_meters, timestamp_date)
    return points, dict(zip(points, timestamps))


def clamp_polyline_by_stops(polyline, stopinfo):
    """
    Take a polyline and a stop. then return the polyline from the first stop to the last stop.
    >>> clamp_polyline_by_stops(
    ...     [(0,0), (0,1), (0,2)], [[(0.5, 0.5)],[(0.5, 1.5)]]) == [(0.0, 0.5), (0.0, 1.0), (0.0, 1.5)]
    True
    >>> clamp_polyline_by_stops([(0,0), (0,1), (0,2)], [[(0, -1)],[(0, 3)]]) == [(0.0, 0.0), (0.0, 1.0), (0.0, 2)]
    True
    """
    # get the first and last stop
    first_stop_location = stopinfo[0][0]
    last_stop_location = stopinfo[-1][0]
    polyline_line_string = LineString(polyline)
    first_stop_on_line = polyline_line_string.interpolate(polyline_line_string.project(Point(first_stop_location)))
    s = split(snap(polyline_line_string, first_stop_on_line, 0.000001), first_stop_on_line)
    if len(s.geoms) == 2:
        polyline_split_by_first_stop = s.geoms[1]
    else:
        polyline_split_by_first_stop = polyline_line_string

    last_stop_on_line = polyline_split_by_first_stop.interpolate(
        polyline_split_by_first_stop.project(Point(last_stop_location)))
    polyline_split_by_last_stop = split(
        snap(polyline_split_by_first_stop, last_stop_on_line, 0.000001), last_stop_on_line).geoms[0]

    return list(polyline_split_by_last_stop.coords)


def generate_noisified_stops_data(
    gen_dataset,
    trip,
    trip_segments,
    num_stops,
    points_per_test=10,
    avg_speed=14,
    signal_every_n_seconds=5,
    avg_gps_accuracy_in_meters=16,
    timestamp_date=datetime.now(),
    add_noise=False,
    noise_stop=0,
    noise_point=0
):
    """
    Generates a List of Coordinates (polyline) on a given polyline of a trip,
    between stops of the trip, that are num_stops apart.
    Generate one polyline for each stop pair, that are num_stops apart.
    If the trip has less than num_stops stops, generate only one test for the whole trip.

    Simulates the GPS-coordinates from a moving device.

    Input:
        gen_dataset: GenerationDataSet object where information about the trips is stored
        trip: trip_id of the trip to generate data for
        trip_segments: list of trip segments of the trip to generate data for
        num_stops: number of stops between the start and end stop of the test
        points_per_test: number of points to generate for each test
        avg_speed: The average speed of the simulated device.
            default: 11m/s (~40km/h)
        signal_every_n_seconds: Every n seconds, the device will send a new (noisy) GPS signal.
            default: 5s
        avg_gps_accuracy_in_meters: The larger the number,
            the farther away the noisified points will be from the original line
            default: 18m
        timestamp_date: date on which the test data is generated for
            it is not checked whether the trip is actually active on that date

    Returns:
        A List of:
            0. A list of points that are close to the given polyline
            1. A list of points from 0, but with added noise
            2. A List of Timestamps, that fit to the points

    Testing (pseudo-)non-deterministic functions is not sensible
    """

    stop_info = gen_dataset.trip_id_to_stopinfo[trip]
    test_data = []

    # trip segments are between stops, so one less than the number of stops
    # have at least 1 test, even if there are less stops than num_stops
    for idx in range(max(len(trip_segments) - num_stops + 1, 1)):
        segments = trip_segments[idx:idx + num_stops]

        # flatten the list of segments, into one polyline
        polyline = [point for segment in segments for point in segment]

        total_distance_in_km, individual_polyline_lengths = calculate_polyline_length(polyline)

        total_time = (total_distance_in_km * 1000) // avg_speed

        num_signals = total_time / signal_every_n_seconds

        avg_travelling_distance_meters = avg_speed * signal_every_n_seconds

        points, points_to_edges = generate_points_along_line(
            polyline,
            num_signals,
            individual_polyline_lengths,
            avg_travelling_distance_meters)

        # randomly select the wanted number of points without duplicates
        list_indices = sorted(sample(range(len(points)), min(len(points), points_per_test)))
        points_random, points_to_edges_random = [], []
        for i in list_indices:
            points_random.append(points[i])
            points_to_edges_random.append(points_to_edges[i])

        # get fitting timestamps, note that the api takes milliseconds, but we generate in seconds epoch time
        timestamps = map(lambda x: x.timestamp() * 1000,
                         gen_timestamps(
                             trip, polyline, points_random, points_to_edges_random,
                             stop_info[idx:idx + num_stops + 1], timestamp_date, add_noise=add_noise,
                             noise_stop=noise_stop, noise_point=noise_point))

        # noisify points here
        points_with_noise = noisify_points(points, avg_gps_accuracy_in_meters=avg_gps_accuracy_in_meters)

        test_data.append((points, list(zip(points_with_noise, timestamps))))

    return test_data


def generate_noisified_gps_data(
        path_to_gtfs,
        trip,
        shape_id,
        avg_speed=14,
        signal_every_n_seconds=5,
        avg_gps_accuracy_in_meters=16,
        timestamp_date=datetime.now(),
        gen_dataset=None,
        verbose=True
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[int]]:
    """
    Generates a List of Coordinates (polyline) that are close to the given polyline.
    Simulates the GPS-coordinates from a moving device.

    Input:
        path_to_gtfs: path to the gtfs file
        trip: trip_id of the trip to generate data for
        shape_id: shape_id of the trip to generate data for
        avg_speed: The average speed of the simulated device.
            default: 11m/s (~40km/h)
        signal_every_n_seconds: Every n seconds, the device will send a new (noisy) GPS signal.
            default: 5s
        avg_gps_accuracy_in_meters: The larger the number,
            the farther away the noisified points will be from the original line
            default: 18m
        timestamp_date: date on which the test data is generated for
            it is not checked whether the trip is actually active on that date
        gen_dataset: GenerationDataSet object where information about the trips is stored

    Returns:
        A Tuple:
            0. A list of points that are close to the given polyline
            1. A list of points from 0, but with added noise
            2. A List of Timestamps, that fit to the points

    Testing (pseudo-)non-deterministic functions is not sensible
    """
    if not gen_dataset:
        stops_file = path_to_gtfs + r"stops.txt"
        stop_times_file = path_to_gtfs + r"stop_times.txt"
        shapes_file = path_to_gtfs + r"shapes.txt"
        # get all the stops with location, arrival and departure times
        stop_info = get_stopinfo(trip, stops_file=stops_file, stop_times_file=stop_times_file)
        polyline = clamp_polyline_by_stops(get_polyline(shape_id, shapes_file), stop_info)
    else:
        stop_info = gen_dataset.trip_id_to_stopinfo[trip]
        polyline = clamp_polyline_by_stops(gen_dataset.shape_id_to_polyline[shape_id], stop_info)

    # calculate total distance of polyline (in meters)
    total_distance_in_km, individual_polyline_lengths = calculate_polyline_length(polyline)

    # total time needed to traverse the distance (in seconds)
    total_time = (total_distance_in_km * 1000) // avg_speed

    # calculate the total number of needed GPS signals
    num_signals = total_time / signal_every_n_seconds

    # so while moving at avg_speed m/s, we will get a signal every signal_every_n_seconds seconds.
    # the average travelling distance between two points is therefore:
    avg_travelling_distance_meters = avg_speed * signal_every_n_seconds

    # generate points on the polyline in regular distances
    points, points_to_edges = generate_points_along_line(
        polyline,
        num_signals,
        individual_polyline_lengths,
        avg_travelling_distance_meters)

    if verbose:
        print(f"points: {points}")
        print(f"polyline: {polyline}")
        print(f"trip: {trip}")

    # generate timestamps, convert datetime to timestamp in microseconds
    timestamps = map(lambda x: x.timestamp() * 1000,
                     gen_timestamps(trip, polyline, points, points_to_edges, stop_info, timestamp_date))

    # noisify points here
    points_with_noise = noisify_points(points, avg_gps_accuracy_in_meters=avg_gps_accuracy_in_meters)

    return points, points_with_noise, list(timestamps)
