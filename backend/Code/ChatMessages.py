"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
from datetime import datetime
from GTFSContainer import GTFSContainer
from TripsWithStops import TripWithStopsAndTimes
import Utilities as Utils


class ChatMessage:

    __slots__ = [
        "user_id",
        "user_name",
        "message",
        "user_time",
    ]

    def __init__(
            self, user_id: int, user_name: str, message: str, user_time: str):
        """
        Properties:
            user_id: Int from the device that sent the message
            user_name: String of the name the user has given himself
            user_time: String of the user_time the message has been sent
            message: String of the message
        """
        self.user_id = user_id
        self.user_name = user_name
        self.user_time = user_time
        self.message = message

    def __repr__(self):
        return "user_id: {self.user_id}, user_name: {self.user_name}," +\
               "user_time: {self.user_time}, message: {self.message}"

    def to_list(self):
        return [self.user_id, self.user_name, self.message, self.user_time]


class Chat:
    """
    Controls a dict {"trip_id": [ChatMessage]}
    Deletes the messages if the trip is not active anymore.
    """

    __slots__ = ["trip_id_to_chat_messages", "gtfs_container", "debug"]

    def __init__(self, container: GTFSContainer, debug: bool = False):
        """
        Input:
            path_to_gtfs_trips_file:
            for example r"../GTFS/Schweiz/SBB/gtfs-out/trips.txt"
        """
        self.trip_id_to_chat_messages = {}
        self.gtfs_container = container
        self.debug = debug

    def add_message(self, trip_id: str, message: ChatMessage):
        """
        Adds a newly sent message from the backend to
        its corresponding dict entry,
        creates a new entry if there is none yet
        """
        if self.debug:
            print(f"trip_id in chat-dict?: \
            {trip_id in self.trip_id_to_chat_messages}")
        if trip_id not in self.trip_id_to_chat_messages:
            self.trip_id_to_chat_messages[trip_id] = [message]
        else:
            self.trip_id_to_chat_messages[trip_id].append(message)

    def get_messages(self, trip_id: str):
        """
        Returns a dict that is ready to be sent to the frontend:
        [[user_id, 'user_name', 'message', 'time_sent'], ...]
        """
        if self.debug:
            print("getting messages from dict:", self.trip_id_to_chat_messages)
            print(f"{trip_id} in dict? -> \
                {trip_id in self.trip_id_to_chat_messages}")
        if trip_id not in self.trip_id_to_chat_messages:
            return []
        return [chat_message.to_list()
                for chat_message in self.trip_id_to_chat_messages[trip_id]]

    @Utils.repeat_every_n_minutes(60)
    def remove_inactive_trips_every_hour(self):
        """
        Removes trips from self.trip_id_to_chat_messages if they are inactive.
        """
        if self.debug:
            print("removing inactive chats")

        current_datetime = datetime.now()
        trips = list(self.trip_id_to_chat_messages.keys())
        for trip_id in trips:
            if trip_id not in \
                    self.gtfs_container.trip_id_to_trip_with_stops_dict:
                self.trip_id_to_chat_messages.pop(trip_id)
                continue

            trip_with_stops_and_times: TripWithStopsAndTimes =\
                self.gtfs_container.trip_id_to_trip_with_stops_dict[trip_id]

            # remove trip_id if the trip is not active.
            if not Utils.is_within_active_hours(
                    trip_with_stops_and_times.active_hours, current_datetime):
                self.trip_id_to_chat_messages.pop(trip_id)
