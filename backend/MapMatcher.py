from time import time
import networkx as nx
from datetime import datetime
from math import sin, cos, atan2, radians, sqrt
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from GTFSContainer import GTFS_Container
from collections import Counter
import pytz
"""
implement simple method for Hidden Markov Model map matching,
or maybe not so hidden for now :D
"""


class StateNode:
    """
    Create a simple Node to represent each Nodes in markov chain
    """
    def __init__(self, point_id, edge, dist,
                 from_node, to_node, ids, terminal=None):
        self.point = point_id
        self.edge = edge
        self.dist = dist
        self.from_node = from_node
        self.to_node = to_node
        self.ids = ids
        self.terminal = terminal
    """
    def __repr__(self):
        x = "None"
        y = "None"
        if self.from_node:
            x = str(self.from_node)
            # x = str(tuple(map(lambda x: int(x * 100000), self.from_node)))
        if self.to_node:
            y = str(self.to_node)
            # y = str(tuple(map(lambda y: int(y * 100000), self.to_node)))
        return str("[" + x + ", " + y + "]")
    """

    @property
    def coordinates(self):
        return [self.from_node, self.to_node]


def remove_outliers(route, dist=100, threshold=4):
    """
    Remove outliers from the route by removing the nodes that are too far away from the route
    Only remove outliers if there are more than 4 (threshold) points

    dist in meters.

    >>> route0 = [(47.99241414912389, 7.853753493925742), (47.99237760873921, 7.855530222165022),
    ...          (47.99214425648649, 7.853534658777162), (47.99165600835941, 7.853362997410464),
    ...          (47.99128981923254, 7.853599031789673)]
    >>> remove_outliers(route0) == [(47.99241414912389, 7.853753493925742), (47.99214425648649, 7.853534658777162),
    ...                            (47.99165600835941, 7.853362997410464), (47.99128981923254, 7.853599031789673)]
    True
    >>> route1 = [(47.99241414912389, 7.853753493925742), (47.99237760873921, 7.855530222165022),
    ...          (47.99214425648649, 7.853534658777162), (47.99165600835941, 7.853362997410464),
    ...          (47.99128981923254, 7.853599031789673), (47.991089634794875, 7.855801255411465),
    ...          (47.990947187112255, 7.856402271333341), (47.99071715891624, 7.856871293187434)]
    >>> remove_outliers(route1) == [(47.99241414912389, 7.853753493925742), (47.99214425648649, 7.853534658777162),
    ...                             (47.99165600835941, 7.853362997410464), (47.99128981923254, 7.853599031789673),
    ...                             (47.991089634794875, 7.855801255411465), (47.990947187112255, 7.856402271333341),
    ...                             (47.99071715891624, 7.856871293187434)]
    True
    """
    num_removed, last_num_removed = 0, -1
    while len(route) >= threshold + 1 and num_removed != last_num_removed:
        last_num_removed = num_removed
        sorted_distances = sorted(calculate_distances(route), key=lambda x: x[1], reverse=True)
        # only remove if the two points that will be connected by remove one point are close enough to each other
        for idx, d in sorted_distances:
            if d < dist:
                break
            if idx == 0 or idx == len(route) - 1 or distance_wrapper(route[idx - 1], route[idx + 1]) < dist:
                route = route[:idx] + route[idx + 1:]
                num_removed += 1
                break

    return route


def calculate_distances(route):
    distances = []
    for i in range(len(route)):
        if i == 0:
            distances.append((i, distance_wrapper(route[i], route[i+1])))
        elif i == len(route) - 1:
            distances.append((i, distance_wrapper(route[i], route[i-1])))
        else:
            distances.append((i, ((distance_wrapper(route[i], route[i-1]) + distance_wrapper(route[i], route[i+1])) / 2)))
    return distances


def find_route_name(network, route, dist=0.05):
    """
    Return the most likely path_saved_dictionaries and line as a dict.

    >>> file = "GTFS/shapes.txt"
    >>> network = NetworkOfRoutes(file)
    >>> route = [[48.002349854,7.8249974251],
    ... [48.002521515,7.8246965408], [48.002868652,7.8241629601]]
    >>> find_route_name(network, route, 0.01)
    """
    path = []
    # route = remove_outliers(route)
    # route: (lat, lon, unix_time)
    if route and route[0] != '0, 0, 0':
        start_time = time()
        path = calculate_path(network, route, dist)[1:-1]
        end_time = time()
        print("Time Calculate Path: %.4f" % (end_time - start_time), flush=True)

        """
        # if empty first try to remove one point
        if not path_saved_dictionaries:
            for i in range(len(route)):
                route_shorter = route[:i] + route[i + 1:]
                path_saved_dictionaries = calculate_path(network, route_shorter, dist)[1:-1]
                if path_saved_dictionaries:
                    break
        """
    
    # if still empty list we can skip everything after
    if not path:
        return {"edges": [[]], "path_saved_dictionaries": [], "route_name": "4",
                "route_type": "Nothing", "route_dest": "Nothing",
                "next_stop": "Nothing", "location": [0, 0]}

    return get_all_data(route[-1], network, path, *get_most_likely_shape(path))


def get_all_data(location, network, path, shape_id, service_id, trip_id, route_id):
    ret = {}
    path_coords = [node.coordinates for node in path]
    # generate a location on the edge
    line = LineString([path_coords[-1][0], path_coords[-1][1]])
    probable_location = line.interpolate(line.project(Point(location)))
    ret["location"] = (probable_location.x, probable_location.y)
    ret["edges"] = path_coords

    start_time = time()
    # get a possible path_saved_dictionaries from the graph with the matched edges
    # set_path_coords = sorted(set(path_coords), key=path_coords.index)
    matched_path = [path_coords[0][0]]
    for i in range(len(path_coords) - 1):
        start = path_coords[i]
        end = path_coords[i + 1]
        # skip if same edge
        if start == end:
            continue
        # if not on the same shape then do not calculate path_saved_dictionaries
        if not (set(map(lambda x: x[0], network.graph.get_edge_data(*start)["shape"][0])) &
                set(map(lambda x: x[0], network.graph.get_edge_data(*end)["shape"][0]))):
            continue
        matched_path.extend(nx.bidirectional_dijkstra(network.graph, start[1], end[0], weight="length")[1])

    # add the end of the path_saved_dictionaries
    ret["path_saved_dictionaries"] = matched_path + [(probable_location.x, probable_location.y)]
    end_time = time()
    print("Time Match Path: %.4f" % (end_time - start_time), flush=True)

    start_time = time()
    ret["next_stop"] = network.tt.get_next_stop(trip_id, (probable_location.x, probable_location.y))
    ret["route_name"] = network.tt.get_route_short_name(route_id)
    ret["route_type"] = network.tt.get_route_type(route_id)
    ret["route_dest"] = network.tt.get_destination(trip_id)
    ret["route_color"] = network.tt.get_route_color(trip_id)
    end_time = time()
    print("Time Get Info: %.4f" % (end_time - start_time), flush=True)
    return ret


def get_most_likely_shape(path):
    """
    Take the route and decide which shape is the most likely one.
    Just count which shape is the most frequent in the nodes of the path_saved_dictionaries.
    Same for the most likely id.

    As input take a path_saved_dictionaries of network x nodes.

    Returns:
        Id of: shape, (service, trip, route)
    """
    shapes_count, shapes_info = {}, {}

    for elem in path:
        for t in elem.ids:
            shape_with_sequence, other_ids = t
            shape, _ = shape_with_sequence
            if shape not in shapes_count:
                shapes_count[shape] = 1
                shapes_info[shape] = other_ids
            else:
                shapes_count[shape] += 1
                shapes_info[shape] += other_ids

    # get key with the highest occurrence
    most_likely_shape_id = max(shapes_count, key=shapes_count.get)
    occ = Counter(shapes_info[most_likely_shape_id])
    service_id, trip_id, route_id = occ.most_common(1)[0][0]

    return most_likely_shape_id, service_id, trip_id, route_id


def calculate_path(network, route, dist=0.05):
    """
    Calculate the most likely path_saved_dictionaries.
    Create a graph that represents the markov chain.
    Take a list of Points as Route and a list of Edges,
    Edges should only be close ones.

    >>> file = "GTFS/TestShapes/testNetwork.txt"
    >>> network = NetworkOfRoutes(file)
    >>> route = [(0, 0.000005), (0.000015, 0.000015)]
    >>> # calculate_path(network, route, 0.001)
    """
    graph = nx.DiGraph()
    start_state = StateNode(None, None, None, None, None, None, "start")
    graph.add_node(start_state)
    last_state = [start_state]

    start_time = time()
    for point_id, coord in enumerate(route):
        current_state = []
        lat, lon, tim = coord

        # get all edges that are reasonably close to the point
        close_edges = network.get_close_edges(lat, lon, tim, dist)

        for edge in close_edges:
            # edge: (id, length, from location, to location, shape names with ids)
            next_state = StateNode(point_id, edge[0], edge[1], edge[2], edge[3], edge[4])
            graph.add_node(next_state)
            current_state.append(next_state)

            for node in last_state:
                graph.add_edge(node, next_state)

        last_state = current_state

    end_state = StateNode(None, None, None, None, None, None, "end")
    graph.add_node(end_state)
    for node in last_state:
        graph.add_edge(node, end_state)

    end_time = time()
    print("Time Get Close edges and build Graph: %.4f" % (end_time - start_time), flush=True)

    start_time = time()
    # calculate the distance between start and first nodes
    distances = {}
    for edge in graph.out_edges(start_state):
        distances[edge] = LineString(edge[1].coordinates).distance(Point(route[0]))

    # calculate the distance between end and last nodes
    for edge in graph.in_edges(end_state):
        distances[edge] = LineString(edge[0].coordinates).distance(Point(route[-1]))

    nx.set_edge_attributes(graph, distances, "distance")

    end_time = time()
    print("Time for start and end node distance: %.4f" % (end_time - start_time), flush=True)

    start_time = time()
    try:
        calculated_path = nx.bidirectional_dijkstra(graph, start_state, end_state, weight=network.edge_likelihood)[1]
    except nx.NetworkXNoPath:
        end_time = time()
        print("Time to calculate shortest path_saved_dictionaries in graph Exception: %.4f" % (end_time - start_time), flush=True)
        return []
    end_time = time()
    print("Time to calculate shortest path_saved_dictionaries in graph: %.4f" % (end_time - start_time), flush=True)

    return calculated_path


def distance_wrapper(point1, point2):
    """
    Calculate the distance between two points.
    point (lat, lon, ...)
    """
    return great_circle_distance(point1[0], point1[1], point2[0], point2[1])


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
    r = 6371e3  # radius of earth in m
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) * sin(dlat / 2) +\
        cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) * sin(dlon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


class NetworkOfRoutes:
    """
    A simple class to represent the line network of routes
    extracted from the GTFS.
    """
    def __init__(self, file_name):
        self.edges = self.gen_edges(file_name)
        self.graph = self.gen_graph()
        self.gi = self.gen_gi()
        self.tt = GTFS_Container(r"GTFS/calendar.txt", r"GTFS/trips.txt",
                                 r"GTFS/stop_times.txt", r"GTFS/routes.txt",
                                 r"GTFS/stops.txt", r"GTFS/shapes.txt",
                                 r"GTFS/calendar_dates.txt", update_dicts=False)
        # path_hamburg_gtfs = r"../GTFS/Hamburg/hvv/gtfs-with-shapes"
        # self.tt = GTFS_Container(
        #     path_hamburg_gtfs + r"/calendar.txt",
        #     path_hamburg_gtfs + r"/trips.txt",
        #     path_hamburg_gtfs + r"/stop_times.txt",
        #     path_hamburg_gtfs + r"/routes.txt",
        #     path_hamburg_gtfs + r"/stops.txt",
        #     path_hamburg_gtfs + r"/shapes.txt",
        #     path_hamburg_gtfs + r"/calendar_dates.txt",
        #     path_saved_dictionaries=r"saved_dictionaries_hamburg",
        #     update_dicts=False)

    def edge_likelihood(self, start, end, attributes):
        """
        First implement a very simple version.
        Use log2 space, so squared distances

        >>> file = "GTFS/TestShapes/testNetwork.txt"
        >>> network = NetworkOfRoutes(file)
        >>> start = StateNode(None, None, None, None, None, None, "start")
        >>> end = StateNode(None, None, None, None, None, None, "end")
        >>> network.edge_likelihood(start, end, None)
        0
        >>> start = StateNode(1, 1, 1.1119492664455877,
        ...                   (0,0), (0.00001,0), None)
        >>> end = StateNode(2, 2, 1.1119492664455877,
        ...                 (0.00001,0.00001), (0.00002,0.00002), None)
        >>> emission = 1.1119492664455877
        >>> distance = 1.1119492664455708
        >>> score = emission + distance
        >>> network.edge_likelihood(start, end, None) == score
        True
        """
        # for start and end node calculate distance to edge from gps location
        if start.terminal == "start" or end.terminal == "end":
            return attributes["distance"] * 1000000

        # if the nodes represent the same edges no cost (* 1)
        if start.from_node == end.from_node and start.to_node == end.to_node:
            return start.dist

        emission = start.dist

        # if the end node has smaller sequence number than start node add cost
        shape_sequence_start = start.ids
        shape_sequence_end = end.ids
        shape_sequence_start.sort(key=lambda x: x[0][0])
        shape_sequence_end.sort(key=lambda x: x[0][0])
        # make intersection of two sorted lists
        # there cannot be the same edge, see case above
        i = 0
        j = 0
        same_shapes = []
        while i < len(shape_sequence_start) and j < len(shape_sequence_end):
            if shape_sequence_start[i][0][0] == shape_sequence_end[j][0][0]:
                same_shapes.append((shape_sequence_start[i][0][1], shape_sequence_end[j][0][1]))
                i += 1
                j += 1
            elif shape_sequence_start[i][0][0] < shape_sequence_end[j][0][0]:
                i += 1
            else:
                j += 1

        # take the average directions, if most are in the wrong direction add cost
        if sum(map(lambda x: 1 if x[0] < x[1] else 0, same_shapes)) < len(same_shapes) / 2:
            emission += 100000

        try:
            distance = nx.bidirectional_dijkstra(self.graph, start.to_node, end.from_node, weight="length")[0]
        except nx.NetworkXNoPath:
            # if there is no path_saved_dictionaries set a high score
            distance = 1000000000

        transition = distance
        return emission + transition

    def get_close_edges(self, lat, lon, time, max_dist=0.05) -> list:
        """
        Get close edges, for each edge remember
        edge, distance, and the nodes on both sides.
        not very accurate, but just find close nodes in graph and
        then take all connected edges
        max_dist in kilometers

        >>> file = "GTFS/TestShapes/testNetwork.txt"
        >>> network = NetworkOfRoutes(file)
        >>> lat, lon = (0, 0.000005)  # (0.00002, 0.00002)]
        >>> network.get_close_edges(lat, lon, 0.001) == [
        ...     (0, 1.1119492664455877, (0.0, 0.0), (1e-05, 0.0), [['shp_1']]),
        ...     (1, 1.1119492664455877, (0.0, 0.0), (0.0, 1e-05), [['shp_2']]),
        ...     (2, 1.1119492664455877, (0.0, 1e-05),
        ...                                       (1e-05, 1e-05), [['shp_4']])]
        True
        """
        # max_dist (1 km), 0.00001° ~ 1.112m => from meters to degrees
        # 1000 / 1.112 * 0.00001 ~= 0.008993
        tim_utc = datetime.fromtimestamp(time)
        tim = tim_utc.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Berlin")).replace(tzinfo=None)
        circle = Point(lat, lon).buffer(max_dist * 0.008993)
        near_edges = []
        for edge in self.gi.query(circle):
            # remove false positives
            if edge.intersects(circle):
                near_edges.append(edge.boundary)

        ret = []
        # find the data for each edge, maybe implement with dict later
        for index, edge_bounds in enumerate(near_edges):
            # edge_info = (start, end, length, line, shape)
            start, end = edge_bounds.geoms
            start_t = (start.x, start.y)
            end_t = (end.x, end.y)
            data = self.graph.get_edge_data(start_t, end_t)
            # line = data["line"]
            dist = data["length"]
            shapes = data["shape"]
            real_dist = edge_bounds.distance(Point(lat, lon))
            new_shapes = []
            # filter the shapes, so that there is traffic at this time
            # start_time = t()
            for shape, sequence_id in shapes[0]:
                ids = list(set(self.tt.isThereTrafficOnShapeReturnIds(shape, start_t, tim) +
                               self.tt.isThereTrafficOnShapeReturnIds(shape, end_t, tim)))
                if ids:
                    new_shapes.append(((shape, sequence_id), ids))
                # print(t() - start_time, flush=True)
                # start_time = t()
            if new_shapes:
                ret.append((index, dist, start_t, end_t, new_shapes, real_dist))

        # print(ret, flush=True)
        ret.sort(key=lambda x: x[5])
        # print(ret[:10], flush=True)
        return ret[:10]

    def gen_gi(self):
        """
        Generate a GeoIndex from with the graph nodes
        """
        return STRtree([LineString(edge) for edge in self.graph.edges])

    def gen_graph(self):
        """
        Generate graph from the list of edges
        first just use a DiGraph, MultiDiGraph might be useful in the future

        >>> import matplotlib.pyplot as plt
        >>> file = "GTFS/TestShapes/testShapesShort.txt"
        >>> network = NetworkOfRoutes(file)
        >>> nx.draw(network.graph, with_labels=True)
        >>> # plt.show()
        """
        graph = nx.DiGraph()
        for edge in self.edges:
            # if the edge in already in the graph just add information
            if graph.has_edge(edge[0], edge[1]):
                shape_old = graph.get_edge_data(edge[0], edge[1])["shape"]
                graph.add_edge(edge[0], edge[1], length=edge[2], line=edge[3], shape=shape_old + [edge[4]])
            else:
                # edge = (start, end, length, line, shape)
                graph.add_edge(edge[0], edge[1], length=edge[2], line=edge[3], shape=[edge[4]])
        return graph

    def gen_edges(self, file_name: str) -> list:
        """
        Generates a list of edges from shape File.

        >>> file = "GTFS/TestShapes/testShapesShort.txt"
        >>> network = NetworkOfRoutes(file)
        >>> # print(network.edges)
        """
        edges = []
        for edge, shapes in self.simplify2(file_name).items():
            start, end = edge
            # shapes = [(shape_name, shape_point_sequence)]
            edges.append((start, end, great_circle_distance(start[0], start[1], end[0], end[1]),
                          LineString([start, end]), shapes))
        # edge = (start, end, length, line, shapes)
        return edges

    def simplify2(self, file_name) -> dict:
        """
        take a GTFS shapes file and remove duplicate shapes.

        Return dictionary of unique edges, with all shape names in a list.
        """
        edges = {}

        with open(file_name) as shapes:
            last_location = ()
            # skip the first line with name of columns
            start = True
            for line in shapes:
                if start:
                    start = False
                    continue
                information = line.rstrip().split(",")
                shape_name = information[0]
                location, shape_point_sequence = (float(information[1]), float(information[2])),  int(information[3])
                if shape_point_sequence == 1:
                    last_location = location
                    continue
                edge = (last_location, location)
                if edge in edges:
                    if shape_name not in edges[edge]:
                        edges[edge] += [(shape_name, shape_point_sequence)]
                else:
                    edges[edge] = [(shape_name, shape_point_sequence)]
                last_location = location
        return edges
