from typing import Tuple
from datetime import datetime, timedelta
from time import time
from shapely.geometry import Point
import pandas as pd
import os
import pickle
from TripsWithStops import TripWithStopsAndTimes
import Utilities as utils


class GTFS_Container:
    """
    Contains GTFS data needed by the HMM to check in O(1) if there is a public transit vehicle on a given shape.
    Load and save GTFS files via the constructor (load: update_dicts=False)
    """

    def __init__(
            self,
            calendar_file,
            trips_file,
            stop_times_file,
            routes_file,
            stops_file,
            shapes_file,
            calendar_dates_file,
            path=r"saved_dictionaries_freiburg",
            update_dicts=False,
            only_update_tripswithstops=False
    ):
        """
        Only (re-)builds the dicts if specified, as it may take a few minutes to load the GTFS data.
        """
        self._weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }

        if not self._doesSavingPathExist(path) and not update_dicts:
            raise "Error: no GTFS files saved under the given path_saved_dictionaries.\n" \
                  "Try 'update_dicts=True' or giving another path_saved_dictionaries like 'saved_dictionaries_freiburg'"

        if update_dicts and only_update_tripswithstops:
            self._loadDictionaries(path, only_update_tripswithstops=True)

            with open(path + r"/trip_id_to_active_days_information.pkl", "rb") as f:
                self._trip_id_to_active_days_information_container = pickle.load(f)

            # {"trip_id": TripWithStopsAndTimes}
            self._trips_with_stops = self._generateTripsWithStopsAndTimes(trips_file)
            self._saveDictionaries(path, only_update_tripswithstops=True)

        # (re)-build dictionaries
        elif update_dicts:
            # {"shape_id": [(lat_0, lon_0), ..., (lat_n, lon_n)]}
            self._shape_id_to_shape_polyline = self._generateShapeIdToShapePolyline(shapes_file)  # saved

            # {"shape_id": [("trip_id", "service_id", "route_id")]}
            self._shape_id_to_service_id_trip_id_and_route_id_container = \
                self._generateShapeIdToServiceIdsShapeIdAndRouteIdDict(trips_file)  # saved

            # {"service_id": ([active weekdays], (start_date, end_date))}
            self._service_id_to_active_weekdays_container = \
                self._generateServiceIdToWeekDaysDict(calendar_file)  # saved

            # {"trip_id":
            # ([active weekdays from 0 (monday) to 6 (sunday)], (start_date, end_date), [extra_dates], [removed_dates])}
            self._trip_id_to_active_days_information_container = \
                self._generateTripIdActiveDayInformation(trips_file, calendar_file, calendar_dates_file)  # todo save

            # {"stop_id": ("stop_name", "stop_lat", "stop_lon")}
            self._stop_id_to_stop_information_container = \
                self._generateStopIdToStopInformationDict(stops_file)  # saved

            # {"trip_id": [(arrival_time(datetime),    # <-- List of stops on trip
            #              departure_time(datetime),
            #              "stop_name",
            #              stop_lat,
            #              stop_lon)]}
            self._trip_id_to_list_of_stops_with_information_container = \
                self._generateTripIdToListOfStopsWithInformation(stop_times_file)

            # {"route_id": ("agency_id", "route_short_name", "route_type")}
            self._route_id_to_route_information_container = \
                self._generateRouteIdToRouteInformationDict(routes_file)  # saved

            # {"trip_id": "Name of last stop on this trip"}
            self._trip_id_to_last_stop_name_of_trip_container = \
                self._generateTripIdToLastStopNameOfTripDict(stop_times_file, stops_file, trips_file)  # saved

            # {"stop name": ["stop_id"]}
            self._stop_name_to_list_of_stop_ids_container = \
                self._generate_stop_name_to_list_of_stop_ids_dict(stops_file)  # saved

            # {"stop_id": ["trip_id", "departure_time"]}
            self._stop_id_to_trips_with_departure_time_container = \
                self._generateStopIdToTripWithDepartureTimeDict(stop_times_file, stops_file)  # saved

            # {"trip_id": ("route_short_name", "route type" (e.g. "Tram" or "Bus"),
            #              "last stop of trip", route_color, route_text_color)}
            self._trip_id_to_route_short_name_route_type_and_destination_container = \
                self._generateTripIdToRouteShortNameRouteTypeAndDestinationDict(trips_file, routes_file)  # saved

            # {"trip_id": TripWithStopsAndTimes}
            self._trips_with_stops = self._generateTripsWithStopsAndTimes(trips_file)

            self._saveDictionaries(path)

        else:
            self._loadDictionaries(path)

    @staticmethod
    def _generateShapeIdToShapePolyline(shapes_file):
        """
        Returns a dict {"shape_id": [(lat_0, lon_0), ..., (lat_n, lon_n)]}
        """
        # debug
        print("Generating shape_id => polylines dictionary")

        df = pd.read_csv(shapes_file, usecols=["shape_id", "shape_pt_lat", "shape_pt_lon"], header=0)
        dct = {}

        # get every shape_id in a list
        shape_ids = list(set(df["shape_id"]))
        num_shape_ids = len(shape_ids)

        for i, shape_id in enumerate(shape_ids):
            polyline = []
            points = df[df["shape_id"] == shape_id]
            for j, row in points.iterrows():
                polyline.append((row["shape_pt_lat"], row["shape_pt_lon"]))
            dct[shape_id] = polyline

            # debug:
            if not i % 100:
                print(f"{round(i / num_shape_ids * 100, 2)}%\tof writing shape_id => polyline - dict")

        # debug
        print("100.0%\tof writing shape_id => polyline - dict")
        print("Finished generating shape_id => polyline dictionary")

        return dct

    @staticmethod
    def _generateShapeIdToServiceIdsShapeIdAndRouteIdDict(trips_file):
        """
        Returns a dict {"shape_id": [("trip_id", "service_id", "route_id")]}
        """
        # debug
        print("Generating shape_id => service_id, trip_id, route_id dictionary")

        df = pd.read_csv(trips_file, usecols=["route_id", "service_id", "trip_id", "shape_id"], header=0)
        dct = {}

        # get every shape_id in a list
        shape_ids = list(set(df["shape_id"]))

        for shape_id in shape_ids:
            # get trip_ids and service_ids where "shape_id" == shape_id
            trips_on_current_shape = df[df["shape_id"] == shape_id]
            # print("\n----------------------------------\n", trips_on_current_shape)

            dct[shape_id] = list(zip(
                list(trips_on_current_shape["service_id"]),
                list(trips_on_current_shape["trip_id"]),
                list(trips_on_current_shape["route_id"])
            ))

        # debug
        print("Finished generating shape_id => service_id, trip_id, route_id dictionary")

        return dct

    def _generateServiceIdToWeekDaysDict(self, calendar_file):
        """
        Returns a dict {"service_id": ([active weekdays], (start_date, end_date))}
        """
        # debug
        print("Generating service_id => weekdays dictionary")

        df = pd.read_csv(calendar_file)
        dct = {}
        for i, row in df.iterrows():
            days = []
            for day in self._weekdays.keys():
                if int(row[day]):
                    days.append(day)
            dct[row["service_id"]] = (days, (row["start_date"], row["end_date"]))

        # debug
        print("Finished generating service_id => weekdays dictionary")

        return dct

    def _generateTripIdActiveDayInformation(
            self,
            trips_file,
            calendar_file,
            calendar_dates_file
    ):
        """
        Returns a dict {"trip_id": ([active weekdays from 0 (monday) to 6 (sunday)],
                                    (start_date, end_date),
                                    [extra_dates],
                                    [removed_dates])}
        """
        # debug
        print("Generating trip_id => weekdays and start/end date dictionary")

        trips_df = pd.read_csv(trips_file, usecols=["service_id", "trip_id"], header=0)
        calendar_df = pd.read_csv(calendar_file)
        calendar_dates_df = pd.read_csv(calendar_dates_file)
        dct = {}

        # get every trip_id in a list
        num_trip_ids = len(trips_df)

        # rows contain service_id and trip_id
        for i, row in trips_df.iterrows():
            # get all the weekdays on which the service_id is active
            calendar_row = calendar_df[calendar_df["service_id"] == row["service_id"]]
            weekdays = []
            for weekday, weekday_num in self._weekdays.items():
                if int(calendar_row[weekday]):
                    weekdays.append(weekday_num)
            weekdays.sort()

            # get start_date and end_date from calendar_file for the current trip_id/service_id
            start_date, end_date = calendar_row["start_date"].values[0], calendar_row["end_date"].values[0]
            start_date_datetime = datetime.strptime(str(start_date), "%Y%m%d")
            end_date_datetime = datetime.strptime(str(end_date), "%Y%m%d")

            # get every exception on the current trip_id/service_id from calendar_date_file
            extra_dates = []
            removed_dates = []
            calendar_dates_rows = calendar_dates_df[calendar_dates_df["service_id"] == row["service_id"]]
            for j, date_exception_type_row in calendar_dates_rows.iterrows():
                # 1 - Service has been added for the specified date
                if date_exception_type_row["exception_type"] == 1:
                    extra_dates.append(datetime.strptime(str(date_exception_type_row["date"]), "%Y%m%d"))
                # 2 - Service has been removed for the specified date
                if date_exception_type_row["exception_type"] == 2:
                    removed_dates.append(datetime.strptime(str(date_exception_type_row["date"]), "%Y%m%d"))

            dct[row["trip_id"]] = (weekdays, (start_date_datetime, end_date_datetime), extra_dates, removed_dates)

            # debug:
            if not i % 100:
                print(f"{round(i / num_trip_ids * 100, 2)}%\tof writing trip_id => weekdays and start/end date - dict")

        # debug
        print("100.0%\tof writing trip_id => weekdays and start/end date - dict")
        print("Finished generating trip_id => weekdays and start/end date dictionary")

        return dct

    def _generateTripIdToListOfStopsWithInformation(self, stop_times_file):
        """
        Returns a dict {"trip_id": [((arrival_time(datetime), arrival_time_overflow),    # <-- List of stops on trip
                                    (departure_time(datetime), departure_time_overflow),
                                    "stop_name",
                                    stop_lat,
                                    stop_lon)]}
        """
        # debug
        print("Generating trip_id => List of stops-information dictionary")

        df = pd.read_csv(stop_times_file, usecols=["trip_id", "arrival_time", "departure_time", "stop_id"], header=0)
        dct = {}

        # get every trip_id in a list
        trip_ids = list(set(df["trip_id"]))
        num_trip_ids = len(trip_ids)

        # debug
        print("Number of trips:", num_trip_ids, "\nNumber of lines in stop_times:", len(df))

        # loop through every trip
        for i, trip_id in enumerate(trip_ids):
            # trip_df: every row in stop_times.txt where "trip_id" is the current trip_id
            trip_df = df[df["trip_id"] == trip_id]

            # loop through every stop on the current trip and add it to the list
            stops = []
            for j, row in trip_df.iterrows():
                # get information on current stop and add it to the stops-list
                arrival_time, arrival_time_overflow = utils.convertGtfsDateToDatetime(row["arrival_time"])
                departure_time, departure_time_overflow = utils.convertGtfsDateToDatetime(row["departure_time"])
                stop_name, stop_lat, stop_lon = self._stop_id_to_stop_information_container[row["stop_id"]]
                stops.append((
                    (arrival_time, arrival_time_overflow),
                    (departure_time, departure_time_overflow),
                    str(stop_name),
                    float(stop_lat),
                    float(stop_lon)
                ))

            dct[trip_id] = stops

            # debug:
            if not i % 100:
                print(f"{round(i / num_trip_ids * 100, 2)}%\tof writing trip_id => List of stops-information - dict")

        # debug
        print("Finished generating trip_id => List of stops-information dictionary")

        return dct

    @staticmethod
    def _generateRouteIdToRouteInformationDict(routes_file):
        """
        Returns a dict {"route_id": ("agency_id", "route_short_name", "route_type")}
        """
        # debug
        print("Generating route_id => route_information dictionary")

        df = pd.read_csv(routes_file, usecols=["route_id", "agency_id", "route_short_name", "route_type"], header=0)
        dct = {}

        for i, row in df.iterrows():
            dct[row["route_id"]] = (row["agency_id"], row["route_short_name"], row["route_type"])

        # debug
        print("Finished generating route_id => route_information dictionary")

        return dct

    @staticmethod
    def _generateStopIdToStopInformationDict(stops_file):
        """
        Returns a dict {"stop_id": ("stop_name", "stop_lat", "stop_lon")}
        """
        # debug
        print("Generating stop_id => stop_information dictionary")

        df = pd.read_csv(stops_file, usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"], header=0)
        dct = {}

        for i, row in df.iterrows():
            dct[row["stop_id"]] = (row["stop_name"], row["stop_lat"], row["stop_lon"])

        # debug
        print("Finished generating stop_id => stop_information dictionary")

        return dct

    @staticmethod
    def _generateTripIdToLastStopNameOfTripDict(stop_times_file, stops_file, trips_file):
        """
        Returns a dict {"trip_id": "Name of last stop on this trip"}
        """
        # debug
        print("Generating trip_id => Last stop of trip dictionary")

        stop_times_df = pd.read_csv(stop_times_file, usecols=["trip_id", "stop_id", "stop_sequence"], header=0)
        stop_df = pd.read_csv(stops_file, usecols=["stop_id", "stop_name"], header=0)
        trips_df = pd.read_csv(trips_file, usecols=["trip_id"], header=0)
        dct = {}

        # get every trip_id in a list
        trip_ids = list(set(trips_df["trip_id"]))
        num_trip_ids = len(trip_ids)

        # debug
        print("Number of trips:", num_trip_ids, "\nNumber of lines in stop_times:", len(stop_times_df))

        for i, trip_id in enumerate(trip_ids):
            # get the last stop of each trip
            last_stop = stop_times_df[stop_times_df["trip_id"] == trip_id].iloc[[-1]]

            # dump the name of the last stop
            dct[trip_id] = stop_df[stop_df["stop_id"] == last_stop["stop_id"].iloc[0]]["stop_name"].iloc[0]

            # debug:
            if not i % 100:
                print(f"{round(i / num_trip_ids * 100, 2)}%\tof writing trip_id => Last stop of trip - dict")

        # debug
        print("Finished generating trip_id => Last stop of trip dictionary")

        return dct

    @staticmethod
    def _generate_stop_name_to_list_of_stop_ids_dict(stops_file):
        """
        Returns a dict {"name of stop": ["stop_id"]}
        """
        # debug
        print("Generating stop name => List of stop_ids dictionary")

        df = pd.read_csv(stops_file, usecols=["stop_id", "stop_name"], header=0)
        dct = {}

        for i, row in df.iterrows():
            # get every stop_id with the current name
            stop_ids = df[df["stop_name"] == row["stop_name"]]

            # for the current stop name, dump a list of every connected stop_id into the dict
            dct[stop_ids["stop_name"].iloc[0]] = stop_ids["stop_id"].tolist()

        # debug
        print("Finished generating stop name => List of stop_ids dictionary")

        return dct

    @staticmethod
    def _generateStopIdToTripWithDepartureTimeDict(stop_times_file, stops_file):
        """
        Returns a dict {"stop_id": ["trip_id", "departure_time"]}
        """
        # debug
        print("Generating stop name => List of stop_ids dictionary")

        stop_times_df = pd.read_csv(stop_times_file, usecols=["trip_id", "departure_time", "stop_id"], header=0)
        stops_df = pd.read_csv(stops_file, usecols=["stop_id"], header=0)
        dct = {}

        # get every stop_id in a list
        stop_ids = list(set(stops_df["stop_id"]))
        num_stop_ids = len(stop_ids)

        for i, stop_id in enumerate(stop_ids):
            # get all the trips that stop at the current stop
            trips_visiting_the_current_stop = stop_times_df[stop_times_df["stop_id"] == stop_id]

            # write all (trip_id, departure_time) that stop at the current stop in a list
            # and dump it in the dict
            lst = []
            for j, row in trips_visiting_the_current_stop[["trip_id", "departure_time"]].iterrows():
                lst.append((row.iloc[0], row.iloc[1]))
            dct[stop_id] = lst

            # debug:
            if not i % 100:
                print(f"{round(i / num_stop_ids * 100, 2)}%\tof writing stop_id => Stop Change Information - dict")

        # debug
        print("Finished generating stop name => List of stop_ids dictionary")

        return dct

    def _generateTripsWithStopsAndTimes(self, trips_file):
        """
        Generates a dict {"trip_id": TripWithStopsAndTimes}
        A TripWithStopsAndTimes knows its shape and matches the stops on a trip to the shape.
            It can decide in ~O(1) whether there is traffic on itself given a position and a time.
        """
        # debug
        print("Generating trips_id => TripsWithStops dictionary")

        trips_df = pd.read_csv(trips_file, usecols=["trip_id", "shape_id"], header=0)
        num_trips = len(trips_df)

        dct = {}
        for i, row in trips_df.iterrows():
            # find polyline of trip
            polyline = self._shape_id_to_shape_polyline[row["shape_id"]]

            # find stops on trip
            # List of ((stop-arrival_time, arrival_time_overflow), (stop-departure_time, departure_time_overflow),
            #           stop_name, stop-lat, stop-lon)-Tuples
            stops = self._trip_id_to_list_of_stops_with_information_container[row["trip_id"]]

            # {"trip_id":
            # ([active weekdays from 0 (monday) to 6 (sunday)], (start_date, end_date), [extra_dates], [removed_dates])}
            activity = self._trip_id_to_active_days_information_container[row["trip_id"]]
            active_weekdays, active_time_span, extra_dates, removed_dates = activity

            # add new TripWithStopsAndTimes to dict
            dct[row["trip_id"]] = TripWithStopsAndTimes(
                trip_id=row["trip_id"],
                shape_of_trip=polyline,
                stops=stops,
                start_date=active_time_span[0],
                end_date=active_time_span[1],
                extra_dates=extra_dates,
                removed_dates=removed_dates,
                active_weekdays=active_weekdays
            )

            # debug:
            if not i % 100:
                print(f"{round(i / num_trips * 100, 2)}%\tof writing trip_id => TripsWithStops - dict")

        # debug
        print("Finished generating trips_id => TripsWithStops dictionary")

        return dct

    def _generateTripIdToRouteShortNameRouteTypeAndDestinationDict(self, trips_file, routes_file):
        """
        Returns a dict {"trip_id": ("route_short_name", "route type" (e.g. "Tram" or "Bus"),
                                    "last stop of trip", route_color, route_text_color)}
        """
        # debug
        print("Generating trips_id => RouteShortName, RouteType and Destination dictionary")

        trips_df = pd.read_csv(trips_file, usecols=["route_id", "trip_id"], header=0)
        routes_df = pd.read_csv(routes_file, usecols=["route_id", "route_color", "route_text_color"], header=0)
        dct = {}

        # get every stop_id in a list
        trip_ids = list(set(trips_df["trip_id"]))
        num_trip_ids = len(trip_ids)

        for i, trip_id in enumerate(trip_ids):
            # find route_id of current trip
            route_id = trips_df[trips_df["trip_id"] == trip_id]["route_id"].iloc[0]

            # get information on current route
            route_short_name = self._route_id_to_route_information_container[route_id][1]

            # get route type
            route_type = self.get_route_type(route_id)

            # get last stop of trip
            destination = self._trip_id_to_last_stop_name_of_trip_container[trip_id]

            # get route_color and route_text_color
            route_color = routes_df[routes_df["route_id"] == route_id]["route_color"].iloc[0]
            route_text_color = routes_df[routes_df["route_id"] == route_id]["route_text_color"].iloc[0]

            if route_color == "":
                route_color = "777777"  # default color is grey
            if route_text_color == "":
                route_text_color = "FFFFFF"  # default text color is white

            dct[trip_id] = (route_short_name, route_type, destination, route_color, route_text_color)

            # debug:
            if not i % 100:
                print(f"{round(i / num_trip_ids * 100, 2)}%\tof writing " +
                      "trip_id => RouteShortName, RouteType and Destination - dict")

        # debug
        print("Finished generating trips_id => RouteShortName, RouteType and Destination dictionary")
        return dct

    @staticmethod
    def _doesSavingPathExist(path):
        """
        True if the given path_saved_dictionaries exists
        """
        return os.path.isdir(path)

    def _saveDictionaries(self, path, only_update_tripswithstops=False):
        """
        As especially the trips => start_stop_times dict takes very long to load,
        save every dictionary to a file.
        """
        # debug
        print("Saving dictionaries")

        # try to make new directory if there is none
        try:
            os.mkdir(path)
        except OSError:
            pass

        if only_update_tripswithstops:
            with open(path + r"/trips_with_stops.pkl", "wb") as f:
                pickle.dump(self._trips_with_stops, f)
            return

        # save dicts
        with open(path + r"/shape_id_to_shape_polyline.pkl", "wb") as f:
            pickle.dump(self._shape_id_to_shape_polyline, f)
        with open(path + r"/shape_id_to_service_id.pkl", "wb") as f:
            pickle.dump(self._shape_id_to_service_id_trip_id_and_route_id_container, f)
        with open(path + r"/service_id_to_active_weekdays.pkl", "wb") as f:
            pickle.dump(self._service_id_to_active_weekdays_container, f)
        with open(path + r"/route_id_to_route_information.pkl", "wb") as f:
            pickle.dump(self._route_id_to_route_information_container, f)
        with open(path + r"/stop_id_to_stop_information.pkl", "wb") as f:
            pickle.dump(self._stop_id_to_stop_information_container, f)
        with open(path + r"/trip_id_to_list_of_stops_with_information.pkl", "wb") as f:
            pickle.dump(self._trip_id_to_list_of_stops_with_information_container, f)
        with open(path + r"/trip_id_to_last_stop_name_of_trip.pkl", "wb") as f:
            pickle.dump(self._trip_id_to_last_stop_name_of_trip_container, f)
        with open(path + r"/stop_name_to_list_of_stop_ids.pkl", "wb") as f:
            pickle.dump(self._stop_name_to_list_of_stop_ids_container, f)
        with open(path + r"/stop_id_to_trips_with_departure_time.pkl", "wb") as f:
            pickle.dump(self._stop_id_to_trips_with_departure_time_container, f)
        with open(path + r"/trip_id_to_route_short_name_route_type_and_destination.pkl", "wb") as f:
            pickle.dump(self._trip_id_to_route_short_name_route_type_and_destination_container, f)
        with open(path + r"/trips_with_stops.pkl", "wb") as f:
            pickle.dump(self._trips_with_stops, f)

        with open(path + r"/trip_id_to_active_days_information.pkl", "wb") as f:
            pickle.dump(self._trip_id_to_active_days_information_container, f)
        # debug
        print("Finished saving dictionaries")

    def _loadDictionaries(self, path, only_update_tripswithstops=False):
        """
        loads the dictionaries from the given path_saved_dictionaries
        """
        # debug
        print("Loading dictionaries...")

        time1 = time()
        with open(path + r"/shape_id_to_shape_polyline.pkl", "rb") as f:
            self._shape_id_to_shape_polyline = pickle.load(f)
        time2 = time()
        print(f"Loaded shape_id => shape_polyline dict in {round(time2 - time1, 2)}s")

        with open(path + r"/shape_id_to_service_id.pkl", "rb") as f:
            self._shape_id_to_service_id_trip_id_and_route_id_container = pickle.load(f)
        time1 = time()
        print(f"Loaded shape_id => service_id dict in {round(time1 - time2, 2)}s")

        with open(path + r"/service_id_to_active_weekdays.pkl", "rb") as f:
            self._service_id_to_active_weekdays_container = pickle.load(f)
        time2 = time()
        print(f"Loaded service_id => active weekdays dict in {round(time2 - time1, 2)}s")

        with open(path + r"/stop_id_to_stop_information.pkl", "rb") as f:
            self._stop_id_to_stop_information_container = pickle.load(f)
        time1 = time()
        print(f"Loaded stop_id => stop information dict in {round(time1 - time2, 2)}s")

        with open(path + r"/trip_id_to_list_of_stops_with_information.pkl", "rb") as f:
            self._trip_id_to_list_of_stops_with_information_container = pickle.load(f)
        time2 = time()
        print(f"Loaded trip_id => list of stops with information dict in {round(time2 - time1, 2)}s")

        with open(path + r"/trip_id_to_last_stop_name_of_trip.pkl", "rb") as f:
            self._trip_id_to_last_stop_name_of_trip_container = pickle.load(f)
        time1 = time()
        print(f"Loaded trip_id => last stop name of trip dict in {round(time1 - time2, 2)}s")

        with open(path + r"/stop_name_to_list_of_stop_ids.pkl", "rb") as f:
            self._stop_name_to_list_of_stop_ids_container = pickle.load(f)
        time2 = time()
        print(f"Loaded trip_id => stop name to list of stop_ids dict in {round(time2 - time1, 2)}s")

        with open(path + r"/stop_id_to_trips_with_departure_time.pkl", "rb") as f:
            self._stop_id_to_trips_with_departure_time_container = pickle.load(f)
        time1 = time()
        print(f"Loaded trip_id => stop_id to trips and departure time dict in {round(time1 - time2, 2)}s")

        with open(path + r"/trip_id_to_route_short_name_route_type_and_destination.pkl", "rb") as f:
            self._trip_id_to_route_short_name_route_type_and_destination_container = pickle.load(f)
        time2 = time()
        print(f"Loaded trip_id => route_short_name, route_type and trip destination dict in {round(time2 - time1, 2)}s")

        if not only_update_tripswithstops:
            with open(path + r"/trips_with_stops.pkl", "rb") as f:
                self._trips_with_stops = pickle.load(f)
        time1 = time()
        print(f"Loaded HUGE trips with stops dict in {round(time1 - time2, 2)}s")

        with open(path + r"/route_id_to_route_information.pkl", "rb") as f:
            self._route_id_to_route_information_container = pickle.load(f)
        time2 = time()
        print(f"Loaded route_id => route information dict in {round(time2 - time1, 2)}s")

        # debug
        print("Finished loading dictionaries.")

    def get_route_short_name(self, route_id):
        """
        Returns the short name of a route (e.g. "4" or "N46")
        """
        return self._route_id_to_route_information_container[route_id][1]

    def get_route_type(self, route_id):
        """
        Returns the route type as a string.

        According to the GTFS reference (https://developers.google.com/transit/gtfs/reference),
        these are the specified route types:

        0  - Tram, Streetcar, Light rail. Any light rail or street level system within a metropolitan area.
        1  - Subway, Metro. Any underground rail system within a metropolitan area.
        2  - Rail. Used for intercity or long-distance travel.
        3  - Bus. Used for short- and long-distance bus routes.
        4  - Ferry. Used for short- and long-distance boat service.
        5  - Cable tram. Used for street-level rail cars where the cable runs beneath the vehicle,
             e.g., cable car in San Francisco.
        6  - Aerial lift, suspended cable car (e.g., gondola lift, aerial tramway). Cable transport where cabins,
             cars, gondolas or open chairs are suspended by means of one or more cables.
        7  - Funicular. Any rail system designed for steep inclines.
        11 - Trolleybus. Electric buses that draw power from overhead wires using poles.
        12 - Monorail. Railway in which the track consists of a single rail or a beam.
        """
        route_type = self._route_id_to_route_information_container[route_id][2]

        if route_type == 0:
            return "Tram"
        if route_type == 1:
            return "Metro"
        if route_type == 2:
            return "Train"
        if route_type == 3:
            return "Bus"
        if route_type == 4:
            return "Ferry"
        if route_type == 5:
            return "Cable tram"
        if route_type == 6:
            return "Gondola"
        if route_type == 7:
            return "Funicular"
        if route_type == 11:
            return "Trolleybus"
        if route_type == 12:
            return "Monorail"

    def getRouteInformationFromShapeId(self, shape_id: str):
        """
        Returns a describing string of the route that operates on the given shape

        WARNING: only gives out one route. There could potentially be more than one route on one shape.
        """
        route_id = self._shape_id_to_service_id_trip_id_and_route_id_container[shape_id][0][2]
        return f"Name: {self.get_route_short_name(route_id)}, Type: {self.get_route_type(route_id)}"

    def _isServiceWithinStartAndEndDate(self, service_id: str, date: datetime):
        """
        Every service_id has a start_date and an end_date. If the given date is within the start_date and the end_date,
        return True. Else False.
        """
        start_date = int(self._service_id_to_active_weekdays_container[service_id][1][0])
        end_date = int(self._service_id_to_active_weekdays_container[service_id][1][1])
        date = int(date.strftime("%Y%m%d"))
        return start_date <= date <= end_date

    def _isThereTrafficOnThisDay(self, service_id: str, date: datetime) -> bool:
        """
        Checks whether there is traffic for the given service_id on the given day
        """
        day = str(date.strftime("%A")).lower()
        return self._service_id_to_active_weekdays_container[service_id][0].__contains__(day)

    def isThereTrafficOnShapeReturnIds(
            self,
            shape_id: str,
            position: Tuple[float, float],
            date: datetime = datetime.now(),
            delay: timedelta = timedelta(minutes=5),
            precipitation: timedelta = timedelta(minutes=1),
            ignore_start_end_date=False,
            allowed_distance_in_m=5
    ) -> list:
        """
        Same as isThereTrafficOnShape, but instead of bool return service, trip and route id
        """
        # get list of trips on the given shape
        trip_ids_and_service_ids = self._shape_id_to_service_id_trip_id_and_route_id_container[shape_id]

        trips_with_service = []
        for service_id, trip_id, route_id in trip_ids_and_service_ids:
            # load trip from dict
            trip = self._trips_with_stops[trip_id]

            if trip.isThereTrafficOnTrip(date, delay, precipitation, ignore_start_end_date):
                trips_with_service.append((trip, service_id, trip_id, route_id))

        # check if position is close to the vehicle on the active trip
        active_close_trips = []
        for trip, service_id, trip_id, route_id in trips_with_service:
            if trip.isCloseToActiveTripSegment(date, position, allowed_distance_in_m, delay, precipitation):
                active_close_trips.append((service_id, trip_id, route_id))

        # for now, only return if there are active trips the given position is close to.
        return active_close_trips

    def get_next_stop(self, trip_id, position):
        """
        take a trip id and the current position

        Returns:
            name of next stop and the destination
        """
        # TODO are the stops already in the correct order???
        trips_stops_times = self._trips_with_stops[trip_id]
        stops = trips_stops_times.stops
        segments = trips_stops_times.trip_segments
        min_dist_idx = -1
        min_dist = 10000
        p = Point(position)
        for i in range(len(segments)):
            dist = segments[i].strtree.nearest(p).distance(p)
            if dist <= min_dist:
                min_dist = dist
                min_dist_idx = i
        # maybe check for index error? there should always be one more stop than line segment!
        next_stop = stops[min_dist_idx + 1][2]

        return next_stop

    def get_destination(self, trip_id):
        # TODO are the stops already in the correct order???
        return self._trip_id_to_list_of_stops_with_information_container[trip_id][-1][2]

    def get_route_color(self, trip_id):
        """
        finds the color of a given trip
        """
        # {"trip_id": ("route_short_name", "route type" (e.g. "Tram" or "Bus"),
        #              "last stop of trip", route_color, route_text_color)}
        _, _, _, color, _ = self._trip_id_to_route_short_name_route_type_and_destination_container[trip_id]
        return color

    def findTransferPossibilities(
            self,
            stop_name: str,
            time: int,
            n: int = 20
    ) -> list[tuple[str, str, str, int, str, str]]:
        """
        Returns a tuple (route_short_name,
                        destination station name,
                        route type(e.g. "Tram", "Bus"),
                        departure time as epoch timestamp,
                        route_color as hex number,
                        route_text_color as hex number)

        Input:
            stop_name: string of the stop name that is to be checked
            time: starting point of the search for the next departures
                as unix timestamp
            n: length of the returned list

        Returns:
            List that contains n tuples as described above
        """
        # get list of stop_ids with the given stop name
        stops_to_check = self._stop_name_to_list_of_stop_ids_container[stop_name]

        # Example: given time is "04:30:00". Any time before would be sorted into lst_before.
        lst_after = []
        lst_before = []

        for stop_id in stops_to_check:
            # get list of trip_ids and the departure time of that trip at the current stop
            trip_ids_and_departure_times = self._stop_id_to_trips_with_departure_time_container[stop_id]

            for trip_id, departure_time in trip_ids_and_departure_times:
                # first, check if the trip is active on the given day
                trip_with_stops = self._trips_with_stops[trip_id]

                # Check whether the trip is active on the given time and day
                if not trip_with_stops.isTripActiveOnDate(datetime.fromtimestamp(time)):
                    continue

                # check if departure_time hour is something like "25:30:00" (if it is overflowing)
                # if so, correct the departure time, so it can be converted to a timestamp
                if int(departure_time[:2]) >= 24:
                    departure_time = str(int(departure_time[:2]) - 24) + departure_time[2:]

                # convert departure time to datetime object
                departure_time = datetime.strptime(datetime.today().date().strftime("%d/%m/%Y") + departure_time,
                                                   "%d/%m/%Y%H:%M:%S")
                # convert departure time to epoch timestamp
                departure_time = datetime.timestamp(departure_time)

                # find route_short_name
                route_short_name, route_type, destination, route_color, route_text_color = \
                    self._trip_id_to_route_short_name_route_type_and_destination_container[trip_id]

                # Example: given time is "043000" (04:30:00). Any time before would be sorted into lst_before.
                if departure_time < time:
                    lst_before.append((route_short_name, destination, route_type, int(departure_time * 1000),
                                       route_color, route_text_color))
                else:
                    lst_after.append((route_short_name, destination, route_type, int(departure_time * 1000),
                                      route_color, route_text_color))

        # only return the next n departing vehicles.
        # sort so that the next time should be the first in the list
        len_after = len(lst_after)
        lst_after.sort(key=lambda x: x[3])

        if len_after >= n:
            return lst_after[:n]

        lst_before.sort(key=lambda x: x[3])
        return lst_after + lst_before[:n - len_after]


if __name__ == '__main__':
    # remove update_dicts=True once the current GTFS data is loaded to avoid long loading times
    tt = GTFS_Container(r"GTFS/calendar.txt",
                        r"GTFS/trips.txt",
                        r"GTFS/stop_times.txt",
                        r"GTFS/routes.txt",
                        r"GTFS/stops.txt",
                        r"GTFS/shapes.txt",
                        r"GTFS/calendar_dates.txt",
                        path=r"saved_dictionaries_freiburg",
                        update_dicts=True,
                        only_update_tripswithstops=True)

    print("================== Hamburg ==============================")
    """
    path_hamburg_gtfs = r"../GTFS/Hamburg/hvv/gtfs-with-shapes"
    tth = GTFS_Container(path_hamburg_gtfs + r"/calendar.txt",
                         path_hamburg_gtfs + r"/trips.txt",
                         path_hamburg_gtfs + r"/stop_times.txt",
                         path_hamburg_gtfs + r"/routes.txt",
                         path_hamburg_gtfs + r"/stops.txt",
                         path_hamburg_gtfs + r"/shapes.txt",
                         path_hamburg_gtfs + r"/calendar_dates.txt",
                         path_saved_dictionaries=r"saved_dictionaries_hamburg",
                         update_dicts=True)
    """
