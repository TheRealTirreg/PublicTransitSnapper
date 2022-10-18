"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""

# so that doctest does not get stuck with API
if __name__ == "__main__":
    from datetime import datetime
    from threading import Thread
    from time import sleep, time
    from flask import Flask, request
    from flask_cors import CORS
    from MapMatcher import NetworkOfRoutes
    from ChatMessages import Chat, ChatMessage
    from GTFSContainer import GTFSContainer
    from ParseConfig import get_config, get_city_config, get_credentials
    from schedule import every, run_pending
    from ControlGTFSFiles import try_to_fetch_gtfs
    from FetchRealtimeUpdates import GTFSrtGetter
    from Utilities import convert_utc_to_local_time

    # get config info
    config = get_config()
    DEBUG = config["DEBUG"]
    CITY = config["CITY"]
    use_gtfs_rt = config["USE_GTFS_RT"]
    city_config = get_city_config(CITY, gtfs_rt=use_gtfs_rt)
    timezone = city_config["timezone"]

    # fetch gtfs rt updates
    updates = {}
    if use_gtfs_rt:
        if "RT-API-key" in city_config:
            api_key_name = city_config["RT-API-key"]
            creds = get_credentials([api_key_name])[api_key_name]
        else:
            creds = None
        gtfs_rt = GTFSrtGetter(CITY, city_config["GTFS-RT-feed"], creds, debug_print=DEBUG)
        # update the gtfs rt dictionary periodically
        gtfs_rt.fetch_trip_updates_every_n_minutes(city_config["RT-UPDATE-PERIOD"])(updates)

    # get GTFS path
    gtfs_path = "../" + city_config["path-to-GTFS"] + "/gtfs-out/"
    print(f"gtfs path: {gtfs_path}")

    # get saved_dictionaries path
    saved_dictionaries_path = r"../saved_dictionaries/" + CITY + "/"
    print(f"saved_dictionaries path: {saved_dictionaries_path}")

    # try to fetch new GTFS files
    if config["UPDATE_GTFS_ON_STARTUP"]:
        try_to_fetch_gtfs(CITY)

    # process GTFS files
    gtfs_container = GTFSContainer(
        path_gtfs=gtfs_path, path_saved_dictionaries=saved_dictionaries_path,
        update_dicts=config["UPDATE_DICTS"], rt_dict=updates, verbose=DEBUG)

    network = NetworkOfRoutes(
        gtfs_container, print_time=DEBUG,
        prefer_last_trip=config["PREFER_LAST_TRIP"],
        baseline=config["BASELINE"],
        baseline_hmm=config["BASELINE_HMM"],
        time_after=config["TIME_AFTER"], slack=config["SLACK"],
        earliness=config["EARLINESS"], delay=config["DELAY"],
        timezone=timezone)

    # start API
    app = Flask(__name__)
    CORS(app)

    # set flag whether the api is on or not
    IS_API_ON = True

    # get server start time after reset to distribute new user_ids
    server_start_timestamp = datetime.now().timestamp()
    last_user_id = 0

    # provide the chat
    chat = Chat(gtfs_container, debug=DEBUG)
    chat.remove_inactive_trips_every_hour()

    def shut_down_api_and_fetch_new_gtfs():
        """
        Shuts down the GTFS container, fetches GTFS data and afterwards turns on the GTFS container again
        """
        global IS_API_ON
        global gtfs_container

        t = time()
        print("shutting down GTFS container", flush=True)

        # shut down GTFS Container
        IS_API_ON = False
        gtfs_container = None

        # try to fetch new GTFS
        try_to_fetch_gtfs(CITY)

        # rebuild GTFS container
        gtfs_container = GTFSContainer(
            path_gtfs=gtfs_path,
            path_saved_dictionaries=saved_dictionaries_path,
            update_dicts=True, rt_dict=updates,
            verbose=DEBUG
        )
        IS_API_ON = True

        print(f"GTFS container is now online again.\n"
              f"Time needed: {round(time() - t, 2)}s", flush=True)

    def scheduler_thread():
        """
        This function can be run in a thread parallel to the API.
        It will run 'shut_down_api_and_fetch_new_GTFS' according to the time and the time interval
            given in config.yml.
        """
        # how many days until the next update
        update_frequency = config["UPDATE_FREQUENCY"]

        # the hour when to update
        update_time = config["UPDATE_TIME"]

        print(f"Will fetch new GTFS files every {update_frequency} days "
              f"at {update_time}. Time now: {datetime.now()}", flush=True)

        every(update_frequency).days.at(update_time).do(shut_down_api_and_fetch_new_gtfs)

        while True:
            run_pending()
            sleep(1 * 60)  # check schedule every minute

    def run_app():
        """
        Runs the API.

        If config["UPDATE_GTFS"], run a thread next to the API that repeatedly checks if it is time
            to fetch new GTFS files and rebuild them.
            During that time, the API will not be able to return anything, as the GTFS container is down.
        """
        global IS_API_ON

        print(f"config['UPDATE_GTFS]: {config['UPDATE_GTFS']}", flush=True)

        print("Server is now online. You can now connect with the frontend.", flush=True)

        if config["UPDATE_GTFS"]:
            # start API in a thread in order to be able to check if it is GTFS fetching time
            IS_API_ON = True

            Thread(target=scheduler_thread).start()
            app.run(host='0.0.0.0', port=config["SERVER_PORT"])
        else:
            IS_API_ON = True
            app.run(host='0.0.0.0', port=config["SERVER_PORT"])

    def manage_user_ids(user_id: int, saved_start_server_timestamp: float) -> int:
        """
        Makes sure that each user has a unique user_id.
        If user_id == 0 or if the server has restarted: Generate a new id.
        Else: just return the given user_id.
        """
        # if the frontend application still has an old user_id stored before a server restart, get a new id
        if user_id == 0 or saved_start_server_timestamp < server_start_timestamp:
            global last_user_id
            last_user_id += 1
            return last_user_id

        # return old user_id if nothing has changed
        return user_id

    @app.route('/map-match', methods=['GET', 'POST'])
    def map_match():
        """
        This function takes a sequence of GPS locations with timestamps.
        It performs a dynamic map-matching und returns the matched trip with
        further information.
        """
        print("Polyline Request start", flush=True)
        if not IS_API_ON:
            print("API is offline", flush=True)
            return {}, 503

        req = request.json
        if DEBUG:
            print("", flush=True)
            print("incoming ", flush=True)
            print(req, flush=True)
            print("", flush=True)

        trip_id = req["trip_id"]
        coordinates = req["coordinates"]

        if not coordinates:
            return {}, 400

        route = []
        for coord in coordinates:
            coord = coord.split(',')
            # lat, lon, time, convert from milliseconds to seconds unix time
            route.append([float(coord[0]), float(coord[1]), int(coord[2]) // 1000])

        most_likely_dict = network.find_route_name(route, dist=0.1, trip_id=trip_id)

        if DEBUG:
            print("", flush=True)
            print("answer ", flush=True)
            print(most_likely_dict, flush=True)
            print("", flush=True)
        print("Polyline Request end", flush=True)
        return most_likely_dict, 200

    @app.route('/connections', methods=['GET', 'POST'])
    def get_connections():
        """
        Sends information to the frontend in order to display the connections at the next stop.
        connections: public transit vehicles that pass by the next stop in the next time period.
        """
        print("Connections Request start", flush=True)
        if not IS_API_ON:
            print("API is offline", flush=True)
            return {}, 503

        req = request.json
        if not req or req['next_stop_name'] == 'next stop':
            return {}, 400

        if req['next_stop_name'] == "" or req['user_time'] == "":
            return {"length": 0}, 200

        if DEBUG:
            print("", flush=True)
            print("incoming ", flush=True)
            print(req, flush=True)
            print("", flush=True)

        trip_id = req['trip_id']

        next_stop_name = req['next_stop_name']
        user_time = int(req['user_time']) // 1000
        user_time_datetime = convert_utc_to_local_time(user_time, timezone_name=timezone)

        print("fetching transfer possibilities...", flush=True)
        possibilities = network.tt.find_transfer_possibilities(next_stop_name, user_time_datetime, trip_id)
        print(f"transfer possibilities for {next_stop_name} at "
              f"{user_time_datetime.strftime('%Y/%m/%d - %H:%M')}:")
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

    @app.route('/shapes', methods=['GET', 'POST'])
    def get_shape():
        """
        As the actual shape from the GTFS data is not loaded in memory (too large),
        calculate the shape based on the GTFS graph in the GTFS-Container.
        """
        print("\nShape Request start", flush=True)
        if not IS_API_ON:
            print("API is offline", flush=True)
            return {}, 503

        req = request.json
        if not req:
            return {}, 400

        if DEBUG:
            print("", flush=True)
            print("incoming ", flush=True)
            print(req, flush=True)
            print("", flush=True)

        polyline, stops = gtfs_container.get_shape_polyline_and_stops(req["shape_id"], req["trip_id"])

        print("Shapes Request end\n", flush=True)
        return {"polyline": polyline, "stops": stops}, 200

    @app.route('/chat', methods=['GET', 'POST'])
    def get_chat():
        """
        Handles the chat messages.
        If a new message has been sent, save it.
        Always send back the current chat messages of the current trip.
        """
        print("Chat Request start", flush=True)
        if not IS_API_ON:
            print("API is offline", flush=True)
            return {}, 503

        print(f"server start stamp: {server_start_timestamp}", flush=True)

        req = request.json
        if DEBUG:
            print(f"req: {req}", flush=True)

        # manage user_id
        user_id = manage_user_ids(int(req["user_id"]), float(req["server_start_timestamp"]))
        trip_id = req['trip_id']

        # save new message if a message has been sent
        if not req['just_fetch'] and not user_id == 0:
            chat.add_message(trip_id, ChatMessage(
                user_id, req['user_name'], req['message'], req['user_time']
            ))

        if DEBUG:
            print(f"get message: {chat.get_messages(trip_id)}")

        ret_dct = {
            'user_id': user_id,
            'server_start_timestamp': server_start_timestamp,
            'messages': chat.get_messages(trip_id)
        }

        print("Chat Request end", flush=True)
        return ret_dct, 200

    run_app()
