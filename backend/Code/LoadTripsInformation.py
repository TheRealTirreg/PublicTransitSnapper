"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
import pandas as pd
from datetime import datetime
from os.path import isfile
from pickle import load as pickle_load, dump as pickle_dump
from random import choice

"""
These functions are only needed for generating test data for
ChromeDevTools or evaluation.
"""


def get_trip_info_dict(city: str, path_to_gtfs: str, new_gtfs: bool = False, path_to_saved=None):
    """
    loads trip_id_to_shape_active_weekdays dict if already saved
    generates and saves dictionary, if none exists yet
    """
    if path_to_saved is None:
        path_to_saved_dictionaries = r"../saved_dictionaries/" + city
    else:
        path_to_saved_dictionaries = path_to_saved

    if isfile(path_to_saved_dictionaries + r"/trip_id_to_shape_active_weekdays.pkl") and not new_gtfs:
        print("Loading dates dict...")
        with open(path_to_saved_dictionaries + r"/trip_id_to_shape_active_weekdays.pkl", "rb") as f:
            dates_dict = pickle_load(f)
        print("Finished loading dates dict!")
    else:
        print("Writing dates dict...")

        dates_dict = generate_trip_id_to_shape_service_information_dict(path_to_gtfs)

        print("Saving dates dict...")
        with open(path_to_saved_dictionaries + r"/trip_id_to_shape_active_weekdays.pkl", "wb") as f:
            pickle_dump(dates_dict, f)
        print("Finished saving dates dict!")

    return dates_dict


def generate_trip_id_to_shape_service_information_dict(path_to_gtfs, mod=2000):
    """
    Returns a dict {"trip_id": ("shape_id",
                                [active weekdays from 0 (monday) to 6 (sunday)],
                                (start_date, end_date),
                                [extra_dates],
                                [removed_dates])}
    """
    trips_file = path_to_gtfs + r"trips.txt"
    calendar_file = path_to_gtfs + r"calendar.txt"
    calendar_dates_file = path_to_gtfs + r"calendar_dates.txt"
    # iterate over calendar.txt go get active_weekdays and (start_date, end_date)
    weekdays_dict = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    calendar_dct = {}  # {"service_id": ([int weekdays], (datetime(start_date), datetime(end_date)))}
    calendar_df = pd.read_csv(calendar_file, header=0)
    num_services = len(calendar_df)
    for i, row in calendar_df.iterrows():
        weekdays = []
        for weekday, weekday_num in weekdays_dict.items():
            if int(row[weekday]):
                weekdays.append(weekday_num)
        weekdays.sort()

        start_end_dates = (
            datetime.strptime(str(row["start_date"]), "%Y%m%d"),
            datetime.strptime(str(row["end_date"]), "%Y%m%d")
        )

        calendar_dct[str(row["service_id"])] = (weekdays, start_end_dates)

        # debug:
        if not i % mod:
            print(f"{round(i / num_services * 100, 2)}%\t"
                  f"of writing service_id => active_weekdays and start_end_dates - dict...")

    del calendar_df

    # iterate over calendar_dates.txt to get extra_dates and removed_dates
    calendar_dates_dct = {}  # {"service_id": ([extra_dates], [removed_dates])} with datetime objects
    calendar_dates_df = pd.read_csv(calendar_dates_file, header=0)
    exceptions = len(calendar_dates_df)
    for i, row in calendar_dates_df.iterrows():
        service_id = str(row["service_id"])
        if service_id not in calendar_dates_dct:
            # initialize dct entry (extra_dates, removed_dates)
            calendar_dates_dct[service_id] = ([], [])

        if int(row["exception_type"]) == 1:  # add to extra_dates
            calendar_dates_dct[service_id][0].append(datetime.strptime(str(row["date"]), "%Y%m%d").date())
        elif int(row["exception_type"]) == 2:  # add to removed_dates
            calendar_dates_dct[service_id][1].append(datetime.strptime(str(row["date"]), "%Y%m%d").date())

        # debug:
        if not i % mod:
            print(f"{round(i / exceptions * 100, 2)}%\t"
                  f"of writing service_id => exceptions - dict...")

    del calendar_dates_df

    # iterate over trips
    dct = {}
    trips_df = pd.read_csv(trips_file, usecols=["service_id", "trip_id", "shape_id"], header=0)
    num_trips = len(trips_df)

    # rows contain service_id and trip_id
    for i, row in trips_df.iterrows():
        service_id = str(row["service_id"])
        if service_id not in calendar_dct:
            print(f"{service_id} not in calendar dict")
            continue
        if service_id not in calendar_dates_dct:
            continue

        shape_id = str(row["shape_id"])
        dct[row["trip_id"]] = (
            shape_id,
            calendar_dct[service_id][0],
            calendar_dct[service_id][1],
            calendar_dates_dct[service_id][0],
            calendar_dates_dct[service_id][1],
        )

        # debug:
        if not i % mod:
            print(f"{round(i / num_trips * 100, 2)}%\t"
                  f"of writing trip_id => service information - dict...")

    return dct


def get_random_trip_from_gtfs(trip_info: dict):
    """
    take a random trip from gtfs
    """
    trips_list = list(trip_info.items())

    counter = 0
    while counter < 100000:
        trip_name, trip_info = choice(trips_list)
        shape_name = trip_info[0]

        if datetime.now().weekday() in trip_info[1] and \
                not any(map(lambda x: x == datetime.today().date(), trip_info[4])):
            # found fitting candidate, so just use this
            break
        counter += 1
    else:  # counter == 100000
        raise Exception("no random trip found")

    return trip_name, shape_name
