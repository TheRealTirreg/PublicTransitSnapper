# https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler
import pandas as pd

tripId = "169.T2.13-15-I-j22-1.5.H"


def find_shape_of_trip(trip_id: str) -> str:
    """
    Returns the shape_id of a given trip_id
    """
    df = pd.read_csv("../GTFS/trips.txt", usecols=[2, 7])  # trip_id, shape_id
    return str(df[df["trip_id"] == trip_id]["shape_id"].iloc[0])


shapeId = find_shape_of_trip(tripId)

x = []
y = []
locations = []
stops = []

with open("../GTFS/shapes.txt") as file:
    for i in file:
        information = i.rstrip().split(",")
        if information[0] == shapeId:
            locations += [(float(information[2]), float(information[1]))]
            x += [float(information[2])]
            y += [float(information[1])]

with open("../GTFS/stop_times.txt") as stoptimes:
    for line in stoptimes:
        information = line.rstrip().split(",")
        if information[0] == tripId:
            stops += [information[3]]

print(f"stops: {stops}")

stop_coords = []

counter = 0
for stop in stops:
    df = pd.read_csv("../GTFS/stops.txt")
    line = df[df["stop_id"] == stop]
    stop_coords += [(float(line["stop_lon"].values[0]), float(line["stop_lat"].values[0]))]

print(f"stop_coords: {stop_coords}")

limUpperX = max(x)
limLowerX = min(x)
limUpperY = max(y)
limLowerY = min(y)
paddingX = (limUpperX - limLowerX) * 0.25
paddingY = (limUpperY - limLowerY) * 0.25

map = geotiler.Map(extent=(limLowerX - paddingX, limLowerY - paddingY, limUpperX + paddingX, limUpperY + paddingY), zoom=16)
img = geotiler.render_map(map)

fig = plt.figure(figsize=(100, 100))
ax = plt.subplot(111)
ax.imshow(img)

xxx, yyy = zip(*(map.rev_geocode(point) for point in stop_coords))
ax.scatter(xxx, yyy, s=100, c='b')

xx, yy = zip(*(map.rev_geocode(point) for point in locations))
ax.scatter(xx, yy, s=50, c='r')


plt.axis('off')
plt.savefig('shapewithstops1.png', bbox_inches='tight', pad_inches=0)
