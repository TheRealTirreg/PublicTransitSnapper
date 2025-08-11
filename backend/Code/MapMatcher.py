"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu

Implements a Hidden Markov Model for the map matching
"""
from time import time
import networkx as nx
from shapely.geometry import LineString, Point
from GTFSContainer import GTFSContainer
import Utilities as Utils
from typing import Tuple, List
from datetime import timedelta
from math import floor


class NetworkOfRoutes:
    """
    A simple class to represent the line network of routes
    extracted from the GTFS.

    Input:
        container: GTFSContainer that has all information from GTFS files
        print_time: prints runtime of major parts
        baseline: use the baseline algorithm, i.e. only use the last GPS point no time
        baseline_hmm: use the baseline algorithm, hmm with no time
        time_after: use time to determine the most likely trip after matching
        slack: if close edges is empty we can skip floor(slack * len(route)) points
            to prevent no match
    """
    class StateNode:
        """
        Create a simple Node to represent each node in Hidden Markov Model
        """
        def __init__(self, point, edge, dist,
                     from_node, to_node, ids, terminal=None):
            self.point = point
            self.edge = edge
            self.dist = dist
            self.from_node = from_node
            self.to_node = to_node
            self.ids = ids
            self.terminal = terminal

        @property
        def coordinates(self):
            return [self.from_node, self.to_node]

    def __init__(self, container: GTFSContainer, print_time=False,
                 prefer_last_trip=False, baseline=False, baseline_hmm=False, time_after=False,
                 slack=0.2, delay=0, earliness=0, timezone="Europe/Berlin"):
        self.print_time = print_time
        self.tt = container
        self.baseline = baseline
        self.baseline_hmm = baseline_hmm
        self.time_after = time_after
        self.slack = slack
        self.prefer_last_trip = prefer_last_trip
        self.delay = timedelta(minutes=delay)
        self.earliness = timedelta(minutes=earliness)
        self.timezone = timezone

    def find_route_name(self, route, trip_id="", dist=0.05):
        """
        Input:
            route: list of coordinates time tuples (length can vary)
            dist: the distance for which edges are considered close

        Returns the most likely path and line as a dict that looks like:
        {
            "route_name": "name of the route",
            "trip_id": "str",
            "route_type": "e.g. 3 for bus",
            "route_dest": "route destination name",
            "route_color": "hex code",
            "shape_id": "str",
            "next_stop": "str",
            "location": [float(latitude), float(longitude)]
        }

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> network = NetworkOfRoutes(gtfs_container, print_time=False)
        >>> r = [(47.499214172500004, 7.55713295935, 1659030303), (47.499652863,7.5573019981, 1659030331),
        ...      (47.500282288, 7.5572729111, 1659030391)]
        >>> dict(sorted(network.find_route_name(r).items())) == {
        ...     'location': (47.500282288, 7.5572729111), 'next_stop': 'Oberwil BL, Huslimatt',
        ...     'route_color': '777777', 'route_dest': 'Oberwil BL, Huslimatt', 'route_name': '10', 'route_type': '0',
        ...     'shape_id': 'shp_0_573', 'trip_id': '1.TA.91-10-A-j22-1.1.H'}
        True
        """
        # if the last n GPS points are too close to each other, do not match
        # if Utils.are_last_gps_points_close_to_each_other(route, 75, 5) or
        #    Utils.are_last_n_coordinates_timewise_too_far_apart(route, n=10, m=5):
        #     return {"route_name": "", "trip_id": "",
        #             "route_type": "", "route_dest": "",
        #             "route_color": "", "shape_id": "",
        #             "next_stop": "", "location": [0, 0]}

        path = []
        start_time = time()

        # route: [(lat, lon, unix_time)]
        if route and route[0] != '0, 0, 0':
            # route = remove_outliers(route)
            if self.baseline:
                path = self.calculate_path([route[-1]], dist)
            else:
                path = self.calculate_path(route, dist)

        end_time = time()
        if self.print_time:
            print("Time Calculate Path: %.4f" % (end_time - start_time), flush=True)

        # if still empty list we can skip everything after
        if not path:
            return {"route_name": "", "trip_id": "",
                    "route_type": "", "route_dest": "",
                    "route_color": "", "shape_id": "",
                    "next_stop": "", "location": [0, 0]}

        path_coords = [node.coordinates for node in path]

        return self.get_all_data(
            route[-1], path_coords, *self.get_most_likely_shape(path, trip_id))

    def get_all_data(self, location, path_coords, shape_id, service_id,
                     trip_id, route_id, trip_segment_ids: List[int]):
        """
        given the last location and a matched path, generate all necessary information for the frontend

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> network = NetworkOfRoutes(gtfs_container, print_time=False)
        >>> _location = (47.500282288, 7.5572729111, 1659030391)
        >>> _path_coords = [[(47.49943924, 7.5572257042), (47.499652863, 7.5573019981)],
        ...       [(47.500076294, 7.557331562), (47.500282288, 7.5572729111)],
        ...       [(47.500076294, 7.557331562), (47.500282288, 7.5572729111)]]
        >>> _shape = "shp_0_573"
        >>> _service_id = "TA+k8700"
        >>> _trip_id = "1.TA.91-10-A-j22-1.1.H"
        >>> _route_id = "91-10-A-j22-1"
        >>> _ts_ids = [2]
        >>> dict(sorted(network.get_all_data(
        ...     _location, _path_coords, _shape, _service_id, _trip_id, _route_id, _ts_ids).items())) == {
        ...     'location': (47.500282288, 7.5572729111), 'next_stop': 'Oberwil BL, Huslimatt',
        ...     'route_color': '777777', 'route_dest': 'Oberwil BL, Huslimatt', 'route_name': '10', 'route_type': '0',
        ...     'shape_id': 'shp_0_573', 'trip_id': '1.TA.91-10-A-j22-1.1.H'}
        True
        """
        ret = {}

        # generate a location on the edge
        line = LineString([path_coords[-1][0], path_coords[-1][1]])
        probable_location = line.interpolate(line.project(Point(location)))
        location_tuple = (probable_location.x, probable_location.y)
        ret["location"] = location_tuple

        start_time = time()
        ret["next_stop"] = self.tt.get_next_stop(trip_id, location_tuple, path_coords[-1], trip_segment_ids)
        ret["route_name"] = self.tt.get_route_short_name(route_id)
        ret["route_type"] = self.tt.get_route_type(route_id)
        ret["route_dest"] = self.tt.get_destination(trip_id)
        ret["route_color"] = self.tt.get_route_color(route_id)
        ret["trip_id"] = trip_id
        ret["shape_id"] = shape_id
        end_time = time()

        if self.print_time:
            print("Time Get Info: %.4f" % (end_time - start_time), flush=True)
        return ret

    def get_most_likely_shape(
            self, path: list, last_trip_id=""
    ) -> Tuple[str, str, str, str, List[int]]:
        """
        Take the route and decide which shape and trip is the most likely one.
        Just count which shape is the most frequent in the nodes of the path.
        Then count the trips of the shape(s) and choose the most frequent one.
        If there are multiple ones randomly choose one.
        If self.time_after, if there are multiple most frequent trips, choose the one that
        has minimal time difference, to the predicted time according to schedule.

        If last_trip_id is specified, prefer the same trip_id, if there are multiply
        most likely trips.

        As input take a path of network x nodes.

        Returns:
            Id of: shape, (service, trip, route)

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> matcher = NetworkOfRoutes(gtfs_container, print_time=False)
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.483882904,7.5473690033, 1659030183)]
        >>> matcher.get_most_likely_shape(matcher.calculate_path(r))
        ('shp_0_573', 'TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.483932904,7.5474190033, 1659030183)]
        >>> matcher.get_most_likely_shape(matcher.calculate_path(r))
        ('shp_0_42', 'TA+k8700', '1.TA.91-10-A-j22-1.2.H', '91-10-A-j22-1', [0])
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.48368454, 7.5464272499, 1659030183)]
        >>> matcher.get_most_likely_shape(matcher.calculate_path(r))
        ('shp_0_573', 'TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.48368454, 7.5464272499, 1659030183)]
        >>> matcher.get_most_likely_shape(matcher.calculate_path(r), '1.TA.91-10-A-j22-1.2.H')
        ('shp_0_573', 'TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])
        >>> r = [(47.499214172500004, 7.55713295935, 1659030303), (47.499652863,7.5573019981, 1659030331),
        ...      (47.500282288, 7.5572729111, 1659030391)]
        >>> matcher.get_most_likely_shape(matcher.calculate_path(r))
        ('shp_0_573', 'TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [2])
        """
        shapes_count, shapes_info, info_to_ts = {}, {}, {}
        route_points = []

        for elem in path:
            added_shapes = set()
            route_points.append(elem.point)
            for t in elem.ids:
                shape_with_sequence, other_ids = t
                shape, _ = shape_with_sequence
                if shape in added_shapes:
                    shapes_info[shape] += other_ids
                    continue

                if shape not in shapes_count:
                    shapes_count[shape] = 1
                    shapes_info[shape] = other_ids
                else:
                    shapes_count[shape] += 1
                    shapes_info[shape] += other_ids

                added_shapes.add(shape)

        # get shape with the highest occurrences
        most_likely_shape_ids = Utils.get_multiple_max_values(list(shapes_count.items()))

        # count all service, trip, route id tuples and get the most frequent
        count_dict = {}

        # for counting, we only need the ids, so remember the ts ids
        for most_likely_shape_id in most_likely_shape_ids:
            for service, trip, route, ts in shapes_info[most_likely_shape_id]:
                ids_no_ts = service, trip, route, most_likely_shape_id
                if ids_no_ts not in count_dict:
                    count_dict[ids_no_ts] = 1
                    info_to_ts[ids_no_ts] = [ts]
                else:
                    count_dict[ids_no_ts] += 1
                    info_to_ts[ids_no_ts].append(ts)

        most_likely_trips = Utils.get_multiple_max_values(list(count_dict.items()))

        most_likely_trip = None
        # if there is only one trip, take it
        if len(most_likely_trips) == 1:
            most_likely_trip = most_likely_trips[0]
        else:
            start_time = time()
            # if last trip id is specified, prefer the same trip id
            # also skip the time based check in this case
            if last_trip_id and self.prefer_last_trip:
                for trip in most_likely_trips:
                    if trip[1] == last_trip_id:
                        most_likely_trip = trip
                        break

            # do the time based matching here
            if not most_likely_trip and self.time_after:
                avg_diff = {}
                for s_id, t_id, r_id, shp in most_likely_trips:
                    to_add = []
                    # for every point in the route calculate the time difference
                    for ts_ids, route_point in zip(info_to_ts[s_id, t_id, r_id, shp], route_points):
                        to_add.append(self.tt.get_time_difference(t_id, route_point, ts_ids))
                    avg_diff[(s_id, t_id, r_id, shp)] = sum(to_add, timedelta()) / len(to_add)

                # get the trip, that has the smallest average time difference
                most_likely_trip = min(avg_diff, key=avg_diff.get)
                end_time = time()
                if self.print_time:
                    print(f"Time based matching took {end_time - start_time} seconds")
            # if no trip was found, just take the first one
            elif not most_likely_trip:
                most_likely_trip = most_likely_trips[0]

        service_id, trip_id, route_id, most_likely_shape_id = most_likely_trip

        # find the trip segments from the original input
        for shape_ids in path[::-1]:
            for shape_seq, tuples in shape_ids.ids:
                if shape_seq[0] == most_likely_shape_id:
                    for tup in tuples:
                        if tup[0] == service_id and tup[1] == trip_id and tup[2] == route_id:
                            ts_ids = tup[3]
                            # if fitting information is found, just return
                            return most_likely_shape_id, service_id, trip_id, route_id, ts_ids

    def calculate_path(self, route, dist=0.05):
        """
        Calculate the most likely path.
        Create a graph that represents the markov chain.
        Take a list of Points as Route and a list of Edges,
        Edges should only be close ones.

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> matcher = NetworkOfRoutes(gtfs_container, print_time=False)
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.48368454, 7.5464272499, 1659030183)]
        >>> [n.coordinates for n in matcher.calculate_path(r)] == [
        ...     [(47.483688354,7.5462784767), (47.48368454,7.5464272499)],
        ...     [(47.483688354,7.5462784767), (47.48368454,7.5464272499)]]
        True
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.483882904,7.5473690033, 1659030183)]
        >>> [n.coordinates for n in matcher.calculate_path(r)] == [
        ...     [(47.483692169, 7.5466852188), (47.483715057, 7.5468816757)],
        ...     [(47.483829498, 7.5472536087), (47.483882904, 7.5473690033)]]
        True
        >>> r = [(47.483688354, 7.5462784767, 1659030123),(47.483932904,7.5474190033, 1659030183)]
        >>> [n.coordinates for n in matcher.calculate_path(r)] == [
        ...     [(47.483692169, 7.5466852188), (47.483765057, 7.5469316757)],
        ...     [(47.483879498, 7.5473036087), (47.483932904, 7.5474190033)]]
        True
        """
        graph = nx.DiGraph()
        start_state = NetworkOfRoutes.StateNode(None, None, None, None, None, None, "start")
        graph.add_node(start_state)
        last_state = [start_state]
        slack = floor(len(route) * self.slack)

        start_time = time()
        for coord in route:
            current_state = []
            lat, lon, tim = coord

            # get all edges that are reasonably close to the point while being active at the time
            close_edges = self.get_close_edges(lat, lon, tim, dist)

            if slack > 0 and not close_edges:
                slack -= 1
                continue

            for edge in close_edges:
                # edge: (id, length, from location, to location, shape names with ids)
                next_state = NetworkOfRoutes.StateNode(coord, edge[0], edge[1], edge[2], edge[3], edge[4])
                graph.add_node(next_state)
                current_state.append(next_state)

                for node in last_state:
                    graph.add_edge(node, next_state)

            last_state = current_state

        end_state = NetworkOfRoutes.StateNode(None, None, None, None, None, None, "end")
        graph.add_node(end_state)
        for node in last_state:
            graph.add_edge(node, end_state)

        end_time = time()
        if self.print_time:
            print("Time Get Close edges and build Graph: %.4f" % (end_time - start_time), flush=True)

        # calculate the distance between the last edges to the last point
        distances = {}
        for edge in graph.in_edges(end_state):
            distances[edge] = LineString(edge[0].coordinates).distance(Point(route[-1]))
        nx.set_edge_attributes(graph, distances, "distance")

        start_time = time()
        try:
            calculated_path = nx.bidirectional_dijkstra(graph, start_state, end_state, weight=self.edge_likelihood)[1]
        except nx.NetworkXNoPath:
            end_time = time()
            if self.print_time:
                print("Time to calculate shortest path in graph Exception: %.4f" % (end_time - start_time), flush=True)
            return []
        end_time = time()
        if self.print_time:
            print("Time to calculate shortest path in graph: %.4f" % (end_time - start_time), flush=True)

        return calculated_path[1:-1]

    def edge_likelihood(self, start, end, attributes=None):
        """
        First implement a very simple version.
        Use log2 space, so squared distances

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> network = NetworkOfRoutes(gtfs_container, print_time=False)
        >>> start_node = NetworkOfRoutes.StateNode(None, None, None, None, None, None, "start")
        >>> end_node = NetworkOfRoutes.StateNode(None, None, None, None, None, None, "end")
        >>> network.edge_likelihood(start_node, end_node, {"distance": 0})
        1
        >>> start_node = NetworkOfRoutes.StateNode((47.483688354,7.5462784767), 1, 11.187683990834213,
        ...                   (47.483688354,7.5462784767), (47.48368454,7.5464272499), [(("a", 1),)], None)
        >>> end_node = NetworkOfRoutes.StateNode((47.483932904,7.5474190033), 2, 10.509894050251068,
        ...                 (47.483879498,7.5473036087), (47.483932904,7.5474190033), [(("a", 4),)], None)
        >>> emission_cost = 0
        >>> distance_cost = Utils.distance_wrapper((47.483688354,7.5462784767), (47.48368454,7.5464272499)) + \
                            Utils.distance_wrapper((47.48368454,7.5464272499), (47.483692169,7.5466852188)) + \
                            Utils.distance_wrapper((47.483692169,7.5466852188), (47.483765057,7.5469316757)) + \
                            Utils.distance_wrapper((47.483765057,7.5469316757), (47.483810834,7.5471090591)) + \
                            Utils.distance_wrapper((47.483810834,7.5471090591), (47.483879498,7.5473036087)) + \
                            Utils.distance_wrapper((47.483829498,7.5472536087), (47.483882904,7.5473690033))
        >>> score = emission_cost + distance_cost
        >>> from math import isclose
        >>> isclose(network.edge_likelihood(start_node, end_node, {"distance": 0}), score, rel_tol=1e-6)
        True
        """
        # for start and end node use distance from gps location
        if start.terminal == "start":
            return 1
        elif end.terminal == "end":
            return attributes["distance"] * 1000000

        # if the nodes represent the same edge, just use the length of the edge
        if start.from_node == end.from_node and start.to_node == end.to_node:
            return start.dist

        emission = LineString([start.from_node, start.to_node]).distance(Point(start.point))

        direction_penalty = Utils.calculate_direction_penalty(
            list(map(lambda x: x[0], start.ids)), list(map(lambda x: x[0], end.ids)))

        # if there is no path set a high score
        distance = 1000000000
        if direction_penalty != -1:
            distance = Utils.bidirectional_dijkstra_modified(
                self.tt.GTFSGraph, start.to_node, end.from_node, weight="length")

        transition = start.dist + distance + end.dist

        if direction_penalty == 1:
            transition += 100000

        return emission + transition

    def get_close_edges(self, lat: float, lon: float, tim: int, max_dist: float = 0.05) -> list:
        """
        Get close edges to a location time tuple.
        For each edge get edge, distance, shapes with sequence and trip information
        Can have multiple edges from the same shape

        Not very accurate in terms of time, only filters for active edges.

        max_dist is in kilometers

        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> network = NetworkOfRoutes(gtfs_container, print_time=False)

        >>> test_lat, test_lon = (47.483688354, 7.5462784767)
        >>> network.get_close_edges(test_lat, test_lon, 1659030121) == [
        ...     (0, 11.187683990834214, (47.483688354, 7.5462784767), (47.48368454, 7.5464272499),
        ...     [(('shp_0_573', 1), [('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])]),
        ...      (('shp_0_42', 1), [('TA+k8700', '1.TA.91-10-A-j22-1.2.H', '91-10-A-j22-1', [0])])], 0.0),
        ...     (1, 19.403764555884866, (47.48368454, 7.5464272499), (47.483692169, 7.5466852188),
        ...     [(('shp_0_573', 2), [('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])]),
        ...      (('shp_0_42', 2), [('TA+k8700', '1.TA.91-10-A-j22-1.2.H', '91-10-A-j22-1', [0])])],
        ...     0.0001488220804655106),
        ...     (2, 14.980623453060634, (47.483692169, 7.5466852188), (47.483715057, 7.5468816757),
        ...     [(('shp_0_573', 3), [('TA+k8700', '1.TA.91-10-A-j22-1.1.H', '91-10-A-j22-1', [0])])],
        ...     0.0004067599908268084),
        ...     (3, 20.21589309829125, (47.483692169, 7.5466852188), (47.483765057, 7.5469316757),
        ...     [(('shp_0_42', 3), [('TA+k8700', '1.TA.91-10-A-j22-1.2.H', '91-10-A-j22-1', [0])])],
        ...     0.0004067599908268084)]
        True
        """
        # convert the utc time to local time zone, that the GTFS uses
        tim_local = Utils.convert_utc_to_local_time(tim, self.timezone)
        point = Point(lat, lon)
        near_edges = self.query_near_edges(point, max_dist)

        shapes_dict, edge_info = {}, {}
        for idx, edge_bounds in enumerate(near_edges):
            real_dist = edge_bounds.distance(point)
            # edge_info = (start, end, length, line, shape)
            start, end = edge_bounds.geoms
            start_t, end_t = (start.x, start.y), (end.x, end.y)
            data = self.tt.GTFSGraph.get_edge_data(start_t, end_t)
            dist, shapes, edge_id = data["length"], data["shape"], data["edge_id"]

            edge_info[edge_id] = (start_t, end_t, dist, shapes, idx, real_dist)
            # filter the shapes, so that there is traffic at this time
            for shape, sequence_id in shapes:
                if shape in shapes_dict:
                    shapes_dict[shape].append((edge_id, sequence_id, real_dist))
                else:
                    shapes_dict[shape] = [(edge_id, sequence_id, real_dist)]

        edges_dict = {}
        for shape, edges_list in shapes_dict.items():
            # sort by the distance from edge to the point -> get the closest active edge of a shape
            for edge_id, sequence_id, _ in sorted(edges_list, key=lambda x: x[2]):
                # ids look like (service_id, trip_id, route_id, trip_segment_ids) where ts_ids -> active trip segments
                ids = self.tt.get_active_trips_information(
                    shape, edge_id, tim_local, delay=self.delay, earliness=self.earliness,
                    ignore_time=(self.baseline or self.baseline_hmm))
                if ids:
                    if edge_id in edges_dict:
                        edges_dict[edge_id].append(((shape, sequence_id), ids))
                    else:
                        edges_dict[edge_id] = [((shape, sequence_id), ids)]

        ret = []
        for edge_id, edge_data in edges_dict.items():
            start_t, end_t, dist, shapes, idx, real_dist = edge_info[edge_id]
            ret.append((idx, dist, start_t, end_t, edge_data, real_dist))

        # sort by the distance between the gps point and the edge, aka real_dist
        ret.sort(key=lambda x: x[5])

        # ret looks like:
        # [(edge_id, length, from location, to location, shapes with sequence and trip information, real_dist), ...]
        # -> Shape with sequence and trip information looks like:
        # [(shape, sequence_id), (service_id, trip_id, route_id, trip_segment_ids)]
        # where trip_segment_ids is a list of ids that are active at the time
        # trip_segment_ids links to the trip segments that are active on the edge at the time
        return ret

    def query_near_edges(self, point: Point, max_dist: float) -> list:
        """
        Query the network for close edges. Max_dist is in kilometers.

        should just be all edges from shapes file => 253 edges
        >>> gtfs_container = GTFSContainer(
        ...     path_gtfs=r"../GTFS/doctest_files",
        ...     path_saved_dictionaries=r"../saved_dictionaries/Doctests",
        ...     verbose=False)
        >>> network = NetworkOfRoutes(gtfs_container, print_time=False)

        >>> t_lat, t_lon = (47.483688354, 7.5462784767)
        >>> len(network.query_near_edges(Point(t_lat, t_lon), 200))
        253

        only the first 3 edges from shp_0_573
        since first 2 edges from shp_0_42 are the same, only the third will be added => total 4
        >>> t_lat, t_lon = (47.483688354, 7.5462784767)
        >>> len(network.query_near_edges(Point(t_lat, t_lon), 0.05))
        4

        should again match 3 surrounding edges
        >>> t_lat, t_lon = (47.083986282, 6.7995955943999995)
        >>> from shapely.geometry import MultiPoint
        >>> e1 = MultiPoint([(47.084133148,6.8000907898), (47.084056854,6.7998485565)]).wkt
        >>> e2 = MultiPoint([(47.084056854,6.7998485565), (47.08391571,6.7993426323)]).wkt
        >>> e3 = MultiPoint([(47.08391571,6.7993426323),(47.083045959,6.7961506844)]).wkt
        >>> sorted(list(map(lambda x: x.wkt, network.query_near_edges(Point(t_lat, t_lon), 0.05)))) == \
            sorted([e1, e2, e3])
        True

        with higher radius should match 4 surrounding edges
        >>> t_lat, t_lon = (47.083986282, 6.7995955943999995)
        >>> len(network.query_near_edges(Point(t_lat, t_lon), 0.1))
        4
        """
        # find close edges by creating a circle of radius max_dist around the gps point
        # max_dist (1 km), 0.00001° ~ 1.112m => from meters to degrees, 1000 / 1.112 * 0.00001 ~= 0.008993
        circle = point.buffer(max_dist * 0.008993)
        near_edges = []
        for edge in self.tt.EdgesGeoIndex.query(circle):
            # remove false positives
            # in shapely intersects is intersecting the boundary or the interior
            if edge.intersects(circle):
                near_edges.append(edge.boundary)

        return near_edges
