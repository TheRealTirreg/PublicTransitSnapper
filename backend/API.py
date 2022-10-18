# write a simple API that get two points and returns the middle
import datetime

from flask import Flask, request
from flask_cors import CORS
import MapMatcher

DEBUG = True

app = Flask(__name__)
CORS(app)
file = "GTFS/shapes.txt"
network = MapMatcher.NetworkOfRoutes(file)


@app.route('/json', methods=['GET', 'POST'])
def map_match():
    print("Polyline Request start", flush=True)
    req = request.json
    if DEBUG:
        print("", flush=True)
        print("incoming ", flush=True)
        print(req, flush=True)
        print("", flush=True)
    coordinates = req["coordinates"]
    if not coordinates:
        return {}, 400
    route = []
    for coord in coordinates:
        coord = coord.split(',')
        # lat, lon, tim
        route.append([float(coord[0]), float(coord[1]), int(coord[2]) // 1000])

    most_likely_dict = MapMatcher.find_route_name(network, route, 0.1)
    if DEBUG:
        print("", flush=True)
        print("answer ", flush=True)
        print(most_likely_dict, flush=True)
        print("", flush=True)
    print("Polyline Request end", flush=True)
    return most_likely_dict, 200


@app.route('/connections', methods=['GET', 'POST'])
def get_connections():
    print("Connections Request start", flush=True)
    req = request.json
    if not req or req['nextStopName'] == 'next stop':
        return {}, 400
    if req['nextStopName'] == "" or req['userTime'] == "":
        return {"length": 0}, 200
    if DEBUG:
        print("", flush=True)
        print("incoming ", flush=True)
        print(req, flush=True)
        print("", flush=True)
    next_stop_name = req['nextStopName']
    user_time = int(req['userTime']) // 1000
    print("fetching transfer possibilities...", flush=True)
    possibilities = network.tt.findTransferPossibilities(next_stop_name, user_time)
    print(f"transfer possibilities for {next_stop_name} at "
          f"{datetime.datetime.fromtimestamp(user_time).strftime('%Y/%m/%d - %H:%M')}:")
    for possibility in possibilities:
        print(possibility)
    idx, connections = 0, {}
    for possibility in possibilities:
        # Linename: Linedirection: next Times
        # skip if the destination is the same as next stop (terminal station)
        if possibility[1] == next_stop_name:
            continue
        connections[str(idx)] = possibility
        idx += 1
    connections['length'] = len(connections)
    print("Connections Request end", flush=True)
    return connections, 200


if __name__ == '__main__':
    app.run(port=5000)
