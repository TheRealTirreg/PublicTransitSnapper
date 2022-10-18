"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
import pandas as pd
from typing import List, Tuple, Any
from math import radians, sin, cos, atan2, sqrt
from datetime import datetime, timedelta, date
from networkx.algorithms.shortest_paths.weighted import _weight_function
from heapq import heappush as push, heappop as pop
from itertools import count
from pytz import timezone as pytz_timezone, utc as pytz_utc
import threading
from functools import wraps


def get_multiple_max_values(lst: List[Tuple[Any, int]]) -> List[Tuple[Any, int]]:
    """
    Take a list of value, int.
    Get all the values with the highest int.
    Only one pass is made over the list. -> O(n)

    >>> get_multiple_max_values([]) == []
    True
    >>> get_multiple_max_values([("a", 1), ("b", 2), ("c", 2), ("d", 1)]) == ["b", "c"]
    True
    """
    ret = []

    if lst:
        max_occ = lst[0][1]
        for name, occ in lst:
            if occ > max_occ:
                max_occ = occ
                ret = [name]
            elif occ == max_occ:
                ret.append(name)

    return ret


def get_colors(color: str, text_color: str, route_type: int) -> (str, str):
    """
    If the route_color and the route_text_color of a vehicle
        are white and black, it is sometimes hard
        to see the trail on the frontend map.
        Therefore, change the colors here.
    Always returns upper case hex numbers

    >>> get_colors("0fffff", "000000", 0)  # don't change already custom colors
    ('0FFFFF', '000000')
    >>> get_colors("ffffff", "000000", 69)  # default case
    ('FFFFFF', '000000')
    >>> get_colors("ffffff", "000000", 0)  # Tram
    ('E010C2', 'FFFFFF')
    >>> get_colors("ffffff", "000000", 3)  # Bus
    ('9B9B9B', 'FFFFFF')
    """
    # use upper case letters
    color = color.upper()
    text_color = text_color.upper()

    # do not change custom colors
    if color != "FFFFFF" or text_color != "000000":
        return color, text_color

    if route_type == 0:        # Tram, Streetcar, Light rail
        color = "E010C2"       # -> pink
        text_color = "FFFFFF"  # -> white
    elif route_type == 1:      # Metro, Subway
        color = "1279F3"       # -> marine blue
        text_color = "FFFFFF"  # -> black
    elif route_type == 2:      # Rail
        color = "000000"       # -> black
        text_color = "FFFFFF"  # -> white
    elif route_type == 3:      # Bus
        color = "9B9B9B"       # -> grey
        text_color = "FFFFFF"  # -> white
    elif route_type == 4:      # Ferry
        color = "A83DC2"       # -> violet
        text_color = "FFFFFF"  # -> white
    elif route_type == 5:      # Cable tram
        color = "ED77FF"       # -> light pink
        text_color = "000000"  # -> black
    elif route_type == 6:      # Aerial lift, suspended cable car, gondola
        color = "F5A623"       # -> orange
        text_color = "000000"  # -> black
    elif route_type == 7:      # Funicular
        color = "F15204"       # -> red
        text_color = "000000"  # -> black
    elif route_type == 11:     # Trolleybus
        color = "32F3C8"       # -> cyan
        text_color = "000000"  # -> black
    elif route_type == 12:     # Monorail
        color = "EA15BE"       # -> pink
        text_color = "000000"  # -> black

    return color, text_color  # default: return (white, black)


def get_delay_single_tuple(delay, time_tuple, difference=timedelta(0)):
    """
    Get the delay for a single option

    >>> test_delay = (datetime(2022, 8, 30, 23,00), True)
    >>> test_time_tuple = (datetime(1900, 1, 1, 22, 00), False)
    >>> test_difference = timedelta(days=44801)
    >>> get_delay_single_tuple(test_delay, test_time_tuple, test_difference) == timedelta(hours=1)
    True
    >>> test_delay = (datetime(2022, 8, 30, 22,00), True)
    >>> test_time_tuple = (datetime(1900, 1, 1, 23, 00), False)
    >>> test_difference = timedelta(days=44801)
    >>> get_delay_single_tuple(test_delay, test_time_tuple, test_difference) == timedelta(hours=-1)
    True
    >>> test_delay = (datetime(2022, 8, 31, 2 ,00), True)
    >>> test_time_tuple = (datetime(1900, 1, 1, 1, 00), True)
    >>> test_difference = timedelta(days=44801)
    >>> get_delay_single_tuple(test_delay, test_time_tuple, test_difference) == timedelta(hours=1)
    True
    >>> test_delay = (datetime(2022, 8, 30, 23 ,00), True)
    >>> test_time_tuple = (datetime(1900, 1, 1, 1, 00), True)
    >>> test_difference = timedelta(days=44801)
    >>> get_delay_single_tuple(test_delay, test_time_tuple, test_difference) == timedelta(hours=-2)
    True
    >>> test_delay = (86400, False)
    >>> test_time_tuple = (datetime(1900, 1, 1, 1, 00), True)
    >>> test_difference = timedelta(days=44801)
    >>> get_delay_single_tuple(test_delay, test_time_tuple, test_difference) == timedelta(days=1)
    True
    """
    # in case of true it is a timestamp, convert to timedelta
    if delay[1]:
        time, overflow = time_tuple
        time_overflow = time + difference + (timedelta(days=1) if overflow else timedelta(0))
        delta = delay[0] - time_overflow
        return delta
    # in the other case it is just the delay in seconds
    return timedelta(seconds=delay[0])


def get_rt_offset(realtime, trip_segment_id, start_time, end_time, difference=timedelta(0)):
    """
    If realtime data is present for a stop,
    then all following stops have the same delay,
    until a stop has new realtime information.

    If stop 1 has a delay of 5 minutes and stop 3 has a delay of 2 minutes,
    then stop 0 has no delay
    stop 1, 2 have a delay of 5 minutes
    stop 3 and all following stops have 2 mintues delay.

    >>> test_ts_id = 0
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_realtime = [(0, None, (300, False), None),
    ...                  (2, None, (600, False), None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time) == (
    ...     timedelta(minutes=5), timedelta(minutes=5))
    True
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_diff = datetime(2022, 8, 31) - datetime(1900, 1, 1)
    >>> test_realtime = [(0, None, (datetime(2022, 8, 31, 18, 35), True), None),
    ...                  (2, None, (datetime(2022, 8, 31, 19, 40), True), None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time, test_diff) == (
    ...     timedelta(minutes=5), timedelta(minutes=5))
    True
    >>> test_ts_id = 1
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_diff = datetime(2022, 8, 31) - datetime(1900, 1, 1)
    >>> test_realtime = [(0, None, (datetime(2022, 8, 31, 18, 35), True), None),
    ...                  (2, (datetime(2022, 8, 31, 19, 40), True), None, None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time, test_diff) == (
    ...     timedelta(minutes=5), timedelta(minutes=10))
    True
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_realtime = [(0, None, (300, False), None),
    ...                  (3, (420, False), (600, False), None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time) == (
    ...     timedelta(minutes=5), timedelta(minutes=5))
    True
    >>> test_ts_id = 3
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_realtime = [(0, None, (300, False), None),
    ...                  (2, (420, False), (600, False), None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time) == (
    ...     timedelta(minutes=10), timedelta(minutes=10))
    True
    >>> test_ts_id = 0
    >>> test_start_time, test_end_time = (datetime(1900, 1, 1, 18, 30), False), (datetime(1900, 1, 1, 19, 30), False)
    >>> test_realtime = [(1, None, (300, False), None),
    ...                  (2, None, (600, False), None)]
    >>> get_rt_offset(test_realtime, test_ts_id, test_start_time, test_end_time) == (
    ...     timedelta(0), timedelta(0))
    True
    """
    start_delay, stop_delay = timedelta(0), timedelta(0)
    # find realtime info for the trip segment
    if realtime is not None:
        for ts_id, arrival_delay, departure_delay, _ in realtime:
            if ts_id >= trip_segment_id + 1:
                if ts_id == trip_segment_id + 1 and arrival_delay:
                    stop_delay = get_delay_single_tuple(arrival_delay, end_time, difference)
                else:
                    stop_delay = start_delay
                break

            if departure_delay:
                delay = get_delay_single_tuple(departure_delay, start_time, difference)
                start_delay, stop_delay = delay, delay

    return start_delay, stop_delay


def get_delays_to_check(user_datetime, realtime_data, list_stop_times_ids):
    """
    Take a list of delays, convert to a list of delays with second

    >>> test_ut = datetime(2022, 8, 30, 22, 30)
    >>> test_rt = [(0, None, (30, False), None),
    ...            (1, (-86400, False), (datetime(2022, 9, 2, 0), True), None)]
    >>> test_st = [((datetime(1900, 1, 1, 22), False), (datetime(1900, 1, 1, 23), False), None),
    ...            ((datetime(1900, 1, 1, 23), False), (datetime(1900, 1, 1, 0), True), None)]
    >>> get_delays_to_check(test_ut, test_rt, test_st) == [timedelta(seconds=30),timedelta(days=-1), timedelta(days=2)]
    True
    """
    delays_to_check = []
    for stop_sequence, arrival_delay, departure_delay, _ in realtime_data:
        arrival_tuple, departure_tuple, _ = list_stop_times_ids[stop_sequence]
        difference = user_datetime.date() - date(1900, 1, 1)
        if arrival_delay:
            to_add = get_delay_single_tuple(arrival_delay, arrival_tuple, difference)
            delays_to_check.append(to_add)
        if departure_delay:
            to_add = get_delay_single_tuple(departure_delay, departure_tuple, difference)
            delays_to_check.append(to_add)
    return delays_to_check


def is_within_active_hours(active_hours: set, current_time: datetime) -> bool:
    """
    True if the given current_time is within the set of active hours set((weekday_int, hour_int), ...)

    >>> t1 = datetime(2022, 7, 31, 16, 36)  # is a sunday
    >>> s1 = {(6, 16, False)}
    >>> is_within_active_hours(s1, t1)
    True
    >>> t2 = t1 + timedelta(hours=1)
    >>> is_within_active_hours(s1, t2)
    False
    >>> s2 = {(6, 23, False), (0, 0, True), (0, 1, True)}
    >>> t3 = datetime(2022, 7, 31, 22, 55)  # is a sunday
    >>> is_within_active_hours(s2, t3)
    False
    >>> is_within_active_hours(s2, t3 + timedelta(hours=1))
    True
    >>> is_within_active_hours(s2, t3 + timedelta(hours=2))
    True
    >>> is_within_active_hours(s2, t3 + timedelta(hours=3))
    True
    >>> is_within_active_hours(s2, t3 + timedelta(hours=4))
    False
    """
    return (current_time.weekday(), current_time.hour, False) in active_hours or \
           (current_time.weekday(), current_time.hour, True) in active_hours


def repeat_every_n_minutes(n: float):
    """
    Repeats a given function once every n minutes.

    no doctest for this function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            threading.Timer(n * 60, wrapper, args, kwargs).start()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def date_span_hour(start_date, end_date):
    """
    Yield once for every hour between two datetime objects.
    >>> time_test1 = datetime.strptime('29.06.2022  22:55', '%d.%m.%Y %H:%M')
    >>> time_test2 = datetime.strptime('29.06.2022  23:55', '%d.%m.%Y %H:%M')
    >>> list(date_span_hour(time_test1, time_test2)) == [datetime(2022, 6, 29, 22, 0), datetime(2022, 6, 29, 23, 0)]
    True
    >>> time_test1 = datetime.strptime('29.06.2022  22:55', '%d.%m.%Y %H:%M')
    >>> time_test2 = datetime.strptime('30.06.2022  02:15', '%d.%m.%Y %H:%M')
    >>> list(date_span_hour(time_test1, time_test2)) == [
    ...     datetime(2022, 6, 29, 22, 0), datetime(2022, 6, 29, 23, 0),
    ...     datetime(2022, 6, 30, 0, 0), datetime(2022, 6, 30, 1, 0),
    ...     datetime(2022, 6, 30, 2, 0)]
    True
    >>> time_test1 = datetime(2022, 6, 29, 23, 55)
    >>> time_test2 = datetime(2022, 6, 30, 0, 5)
    >>> list(date_span_hour(time_test1, time_test2)) == [datetime(2022, 6, 29, 23, 0), datetime(2022, 6, 30, 0, 0)]
    True
    """
    delta = timedelta(hours=1)
    current_date = date_floor_hour(start_date)
    while current_date < end_date:
        yield current_date
        current_date += delta


def date_floor_hour(time):
    """
    Round the datetime by hour down to the next hour
    >>> time_test = datetime.strptime('29.06.2022  23:55', '%d.%m.%Y %H:%M')
    >>> date_floor_hour(time_test) == datetime(2022, 6, 29, 23, 0)
    True
    """
    return time.replace(hour=time.hour, minute=0, second=0, microsecond=0)


def generate_weekday_time_tuple(time, delay=None, weekday=None):
    """
    Input: datetime
    optionally take a delay in seconds, negative values possible if a vehicle is too early
    optionally take the weekday as integer as used by the datetime.weekday(), then use this as weekday.
    Monday is 0 ...

    Then generate tuple (weekday, hour). This can be used to quickly check if a trip is active on a given time.
    >>> time_test = datetime.strptime('29.06.2022  23:55', '%d.%m.%Y %H:%M')
    >>> generate_weekday_time_tuple(time_test)
    (2, 23)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(seconds=1))
    (2, 23)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(days=1))
    (1, 23)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(days=-1))
    (3, 23)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(minutes=5))
    (2, 23)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(minutes=-5))
    (3, 0)
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(days=-3))
    (5, 23)
    >>> weekday_test = 6
    >>> generate_weekday_time_tuple(time_test, weekday=weekday_test)
    (6, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, weekday=weekday_test)
    (0, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(seconds=1), weekday=weekday_test)
    (0, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(days=1), weekday=weekday_test)
    (6, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(days=-1), weekday=weekday_test)
    (1, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(minutes=5), weekday=weekday_test)
    (0, 23)
    >>> weekday_test = 0
    >>> generate_weekday_time_tuple(time_test, delay=timedelta(minutes=-5), weekday=weekday_test)
    (1, 0)
    """
    # if no delay, just return the data from time.
    if not delay:
        return (weekday, time.hour) if weekday is not None else (time.weekday(), time.hour)

    time_with_delay = (time - delay)
    if weekday is not None:
        weekday_with_delay = weekday
        # adding / subtracting the delay does change the preset weekday
        if time.date() != time_with_delay.date():
            # if the delay is positive, go to the next day else go one day back
            weekday_diff = -1 if delay > timedelta() else 1
            weekday_with_delay = (weekday + weekday_diff) % 7

        return weekday_with_delay, time_with_delay.hour

    return time_with_delay.weekday(), time_with_delay.hour


def time_difference_calculator(t1: datetime, o1: bool, t2: datetime, o2: bool):
    """
    Return timedelta of two time, that also considers overflow / overtime, when a trip goes over the day border

    >>> t1_test, o1_test = datetime.strptime('29.06.2022  13:00', '%d.%m.%Y %H:%M'), False
    >>> t2_test, o2_test = datetime.strptime('29.06.2022  13:10', '%d.%m.%Y %H:%M'), False
    >>> time_difference_calculator(t1_test, o1_test, t2_test, o2_test) == timedelta(minutes=10)
    True
    >>> t1_test, o1_test = datetime.strptime('29.06.2022  23:55', '%d.%m.%Y %H:%M'), False
    >>> t2_test, o2_test = datetime.strptime('29.06.2022  00:05', '%d.%m.%Y %H:%M'), True
    >>> time_difference_calculator(t1_test, o1_test, t2_test, o2_test) == timedelta(minutes=10)
    True
    """
    if not o1 and o2:
        return t2 - t1 - timedelta(days=-1)
    else:
        return t2 - t1


def are_last_gps_points_close_to_each_other(
        route: List[Tuple[float, float]],
        average_movement_in_meters=40,
        use_last_n_points=5,
        print_time=True
):
    """
    Do not match if the last gps points have not moved averagely for more than
        average_movement_in_meters meters
    route: [[lat, lon, timestamp], ...]

    >>> close_points = [(48.012349, 7.835795), (48.012469, 7.835507), (48.012239, 7.835473),
    ...     (48.012322, 7.836036), (48.012474, 7.836006)]
    >>> are_last_gps_points_close_to_each_other(close_points, print_time=False)
    True
    >>> points_along_a_route = [(48.012028, 7.835449), (48.012366, 7.835818), (48.012656, 7.836430),
    ...     (48.012736, 7.836416), (48.013010, 7.836828)]
    >>> are_last_gps_points_close_to_each_other(points_along_a_route, print_time=False)
    False
    >>> points_along_a_short_route = [(48.012028, 7.835449), (48.012366, 7.835818), (48.012656, 7.836430)]
    >>> are_last_gps_points_close_to_each_other(points_along_a_short_route, print_time=False)
    False
    >>> points_that_start_on_a_route_but_then_stop = [(48.011569, 7.834725),  # should only take the last 5 points
    ...     (48.011941, 7.835387), (48.012269, 7.835590), (48.012311, 7.835943), (48.012403, 7.835899),
    ...     (48.012318, 7.835961), (48.012361, 7.835937)]
    >>> are_last_gps_points_close_to_each_other(points_that_start_on_a_route_but_then_stop, print_time=False)
    True
    >>> points_that_start_on_a_route_but_then_stop_closer_points = [(48.011941, 7.835387),
    ...     (48.012269, 7.835590), (48.012311, 7.835943), (48.012403, 7.835899),
    ...     (48.012318, 7.835961), (48.012361, 7.835937), (48.012332, 7.835850)]
    >>> are_last_gps_points_close_to_each_other(
    ...     points_that_start_on_a_route_but_then_stop_closer_points, print_time=False)
    True
    """
    # get the geographical center of the last GPS points
    num_points = min(use_last_n_points, len(route))
    route = route[-num_points:]  # take last n items

    lat_sum, lon_sum = 0, 0
    for point in route:
        lat, lon = point[0], point[1]
        lat_sum += lat
        lon_sum += lon

    average_point = (lat_sum / num_points, lon_sum / num_points)

    # remove the point that is the furthest away to reduce outlier problem
    greatest_dist = 0
    greatest_index = 0
    for i, point in enumerate(route):
        lat, lon = point[0], point[1]
        dist = great_circle_distance(lat, lon, average_point[0], average_point[1])
        if dist > greatest_dist:
            greatest_dist = dist
            greatest_index = i
    route.pop(greatest_index)

    # check if every point is within average_movement_in_meters distance
    for point in route:
        lat, lon = point[0], point[1]
        dist = great_circle_distance(lat, lon, average_point[0], average_point[1])
        if dist > average_movement_in_meters:
            return False

    if print_time:
        print("not matching, because GPS points are too close to each other")

    return True


def are_last_n_coordinates_timewise_too_far_apart(
        coords_with_timestamps: List[Tuple[float, float, float]], n: int = 10, m: int = 5) -> bool:
    """
    Looks at the last n timestamps. If some of them are m minutes or more apart, return True

    >>> coords_w_timestamps = [(1, 2, 1664985350689 // 1000), (1, 2, 1664985350689 // 1000)]
    >>> are_last_n_coordinates_timewise_too_far_apart(coords_w_timestamps)
    False
    >>> coords_w_timestamps = [(1, 2, 1664985350689 // 1000), (1, 2, 1664985350689 // 1000 + 3 * 60)]
    >>> are_last_n_coordinates_timewise_too_far_apart(coords_w_timestamps)
    False
    >>> coords_w_timestamps = [(1, 2, 1664985350689 // 1000), (1, 2, 1664985350689 // 1000 + 5 * 60)]
    >>> are_last_n_coordinates_timewise_too_far_apart(coords_w_timestamps)
    True
    >>> coords_w_timestamps = [(1, 2, 1664985350689 // 1000), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60)]
    >>> are_last_n_coordinates_timewise_too_far_apart(coords_w_timestamps)
    True
    >>> coords_w_timestamps = [(1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60),
    ...     (1, 2, 1664985350689 // 1000 + 5 * 60), (1, 2, 1664985350689 // 1000 + 5 * 60)]
    >>> are_last_n_coordinates_timewise_too_far_apart(coords_w_timestamps)
    False
    """
    num_coords = min(n, len(coords_with_timestamps))
    for i in range(num_coords - 1):
        t0, t1 = coords_with_timestamps[i][2], coords_with_timestamps[i+1][2]
        if t1 - t0 >= m * 60:  # if time difference > m minutes (in seconds)
            return True
    return False


def distance_wrapper(point1, point2):
    """
    Calculate the distance between two points.
    Use the great circle distance
    point (lat, lon, ...)

    >>> from math import isclose
    >>> isclose(111194.925,
    ...     distance_wrapper((0,0),(0,1)),
    ...     rel_tol = 0.01)
    True
    >>> isclose(134182.004,
    ...     distance_wrapper((48.009833, 7.782528), (47.009833, 6.782528)),
    ...     rel_tol = 0.01)
    True
    """
    return great_circle_distance(point1[0], point1[1], point2[0], point2[1])


def great_circle_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two Gps Points in meters,
    using haversine formula.
    Formula found here: http://www.movable-type.co.uk/scripts/latlong.html

    L = 2*pi*r*A / 360, r = 6371 km, A change in Degree
    * 1000 for L in meters

    >>> from math import isclose
    >>> isclose(111194.925,
    ...     great_circle_distance(0,0,0,1),
    ...     rel_tol = 0.01)
    True
    >>> isclose(134182.004,
    ...     great_circle_distance(48.009833, 7.782528, 47.009833, 6.782528),
    ...     rel_tol = 0.01)
    True
    """
    r = 6371e3  # radius of earth in m
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) * sin(d_lat / 2) + \
        cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) * sin(d_lon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def convert_utc_to_local_time(timestamp, timezone_name="Europe/Berlin") -> datetime:
    """
    Converts the input utc timestamp to local time as a datetime object
    1659030123 corresponds to 17:42:03 in utc time
    In Germany the time should be 2 hours later
    >>> convert_utc_to_local_time(1659030123) == datetime(2022, 7, 28, 19, 42, 3)
    True
    """
    tim_utc = datetime.utcfromtimestamp(timestamp)
    return tim_utc.replace(tzinfo=pytz_utc).astimezone(pytz_timezone(timezone_name)).replace(tzinfo=None)


def convert_local_time_to_utc(local_datetime: datetime, timezone_name="Europe/Berlin") -> datetime:
    """
    >>> convert_local_time_to_utc(datetime(2022, 7, 28, 19, 42, 3)) == datetime(2022, 7, 28, 17, 42, 3)
    True
    """
    local_tz = pytz_timezone(timezone_name)
    return local_tz.localize(local_datetime, is_dst=None).astimezone(pytz_utc).replace(tzinfo=None)


def calculate_direction_penalty(shape_seq_start: List[Tuple[str, int]], shape_seq_end: List[Tuple[str, int]]) -> int:
    """
    Calculate the average direction of the edges, by using shape_id and the sequence_id

    if the end node has smaller sequence number than start node add cost
    take the average directions, if most are in the wrong direction add cost

    -1 = if edges are not same shape
    0 = do not add penalty
    1 = add penalty

    >>> test_l1 = []
    >>> test_l2 = []
    >>> calculate_direction_penalty(test_l1, test_l2)
    -1
    >>> test_l1 = [("shp_1", 1), ("shp_1", 3)]
    >>> test_l2 = [("shp_2", 2), ("shp_2", 4)]
    >>> calculate_direction_penalty(test_l1, test_l2)
    -1
    >>> test_l1 = [("shp_1", 1), ("shp_2", 3)]
    >>> test_l2 = [("shp_1", 2), ("shp_2", 4)]
    >>> calculate_direction_penalty(test_l1, test_l2)
    0
    >>> test_l1 = [("shp_1", 1)]
    >>> test_l2 = [("shp_1", 2), ("shp_2", 4)]
    >>> calculate_direction_penalty(test_l1, test_l2)
    0
    >>> test_l1 = [("shp_1", 1), ("shp_2", 4)]
    >>> test_l2 = [("shp_1", 2), ("shp_2", 3)]
    >>> calculate_direction_penalty(test_l1, test_l2)
    0
    >>> test_l1 = [("shp_1", 2)]
    >>> test_l2 = [("shp_1", 1), ("shp_2", 4)]
    >>> calculate_direction_penalty(test_l1, test_l2)
    1
    """
    counter = 0
    same_shape_counter = 0
    for shape_start, seq_start in shape_seq_start:
        for shape_end, seq_end in shape_seq_end:
            if shape_start == shape_end:
                same_shape_counter += 1
                if seq_start <= seq_end:
                    counter += 1
                # a shape should only appear once in the list
                break

    if same_shape_counter == 0:
        return -1

    return 0 if counter >= min(len(shape_seq_start), len(shape_seq_end)) / 2 else 1


def convert_gtfs_date_to_datetime(s: str) -> (datetime, bool):
    """
    Converts a given date from GTFS to a datetime object
    Occasionally, when a trip starts on one day and finishes on another day,
        the GTFS-Date will be like 25:01:00 ("%H:%M:%S").
        This will result in a ValueError.
        This method prevents this error.

    Input:
        s: string in '%H:%m:%s' format

    Returns:
        Tuple of a datetime object and a bool 'overflow' (True if the given GTFS-Date overlapped)

    >>> convert_gtfs_date_to_datetime("00:00:00")  # should not overflow
    (datetime.datetime(1900, 1, 1, 0, 0), False)
    >>> convert_gtfs_date_to_datetime("25:25:00")  # should overflow by 1h and 25mins
    (datetime.datetime(1900, 1, 1, 1, 25), True)
    """
    try:
        date = datetime.strptime(s, "%H:%M:%S")
        overflow = False
    except ValueError:
        hour = str(int(s[:2]) - 24)
        if len(hour) == 1:
            hour = "0" + hour
        rest = s[2:]
        date = datetime.strptime(hour + rest, "%H:%M:%S")
        overflow = True

    return date, overflow


def bidirectional_dijkstra_modified(g, source, target, weight="weight", penalty=1000000000, thresh=500):
    """
    Modified version of bidirectional_dijkstra from networkx

    This version does not raise error, instead it returns penalty if no path is found.
    It also stops if the cost for one side of the dijkstra is higher than the threshold.

    Reason for this, is to improve the performance of the algorithm.
    Typically, original networkx is very fast, but some outliers are causing the algorithm to take too long.

    >>> import networkx as nx
    >>> g = nx.DiGraph()
    >>> g.add_edge(0, 1, weight=1)
    >>> g.add_edge(0, 2, weight=1)
    >>> g.add_edge(1, 2, weight=1)
    >>> bidirectional_dijkstra_modified(g, 0, 2) == 1
    True

    >>> g = nx.DiGraph()
    >>> g.add_edge(0, 1, weight=1)
    >>> g.add_edge(0, 2, weight=3)
    >>> g.add_edge(1, 2, weight=1)
    >>> bidirectional_dijkstra_modified(g, 0, 2) == 2
    True

    >>> g = nx.DiGraph()
    >>> g.add_edge(0, 1, weight=500)
    >>> g.add_edge(0, 2, weight=1000)
    >>> g.add_edge(1, 2, weight=500)
    >>> bidirectional_dijkstra_modified(g, 0, 2) == 1000000000
    True

    >>> g = nx.DiGraph()
    >>> g.add_edge(0, 1, weight=1)
    >>> g.add_edge(0, 4, weight=1)
    >>> g.add_edge(4, 3, weight=1000)
    >>> g.add_edge(1, 2, weight=2)
    >>> g.add_edge(2, 3, weight=3)
    >>> bidirectional_dijkstra_modified(g, 0, 2) == 3
    True
    """
    # no check if in graph, in our use case it is always true
    # no check if they are the same, it is already checked

    weight = _weight_function(g, weight)
    dists = [{}, {}]  # dictionary of final distances
    paths = [{source: [source]}, {target: [target]}]  # dictionary of paths
    fringe = [[], []]  # heap of (distance, node) tuples for each side
    seen = [{source: 0}, {target: 0}]  # dict of distances to each node
    c = count()
    # initialize fringe heap
    push(fringe[0], (0, next(c), source))
    push(fringe[1], (0, next(c), target))
    # we only use a directed graph
    neighs = [g._succ, g._pred]
    # variables to hold shortest discovered path
    finaldist = 1e30000
    finalpath = []
    dir = 1
    while fringe[0] and fringe[1]:
        # choose direction
        # dir == 0 is forward direction and dir == 1 is back
        dir = 1 - dir
        # extract closest to expand
        (dist, _, v) = pop(fringe[dir])
        if v in dists[dir]:
            # Shortest path to v has already been found
            continue
        # update distance
        dists[dir][v] = dist  # equal to seen[dir][v]
        if v in dists[1 - dir]:
            # if we have scanned v in both directions we are done
            # we have now discovered the shortest path
            return finaldist

        for w, d in neighs[dir][v].items():
            if dir == 0:  # forward
                vw_length = dists[dir][v] + weight(v, w, d)
            else:  # back, must remember to change v,w->w,v
                vw_length = dists[dir][v] + weight(w, v, d)
            if vw_length > thresh:
                break
            if w in dists[dir]:
                # no negative weights
                continue
            elif w not in seen[dir] or vw_length < seen[dir][w]:
                # relaxing
                seen[dir][w] = vw_length
                push(fringe[dir], (vw_length, next(c), w))
                paths[dir][w] = paths[dir][v] + [w]
                if w in seen[0] and w in seen[1]:
                    # see if this path is better than the already
                    # discovered shortest path
                    totaldist = seen[0][w] + seen[1][w]
                    if finalpath == [] or finaldist > totaldist:
                        finaldist = totaldist
                        revpath = paths[1][w][:]
                        revpath.reverse()
                        finalpath = paths[0][w] + revpath[1:]
    return penalty


def replace_route_type(routes_file, what_to_replace: List[str], replace_by: List[str]):
    """
    The switzerland GTFS use weird route_types that cannot be processed by pfaedle.
    Therefore, we need to replace them.

    Example:
        'what_to_replace' and 'replace_by' have to have the same lengths, for example
        what_to_replace = ['1700', '1501']\n"
        replace_by      = ['1300', '700']\n"
        Here, 1700 will be replaced by 1300 and 1501 will be replaced by 700.

    >>> header = ["route_id", "agency_id", "route_short_name", "route_long_name", "route_desc",
    ...     "route_type", "route_url", "route_color", "route_text_color"]
    >>> row1 = ["1", "0", "shortname", "longname", "", "0", "", "", ""]
    >>> row2 = ["2", "0", "shortname", "longname", "", "1501", "", "", ""]
    >>> row3 = ["3", "0", "shortname", "longname", "", "1700", "", "", ""]
    >>> row4 = ["4", "0", "shortname", "longname", "", "700", "", "", ""]
    >>> row5 = ["5", "0", "shortname", "longname", "", "1300", "", "", ""]
    >>> routes_df = pd.DataFrame([row1, row2, row3, row4, row5], columns=header)
    >>> what_to_replace = ['1700', '1501']
    >>> replace_by = ['1300', '700']
    >>> for i, replace_this in enumerate(what_to_replace):
    ...     routes_df["route_type"].replace(to_replace=[replace_this], value=replace_by[i], inplace=True)
    >>> len(routes_df[routes_df["route_type"] == '1700'])
    0
    >>> len(routes_df[routes_df["route_type"] == '1501'])
    0
    >>> len(routes_df[routes_df["route_type"] == '1300'])
    2
    >>> len(routes_df[routes_df["route_type"] == '700'])
    2
    """
    if len(what_to_replace) != len(replace_by):
        raise Exception("'what_to_replace' and 'replace_by' have to have the same lengths, for example:\n"
                        "what_to_replace = ['1700', '1501']\n"
                        "replace_by      = ['1300', '700']\n"
                        "Here, 1700 will be replaced by 1300 and 1501 will be replaced by 700.")

    routes_df = pd.read_csv(routes_file)

    for i, replace_this in enumerate(what_to_replace):
        routes_df["route_type"].replace(to_replace=[replace_this], value=replace_by[i], inplace=True)

    routes_df.to_csv(routes_file, index=False, header=True)
