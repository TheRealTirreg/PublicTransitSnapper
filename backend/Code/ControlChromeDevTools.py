"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
from numpy import random
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from GPSTestdata import generate_noisified_gps_data_return_dicts
from flask import Flask, request
from flask_cors import CORS
from requests import post
from datetime import datetime
from threading import Thread
from ParseConfig import get_config, get_city_config_attribute
from LoadTripsInformation import get_trip_info_dict, get_random_trip_from_gtfs

"""
Create a simple Api, that will just forward all traffic added with simulated time
The proxy changes teh content of the json request only for the map match api call
"""
app = Flask(__name__)
CORS(app)


@app.route('/map-match', methods=['GET', 'POST'])
def map_match_forward():
    req = request.json
    print(req, flush=True)
    coordinates = req["coordinates"]
    coord_updated_time = []
    for coord in coordinates:
        lat_c, lon_c, _ = coord.split(',')
        coord_updated_time.append(
            f"{lat_c},{lon_c},{int(map_points_to_time[(float(lat_c), float(lon_c))])}")
    req["coordinates"] = coord_updated_time
    answer = post(SERVER + '/map-match', json=req).json()
    return answer


@app.route('/connections', methods=['GET', 'POST'])
def connections_forward():
    req = request.json
    answer = post(SERVER + '/connections', json=req).json()
    return answer


@app.route('/shapes', methods=['GET', 'POST'])
def shapes_forward():
    req = request.json
    answer = post(SERVER + '/shapes', json=req).json()
    return answer


@app.route('/chat', methods=['GET', 'POST'])
def chat_forward():
    req = request.json
    answer = post(SERVER + '/chat', json=req).json()
    return answer


def geo_location_test(polyline):
    """
    This function takes in a polyline,
    and then simulates a device going along the polyline.
    It sets the location in ChromeDevTool every 4-6 seconds.
    """
    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s)

    localhost = "http://localhost:%s/#/" % DEVTOOL_PORT
    driver.get(localhost)

    polyline_dicts = [{"latitude": y, "longitude": x, "accuracy": 100} for y, x in polyline]
    print("UI:", polyline_dicts)

    for coordinate in polyline_dicts:
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", coordinate)
        sleep_for = random.randint(4, 6)
        sleep(sleep_for)
        print(coordinate)

    print("trip simulation over")
    sleep(100000)  # keep window open


if __name__ == '__main__':
    # get all necessary config parameters
    config = get_config(dev_tools=True)
    server_address, port = config["SERVER_ADDRESS"], str(config["SERVER_PORT"])
    if server_address == "https://ad-research.informatik.uni-freiburg.de/transitmm":
        SERVER = server_address
    else:
        SERVER = "http://" + config["SERVER_ADDRESS"] + ":" + str(config["SERVER_PORT"])
    PROXY_PORT = config["PROXY_PORT"]
    DEVTOOL_PORT = config["DEVTOOL_PORT"]
    CITY = config["CITY"]
    NEW_GTFS = config["NEW_GTFS"]
    path_to_gtfs = r"../" + get_city_config_attribute(CITY, "path-to-GTFS") + "/gtfs-out/"

    # get info about all trips
    trip_info = get_trip_info_dict(CITY, path_to_gtfs, NEW_GTFS)
    # get a random trip for testing, that is active today
    trip_id, shape_id = get_random_trip_from_gtfs(trip_info)

    print("Selected Trip: ", trip_id, shape_id)
    points, map_points_to_time = generate_noisified_gps_data_return_dicts(path_to_gtfs, trip_id, shape_id)
    print(map_points_to_time)
    for idx, (lat, lon) in enumerate(map_points_to_time.keys()):
        print('"%s,%s,%s",' % (lat, lon, idx))
    for idx, time in enumerate(map_points_to_time.values()):
        print(str(idx) + " " + str(datetime.fromtimestamp(time / 1000)))

    # start the proxy in a separate thread
    Thread(target=lambda: app.run(port=PROXY_PORT)).start()
    geo_location_test(points)
