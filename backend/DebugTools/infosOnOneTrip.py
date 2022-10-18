import pandas as pd


def getAllInfoOnOneTrip(trip_id: str, gtfs_path: str = r"../GTFS/Freiburg/VAG/gtfs-out/"):
    """
    Debug tool that lists all relevant information on the given trip
    """
    trips_df = pd.read_csv(gtfs_path + r"trips.txt", header=0)
    trips_row = trips_df[trips_df["trip_id"] == trip_id]

    route_id = trips_row["route_id"].iloc[0]
    service_id = trips_row["service_id"].iloc[0]
    shape_id = trips_row["shape_id"].iloc[0]

    del trips_df

    route_df = pd.read_csv(gtfs_path + r"routes.txt", header=0)
    route_row = route_df[route_df["route_id"] == route_id]

    route_short_name = route_row["route_short_name"].iloc[0]
    route_type = route_row["route_type"].iloc[0]

    del route_df

    calendar_df = pd.read_csv(gtfs_path + r"calendar.txt", header=0)
    calendar_row = calendar_df[calendar_df["service_id"] == service_id]

    active_weekdays = []
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        if calendar_row[day].iloc[0]:
            active_weekdays.append(day)

    del calendar_df

    calendar_dates_df = pd.read_csv(gtfs_path + r"calendar_dates.txt", header=0)
    calendar_dates_rows = calendar_dates_df[calendar_dates_df["service_id"] == service_id]

    extra_dates = []
    removed_dates = []
    for i, row in calendar_dates_rows.iterrows():
        if row["exception_type"] == 1:  # extra date
            extra_dates.append(row["date"])
        if row["exception_type"] == 2:  # removed date
            removed_dates.append(row["date"])

    del calendar_dates_df

    shape_df = pd.read_csv(gtfs_path + r"shapes.txt", header=0)
    shape_rows = shape_df[shape_df["shape_id"] == shape_id]

    polyline = []
    for i, row in shape_rows.iterrows():
        polyline.append((row["shape_pt_lat"], row["shape_pt_lon"]))

    del shape_df

    stop_times_df = pd.read_csv(gtfs_path + r"stop_times.txt", header=0)
    stop_times_rows = stop_times_df[stop_times_df["trip_id"] == trip_id]

    stops_df = pd.read_csv(gtfs_path + r"stops.txt", header=0)

    stops = []
    for i, row in stop_times_rows.iterrows():
        stop_row = stops_df[stops_df["stop_id"] == row["stop_id"]]
        stop_name = stop_row["stop_name"].iloc[0]
        stop_lat = stop_row["stop_lat"].iloc[0]
        stop_lon = stop_row["stop_lon"].iloc[0]

        stops.append((
            stop_name,
            row["arrival_time"],
            row["departure_time"],
            stop_lat,
            stop_lon
        ))

    del stops_df
    del stop_times_df

    print(f"================= INFORMATION ON TRIP {trip_id} ====================")
    print(f"route_id: {route_id}")
    print(f"Route name: {route_short_name}")
    print(f"Route type: {route_type}")
    print()
    print(f"service_id: {service_id}")
    print(f"Trip active on: {active_weekdays}")
    print()
    print(f"Extra trips:")
    for date in extra_dates:
        date = str(date)
        print(f"{date[6]}{date[7]}.{date[4]}{date[5]}.{date[0]}{date[1]}{date[2]}{date[3]}")
        # print(f"{date[6:]}.{date[4:6]}.{date[:4]}")
    print()
    print(f"Removed trips:")
    for date in removed_dates:
        date = str(date)
        print(f"{date[6]}{date[7]}.{date[4]}{date[5]}.{date[0]}{date[1]}{date[2]}{date[3]}")
        # print(f"{date[6:]}.{date[4:6]}.{date[:4]}")
    print()
    print(f"Stops:")
    for stop in stops:
        print(f"{stop[0]:<40}\t({stop[3]}, {stop[4]}):\tarrival time: {stop[1]}\tdeparture time: {stop[2]}")
    print()
    print(f"shape_id '{shape_id}' has {len(polyline)} points")
    print(polyline)


if __name__ == '__main__':
    while True:
        ipt = input("Enter trip_id: ")
        getAllInfoOnOneTrip(ipt)
