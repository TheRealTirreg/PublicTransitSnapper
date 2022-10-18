# https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler


file_name = "plot_shape.png"
shapeId = "shp_3_23"
folder = "../GTFS/Freiburg/VAG/gtfs-out"

x = []
y = []
locations = []

with open(folder + "/shapes.txt") as file:
    for i in file:
        information = i.rstrip().split(",")
        if information[0] == shapeId:
            locations += [(float(information[2]), float(information[1]))]
            x += [float(information[2])]
            y += [float(information[1])]

limUpperX = max(x)
limLowerX = min(x)
limUpperY = max(y)
limLowerY = min(y)
paddingX = (limUpperX - limLowerX) * 0.25
paddingY = (limUpperY - limLowerY) * 0.25

map_data = geotiler.Map(
    extent=(limLowerX - paddingX, limLowerY - paddingY, limUpperX + paddingX, limUpperY + paddingY), zoom=16)
img = geotiler.render_map(map_data)

fig = plt.figure(figsize=(100, 100))
ax = plt.subplot(111)
ax.imshow(img)

xx, yy = zip(*(map_data.rev_geocode(point) for point in locations))
ax.plot(xx, yy, 'r-')

plt.axis('off')
plt.savefig(file_name, bbox_inches='tight', pad_inches=0)
