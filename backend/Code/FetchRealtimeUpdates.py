"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
from google.transit import gtfs_realtime_pb2
from requests import get
from protobuf_to_dict import protobuf_to_dict
from Utilities import repeat_every_n_minutes

# from https://github.com/MobilityData/gtfs-realtime-bindings

# more info for the entities:
# https://github.com/google/transit/blob/master/gtfs-realtime/proto/gtfs-realtime.proto

# some available gtfs-realtime feeds:
# https://openmobilitydata.org/search?q=gtfsrt

# guide to protocol buffers:
# https://developers.google.com/protocol-buffers/docs/proto


def get_feed_no_auth(url: str) -> bytes:
    return get(url).content


def get_feed_switzerland(url: str, api_key: str) -> bytes:
    headers = {"Authorization": api_key, "Content-Type": "text/XML", "Accept": "application/octet-stream"}
    return get(url, headers=headers).content


map_city_to_getter_function = {
    "Freiburg": get_feed_no_auth,  # only used for testing, there is no official/real feed for Freiburg
    "Schweiz": get_feed_switzerland
}


class GTFSrtGetter:
    """
    Class that can read a gtfs-realtime feed from an url and return a dict with the information

    In order to use this class, you need to specify in map_city_to_getter_function the function that can read the feed.

    Note that depending on the city, the feed might need authentication. In this case, you need to implement
    the function yourself (Authentication method might differ).
    The function should take either url or, url and api_key as parameters.
    The function should return the bytes of the response with the content of the feed.
    """
    def __init__(self, city: str, url: str, api_key: str = None, debug_print: bool = False):
        if city not in map_city_to_getter_function:
            raise ValueError(f"{city} not found, please add to map_city_to_getter_function")
        self._url = url
        self._api_key = api_key
        self._func_get_feed = map_city_to_getter_function[city]
        self._debug_print = debug_print

    @property
    def _feed_dict(self) -> dict:
        feed = gtfs_realtime_pb2.FeedMessage()
        # if there is an api key, pass url and api key to the function
        args = (self._url, self._api_key) if self._api_key else (self._url, )
        feed.ParseFromString(self._func_get_feed(*args))
        return protobuf_to_dict(feed)

    def fetch_trip_updates_every_n_minutes(self, n: float):
        @repeat_every_n_minutes(n)
        def fetch_trip_updates(trip_updates: dict):
            """
            Fetch latest realtime stream and generate dict with new information
            """
            feed_dict = self._feed_dict
            if self._debug_print:
                print(f"GTFS RT feed:\n{feed_dict}")

            # currently only the full dataset update is implemented
            # feed header can be differential or full dataset
            if "incrementality" in feed_dict["header"]:
                inc_mode = feed_dict["header"]["incrementality"]
                if inc_mode != gtfs_realtime_pb2.FeedHeader.FULL_DATASET:
                    raise Exception(f'GTFS-Realtime {inc_mode} incrementality not supported')

            if "entity" not in feed_dict:
                print("no entities in feed")
                return

            new_dict = {}
            for entity in feed_dict["entity"]:
                if "trip_update" in entity and "stop_time_update" in entity["trip_update"]:
                    trip_update = entity["trip_update"]
                    start_date = trip_update["trip"]["start_date"]

                    for stop_time_update in trip_update["stop_time_update"]:
                        arrival_time, departure_time, stop_sequence = None, None, None

                        # since all information is optional in the standard,
                        # we need to check if it is present
                        # note: if both time and delay are specified, according to the standard
                        #   time should take precedence, ideally they should be the same
                        if "arrival" in stop_time_update:
                            if "time" in stop_time_update["arrival"]:
                                arrival_time = stop_time_update["arrival"]["time"], True
                            elif "delay" in stop_time_update["arrival"]:
                                arrival_time = stop_time_update["arrival"]["delay"], False

                        if "departure" in stop_time_update:
                            if "time" in stop_time_update["departure"]:
                                departure_time = stop_time_update["departure"]["time"], True
                            elif "delay" in stop_time_update["departure"]:
                                departure_time = stop_time_update["departure"]["delay"], False

                        if "stop_sequence" in stop_time_update:
                            # stop_sequence is 1 based, trip_segment_id is 0 based
                            stop_sequence = stop_time_update["stop_sequence"] - 1

                        # only works if stop_sequence and one of the times is present
                        if (arrival_time or departure_time) and stop_sequence:
                            trip_id = trip_update["trip"]["trip_id"]
                            if trip_id not in new_dict:
                                new_dict[trip_id] = []
                            new_dict[trip_id].append((stop_sequence, arrival_time, departure_time, start_date))

            # update the global dict with the new data
            trip_updates.clear()
            trip_updates.update(new_dict)

            if self._debug_print:
                print(f"Trip Updates Dict:\n{trip_updates}")

        return fetch_trip_updates


if __name__ == '__main__':
    DEBUG = True
    updates = {}
    gtfs_rt = GTFSrtGetter("Freiburg", "http://localhost:9090/tripupdates", debug_print=DEBUG)

    gtfs_rt.fetch_trip_updates_every_n_minutes(1)(updates)
