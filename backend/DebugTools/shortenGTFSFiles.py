from typing import Optional, List
import pandas as pd
import os


def shorten_GTFS_files(
        gtfs_in=r"../GTFS/Freiburg/VAG/gtfs-out/",
        gtfs_out=r"../GTFS/Freiburg/shortened_gtfs/gtfs-out/",
        agencies: Optional[List[str]] = None,
        route_types: Optional[List[int]] = None
):
    """
    Reads GTFS files and removes routes and entailing information
        that do not match the given properties:

    agencies:
        If None: keep everything
        example for a list: ["agency_id_01", "agency_id_03"]
            => will keep only routes with the agency_ids from the list.

    route_types:
        If None: keep everything
        example for a list: [0, 5]
            => will only keep routes that are operated by trams (0) and cable trams (5).

    After removing the routes, only keep the trips with route_ids that have not been deleted.
    Only keep the needed shapes, stops, stop_times and services.
    """
    if agencies is None and route_types is None:
        print("Nothing has been changed")
        print("Done.")
        return

    routes_df = pd.read_csv(gtfs_in + r"routes.txt", header=0)

    # remove all routes where the agency_id is not in agencies
    if agencies is not None:
        routes_df = routes_df[routes_df["agency_id"].isin(agencies)]

    # remove all routes where the route_type is not in route_types
    if route_types is not None:
        routes_df = routes_df[routes_df["route_type"].isin(route_types)]

    # write routes_txt
    if not os.path.exists(gtfs_out):
        print("Output folder does not exist. Creating it...")
        os.makedirs(gtfs_out)

    routes_df.to_csv(gtfs_out + r"routes.txt", index=False)

    # remove all trips where the route_id does not exist
    trips_df = pd.read_csv(gtfs_in + r"trips.txt", header=0)
    trips_df = trips_df[trips_df["route_id"].isin(routes_df["route_id"])]
    trips_df.to_csv(gtfs_out + r"trips.txt", index=False)
    del routes_df

    # remove all shapes where the shape_id is not used by trips.txt
    shapes_df = pd.read_csv(gtfs_in + r"shapes.txt", header=0)
    shapes_df = shapes_df[shapes_df["shape_id"].isin(trips_df["shape_id"])]
    shapes_df.to_csv(gtfs_out + r"shapes.txt", index=False)
    del shapes_df

    # remove all services from calendar.txt that are not used by trips.txt
    calendar_df = pd.read_csv(gtfs_in + r"calendar.txt", header=0)
    calendar_df = calendar_df[calendar_df["service_id"].isin(trips_df["service_id"])]
    calendar_df.to_csv(gtfs_out + r"calendar.txt", index=False)
    del calendar_df

    # remove all services from calendar_dates.txt that are not used by trips.txt
    calendar_dates_df = pd.read_csv(gtfs_in + r"calendar_dates.txt", header=0)
    calendar_dates_df = calendar_dates_df[calendar_dates_df["service_id"].isin(trips_df["service_id"])]
    calendar_dates_df.to_csv(gtfs_out + r"calendar_dates.txt", index=False)
    del calendar_dates_df

    # remove all stop_times rows that are not used by trips.txt
    stop_times_df = pd.read_csv(gtfs_in + r"stop_times.txt", header=0, low_memory=False)
    stop_times_df = stop_times_df[stop_times_df["trip_id"].isin(trips_df["trip_id"])]
    stop_times_df.to_csv(gtfs_out + r"stop_times.txt", index=False)
    del trips_df

    # remove all stop_times rows that are not used by trips.txt
    stops_df = pd.read_csv(gtfs_in + r"stops.txt", header=0)
    stops_df = stops_df[stops_df["stop_id"].isin(stop_times_df["stop_id"])]
    stops_df.to_csv(gtfs_out + r"stops.txt", index=False)
    del stops_df


if __name__ == '__main__':
    # shorten_GTFS_files(
    #     gtfs_in=r"../GTFS/Freiburg/VAG/gtfs-out/",
    #     gtfs_out=r"../GTFS/Freiburg/shortened_gtfs/gtfs-out/",
    #     agencies=None,
    #     route_types=[3]
    # )
    # Zurich
    # shorten_GTFS_files(
    #     gtfs_in=r"../GTFS/Schweiz/SBB/gtfs-out/",
    #     gtfs_out=r"../GTFS/Schweiz/Zurich/gtfs-out/",
    #     agencies=["849"],
    #     route_types=None
    # )
    # SWEG
    shorten_GTFS_files(
        gtfs_in=r"../GTFS/BW/bwspnv/gtfs-out/",
        gtfs_out=r"../GTFS/BW/SWEG/gtfs-out/",
        agencies=["S6"],
        route_types=None
    )
