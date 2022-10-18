import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from shapely.geometry import LineString, Point
from shapely.ops import split
from typing import List, Tuple, Dict, Any
from math import acos, pi, floor
from math import sin, cos, atan2, radians, sqrt
import Utilities as utils


def great_circle(lat1, lon1, lat2, lon2, percentage=1.0):
    """
    calculates distance between to geolocation points in kilometers
    source: https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    return 6371 * percentage * (acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)))


def great_circle_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two Gps Points in meters,
    using haversine formula.
    Formula found here: http://www.movable-type.co.uk/scripts/latlong.html

    L = 2*pi*r*A / 360, r = 6371 km, A change in Degree
    * 1000 for L in meters

    >>> from math import isclose
    >>> print(isclose(111194.925,
    ... great_circle_distance(0,0,0,1),
    ... rel_tol = 0.01))
    True
    >>> print(isclose(134000,
    ... great_circle_distance(48.009833, 7.782528, 47.009833, 6.782528),
    ... rel_tol = 0.01))
    True
    """
    r = 6371  # radius of earth in m
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) * sin(dlat / 2) + \
        cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def calculateLengthOfPolyline(polyline: List[Tuple[float, float]]) -> Tuple[float, list]:
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

    >>> calculateLengthOfPolyline(polyline)
    (0.7167778718160418, [0.3223418685694302, 0.2940580665973436, 0.036627558660264195, 0.06375037798900368])
    """
    num_coordinates = len(polyline)
    distances = []

    for i in range(num_coordinates - 1):
        distances.append(great_circle_distance(polyline[i][0], polyline[i][1], polyline[i+1][0], polyline[i+1][1]))

    return sum(distances), distances


def estimateAverageSpeed(polyline_segments_lengths: List[float], min_speed=5, max_speed=15) -> List[float]:
    """
    Estimates the average speed of a device, depending on the length of the given polyline segment lengths
    The longer the segment, the faster the device will be.

    Input:
        polyline_segments_lengths: lengths of a polyline segment in km
        min_speed: minimum average speed of a device (when driving through a bend or so)
        max_speed: maximum average speed of a device (when on a straight main street for example)

    Returns:
        List of the calculated estimated speed of the device
    """
    pass


def addMetersToGPSCoordinate(point: Tuple[float, float], dy, dx) -> Tuple[float, float]:
    """
    Adds an offset in meters to a given coordinate

    Input:
        point: (lat, lon) as a GPS coordinate (degrees)
        dy: offset that will be added to the latitude (in meters)
        dx: offset that will be added to the longitude (in meters)

    Returns:
        Point with the calculated offset.

    >>> freiburg_technische_fakultaet = (48.011757, 7.835033)
    >>> addMetersToGPSCoordinate(freiburg_technische_fakultaet, 10, 100)
    (48.011846831528416, 7.833609515722384)
    >>> addMetersToGPSCoordinate(freiburg_technische_fakultaet, 1000, -100)
    (48.0207401528412, 7.836456484277616)
    >>> addMetersToGPSCoordinate(freiburg_technische_fakultaet, -123, 0)
    (48.010652072200536, 7.835033)
    """
    r_earth = 6378137  # meters
    return point[0] + (180/pi)*(dy/r_earth), point[1] + (180/pi)*(dx/r_earth)/cos(point[0])


def getPointOnPolylineSegment(
        line: Tuple[Tuple[float, float], Tuple[float, float]],
        percentage: "float between 0 and 1",
        STEP=0.0005
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

    >>> getPointOnPolylineSegment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.3)
    (48.01146429837473, 7.834533)
    >>> getPointOnPolylineSegment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.5)
    (48.01087889512419, 7.833533)
    >>> getPointOnPolylineSegment((freiburg_technische_fakultaet, freiburg_elsaesser_strasse), percentage=0.9)
    (48.01029349187366, 7.832533)
    """
    if percentage == 0:  # no movement
        return line[0]
    assert 0 < percentage < 1, "percentage needs to be a value between 0 and 1"

    y1, x1 = line[0]
    y2, x2 = line[1]
    y, x = line[0]      # y and x need to be initialized in case no loop runs

    if abs(y2-y1) <= abs(x2-x1):
        a = floor((x2 - x1) / STEP * percentage) + 1
        if a == 0:
            return y, x
        sgn = a // abs(a)
        for i in range(abs(a) + 1):
            x = x1 + i * STEP * sgn
            y = (y1 - y2) / (x1 - x2) * (x - x1) + y1
    else:
        a = floor((y2 - y1) / STEP * percentage) + 1
        if a == 0:
            return y, x
        sgn = a // abs(a)
        for i in range(abs(a) + 1):
            y = y1 + i * STEP * sgn
            x = (x1 - x2) / (y1 - y2) * (y - y1) + x1

    return y, x


def generate_points_along_line(
        polyline: List[Tuple[float, float]],
        num_signals: float,
        individual_polyline_lengths: List[float],
        avg_travelling_distance_meters: int
) -> List[Tuple[float, float]]:
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

    >>> total_distance_in_km, individual_polyline_lengths = calculateLengthOfPolyline(polyline)
    >>> total_time = (total_distance_in_km * 1000) // avg_speed
    >>> num_signals = total_time / signal_every_n_seconds
    >>> avg_travelling_distance = avg_speed * signal_every_n_seconds

    >>> from math import isclose
    >>> isclose(total_distance_in_km * 1000, 716.7778718160419)  # test in meters
    True
    >>> individual_polyline_lengths == [
    ...     0.3223418685694302, 0.2940580665973436, 0.036627558660264195, 0.06375037798900368
    ... ]
    True
    >>> total_time == 51.0  # seconds (for 716.7778718160419m) with average speed of 14 m/s
    True
    >>> num_signals == 10.2  # => floor(10.2) = 10 GPS signals, as there is one signal every 5 seconds
    True
    >>> avg_travelling_distance == 70  # m/s
    True

    >>> points = generate_points_along_line(polyline,num_signals,individual_polyline_lengths, avg_travelling_distance)

    >>> points == [(48.011757, 7.835033), (48.01146429837473, 7.834533), (48.01117159674946, 7.834033),
    ...     (48.01058619349892, 7.833033), (48.01029349187366, 7.832533), (48.009848, 7.831772),
    ...     (48.009530024432806, 7.831272), (48.00889407329843, 7.830272), (48.008576097731236, 7.829772),
    ...     (48.008026, 7.828907), (48.00725378531074, 7.8297680000000005)]
    True

    """
    current_polyline_part = 0
    points = [polyline[0]]  # initialize with start of polyline (starting point)
    path_travelled_on_polyline_segment = 0

    for signal in range(int(num_signals)):
        # get length of current polyline segment
        length_polyline_segment = individual_polyline_lengths[current_polyline_part]

        # calculate path_saved_dictionaries travelled on current polyline segment
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
        percentage = 1 - ((length_polyline_segment
                           - path_travelled_on_polyline_segment) / length_polyline_segment)

        # add new point to points
        points.append(getPointOnPolylineSegment(
            line=(polyline[current_polyline_part], polyline[current_polyline_part + 1]),
            percentage=percentage
        ))

    return points


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

    >>> # Testen ist bei (pseudo-)nicht-deterministischen Funktionen nicht sinnvoll.
    """
    mu = 0
    sigma = avg_gps_accuracy_in_meters
    num_points = len(points)
    x_deviations = np.random.normal(mu, sigma, num_points)
    y_deviations = np.random.normal(mu, sigma, num_points)
    noisified_points = []
    for i, point in enumerate(points):
        noisified_points.append(addMetersToGPSCoordinate(point, y_deviations[i], x_deviations[i]))
    return noisified_points


def gen_timestamps(trip, shape_points, points):
    """
    Generate plausible times for each point.
    Calculate how much of a route the train has travelled and
    get a time from it, might not be the most accurate

    >>> trip = "1.T0.10-46-I-j22-1.2.H"
    >>> shape = "shp_3_67"
    >>> shape_points = get_polyline(shape)
    >>> total_distance_in_km, individual_polyline_lengths = calculateLengthOfPolyline(shape_points)
    >>> total_time = (total_distance_in_km * 1000) // 14
    >>> num_signals = total_time / 5
    >>> avg_travelling_distance_meters_per_second = 14 * 5
    >>> points = generate_points_along_line(shape_points, num_signals, individual_polyline_lengths, avg_travelling_distance_meters_per_second)
    >>> timestamps = gen_timestamps(trip, shape_points, points)
    >>> # [(time.hour, time.minute, time.second) for time in timestamps]
    """
    times = []
    shape_line = LineString(shape_points)
    stop_info = get_stopinfo(trip)
    print(stop_info)

    # generate edges between stops
    stop_coords = []
    stop_times = [stop_info[0][1]]
    # project the stop coord onto shape line
    for coord, arri_time, dept_time in stop_info:
        stop_coords.append(coord)
        stop_times += [arri_time, dept_time]
    stop_times += [stop_info[-1][1]]
    # convert stop_times into tuples
    it = iter(stop_times)
    stop_times = list(zip(it, it))

    print("test")
    """
    # check if the first stop coordinate is before first line
    if great_circle(*shape_line.coords[1], *shape_line.coords[0]) < \
            great_circle(*shape_line.coords[1], *project_point_to_line(LineString(
                [shape_line.coords[1], shape_line.coords[0]]), Point(stop_info[0][0]))):
        print("too short")
        shape_points = [stop_coords[0]] + shape_points

    if great_circle(*shape_line.coords[-2], *shape_line.coords[-1]) < \
            great_circle(*shape_line.coords[-2], *project_point_to_line(LineString(
                [shape_line.coords[-2], shape_line.coords[-1]]), Point(stop_info[-1][0]))):
        print("not long enough")
        shape_points = shape_points + [stop_coords[-1]]
    if great_circle(*shape_line.coords[1], *shape_line.coords[0]) < \
        great_circle(*shape_line.coords[1], *project_point_to_line(LineString(
            [shape_line.coords[1], shape_line.coords[0]]), Point(stop_info[0][0]))):
        stop_times = stop_times[1:]
        stop_coords = stop_coords[1:]

    # check if the last stop coordinate is after last line
    if great_circle(*shape_line.coords[-2], *shape_line.coords[-1]) < \
            great_circle(*shape_line.coords[-2], *project_point_to_line(LineString(
                [shape_line.coords[-2], shape_line.coords[-1]]), Point(stop_info[-1][0]))):
        stop_times = stop_times[:-1]
        stop_coords = stop_coords[:-1]
    """

    segments_split_by_stop = []
    for stop_coord in stop_coords:
        old_distance = 1000000000
        j = len(shape_points) - 2
        for idx, segment in enumerate(zip(shape_points[:-1], shape_points[1:])):
            distance = LineString(segment).distance(Point(stop_coord))
            if old_distance > 0.0001 or distance <= old_distance:
                old_distance = distance
            else:
                j = idx - 1
                break
        closest_segment = LineString(shape_points[j:j+2])
        closest_point_on_segment = closest_segment.interpolate(closest_segment.project(Point(stop_coord))).coords[0]
        if shape_points[:j]:
            segments_split_by_stop.append(shape_points[:j] + [closest_point_on_segment])
        else:
            segments_split_by_stop.append([stop_coord] + [closest_point_on_segment])
        shape_points = [closest_point_on_segment] + shape_points[j:]

    # for each point now calculate a fitting time
    last_index = 0
    for point in points:
        old_distance = 1000000000
        edge = LineString(segments_split_by_stop[-1])
        j = len(segments_split_by_stop) - 1
        for idx, segment in enumerate(segments_split_by_stop[last_index:]):
            distance = LineString(segment).distance(Point(point))
            if old_distance > 0.0005 or distance <= old_distance:
                old_distance = distance
            else:
                j = last_index + idx - 1
                last_index = j
                edge = LineString(segment)
                break
        # get the closest edge and time info
        time_start_info, time_end_info = stop_times[j]

        percentage = 0
        if edge.length != 0:
            # calculate how far the train has travelled on the edge
            point_on_line = Point(edge.interpolate(edge.project(Point(point)))).buffer(1e-9)
            dist_to_point = split(edge, point_on_line).geoms[0].length

            percentage = dist_to_point / edge.length

        # generate timestamp
        times.append(calculate_time_difference(*time_start_info, *time_end_info, percentage))

    return times


def project_point_to_line(line, point):
    """
    Project point onto the line, point may not lie on the line, but on its extent
    https://stackoverflow.com/questions/49061521/projection-of-a-point-to-a-line-segment-python-shapely
    >>> line = LineString([(0, 1), (1, 1)])
    >>> point = Point(0.5, 0.5)
    >>> project_point_to_line(line, point)
    (0.5, 1.0)
    >>> line = LineString([(0, 1), (1, 1)])
    >>> point = Point(2, 2)
    >>> project_point_to_line(line, point)
    (2.0, 1.0)
    """
    x = np.array(point.coords[0])
    u = np.array(line.coords[0])
    v = np.array(line.coords[-1])
    n = v - u
    n /= np.linalg.norm(n, 2)
    new_point = u + n * np.dot(x - u, n)
    return new_point[0], new_point[1]


def calculate_time_difference(time1: datetime, overflow1, time2: datetime, overflow2, percentage):
    """
    Calculate the difference in time, respecting overflow.
    Return time1, with date as today added with a percentage of the difference

    Note: time1 must be before time2
    >>> time1 = datetime.now()
    >>> time2 = datetime.now() + timedelta(hours=10)
    >>> calculate_time_difference(time1, False, time2, False, 1) == time2
    True
    >>> time1 = datetime.now()
    >>> time2 = datetime.now()
    >>> calculate_time_difference(time1, False, time2, True, 0.5) == time2 + timedelta(hours=12)
    True
    """
    oneday = timedelta(days=1)
    if overflow1:
        time1 += oneday
    if overflow2:
        time2 += oneday

    delta = time2 - time1

    # set time to time1 and date to today
    time = datetime.now().replace(
        hour=time1.hour, minute=time1.minute,
        second=time1.second, microsecond=time1.microsecond)

    # add the offset to time
    time += delta * percentage
    if overflow1:
        time += oneday
    return time


def get_stopinfo(trip, stop_times_file="GTFS/stop_times.txt", stops_file="GTFS/stops.txt"):
    """
    go through the files and get all the info for stop, location and time
    >>> d = [
    ...  ((47.996483, 7.841457), (datetime(1900, 1, 1, 4, 40), False), (datetime(1900, 1, 1, 4, 40), False)),
    ...  ((48.027836, 7.775781), (datetime(1900, 1, 1, 4, 49), False), (datetime(1900, 1, 1, 4, 49), False)),
    ...  ((48.029289, 7.77182), (datetime(1900, 1, 1, 4, 50), False), (datetime(1900, 1, 1, 4, 50), False)),
    ...  ((48.031109, 7.767984), (datetime(1900, 1, 1, 4, 51), False), (datetime(1900, 1, 1, 4, 51), False)),
    ...  ((48.031902, 7.762423), (datetime(1900, 1, 1, 4, 52), False), (datetime(1900, 1, 1, 4, 52), False)),
    ...  ((48.031033, 7.761049), (datetime(1900, 1, 1, 4, 52), False), (datetime(1900, 1, 1, 4, 52), False)),
    ...  ((48.028946, 7.758435), (datetime(1900, 1, 1, 4, 53), False), (datetime(1900, 1, 1, 4, 53), False)),
    ...  ((48.023899, 7.724595), (datetime(1900, 1, 1, 4, 56), False), (datetime(1900, 1, 1, 4, 56), False)),
    ...  ((48.023415, 7.719223), (datetime(1900, 1, 1, 4, 57), False), (datetime(1900, 1, 1, 4, 57), False)),
    ...  ((48.022087, 7.720041), (datetime(1900, 1, 1, 4, 58), False), (datetime(1900, 1, 1, 4, 58), False)),
    ...  ((48.011425, 7.723742), (datetime(1900, 1, 1, 5, 1), False), (datetime(1900, 1, 1, 5, 1), False)),
    ...  ((48.004467, 7.720023), (datetime(1900, 1, 1, 5, 3), False), (datetime(1900, 1, 1, 5, 3), False)),
    ...  ((48.000252, 7.71545), (datetime(1900, 1, 1, 5, 4), False), (datetime(1900, 1, 1, 5, 4), False)),
    ...  ((47.997379, 7.712729), (datetime(1900, 1, 1, 5, 5), False), (datetime(1900, 1, 1, 5, 5), False)),
    ...  ((47.990166, 7.717085), (datetime(1900, 1, 1, 5, 8), False), (datetime(1900, 1, 1, 5, 8), False)),
    ...  ((47.988262, 7.715486), (datetime(1900, 1, 1, 5, 9), False), (datetime(1900, 1, 1, 5, 9), False)),
    ...  ((47.9828, 7.714516), (datetime(1900, 1, 1, 5, 10), False), (datetime(1900, 1, 1, 5, 10), False)),
    ...  ((47.981964, 7.71139), (datetime(1900, 1, 1, 5, 11), False), (datetime(1900, 1, 1, 5, 11), False)),
    ...  ((47.978909, 7.707554), (datetime(1900, 1, 1, 5, 12), False), (datetime(1900, 1, 1, 5, 12), False)),
    ...  ((47.97282, 7.701059), (datetime(1900, 1, 1, 5, 13), False), (datetime(1900, 1, 1, 5, 13), False)),
    ...  ((47.969082, 7.699344), (datetime(1900, 1, 1, 5, 14), False), (datetime(1900, 1, 1, 5, 14), False)),
    ...  ((47.967575, 7.695705), (datetime(1900, 1, 1, 5, 15), False), (datetime(1900, 1, 1, 5, 15), False))]
    >>> get_stopinfo("1.T0.10-46-I-j22-1.2.H") == d
    True
    """
    ret = []
    trips = pd.read_csv(stop_times_file, usecols=[0, 1, 2, 3])
    stops = pd.read_csv(stops_file, usecols=[0, 4, 5])

    trip_df = trips[trips["trip_id"] == trip]

    for _, info in trip_df.iterrows():
        arrival_time, arrival_time_overflow = \
            utils.convertGtfsDateToDatetime(info["arrival_time"])
        departure_time, departure_time_overflow = \
            utils.convertGtfsDateToDatetime(info["departure_time"])
        stop_name, stop_lat, stop_lon = \
            list(stops[stops["stop_id"] == info["stop_id"]].iterrows())[0][1]
        ret.append(((float(stop_lat), float(stop_lon)), (arrival_time, arrival_time_overflow), (departure_time, departure_time_overflow)))
    return ret


def get_polyline(shape_id, shapes_input_file="GTFS/shapes.txt"):
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


def generate_noisified_gps_data(
        trip,
        shape_id,
        avg_speed=14,
        signal_every_n_seconds=5,
        avg_gps_accuracy_in_meters=16
) -> tuple[list[tuple[float, float]], dict[tuple[float, float], int]]:
    """
    Generates a List of Coordinates (polyline) that are close to the given polyline.
    Simulates the GPS-coordinates from a moving device.

    Input:
        polyline: List of Coordinates (lat, lon). Each coordinate is connected to its neighbors in the list.
        avg_speed: The average speed of the simulated device.
            default: 11m/s (~40km/h)
        signal_every_n_seconds: Every n seconds, the device will send a new (noisy) GPS signal.
            default: 5s
        avg_gps_accuracy_in_meters: The larger the number,
            the farther away the noisified points will be from the original line
            default: 18m

    Returns:
        A Tuple:
            0. A list of points that are close to the given polyline
            1. A dict {(lat, lon): timestamp} with (lat, lon) ∈ the list of points from 0.
                and timestamp being the estimated time the public transit vehicle is at the (lat, lon) point

    >>> # Testen ist bei (pseudo-)nicht-deterministischen Funktionen nicht sinnvoll.
    """
    polyline = get_polyline(shape_id)

    # calculate total distance of polyline (in meters)
    total_distance_in_km, individual_polyline_lengths = calculateLengthOfPolyline(polyline)

    # total time needed to traverse the distance (in seconds)
    total_time = (total_distance_in_km * 1000) // avg_speed

    # calculate the total number of needed GPS signals
    num_signals = total_time / signal_every_n_seconds

    # so while moving at avg_speed m/s, we will get a signal every signal_every_n_seconds seconds.
    # the average travelling distance between two points is therefore:
    avg_travelling_distance_meters = avg_speed * signal_every_n_seconds

    # print("\n")
    # print(f"Total Polyline distance: {total_distance_in_km * 1000}m")
    # print(f"Individual polyline lengths: {individual_polyline_lengths}")
    # print(f"Time needed: {total_time}s (for {total_distance_in_km * 1000}m) with average speed of {avg_speed} m/s")
    # print(f"There will be {num_signals} GPS signals, as there is one signal every {signal_every_n_seconds} seconds")
    # print(f"The average travelling distance is {avg_travelling_distance_meters} m")
    # print("\n")

    # generate points on the polyline in regular distances
    points = generate_points_along_line(
        polyline,
        num_signals,
        individual_polyline_lengths,
        avg_travelling_distance_meters)

    print(f"points: {points}")
    print(f"polyline: {polyline}")
    print(f"trip: {trip}")
    # generate timestamps, convert datetime to timestamp in microseconds
    timestamps = map(lambda x: x.timestamp() * 1000, gen_timestamps(trip, polyline, points))

    # noisify points here
    points = noisify_points(points, avg_gps_accuracy_in_meters=avg_gps_accuracy_in_meters)

    return points, dict(zip(points, timestamps))


if __name__ == '__main__':
    hamburg = (53.553406, 9.992196)
    berlin = (52.523403, 13.4114)
    new_york = (40.71427, -74.00597)
    san_francisco = (37.77493, -122.41942)
    anchorage = (61.189762, -149.865870)
    freiburg_technische_fakultaet = (48.011757, 7.835033)
    freiburg_elsaesser_strasse = (48.009848, 7.831772)
    freiburg_berliner_allee_kurve_1 = (48.008026, 7.828907)
    freiburg_berliner_allee_kurve_2 = (48.007710, 7.828768)
    freiburg_berliner_allee_station = (48.007387, 7.829476)

    SAMPLE_LINE = [freiburg_technische_fakultaet,
                   freiburg_elsaesser_strasse,
                   freiburg_berliner_allee_kurve_1,
                   freiburg_berliner_allee_kurve_2,
                   freiburg_berliner_allee_station]

    polyline_freiburg = [(47.995189667, 7.8501930237), (47.99502182, 7.8500418663), (47.994976044, 7.8499689102), (47.99495697, 7.8499059677), (47.994941711, 7.8498311043), (47.994949341, 7.8497796059), (47.994987488, 7.8496174812), (47.995037079, 7.8494887352), (47.99514389, 7.8491482735), (47.99520874, 7.8488917351), (47.995227814, 7.8488097191), (47.995262146, 7.848587513), (47.995269775, 7.8484711647), (47.995269775, 7.8483338356), (47.995265961, 7.8481149673), (47.995239258, 7.8476037979), (47.995235443, 7.8473596573), (47.995235443, 7.8471503258), (47.995246887, 7.846930027), (47.995285034, 7.8465924263), (47.995353699, 7.8462543488), (47.99553299, 7.8453826904), (47.995616913, 7.8449826241), (47.995769501, 7.8442530632), (47.995815277, 7.8440475464), (47.9958992, 7.8436908722), (47.996116638, 7.842707634), (47.996498108, 7.8408851624), (47.996593475, 7.8404259682), (47.996688843, 7.83994627), (47.996757507, 7.8396110535), (47.996803284, 7.8394126892), (47.996860504, 7.8392062187), (47.996940613, 7.8389472961), (47.99704361, 7.8386716843), (47.997138977, 7.8384418488), (47.997238159, 7.8382353783), (47.997390747, 7.8379340172), (47.997745514, 7.8372759819), (47.997802734, 7.8371534348), (47.997982025, 7.8366980553), (47.998146057, 7.8362779617), (47.998271942, 7.8359618187), (47.99830246, 7.8359055519), (47.998680115, 7.8352718353), (47.998851776, 7.8349218369), (47.998943329, 7.8347043991), (47.999340057, 7.8336935043), (47.999542236, 7.8331599236), (47.999671936, 7.8327813148), (47.999736786, 7.8326630592), (47.999767303, 7.8326272964), (47.999797821, 7.832608223), (47.9998703, 7.8325862885), (47.999912262, 7.8325858116), (47.999992371, 7.8326191902), (48.000297546, 7.8328928947), (48.000465393, 7.8330430984), (48.00088501, 7.8334326744), (48.00213623, 7.8345861435), (48.002426147, 7.8349084854), (48.003425598, 7.8362293243), (48.003585815, 7.8364524841), (48.003734589, 7.8366532326), (48.003780365, 7.8367271423), (48.003799438, 7.836751461), (48.003860474, 7.8368067741), (48.003917694, 7.8368310928), (48.0039711, 7.836836338), (48.003997803, 7.836836338), (48.004062653, 7.8368110657), (48.00409317, 7.8367857933), (48.004127502, 7.8367390633), (48.004520416, 7.8361368179), (48.004901886, 7.8355174065), (48.005104065, 7.835149765), (48.005172729, 7.8349881172), (48.005214691, 7.8349137306), (48.005428314, 7.8345556259), (48.005573273, 7.8343105316), (48.005996704, 7.8335952759), (48.006328583, 7.8328666687), (48.006813049, 7.8316273689), (48.006988525, 7.831138134), (48.00743866, 7.8294949532), (48.007518768, 7.8291988373), (48.007583618, 7.8289952278), (48.007602692, 7.8289556503), (48.007656097, 7.8288707733), (48.007694244, 7.82883358), (48.007759094, 7.8288035393), (48.007827759, 7.8288016319), (48.007919312, 7.8288369179), (48.007965088, 7.8288831711), (48.009029388, 7.8305420876), (48.009319305, 7.8310127258), (48.00957489, 7.8314151764), (48.009750366, 7.8316869736), (48.009925842, 7.8319654465), (48.011363983, 7.8341937065), (48.011665344, 7.834692955), (48.011833191, 7.8349804878), (48.011898041, 7.8350992203), (48.012077332, 7.8354086876), (48.012214661, 7.8356385231), (48.012294769, 7.8357796669), (48.012805939, 7.8365736008), (48.01285553, 7.8366150856), (48.012992859, 7.8366503716), (48.013168335, 7.8366708755), (48.014026642, 7.8366746902), (48.014575958, 7.8366503716), (48.014907837, 7.8366203308), (48.015266418, 7.8365879059), (48.015380859, 7.8365855217), (48.015464783, 7.8365926743), (48.015769958, 7.8366603851), (48.01720047, 7.8366122246), (48.017341614, 7.8366322517), (48.017490387, 7.8366689682), (48.017654419, 7.8367519379), (48.017799377, 7.8368616104), (48.017967224, 7.8370165825), (48.018173218, 7.8372812271), (48.018291473, 7.8374576569), (48.018405914, 7.8376646042), (48.018520355, 7.8379426003), (48.01858139, 7.8381576538), (48.018596649, 7.838218689), (48.018661499, 7.8383150101), (48.018730164, 7.8383593559), (48.018917084, 7.8384389877), (48.018993378, 7.8385190964), (48.019042969, 7.8386726379), (48.019260406, 7.8395271301)]

    print("----------------------------------------")
    a = calculateLengthOfPolyline(polyline_freiburg)
    print(a[1])
    print(sum(a[1])/len(a[1]))
    #
    # print(calculateLengthOfPolyline(SAMPLE_LINE))
    # print(generate_gps_data(SAMPLE_LINE))
