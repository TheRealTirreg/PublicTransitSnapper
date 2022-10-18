#https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler
file_name = "plot_points_3.png"
points = eval(input("List of points: "))

x = []
y = []
locations = []

for lat, lon in points:
    locations.append((lon, lat))
    x.append(lon)
    y.append(lat)

limUpperX = max(x)
limLowerX = min(x)
limUpperY = max(y)
limLowerY = min(y)
paddingX = (limUpperX - limLowerX) * 0.25
paddingY = (limUpperY - limLowerY) * 0.25

print(limUpperY, limUpperX, limLowerY, limLowerX)

map_data = geotiler.Map(
    extent=(limLowerX - paddingX, limLowerY - paddingY, limUpperX + paddingX, limUpperY + paddingY), zoom=19)
img = geotiler.render_map(map_data)

fig = plt.figure(figsize=(100, 100))
ax = plt.subplot(111)
ax.imshow(img)

image_points_lon = []
image_points_lat = []
for point in points:
    lat, lon = point
    image_point = map_data.rev_geocode((lon, lat))
    image_points_lon.append(image_point[0])
    image_points_lat.append(image_point[1])
print(image_points_lon, "\n", image_points_lat)
ax.plot(image_points_lon, image_points_lat, 'r-', linewidth=20)  # draw polylines

# xx, yy = zip(*(map_data.rev_geocode(point) for point in locations))

# ax.scatter(xx, yy, s=50, c='r')
plt.axis('off')
plt.savefig(file_name, bbox_inches='tight', pad_inches=0)
