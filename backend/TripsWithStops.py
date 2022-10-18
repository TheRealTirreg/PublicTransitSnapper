from typing import List, Tuple
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
from datetime import datetime, timedelta
import Utilities as util


class TripSegment:
    """
    Part of a TripWithStops. Each trip has n = |stops| - 1 TripSegments.
    """

    __slots__ = [
        "start_position",
        "stop_position",
        "start_time",
        "start_overflow",
        "end_time",
        "end_overflow",
        "strtree"
    ]

    def __init__(
            self,
            start_position: Tuple[float, float],
            start_time: Tuple[datetime, bool],
            polyline: List[Point],
            stop_position: Tuple[float, float],
            end_time: Tuple[datetime, bool]
    ):
        """
        start_position: coordinate from GTFS stops.txt. Start of the segment.
        stop_position: coordinate from GTFS stops.txt. End of the segment.
        polyline: List of coordinates a public transit vehicle can move along on
        start_time: Tuple of datetime (%H:%M:%S)
                    and a bool which indicates whether the stop is visited on the same day as the first stop of the trip
        end_time: Tuple of datetime (%H:%M:%S)
                    and a bool which indicates whether the stop is visited on the same day as the first stop of the trip
        nr: each trip has n = |stops| - 1 segments. nr indicates the number of the trip segment.
        """
        self.start_position = start_position
        self.stop_position = stop_position
        self.start_time = start_time[0] + timedelta(days=1) if start_time[1] else start_time[0]
        self.start_overflow = start_time[1]
        self.end_time = end_time[0] + timedelta(days=1) if end_time[1] else end_time[0]
        self.end_overflow = end_time[1]
        try:
            self.strtree = STRtree(util.splitLineString(polyline))
        except ValueError:
            print(polyline)
            raise ValueError(f"polyline: {polyline}")

    def __repr__(self):
        return "Start_pos :" + str(self.start_position) + "End_pos :" + str(self.stop_position)

    def isActive(self, time: datetime, delay: timedelta, precipitation: timedelta) -> bool:
        """
        Returns True if there is a vehicle on this TripSegment, else False
        """
        # Only take time.date() to compare time.time(). This function only compares hours and such.
        # Example: time.time() is 00:00:00. With precipitation, we have an 'underflow' to the previous day.
        # That's why we take time.date() to be able to subtract these sorts of times.
        day = time.date()
        start_day, end_day = day, day

        if self.start_overflow:
            start_day = day + timedelta(days=1)
        if self.end_overflow:
            end_day = day + timedelta(days=1)

        start_time = datetime.combine(start_day, self.start_time.time()) - precipitation
        end_time = datetime.combine(end_day, self.end_time.time()) + delay

        return start_time <= time <= end_time

    def isClose(self, position: Tuple[float, float], allowed_distance_in_m: float = 50) -> bool:
        """
        True if the given position is close to the polyline
        allowed_distance_in_m: max. distance the given position can be away from the polyline
        """
        # allowed_distance_in_m, 0.00001° ~ 1.112m => from meters to degrees
        # 1.112 * 0.00001 ~= 0.00008993
        meters_to_degrees = 0.00008993
        point = Point(position)
        closest_line = self.strtree.nearest(point)
        return point.distance(closest_line) < allowed_distance_in_m * meters_to_degrees


class TripWithStopsAndTimes:
    """
    Stores information for one trip.
    Given a time and a date, it is able to say whether there is currently traffic on the given shape
    """

    __slots__ = [
        "trip_id",
        "trip_segments",
        "stops",
        "extra_dates",
        "removed_dates",
        "active_weekdays",
        "date_borders",
        "time_interval"
    ]

    def __init__(
            self,
            trip_id: str,
            shape_of_trip: List[Tuple[float, float]],
            stops: List[Tuple[Tuple[datetime, bool], Tuple[datetime, bool], str, float, float]],
            start_date: datetime,
            end_date: datetime,
            extra_dates: List[datetime],
            removed_dates: List[datetime],
            active_weekdays: List[int],
    ):
        """
        trip_id: GTFS trip_id
        self.trip_segments: List of TripSegment-objects
            (each containing a start, a stop, an inbetween polyline and its nr)
        stops: List of ((stop-arrival_time, arrival_time_overflow), (stop-departure_time, departure_time_overflow),
                        stop_name, stop-lat, stop-lon)-Tuples
        extra_dates: List of datetime objects. On these dates, there is traffic even though there should not be traffic
            according to active_weekdays or start_date or end_date.
        removed_dates: List of datetime objects. On these dates, there is no traffic even though there should be traffic
            according to active_weekdays or start_date or end_date.
        active_weekdays: List of integers, where 0 represents monday, ..., 6 represents sunday.
            There is no traffic on a day if it does not occur in the list.
        date_borders: start and end boundaries of the trip as (%Y%m%d)
        time_interval: (start_of_the_trip: datetime, end_of_the_trip: datetime, overflow: bool)
            in %H%M%S format. If overflow, the trip is taking place over midnight.
        """
        self.trip_id = trip_id
        self.trip_segments = self._generateTripSegments(stops, shape_of_trip)
        self.stops = stops
        self.date_borders = (start_date, end_date)
        self.extra_dates = extra_dates
        self.removed_dates = removed_dates
        self.active_weekdays = active_weekdays
        self.time_interval = self._calculateTimeInterval()

    def __repr__(self):
        s = f"Trip_id: {self.trip_id}, time interval: {self.time_interval[0], self.time_interval[1]}"
        return s

    def __lt__(self, other):
        """
        trip_1 < trip_2 iff trip_1.start_time < trip_2.start_time
        Is used by the sorted()-method.
        """
        self_start, other_start = self.time_interval[0], other.time_interval[0]
        if self.time_interval[2]:  # start_overflow
            self_start += timedelta(days=1)
        if other.time_interval[2]:  # start_overflow
            other_start += timedelta(days=1)
        return self_start < other_start

    def _generateTripSegments(self, stops, polyline):
        """
        Generates a list of TripSegments.
        A TripSegment knows its start, stop, an inbetween polyline and its nr
        """
        # For each stop, find out the closest line segment of the polyline
        # On that segment, find the point that is closest to the stop_position
        # Add a new TripSegment with the last stop, the current stop and the polylines since the last stop
        # Remove every old line segment from polylines
        # and replace it with the newly split polyline segment that is not part of the new TripSegment

        # stops: List of ((stop-arrival_time, arrival_time_overflow), (stop-departure_time, departure_time_overflow),
        #                  stop_name, stop-lat, stop-lon)-Tuples
        trip_segments = []
        num_stops = len(stops)
        for i in range(1, num_stops):
            # generate STRtree to locate the closest line segment of polyline

            arrival_time_and_overflow, _, stop_name, stop_lat, stop_lon = stops[i]
            _, last_stop_departure_time_and_overflow, _, _, _ = stops[i - 1]
            stop_location = Point(stop_lat, stop_lon)

            # find closest line segment of polyline
            old_distance = 10000000000
            j = len(polyline) - 2
            # loop over line segments in order, to avoid wrong matching
            # if the vehicle drives on the same street more than once
            for idx, segment in enumerate(zip(polyline[:-1], polyline[1:])):
                if segment[0] == segment[1]:
                    continue
                distance = LineString(segment).distance(stop_location)
                # if distance gets smaller, check the next line segment, only if within 25 meters
                if old_distance > 0.00025 or distance <= old_distance:
                    old_distance = distance
                # if distance is now bigger, then we have found the closest line segment
                else:
                    j = idx - 1
                    break

            # find closest point on line segment
            closest_polyline_segment = LineString(polyline[j: j + 2])
            closest_point_on_line = closest_polyline_segment.interpolate(closest_polyline_segment.project(stop_location))
            closest_point_on_line = (closest_point_on_line.x, closest_point_on_line.y)

            if not polyline[:j]:
                print(f"Polyline empty. Trip: {self.trip_id}")
                continue

            # add new trip segment to trip_segments
            trip_segments.append(TripSegment(
                start_position=polyline[0],
                stop_position=closest_point_on_line,
                polyline=polyline[:j] + [closest_point_on_line],
                start_time=last_stop_departure_time_and_overflow,
                end_time=arrival_time_and_overflow)
            )

            polyline = [closest_point_on_line] + polyline[j:]

        return trip_segments

    def _calculateTimeInterval(self) -> Tuple[datetime, datetime, bool, bool]:
        """
        Calculates the time interval between the start and the end of a trip
        (start_of_the_trip: datetime, end_of_the_trip: datetime, start_overflow: bool, end_overflow: bool)
        in %H%M%S format. If overflow, the trip is taking place over midnight.
        """
        if not self.trip_segments:
            # if there are no trip segments, the trip can never be active ("fake-trip")
            return datetime.min, datetime.min, False, False

        return self.trip_segments[0].start_time, \
               self.trip_segments[-1].end_time, \
               self.trip_segments[0].start_overflow, \
               self.trip_segments[-1].end_overflow

    def _isTimeWithinTrip(
            self,
            date: datetime,
            delay: timedelta,
            precipitation: timedelta
    ) -> (bool, bool):
        """
        WARNING: Assumes that no trip will take longer than 24h!

        Input:
            date: Date to check whether there is a public transit vehicle on this trip
            delay: allowed delay of the public transit vehicle
            precipitation: allowed time that the public transit vehicle can be too late

        Returns:
            first bool: True if the given time is within the time interval of this trip.
            second bool: True if in overtime (so if we need to consider the next days date)
        """
        trip_start, trip_end, start_overflow, end_overflow = self.time_interval

        # trips with the datetime.min are fake-trips (trips with no trip segments) => Ignore
        if trip_start == datetime.min:
            return False, False

        # add delay if the time does not overflow to the previous day (like from 0h01 => 23h56)
        # in that case, ignore the delay.
        if (trip_start - precipitation).time() > trip_start.time():
            start_overflow = False
        trip_start = trip_start - precipitation

        # add the precipitation
        if (trip_end + delay).time() < trip_end.time():
            end_overflow = True
        trip_end = trip_end + delay

        # does_the_given_date_belong_to_the_last_day?
        date_overflow = False

        # if start_overflow, end_overflow also has to be true (as we assume that trips are < 24h)
        # and we can compare the datetime.time()s normally (datetime.time() only compares hours)
        if start_overflow:
            date_overflow = True

        if not start_overflow and end_overflow:
            if date.time() < trip_end.time():
                return True, True
            if date.time() > trip_start.time():
                return True, False

        # base case: no overflow.
        # Returns (within_time_interval, does_the_given_date_belong_to_the_last_day = False)
        return (True, date_overflow) if trip_start.time() < date.time() < trip_end.time() else (False, date_overflow)

    def _isTrafficOnDay(self, date: datetime, overflow: bool):
        """
        Checks whether the trip is active on the given date.
        Takes into account if a trip started on the previous day

        Input:
            date: date to check whether there is traffic
            overflow: true if we need to check for the next day
        """
        if not overflow:
            if date.weekday() not in self.active_weekdays:
                # check in extra_dates if there is additional service on the given date
                for extra_date in self.extra_dates:
                    if date.date() == extra_date.date():
                        return True
                return False

        else:
            if (date.weekday() + 1) % 7 not in self.active_weekdays:
                # check in extra_dates if there is additional service on the given date
                for extra_date in self.extra_dates:
                    if date.date() == extra_date.date() - timedelta(days=1):  # check for the previous day if overflow
                        return True
                return False

        # check if day is in removed_dates
        delta = timedelta(days=1) if overflow else timedelta()
        for removed_date in self.removed_dates:
            if date.date() == removed_date.date() - delta:  # check for the previous day if overflow
                return False

        return True

    def _getActiveTripSegments(self, time: datetime, delay: timedelta, precipitation: timedelta) -> List[TripSegment]:
        """
        Returns every TripSegment that is currently active.
        """
        active_trip_segments = []
        for trip_segment in self.trip_segments:
            if trip_segment.isActive(time, delay, precipitation):
                active_trip_segments.append(trip_segment)

        return active_trip_segments

    def isThereTrafficOnTrip(
            self,
            date: datetime,
            delay: timedelta,
            precipitation: timedelta,
            ignore_start_end_date=False
    ) -> bool:
        """
        True there is a Trip on the shape the trip is on, else False

        If ignore_start_end_date is true, ignore the start_date / end_date boundary from GTFS calendar.txt
        """
        if not ignore_start_end_date:
            # return False if the GTFS is not up-to-date
            # start_date as (%Y%m%d) < date < end_date as (%Y%m%d)
            if not (self.date_borders[0] < date < self.date_borders[1]):
                return False

        # first: check time (%H%M%S) interval
        within_trip, in_overtime = self._isTimeWithinTrip(date, delay, precipitation)
        if not within_trip:
            return False

        # then, check if there can be traffic on the given day
        if not self._isTrafficOnDay(date, in_overtime):
            return False

        return True

    def isTripActiveOnDate(self, day: datetime, ignore_start_end_date=False):
        """
        True if
            - The trip is within the start/end dates
            - There is traffic on the given day
        Does not take into account the time (%H:%M:%S), but only the date (%Y/%m/%d).
        """
        if not ignore_start_end_date:
            # return False if the GTFS is not up-to-date
            # start_date as (%Y%m%d) < date < end_date as (%Y%m%d)
            if not (self.date_borders[0] < day < self.date_borders[1]):
                return False

        # Check if there can be traffic on the given day
        return self._isTrafficOnDay(day - timedelta(days=1), overflow=True) \
            or self._isTrafficOnDay(day, overflow=False)

    def isCloseToActiveTripSegment(
            self,
            time: datetime,
            position: Tuple[float, float],
            distance_in_m: float,
            delay: timedelta,
            precipitation: timedelta
    ):
        """
        Assumes that there is currently traffic on the trip.
        True, if the given position is close enough to the active TripSegment.
        """
        active_trip_segments = self._getActiveTripSegments(time, delay, precipitation)

        # determine whether the given position is close to any of the active TripSegments
        for active_segment in active_trip_segments:
            if active_segment.isClose(position, distance_in_m):
                return True

        return False


if __name__ == '__main__':
    b = datetime.today() - timedelta(days=1)
    a = datetime.today()

    print(a < b, b < a)

    print(b - a)

    # p = Point((0, 1))
    p = (0, 1)
    print(LineString([p, p]))
