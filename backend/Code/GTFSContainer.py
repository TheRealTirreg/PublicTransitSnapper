"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
import sys
from typing import Tuple, List
from datetime import datetime, timedelta
from shapely.geometry import Point, LineString
from shapely.ops import split, snap
import os
import subprocess as sp
import LoadJson
from operator import itemgetter
import Utilities as Utils


class GTFSContainer:
    """
    Contains GTFS data needed by the MapMatcher to quickly check if there is a public transit vehicle on a given shape.
    Load and save GTFS files via the constructor (load only: update_dicts=False)
    """

    def __init__(self, path_gtfs, path_saved_dictionaries, update_dicts=False, verbose=False, rt_dict=None):
        """
        Only (re-)builds the dicts if specified, as it may take a few minutes to load the GTFS data.
        """
        self.verbose = verbose
        # debug
        old_stdout = sys.stdout
        if not self.verbose:
            f = open(os.devnull, 'w')
            sys.stdout = f

        if path_gtfs[-1] != "/":
            path_gtfs += "/"
        if path_saved_dictionaries[-1] != "/":
            path_saved_dictionaries += "/"

        # These are the available dicts, loaded in self._loadDictionaries
        # {"trip_id": ("route_id", [((start_time, start_overtime), (end_time, end_overtime), stop_id), ...])}
        self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict = None
        # {"trip_id": TripWithStopsAndTimes}
        self.trip_id_to_trip_with_stops_dict = None
        self.GTFSGraph = None
        self.EdgesGeoIndex = None
        #  int      int
        # {hash: {edge_id: [trip_segments]}}
        self.hash_to_edge_id_to_trip_segment_id_dict_dict = None
        # {"route_id" : (agency_id, route_short_name, route_long_name, route_type, route_color, route_text_color)}
        self.route_id_to_route_information_dict = None
        # {"shape_id": [first_edge_of_the_shape (lat0, lon0, lat1, lon1)] + [(trip_id, service_id, route_id), ...]}
        self.shape_id_to_trip_service_route_ids_dict = None
        # {"stop_id" : (stop_name, stop_lat, stop_lon)}
        self.stop_id_to_stop_information_dict = None
        # {"stop_id" : [(trip_id, departure_time)]}
        self.stop_id_to_trips_with_departure_time_dict = None
        # {"stop_name" : [stop_id]}
        self.stop_name_to_list_of_stop_ids_dict = None
        # {"service_id" : (active_weekdays, start_time, end_time, extra_dates, removed_dates)}
        self.service_id_to_service_information_dict = None

        self.gtfs_rt_dict = rt_dict

        if not update_dicts and not self._does_saving_path_exist(path_saved_dictionaries):
            raise FileNotFoundError(f"No JSON files saved under the given path_saved_dictionaries "
                                    f"{path_saved_dictionaries}.\n"
                                    f"Try 'UPDATE_DICTS=True' in the config.yml or giving another "
                                    f"path_saved_dictionaries like 'saved_dictionaries/Freiburg'")

        # (re)-build dictionaries
        if update_dicts:
            self._build_dictionaries(path_gtfs, path_saved_dictionaries)

        # load dictionaries
        self._load_dictionaries(path_saved_dictionaries)

        # debug
        sys.stdout = old_stdout

    @staticmethod
    def _does_saving_path_exist(path):
        """
        True if the given path_saved_dictionaries exists
        """
        return os.path.isdir(path)

    def _generate_dicts_process_1(self, file_path):
        """
        Used by self._loadDictionaries
        """
        self.service_id_to_service_information_dict = \
            LoadJson.generate_service_id_to_service_information(file_path + "service_id_to_service_information.json")
        self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict = \
            LoadJson.generate_trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict(
                file_path + r"trip_id_to_route_id_and_list_of_stop_times_and_stop_id.json")
        self.trip_id_to_trip_with_stops_dict = LoadJson.generate_trip_id_to_trips_with_stops_dict(
            file_path + r"trips_with_stops_and_times.json",
            self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict,
            self.service_id_to_service_information_dict)

    def _generate_dicts_process_2(self, file_path):
        """
        Used by self._loadDictionaries
        """
        self.GTFSGraph, self.EdgesGeoIndex = LoadJson.generate_graph_and_geo_index(
            file_path + r"edges_for_graph.json")
        self.hash_to_edge_id_to_trip_segment_id_dict_dict = \
            LoadJson.generate_hash_to_edge_id_to_trip_segment_id_dict_dict(
                file_path + r"map_hash_to_edge_id_to_trip_segment_id.json")
        self.route_id_to_route_information_dict = LoadJson.generate_route_id_to_route_information_dict(
            file_path + r"route_id_to_route_information.json")
        self.shape_id_to_trip_service_route_ids_dict = LoadJson.generate_shape_id_to_trip_service_route_ids_dict(
            file_path + r"shape_id_to_trip_service_route_ids.json")
        self.stop_id_to_stop_information_dict = LoadJson.generate_stop_id_to_stop_information_dict(
            file_path + r"stop_id_to_stop_information.json")
        self.stop_id_to_trips_with_departure_time_dict = LoadJson.generate_stop_id_to_trips_with_departure_time_dict(
            file_path + r"stop_id_to_trips_with_departure_time.json")
        self.stop_name_to_list_of_stop_ids_dict = LoadJson.generate_stop_name_to_list_of_stop_ids_dict(
            file_path + r"stop_name_to_list_of_stop_ids.json")

    def _build_dictionaries(self, path_gtfs, path_saved_dictionaries):
        """
        Reads the GTFS files using a c++ program.
        """
        if self.verbose:
            print("Saving dictionaries", flush=True)
            print(f"input: {path_gtfs}, output: {path_saved_dictionaries}", flush=True)

        if not self._does_saving_path_exist(path_gtfs):
            ls_process = sp.Popen(["ls", "-R", "-ls"],
                                  stdout=sys.stdout, stderr=sys.stderr)
            ls_process.wait()
            raise OSError(f"Error: The path {path_gtfs} does not exist!")

        # try to make new directory if there is none
        if not self._does_saving_path_exist(path_saved_dictionaries):
            os.mkdir(path_saved_dictionaries)

        if self.verbose:
            print("generating json files using c++", flush=True)
            print(f"input: {path_gtfs}, output: {path_saved_dictionaries}", flush=True)
        # generate json files using c++                       input                 output
        generating_json_process = sp.Popen([r"parseGTFS/parseGTFSMain", path_gtfs, "-o", path_saved_dictionaries],
                                           stdout=sys.stdout, stderr=sys.stderr)
        generating_json_process.wait()

        if self.verbose:
            print("Finished saving dictionaries", flush=True)

    def _load_dictionaries(self, path):
        """
        loads the json files from the given path into the ram
        """
        if self.verbose:
            print(f"Loading dictionaries from path {path} ...", flush=True)

        self._generate_dicts_process_1(path)
        self._generate_dicts_process_2(path)

        if self.verbose:
            print("Finished loading dictionaries.", flush=True)

    def get_route_short_name(self, route_id) -> str:
        """
        Returns the short name of a route (e.g. "4" or "N46")

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.get_route_short_name("91-10-A-j22-1")
        '10'
        """
        return self.route_id_to_route_information_dict[route_id][0]

    def get_route_type(self, route_id: str) -> str:
        """
        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.get_route_type("91-10-A-j22-1") == "0"
        True
        >>> tt.get_route_type("91-20-Y-j22-1") == "2"
        True
        >>> tt.get_route_type("92-8-L-j22-1") == "3"
        True
        """
        return str(self.route_id_to_route_information_dict[route_id][1])

    def get_active_trips_information(
            self,
            shape_id: str,
            edge_id: int,
            date: datetime = datetime.now(),
            delay: timedelta = timedelta(minutes=5),
            earliness: timedelta = timedelta(minutes=1),
            ignore_start_end_date=False,
            ignore_time=False
    ) -> list:
        """
        Returns the [(service_id, trip_id, route_id, [trip_segment_ids]), ...] of all trips that are currently active
            given the date, the shape_id and the edge_id.

        >>> tt = GTFSContainer("../GTFS/doctest_files", "../saved_dictionaries/Doctests", verbose=False)
        >>> shp = "shp_0_573"
        >>> e_id = 27
        >>> dat = datetime(2022, 7, 28, 19, 45, 0)  # is a thursday (3) 19h45
        >>> tt.get_active_trips_information(shp, e_id, dat) == [
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [1, 2]),
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.3.H', '91-10-A-j22-1', [1])]
        True
        >>> dat = datetime(2022, 7, 28, 18, 45, 0)  # 18h45
        >>> tt.get_active_trips_information(shp, e_id, dat)
        []
        >>> dat = datetime(2022, 7, 28, 19, 43, 0)  # 19h43 (only traffic on ts 1 19:44 - 19:45) 1 min earliness
        >>> tt.get_active_trips_information(shp, e_id, dat)
        [('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [1])]
        >>> dat = datetime(2022, 7, 28, 19, 56, 0)  # 10 minutes delay, not 5 minutes
        >>> tt.get_active_trips_information(shp, e_id, dat, delay=timedelta(minutes=10)) == [
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [2]),
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.3.H', '91-10-A-j22-1', [1, 2])]
        True
        >>> dat = datetime(2022, 7, 28, 19, 43, 0)  # 19h43 but with an earliness of 2mins, not 1min
        >>> tt.get_active_trips_information(shp, e_id, dat, earliness=timedelta(minutes=2))
        [('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [1, 2])]
        >>> realtime_update = {'1.TA.91-10-A-j22-1.1.H':
        ...     [(1, None, (datetime(2022, 7, 28, 19, 46), True), None),
        ...      (2, None, (-600, False), None)]}
        >>> tt = GTFSContainer("../GTFS/doctest_files", "../saved_dictionaries/Doctests",
        ...     verbose=False, rt_dict=realtime_update)
        >>> shp = "shp_0_573"
        >>> e_id = 27
        >>> dat = datetime(2022, 7, 28, 19, 46)  # is a thursday (3) 19h45
        >>> tt.get_active_trips_information(shp, e_id, dat, delay=timedelta(0), earliness=timedelta(0)) == [
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [1]),
        ...     ('TA+k8700', '1.TA.91-10-A-j22-1.3.H', '91-10-A-j22-1', [1])]
        True
        """
        # get list of trips on the given shape
        # shape_id_to_trip_service_route_ids_dict looks like {"shape_id": [
        #             (first edge of shape),
        #             (trip_id, service_id, route_id),
        #             another (trip_id, service_id, route_id),
        #             ...
        #         ]}
        # so the first element of the entry is not a (trip_id, service_id, route_id) tuple.
        # that is the reason for the [1:] slice.
        trip_service_route_ids = self.shape_id_to_trip_service_route_ids_dict[shape_id][1:]

        trips_with_service = []
        for trip_id, service_id, route_id in trip_service_route_ids:
            if ignore_time:
                trips_with_service.append((service_id, trip_id, route_id, [0]))
                continue
            # load trip from dict
            trip = self.trip_id_to_trip_with_stops_dict[trip_id]

            # get realtime data, if available
            realtime_data = None
            if self.gtfs_rt_dict and trip_id in self.gtfs_rt_dict:
                realtime_data = self.gtfs_rt_dict[trip_id]

            trip_segment_ids = trip.get_active_trip_segment_ids(
                date, edge_id, self, realtime_data, ignore_start_end_date, delay, earliness)
            if trip_segment_ids:
                trips_with_service.append((service_id, trip_id, route_id, trip_segment_ids))

        return trips_with_service

    def get_time_difference(self, trip_id, location_time, ts_ids):
        """
        Take a trip_id, a location, a time and a list of trip segment ids.
        Calculate a predicted time for the trip at the location at the given time.

        This time uses the stop times of stops at each end of a trip segment.
        It assumes that the vehicle travels at constant speed on a trip segment.

        For all the trip segments just get the minimal time difference.

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...                    path_saved_dictionaries=r"../saved_dictionaries/Doctests", verbose=False)
        >>> tt.get_time_difference("1.TA.91-10-A-j22-1.1.H", (47.49943924, 7.5572257042, 1663263900), [1, 2]) < \
                timedelta(seconds=2)
        True
        """
        ret = None
        trip_id_hash = self.trip_id_to_trip_with_stops_dict[trip_id].hash_to_edge_id_to_trip_segments_dict
        ts_polyline = self.hash_to_edge_id_to_trip_segment_id_dict_dict[trip_id_hash][1]
        stops_in_trip = self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[trip_id][1]

        for ts in ts_ids:
            if ts >= len(ts_polyline):
                continue

            # get polyline, location and user_datetime
            line_string = ts_polyline[ts]
            lat, lon, tim = location_time
            location = lat, lon
            user_datetime = Utils.convert_utc_to_local_time(tim)

            # calculate how much of a trip segment the vehicle has travelled
            _, ts_start_time, start_stop_id = stops_in_trip[ts]
            ts_end_time, _, end_stop_id = stops_in_trip[ts + 1]
            if line_string.length == 0:
                edge_travelled_percentage = 0
            else:
                nearest_point_on_line = line_string.interpolate(line_string.project(Point(location)))
                edge_travelled_percentage = split(
                    snap(line_string, nearest_point_on_line, 0.000001),
                    nearest_point_on_line).geoms[0].length / line_string.length

            # based on the travelled percentage, calculate the time difference
            diff = Utils.time_difference_calculator(*ts_start_time, *ts_end_time) * edge_travelled_percentage
            time_to_beginning = user_datetime.date() - datetime(1900, 1, 1).date()
            trip_with_stops = self.trip_id_to_trip_with_stops_dict[trip_id]

            start_ot = ts_start_time[1]

            # handle the overtime case, if the user is in overtime
            # we need to subtract a day from the start time
            td = timedelta(0)
            wd, ah = Utils.generate_weekday_time_tuple(user_datetime)
            if (wd, ah, True) in trip_with_stops.active_hours:
                if not start_ot:
                    td = timedelta(days=-1)
            else:
                if start_ot:
                    td = timedelta(days=1)

            optimal_time = ts_start_time[0] + time_to_beginning + diff + td

            # we are only interested in the absolute time difference
            # it does not matter if early or late
            time_difference = abs(optimal_time - user_datetime)
            if ret is None or time_difference < ret:
                ret = time_difference

        return timedelta(0) if ret is None else ret

    def get_next_stop(
            self,
            trip_id: str,
            position: Tuple[float, float],
            last_edge: List[Tuple[float, float]],
            trip_segment_ids: List[int]
    ) -> str:
        """
        Takes a trip id, the predicted current position, the last edge and the list of trip segment ids

        Returns:
            name of possible next stop

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...                    path_saved_dictionaries=r"../saved_dictionaries/Doctests", verbose=False)
        >>> tt.get_next_stop("1.TA.91-10-A-j22-1.1.H", (47.49943924, 7.5572257042),
        ...                  [(47.498989105,7.5570402145), (47.49943924,7.5572257042)], [1, 2, 3]) == \
        "Oberwil BL, Huslimatt"
        True
        """
        # if there is no trip segment id, we cannot determine the next stop
        if len(trip_segment_ids) == 0:
            return ""

        stops_in_trip = self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[trip_id][1]
        _, _, stop_id = stops_in_trip[trip_segment_ids[0] + 1]
        stop_name, stop_lat, stop_lon = self.stop_id_to_stop_information_dict[stop_id]

        # if there is just one trip segment is, then it must be the stop at the end of the trip segment
        if len(trip_segment_ids) == 1:
            return stop_name

        # if there are multiple trip segment ids
        # if gps point is closer than the stop on the edge to the start of the edge
        # then it is just the stop at the end of the trip segment, else it is the stop
        edge_line, current_point = LineString(last_edge), Point(position)
        last_edge_start = Point(last_edge[0])

        for trip_segment_id in trip_segment_ids[1:]:
            stop_point = Point(stop_lat, stop_lon)
            stop_pos_on_last_edge = edge_line.interpolate(edge_line.project(stop_point))
            stop_dist_to_start = stop_pos_on_last_edge.distance(last_edge_start)
            current_point_dist_to_start = current_point.distance(last_edge_start)

            if current_point_dist_to_start > stop_dist_to_start and \
                    stops_in_trip[trip_segment_id + 1:]:
                _, _, stop_id = stops_in_trip[trip_segment_id + 1]
                stop_name, stop_lat, stop_lon = self.stop_id_to_stop_information_dict[stop_id]
            else:
                break

        return stop_name

    def get_destination(self, trip_id: str) -> str:
        """
        Returns the name of the last stop of the given trip

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.get_destination("1.TA.91-10-A-j22-1.1.H")
        'Oberwil BL, Huslimatt'
        >>> tt.get_destination("1.TA.92-8-L-j22-1.1.H")
        'Solothurn, Hauptbahnhof'
        """
        stop_id = self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[trip_id][1][-1][2]
        return self.stop_id_to_stop_information_dict[stop_id][0]

    def get_route_color(self, route_id: str) -> str:
        """
        Finds the color of a given route

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.get_route_color("91-10-A-j22-1")
        '777777'
        """
        # {"route_id": ("route_short_name", route_type, route_color, route_text_color)}
        return self.route_id_to_route_information_dict[route_id][2]

    def find_transfer_possibilities(
            self,
            stop_name: str,
            time: datetime,
            trip_id_frontend: str,
            n: int = 20
    ) -> List[Tuple[str, str, str, int, str, str]]:
        """
        Returns a list of tuples [(route_short_name,
                                   destination station name,
                                   route type(e.g. "Tram", "Bus"),
                                   departure time as epoch timestamp,
                                   route_color as hex number,
                                   route_text_color as hex number)]

        Input:
            stop_name: string of the stop name that is to be checked
            time: starting point of the search for the next departures
                as datetime object
            trip_id_frontend: trip_id of the current trip in the frontend
            n: length of the returned list

        Returns:
            List that contains n tuples as described above

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.find_transfer_possibilities(
        ...     "Ettingen, Bahnhof",
        ...     datetime(2022, 9, 12, 19, 42),  # is a monday, there should be no service
        ...     "1.TA.91-10-A-j22-1.1.H"
        ... )
        []
        >>> tt.find_transfer_possibilities(
        ...     "Ettingen, Bahnhof",
        ...     datetime(2022, 9, 15, 19, 42),  # is a thursday, trip '1.TA.91-10-A-j22-1.3.H' should be active
        ...     "1.TA.91-10-A-j22-1.1.H"
        ... )
        [('10', 'Oberwil BL, Huslimatt', '0', 1663256580000, '777777', 'FFFFFF')]
        """
        # get list of stop_ids with the given stop name
        stops_to_check = self.stop_name_to_list_of_stop_ids_dict[stop_name]

        possible_connections_list = []

        # repeat 5 times, to check active trips for the next 4 to 5 hours if there are less than 20 trips accumulated
        hours = 0
        while hours < 5:
            for stop_id in stops_to_check:
                # get list of trip_ids and the departure time of that trip at the current stop
                if stop_id not in self.stop_id_to_trips_with_departure_time_dict:
                    # might be parent stop, that combines multiple stops together
                    # they might not have trips, so skip in this case
                    continue
                trip_ids_and_departure_times = self.stop_id_to_trips_with_departure_time_dict[stop_id]

                for trip_id, departure_time in trip_ids_and_departure_times:
                    # no need to show own trip on the connections page
                    if trip_id == trip_id_frontend:
                        continue

                    # Get the trip
                    trip_with_stops = self.trip_id_to_trip_with_stops_dict[trip_id]

                    # get the time plus a couple of hours to catch trips that have not yet started,
                    # but still pass the current stop
                    time_offset = time + timedelta(hours=hours)

                    # Check whether the trip is active on the given time and day  (time: user time)
                    is_active, overtime = trip_with_stops.is_trip_active(
                        time_offset, self)

                    if not is_active:
                        continue

                    # check if departure_time hour is something like "25:30:00" (if it is overflowing)
                    # if so, correct the departure time, so it can be converted to a timestamp
                    departure_overtime = False
                    if int(departure_time[:2]) >= 24:
                        departure_time = str(int(departure_time[:2]) - 24) + departure_time[2:]
                        departure_overtime = True

                    # add or subtract a day if needed
                    delta = timedelta(0)
                    if overtime and not departure_overtime:
                        delta = timedelta(days=-1)
                    if not overtime and departure_overtime:
                        delta = timedelta(days=1)

                    # convert departure time to datetime object
                    departure_time = datetime.strptime(
                        time_offset.date().strftime("%d/%m/%Y") + departure_time, "%d/%m/%Y%H:%M:%S") + delta

                    # datetime object is in utc, because server uses utc.
                    departure_time_utc = Utils.convert_local_time_to_utc(departure_time)

                    # convert departure time to epoch timestamp
                    departure_timestamp = datetime.timestamp(departure_time_utc)

                    # trips with more than 22h offset should not be shown
                    # (who wants to see a trip that starts in more than 22h?)
                    if abs(departure_time - time) > timedelta(hours=22):
                        continue

                    route_id = self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[trip_id][0]

                    # find route_short_name
                    # agency_id, short_name, long_name, route_type, color, text_color
                    route_short_name, route_type, route_color, route_text_color = \
                        self.route_id_to_route_information_dict[route_id]

                    # find last stop of trip
                    destination = self.get_destination(trip_id)

                    # only take NEW trips that are not yet in the possible_connections_list
                    # also only choose trips that start AFTER the user time.
                    if departure_time > time and (
                            route_short_name, destination, str(route_type), int(departure_timestamp * 1000),
                            route_color, route_text_color) not in possible_connections_list:
                        possible_connections_list.append((route_short_name, destination, str(route_type),
                                                          int(departure_timestamp * 1000),
                                                          route_color, route_text_color))
            hours += 1

        # only return the next n departing vehicles.
        possible_connections_list.sort(key=itemgetter(3))
        return possible_connections_list[:n]

    def get_shape_polyline_and_stops(
            self,
            shape_id: str,
            trip_id: str
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Calculates the shape of a given shape_id, as well as the trips stops along the shape
        Because we have to keep the memory usage under 32GB ram
            for bigger GTFS feeds like switzerland, we have to calculate
            the shape using the GeoIndex (STRtree).

        >>> tt = GTFSContainer(path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False
        ... )
        >>> tt.get_shape_polyline_and_stops("shp_0_573", "1.TA.91-10-A-j22-1.1.H") == (
        ...     [(47.483688354, 7.5462784767), (47.483692169, 7.5466852188), (47.483715057, 7.5468816757),
        ...      (47.483760834, 7.5470590591), (47.483829498, 7.5472536087), (47.483882904, 7.5473690033),
        ...      (47.48400116, 7.5475687981), (47.484149933, 7.5477590561), (47.484313965, 7.5479159355),
        ...      (47.484695435, 7.548224926), (47.48758316, 7.5504612923), (47.487873077, 7.5506505966),
        ...      (47.488166809, 7.5507864952), (47.488594055, 7.5509586334), (47.488918304, 7.5511059761),
        ...      (47.489227295, 7.5512914658), (47.491275787, 7.5526132584), (47.491703033, 7.5528650284),
        ...      (47.49213028, 7.5530743599), (47.492984772, 7.5534076691), (47.493392944, 7.5536031723),
        ...      (47.493618011, 7.553730011), (47.49508667, 7.554643631), (47.497966766, 7.5564360619),
        ...      (47.498378754, 7.556702137), (47.498760223, 7.5569338799), (47.498989105, 7.5570402145),
        ...      (47.49943924, 7.5572257042), (47.499652863, 7.5573019981), (47.499866486, 7.5573401451),
        ...      (47.500076294, 7.557331562), (47.500282288, 7.5572729111), (47.500461578, 7.5571899414),
        ...      (47.500904083, 7.5569424629), (47.5013237, 7.55671978), (47.501781464, 7.5564575195),
        ...      (47.502212524, 7.5562238693), (47.502635956, 7.5559797287), (47.503059387, 7.5557575226),
        ...      (47.503421783, 7.555606842), (47.504943848, 7.5551428795), (47.505081177, 7.5551075935),
        ...      (47.50535202, 7.5550575256), (47.505638123, 7.5550513268), (47.505924225, 7.5550932884),
        ...      (47.506542206, 7.5552787781), (47.506729126, 7.5553364754)],
        ...     [(47.483779907, 7.5460100173999995), (47.495082855, 7.554687976799999),
        ...      (47.49933242800001, 7.5571761131), (47.506542206000006, 7.5552716255000005)])
        True
        """
        # get the first edge of the shape
        # first_edge: (float, float, float, float)
        first_edge = self.shape_id_to_trip_service_route_ids_dict[shape_id][0]
        edge_end_point = (first_edge[2], first_edge[3])

        traversed_sequence_ids = []

        counter = 0
        polyline = [(first_edge[0], first_edge[1])]
        while True:
            # get neighbors of current edge end point
            # close_edges is a dict containing the destinations of the edges,
            #   as well as their attributes:
            #   For a DiGraph G containing the edges ((0, 0), (1, 1)),
            #                      ((1, 1), (1, 2)), ((1, 1), (2, 2)),
            # the neighbors G[(1, 1)] would be (1, 2) and (2, 2).
            # The dict would look like
            # {(2, 2): {'attribute': 'value'}, (1, 2): {'attribute': 'value'}}
            close_edges = self.GTFSGraph[edge_end_point]

            # neighbour edges with same shape_id
            neighbor_edges_with_same_shape = []

            for close_edge_destination, attributes in close_edges.items():
                # only use the next edge(s) of the given shape, ignore other shapes
                # attributes["shape"]: [(shape_id, sequence_id), ...]
                for shape, sequence_id in attributes["shape"]:
                    if shape == shape_id and sequence_id not in traversed_sequence_ids:
                        neighbor_edges_with_same_shape.append((close_edge_destination, sequence_id))

            if len(neighbor_edges_with_same_shape) == 0:
                # print(f"shape {shape_id} done:\n{polyline}", flush=True)
                break

            if len(neighbor_edges_with_same_shape) > 1:
                # choose the edge with the smallest sequence id
                neighbor_edges_with_same_shape.sort(key=lambda x: x[1])  # in-place sorting
                traversed_sequence_ids.append(neighbor_edges_with_same_shape[0][1])

            polyline.append(neighbor_edges_with_same_shape[0][0])
            edge_end_point = neighbor_edges_with_same_shape[0][0]

            counter += 1
            if counter % 1000 == 0:
                print(counter, flush=True)

            # should never arise, but just in case
            if counter > 100000:
                break

        # get stops
        stops = self.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[trip_id][1]
        stop_positions = []
        for _, _, stop_id in stops:
            name, lat, lon = self.stop_id_to_stop_information_dict[stop_id]
            stop_positions.append((lat, lon))

        return polyline, stop_positions
