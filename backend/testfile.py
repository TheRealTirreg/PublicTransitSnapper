import pandas as pd
from datetime import datetime, timedelta
from GTFSContainer import GTFS_Container
from TripsWithStops import TripWithStopsAndTimes


def find_all_trips_of_route(trips_file: str, route_id: str) -> list:
    df = pd.read_csv(trips_file)
    tmp = df[df["route_id"] == route_id]
    return list(set(tmp["trip_id"]))


def find_all_trips_active_on(dt: datetime, trips: list[str]) -> list[TripWithStopsAndTimes]:
    # get TripsWithStops for each trip
    trips_with_stops = []
    for trip_id in trips:
        trips_with_stops.append(tt._trips_with_stops[trip_id])

    ret = []
    for trip in trips_with_stops:
        if trip._isTrafficOnDay(dt, False):
            ret.append(trip)

    return ret


def find_active_trips_in_time_window(
        time: datetime,
        delay: timedelta = timedelta(0),
        precipitation: timedelta = timedelta(0)
) -> list[TripWithStopsAndTimes]:
    late_trips = []
    for active_trip in active_trips:
        if active_trip.isThereTrafficOnTrip(time, delay, precipitation):
            late_trips.append(active_trip)

    return late_trips


if __name__ == '__main__':
    route_id_route_4 = "11-4-I-j22-1"
    trips_of_route_4 = find_all_trips_of_route(r"GTFS/trips.txt", route_id=route_id_route_4)
    tt = GTFS_Container(r"GTFS/calendar.txt",
                        r"GTFS/trips.txt",
                        r"GTFS/stop_times.txt",
                        r"GTFS/routes.txt",
                        r"GTFS/stops.txt",
                        r"GTFS/shapes.txt",
                        r"GTFS/calendar_dates.txt",
                        path=r"saved_dictionaries_freiburg",
                        update_dicts=False,
                        only_update_tripswithstops=False)

    date = datetime(2022, 5, 12, 22)
    active_trips = find_all_trips_active_on(date, trips_of_route_4)

    for trip in sorted(find_active_trips_in_time_window(
            date, delay=timedelta(hours=1), precipitation=timedelta(hours=1))):
        print(trip)
