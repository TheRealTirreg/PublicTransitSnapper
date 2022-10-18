"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu

This file handles data needed for generating the evaluation.
"""
import csv
from os.path import isfile
from json import load as json_load

import sys
import os.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from Utilities import convert_gtfs_date_to_datetime
from LoadTripsInformation import get_trip_info_dict
from LoadJson import generate_hash_to_edge_id_to_trip_segment_id_dict_dict


class GenerationDataSet:
    """
    Load all data for generating the evaluation dataset.
    """
    def __init__(self, path_to_gtfs):
        self.trip_id_to_stopinfo = self.gen_trip_id_to_stopinfo(path_to_gtfs)
        self.shape_id_to_polyline = self.gen_shape_id_to_polyline(path_to_gtfs)

    @staticmethod
    def gen_shape_id_to_polyline(path_to_gtfs):
        """
        Get a dictionary, that maps shape_id to the polyline of the shape.
        """
        shape_id_to_polyline = {}
        shapes_file = path_to_gtfs + r"shapes.txt"
        with open(shapes_file, "r") as shapes_csv:
            reader = csv.DictReader(shapes_csv, delimiter=",", quotechar='"')
            for line in reader:
                shape_id = str(line["shape_id"])
                location = float(line["shape_pt_lat"]), float(line["shape_pt_lon"])

                if shape_id in shape_id_to_polyline:
                    shape_id_to_polyline[shape_id].append(location)
                else:
                    shape_id_to_polyline[shape_id] = [location]

        shapes_csv.close()

        return shape_id_to_polyline

    @staticmethod
    def gen_trip_id_to_stopinfo(path_to_gtfs: str = r"../GTFS/doctest_files/"):
        """
        Get a dictionary, that maps trip_id to a list of stop information.
        """
        ret = {}
        stops_file = path_to_gtfs + r"stops.txt"
        stop_times_file = path_to_gtfs + r"stop_times.txt"

        # first read the stops file and map stop_id to their location
        stop_id_to_location = {}
        with open(stops_file, "r") as stops_csv:
            reader = csv.DictReader(stops_csv, delimiter=",", quotechar='"')
            for line in reader:
                stop_id = str(line["stop_id"])
                location = float(line["stop_lat"]), float(line["stop_lon"])
                stop_id_to_location[stop_id] = location

        stops_csv.close()

        with open(stop_times_file, "r") as stop_times_csv:
            reader = csv.DictReader(stop_times_csv, delimiter=",", quotechar='"')
            for line in reader:
                trip_id = str(line["trip_id"])
                stop_id = str(line["stop_id"])
                arrival_tuple = convert_gtfs_date_to_datetime(line["arrival_time"])
                departure_tuple = convert_gtfs_date_to_datetime(line["departure_time"])
                stop_info = stop_id_to_location[stop_id], arrival_tuple, departure_tuple

                if trip_id in ret:
                    ret[trip_id].append(stop_info)
                else:
                    ret[trip_id] = [stop_info]

        stop_times_csv.close()

        return ret


def get_trip_infos(city: str, path_to_gtfs: str, path_to_saved: str, new_gtfs: bool = False):
    """
    This is only used for the evaluation.
    Loads trip_id_to_shape_active_weekdays dict.
    Additionally, the saved trips with stops and time and map hash to edge id is loaded as well
    """

    dates_dict = get_trip_info_dict(city, path_to_gtfs, new_gtfs, path_to_saved)

    if isfile(path_to_saved + r"/trips_with_stops_and_times.json") and \
            isfile(path_to_saved + r"/map_hash_to_edge_id_to_trip_segment_id.json"):
        with open(path_to_saved + r"/trips_with_stops_and_times.json", "r") as tws:
            trips_with_stops_and_times = json_load(tws)
            map_hash_to_edge_id_to_trip_segment_id = \
                generate_hash_to_edge_id_to_trip_segment_id_dict_dict(
                    path_to_saved + r"/map_hash_to_edge_id_to_trip_segment_id.json",
                    line_string=False)
    else:
        print("Missing generated Json file, aborting...")

    return dates_dict, trips_with_stops_and_times, map_hash_to_edge_id_to_trip_segment_id
