"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
from typing import List, Tuple
from datetime import datetime, timedelta, date
import Utilities as Utils


class TripWithStopsAndTimes:
    """
    Stores information for one trip.
    Given a time and a date, it is able to say whether there is currently traffic on the given shape
    """

    __slots__ = [
        "trip_id",
        "hash_to_edge_id_to_trip_segments_dict",
        "service_id",
        "time_interval",
        "active_hours"
    ]

    def __init__(
            self,
            trip_id: str,
            hash_to_edge_id_to_trip_segments_dict: int,
            service_id: str,
            active_weekdays: List[int],
            start_time: datetime,
            start_overtime: bool,
            end_time: datetime,
            end_overtime: bool
    ):
        """
        Input:
            trip_id: GTFS trip_id
            hash_to_edge_id_to_trip_segments_dict: Hash value to access the edge_id_to_trip_segments_dict
            service_id: GTFS service_id
            active_weekdays: List of ints (Monday = 0, ..., Sunday = 6) where the trip is active / has service
            start_time: start time of the trip in "%H%M%S" format
            start_overtime: if the start_time in the GTFS file was something like "25:00:00", then start_time will be
                "01:00:00" and start_overtime will be true.
            end_time and end_overtime analog.
            end_overtime: the same case as start_overtime

        Properties:
            trip_id: GTFS trip_id
            hash_to_edge_id_to_trip_segments_dict: Hash value to access the edge_id_to_trip_segments_dict
            service_id: service_id of the trip, needed to access date-borders, removed_dates and extra_dates.
            active_hours: Set the hours of the week when this trip is active: set((weekday: int, hour: int))
            time_interval: (start_time, end_time, start_overtime, end_overtime) as datetime objects
        """
        self.trip_id = trip_id
        self.hash_to_edge_id_to_trip_segments_dict = hash_to_edge_id_to_trip_segments_dict
        self.service_id = service_id
        self.active_hours = self._generate_active_hours(
            set(active_weekdays), start_time, start_overtime, end_time, end_overtime)
        self.time_interval = start_time, end_time, start_overtime, end_overtime

    def __repr__(self):
        s = f"Trip_id: {self.trip_id}, time interval: {self.time_interval[0], self.time_interval[1]}"
        return s

    @staticmethod
    def _generate_active_hours(weekdays, start_time, start_overtime, end_time, end_overtime):
        """
        from the active days and the stops generate a set,
        which contains the hours of the week when this trip is active.

        the time tuple is generated as follows (weekday, hour).
        eg. if a trip is active on Monday at 1:5 o'clock then (0, 1) is in the set.
        thus the hours includes everything up to the next hour. This ensures that it is much faster to check if a
        trip is actually active.

        >>> from GTFSContainer import GTFSContainer
        >>> test_tt = GTFSContainer("../GTFS/doctest_files", "../saved_dictionaries/Doctests", verbose=False)
        >>> test_trip = test_tt.trip_id_to_trip_with_stops_dict["1.TA.91-10-A-j22-1.1.H"]
        >>> weekdays = [0]  # active on monday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 10, 0, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 11, 0, 0), False
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(0, 10, False)}
        True
        >>> weekdays = [0]  # active on monday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 10, 30, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 11, 30, 0), False
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(0, 10, False), (0, 11, False)}
        True
        >>> weekdays = [0, 1]  # active on monday and tuesday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 10, 0, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 11, 0, 0), False
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(0, 10, False), (1, 10, False)}
        True
        >>> weekdays = [6]  # active on sunday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 10, 0, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 11, 0, 0), False
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(6, 10, False)}
        True
        >>> weekdays = [6]  # active on sunday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 22, 0, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 0, 0, 0), True
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(6, 23, False), (6, 22, False)}
        True
        >>> weekdays = [6]  # active on sunday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 22, 0, 0), False
        >>> end_time, end_overtime = datetime(1990, 1, 1, 0, 15, 0), True
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {
        ...     (6, 23, False), (6, 22, False), (0, 0, True)}
        True
        >>> weekdays = [5]  # active on saturday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 1, 0, 0), True
        >>> end_time, end_overtime = datetime(1990, 1, 1, 1, 15, 0), True
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(6, 1, True)}
        True
        >>> weekdays = [6]  # active on sunday
        >>> start_time, start_overtime = datetime(1990, 1, 1, 1, 0, 0), True
        >>> end_time, end_overtime = datetime(1990, 1, 1, 1, 15, 0), True
        >>> test_trip._generate_active_hours(
        ...     weekdays, start_time, start_overtime, end_time, end_overtime) == {(0, 1, True)}
        True
        """
        active_hours = set()
        shift_weekday = False
        overtime_time = False

        delta_start = timedelta(days=1) if start_overtime else timedelta(0)
        delta_end = timedelta(days=1) if end_overtime else timedelta(0)

        # start_time and end_time don't carry any information on the date, e.g. they look like
        # datetime(1990, 1, 1, insert_meaningful_hours)
        # so if start_overtime, then also end_overtime. In this case, shift every weekday one day to the right,
        # e.g. [0, 3, 4, 6] => [0, 1, 4, 5]
        if start_overtime:
            new_weekdays = []
            for weekday in weekdays:
                new_weekdays.append((weekday + 1) % 7)
            weekdays = sorted(new_weekdays)
            overtime_time = True
        elif end_overtime:  # not start_overtime, but end_overtime
            shift_weekday = True

        for active_time in Utils.date_span_hour(start_time + delta_start, end_time + delta_end):
            for active_day in weekdays:
                if shift_weekday and active_time.day == 2:  # datetime(1990, 1, 2)
                    active_day = (active_day + 1) % 7
                    overtime_time = True
                wd, ah = Utils.generate_weekday_time_tuple(active_time, weekday=active_day)
                active_hours.add((wd, ah, overtime_time))

        return active_hours

    def is_trip_active(self, user_datetime: datetime, tt, realtime=None) -> Tuple[bool, bool]:
        """
        Checks whether the trip is active on the given date.
        Takes into account if a trip started on the previous day

        Input:
            user_datetime: date from the frontend to check whether there is traffic

        >>> from GTFSContainer import GTFSContainer
        >>> test_tt = GTFSContainer("../GTFS/doctest_files", "../saved_dictionaries/Doctests", verbose=False)
        >>> test_trip = test_tt.trip_id_to_trip_with_stops_dict["1.TA.91-10-A-j22-1.1.H"]
        >>> day1 = datetime(2022, 7, 28, 18, 20, 0)  # is a thursday (3)
        >>> test_trip.is_trip_active(day1, test_tt) == (False, False)
        True
        >>> day2 = datetime(2022, 7, 28, 19, 45, 0)  # is a thursday (3)
        >>> test_trip.is_trip_active(day2, test_tt) == (True, False)
        True
        >>> day3 = datetime(2022, 7, 29, 19, 45, 0)  # is a friday (4)
        >>> test_trip.is_trip_active(day3, test_tt) == (False, False)
        True
        >>> test_realtime = [(0, None, (86400, False), None),
        ...                  (2, None, (86400, False), None)]
        >>> day1 = datetime(2022, 7, 28, 18, 20, 0)  # is a thursday (3)
        >>> test_trip.is_trip_active(day1, test_tt, test_realtime) == (False, False)
        True
        >>> day2 = datetime(2022, 7, 28, 19, 45, 0)  # is a thursday (3)
        >>> test_trip.is_trip_active(day2, test_tt, test_realtime) == (False, False)
        True
        >>> day3 = datetime(2022, 7, 29, 19, 45, 0)  # is a friday (4)
        >>> test_trip.is_trip_active(day3, test_tt, test_realtime) == (True, False)
        True
        """
        # when using realtime data, we have to check once for every delay possible
        # we do not know the trip segment yet, thus go through all possible delays,
        # break if any of them is true
        if realtime:
            delays_to_check = Utils.get_delays_to_check(
                user_datetime, realtime,
                tt.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[self.trip_id][1])

            extra_dates, removed_dates = tt.service_id_to_service_information_dict[self.service_id][3:5]

            # every weekday, tuple only needs to be checked once, therefore just remember checked
            false_tuples = set()
            for delay_to_check in delays_to_check:
                weekday, activehour = Utils.generate_weekday_time_tuple(user_datetime, delay_to_check)
                if (weekday, activehour) in false_tuples:
                    continue
                false_tuples.add((weekday, activehour))

                overtime = False
                if (weekday, activehour, False) in self.active_hours:
                    difference = timedelta(0)
                    active = True
                elif (weekday, activehour, True) in self.active_hours:
                    difference = timedelta(days=1)
                    overtime = True
                    active = True
                else:
                    difference = timedelta(0)
                    active = False

                if not active:
                    # check in extra_dates if there is additional service on the given date
                    extra_dates = tt.service_id_to_service_information_dict[self.service_id][3]
                    if (user_datetime - delay_to_check).date() - difference in extra_dates:
                        return True, overtime
                    return False, overtime

                # check if day is in removed_dates
                if (user_datetime - delay_to_check).date() in removed_dates:
                    return False, overtime

                return True, overtime

            return False, False

        # in this case there is no realtime data, just check with no delay
        else:
            weekday, activehour = Utils.generate_weekday_time_tuple(user_datetime)
            overtime = False
            if (weekday, activehour, False) in self.active_hours:
                difference = timedelta(0)
                active = True
            elif (weekday, activehour, True) in self.active_hours:
                difference = timedelta(days=1)
                overtime = True
                active = True
            else:
                difference = timedelta(0)
                active = False

            if not active:
                # check in extra_dates if there is additional service on the given date
                extra_dates = tt.service_id_to_service_information_dict[self.service_id][3]
                if user_datetime.date() - difference in extra_dates:
                    return True, overtime
                return False, overtime

            removed_dates = tt.service_id_to_service_information_dict[self.service_id][4]
            # check if day is in removed_dates
            if user_datetime.date() - difference in removed_dates:
                return False, overtime

            return True, overtime

    def get_active_trip_segment_ids(
            self, user_datetime: datetime, edge_id: int, tt,
            realtime_data=None, ignore_start_end_date: bool = False,
            delay: timedelta = timedelta(0),
            earliness: timedelta = timedelta(0),
    ) -> List[int]:
        """
        Returns the trip_segment_ids for every trip segment where there is traffic.
            [] if there is no active trip_segment.

        If ignore_start_end_date is true, ignore the start_date / end_date boundary from GTFS calendar.txt

        Earliness describes how many minutes a public transit vehicle is allowed to be early.
            The naming is based on a translation error.

        >>> from GTFSContainer import GTFSContainer
        >>> test_tt = GTFSContainer("../GTFS/doctest_files", "../saved_dictionaries/Doctests", verbose=False)
        >>> test_trip = test_tt.trip_id_to_trip_with_stops_dict["1.TA.91-10-A-j22-1.1.H"]
        >>> test_id = 142
        >>> test_time = datetime(2022, 7, 28, 19, 46, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == []
        True
        >>> test_id = 27
        >>> test_time = datetime(2022, 7, 27, 19, 46, 0)  # is a wednesday (2)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == []
        True
        >>> test_time = datetime(2022, 7, 28, 19, 44, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == [1]
        True
        >>> test_time = datetime(2022, 7, 28, 19, 45, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == [1, 2]
        True
        >>> test_time = datetime(2022, 7, 28, 19, 46, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == [2]
        True
        >>> test_id = 28
        >>> test_time = datetime(2022, 7, 28, 19, 46, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == [2]
        True
        >>> test_id = 26
        >>> test_time = datetime(2022, 7, 28, 19, 46, 0)  # is a thursday (3)
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt) == []
        True
        >>> test_id = 27
        >>> test_time = datetime(2022, 7, 28, 19, 46, 0)  # is a thursday (3)
        >>> test_realtime = [(1, None, (datetime(2022, 7, 28, 19, 46), True), None),
        ...                  (2, (datetime(2022, 7, 28, 19, 46), True), None, None)]
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt, test_realtime) == [1, 2]
        True
        >>> test_realtime = [(1, None, (datetime(2022, 7, 28, 19, 46), True), None),
        ...                  (2, None, (-600, False), None)]
        >>> test_trip.get_active_trip_segment_ids(test_time, test_id, test_tt, test_realtime) == [1]
        True
        """
        edge_id_to_trip_segment_id_dict = \
            tt.hash_to_edge_id_to_trip_segment_id_dict_dict[self.hash_to_edge_id_to_trip_segments_dict][0]

        if edge_id not in edge_id_to_trip_segment_id_dict:
            return []

        if not ignore_start_end_date:
            # return False if the GTFS is not up-to-date
            # start_date as (%Y%m%d) < date < end_date as (%Y%m%d)
            start_date, end_date = tt.service_id_to_service_information_dict[self.service_id][1:3]
            if not (start_date < user_datetime.date() < end_date):
                return []

        active, overtime = self.is_trip_active(user_datetime, tt, realtime=realtime_data)
        if not active:
            return []

        # all the stop_times has date 1900.1.1, difference needed to convert to the user date
        difference = user_datetime.date() - date(1900, 1, 1)
        trip_segment_ids = []
        stops_list = tt.trip_id_to_route_id_and_list_of_stop_times_and_stop_id_dict[self.trip_id][1]
        # loop through trip segments
        for trip_segment_id in edge_id_to_trip_segment_id_dict[edge_id]:
            # get time info for stops
            _, start_tuple, _ = stops_list[trip_segment_id]
            end_tuple, _, _ = stops_list[trip_segment_id + 1]
            start_time, start_ot = start_tuple
            end_time, end_ot = end_tuple

            td_start, td_end = timedelta(0), timedelta(0)
            # if user is in overtime, the start time and end time might be from the last day
            # unless they have overtime, then we do not need to change
            if overtime:
                if not start_ot and not end_ot:
                    td_start = timedelta(days=-1)
                    td_end = timedelta(days=-1)
                elif not start_ot:
                    td_start = timedelta(days=-1)
            # if user is not in overtime, then if start and end time have overtime,
            # then that would be on the next day
            else:
                if not start_ot and end_ot:
                    td_end = timedelta(days=1)
                elif start_ot and end_ot:
                    td_start = timedelta(days=1)
                    td_end = timedelta(days=1)

            # get delay from the realtime data/dict
            start_delay, stop_delay = Utils.get_rt_offset(
                realtime_data, trip_segment_id, start_tuple, end_tuple, difference)

            start_with_offset = start_time - earliness + difference + td_start + start_delay
            end_with_offset = end_time + delay + difference + td_end + stop_delay

            # only append if the time fits, with all the offsets
            if start_with_offset <= user_datetime <= end_with_offset:
                trip_segment_ids.append(trip_segment_id)

        return trip_segment_ids
