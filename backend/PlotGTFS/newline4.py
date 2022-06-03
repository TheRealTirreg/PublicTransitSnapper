#https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler

x = []
y = []
locations = []
tripId = "10.T2.11-4-I-j21-1.1.R"
stops = []
shapedId = ""

with open("line4") as file:
    for i in file:
        information = i.rstrip().split(",")
        locations += [(float(information[2]), float(information[1]))]
        x += [float(information[2])]
        y += [float(information[1])]
        shapeId = information[0]

with open("../GTFS/stop_times.txt") as stoptimes:
    for line in stoptimes:
        information = line.rstrip().split(",")
        if information[0] == tripId:
            stops += [information[3]]

print(f"stops: {stops}")

stop_coords = []

counter = 0
for stop in stops:
    with open("../GTFS/stops.txt") as stopsfile:
        for line in stopsfile:
            counter += 1
            information = line.rstrip().split(",")
            if information[0] == stop:
                print(information)
                stop_coords += [(float(information[6]), float(information[5]))]
                break
        stopsfile.close()

print(counter)
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
ax.scatter(xxx, yyy, s = 100, c = 'b')

xx, yy = zip(*(map.rev_geocode(point) for point in locations))
ax.scatter(xx, yy, s = 50, c = 'r')


plt.axis('off')
plt.savefig('newline4.png', bbox_inches='tight', pad_inches=0)
