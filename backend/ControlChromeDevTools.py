import pandas as pd
import numpy as np
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from GPSTestdata import generate_noisified_gps_data
from flask import Flask, request
from flask_cors import CORS
from requests import post
from datetime import datetime
from os.path import isfile
import threading
import pickle
import yaml

SERVER = 'http://localhost:5000'
DEBUG_PORT = 'http://localhost:5000'
CHROME = '21698'

def generateTripIdActiveDayInformation(
        trips_file="GTFS/trips.txt",
        calendar_file="GTFS/calendar.txt",
        calendar_dates_file="GTFS/calendar_dates.txt"):
    """
    Returns a dict {"trip_id": ([active weekdays from 0 (monday) to 6 (sunday)],
                                (start_date, end_date),
                                [extra_dates],
                                [removed_dates])}
    >>> # a = generateTripIdActiveDayInformation()
    >>> # a["1.T0.10-46-I-j22-1.2.H"]
    True
    """
    weekdays_dict = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}

    trips_df = pd.read_csv(trips_file, usecols=[1, 2])
    calendar_df = pd.read_csv(calendar_file)
    calendar_dates_df = pd.read_csv(calendar_dates_file)
    dct = {}

    # rows contain service_id and trip_id
    for i, row in trips_df.iterrows():
        # get all the weekdays on which the service_id is active
        calendar_row = calendar_df[calendar_df["service_id"] == row["service_id"]]
        weekdays = []
        for weekday, weekday_num in weekdays_dict.items():
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

    return dct


def geoLocationTest(polyline):
    """
    This function takes in a polyline, alters the points from it by a few meters and then simulates
    a device going along the polyline.

    User manual:
        Start the frontend-app with chrome.
        From the browser search bar, copy the localhost and paste it to the TODO.
    """
    # r"C:\Users\gerri\Desktop\chromedriver.exe"

    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s)

    localhost = "http://localhost:%s/#/" % CHROME  # TODO insert current localhost here!
    driver.get(localhost)

    polyline_dicts = [{"latitude": y, "longitude": x, "accuracy": 100} for y, x in polyline]
    print("UI:", polyline_dicts)

    for coordinate in polyline_dicts:
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", coordinate)
        sleep_for = np.random.randint(4, 6)
        sleep(sleep_for)
        print(coordinate)

    print("wait")
    sleep(100000)  # keep window open


def get_random_trip_from_gtfs(trips_file="GTFS/trips.txt", trips_file_hamburg=""):
    """
    take a random trip from gtfs
    """
    if trips_file_hamburg:
        trips_file = trips_file_hamburg

    # get pandas dataframe of input file
    df = pd.read_csv(trips_file, header=0, usecols=[2, 7])

    shape_name = None
    trip_name = None

    while True:
        # get a random shape from the file
        row = np.random.randint(len(df) - 1)
        trip_name = df.loc[row].trip_id
        shape_name = df.loc[row].shape_id
        trip_date_info = datesDict[trip_name]

        if datetime.now().weekday() in trip_date_info[0] and not any(map(lambda x: x.date() == datetime.today().date(),
                                                                         trip_date_info[3])):
            # found fitting candidate, so just use this
            break

    return trip_name, shape_name


map_points_to_time = {}
# Create a simple Api, that will just forward all traffic added with own time
app = Flask(__name__)
CORS(app)

datesDict = {}

IS_HAMBURG = False  # true if gtfs data from hamburg is used
if IS_HAMBURG:
    path = r"saved_dictionaries_hamburg"
    trips_file_name = r"GTFS/Hamburg/hvv/gtfs-with-shapes/trips.txt"
    calendar_file_name = r"GTFS/Hamburg/hvv/gtfs-with-shapes/calendar.txt"
    calendar_dates_file_name = r"GTFS/Hamburg/hvv/gtfs-with-shapes/calendar_dates.txt"
else:
    path = r"saved_dictionaries_freiburg"
    trips_file_name = r"GTFS/trips.txt"
    calendar_file_name = r"GTFS/calendar.txt"
    calendar_dates_file_name = r"GTFS/calendar_dates.txt"

if isfile(path + r"/trip_id_to_active_weekdays.pkl"):
    print("Loading dates dict...")
    with open(path + r"/trip_id_to_active_weekdays.pkl", "rb") as f:
        datesDict = pickle.load(f)
    print("Finished loading dates dict!")
else:
    print("Writing dates dict...")
    datesDict = generateTripIdActiveDayInformation(
        trips_file=trips_file_name, calendar_file=calendar_file_name, calendar_dates_file=calendar_dates_file_name)
    print("Saving dates dict...")
    with open(path + r"/trip_id_to_active_weekdays.pkl", "wb") as f:
        pickle.dump(datesDict, f)
    print("Finished saving dates dict!")


@app.route('/json', methods=['GET', 'POST'])
def json_forward():
    req = request.json
    coordinates = req["coordinates"]
    coord_updated_time = []
    for coord in coordinates:
        lat, lon, tim = coord.split(',')
        coord_updated_time.append(f"{lat},{lon},{int(map_points_to_time[(float(lat), float(lon))])}")
    req["coordinates"] = coord_updated_time
    answer = post(SERVER + '/json', json=req).json()
    return answer


@app.route('/connections', methods=['GET', 'POST'])
def connections_forward():
    req = request.json
    answer = post(SERVER + '/connections', json=req).json()
    return answer


def get_config(file="config.yml"):
    config = {}
    with open(file, "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e)

    if 'SERVER-ADDRESS' in config and 'SERVER-PORT' in config:
        global SERVER
        SERVER = ('http://%s:%s' % (config['SERVER-ADDRESS'], config['SERVER-PORT']))
        print("loaded server address %s" % SERVER)
    else:
        print("Server config incomplete, using default value %s" % SERVER)
    if 'DEBUG-PORT' in config:
        global DEBUG_PORT
        DEBUG_PORT = config['DEBUG-PORT']
        print("loaded debug port %s" % DEBUG_PORT)
    else:
        print("Debug port missing, using default value %s" % DEBUG_PORT)
    if 'DEVTOOL-PORT' in config:
        global CHROME
        CHROME = config['DEVTOOL-PORT']
        print("loaded chrome port %s" % CHROME)
    else:
        print("Chrome port missing, using default value %s" % CHROME)


if __name__ == '__main__':
    get_config()
    # run on http://localhost:5000/json in the app (connect_to_internet.dart)
    # also make sure that --web-port=21698 is set in "Run -> Edit configurations" in Android Studio
    # random_trip = get_random_trip_from_gtfs(trips_file_hamburg=r"../GTFS/Hamburg/hvv/gtfs-with-shapes/trips.txt")
    random_trip = get_random_trip_from_gtfs()
    points, map_points_to_time = generate_noisified_gps_data(*random_trip)
    print("Selected Trip: ", random_trip)
    print(map_points_to_time)
    for idx, point in enumerate(map_points_to_time.keys()):
        lat, lon = point
        print('"%s,%s,%s",' % (lat, lon, idx))
    for idx, time in enumerate(map_points_to_time.values()):
        print(str(idx) + " " + str(datetime.fromtimestamp(time / 1000)))
    threading.Thread(target=lambda: app.run(port=int(DEBUG_PORT))).start()
    geoLocationTest(points)
