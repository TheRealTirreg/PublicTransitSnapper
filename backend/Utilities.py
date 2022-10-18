from datetime import datetime, timedelta
from shapely.geometry import LineString


def splitLineString(line):
    """
    Takes in a LineString and splits it in its line segments:

    line = LineString([(0, 0), (1, 1), (2, 2)])

    line_segments = segments(line)
    for segment in line_segments:
        print(segment)
    >> LINESTRING (0 0, 1 1)
    >> LINESTRING (1 1, 2 2)

    Taken from https://stackoverflow.com/questions/62053253/how-to-split-a-linestring-to-segments
    """
    return list(map(LineString, zip(line[:-1], line[1:])))


def convertGtfsDateToDatetime(s: str) -> (datetime, bool):
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


if __name__ == '__main__':
    line = LineString([(0, 0), (1, 1), (2, 2)])

    line_segments = splitLineString(line)
    for segment in line_segments:
        print(segment)
    # LINESTRING (0 0, 1 1)
    # LINESTRING (1 1, 2 2)

    from shapely.strtree import STRtree
    from shapely.geometry import Point
    tree = STRtree(line_segments)
    print(tree.nearest(Point(-1, -1)))
