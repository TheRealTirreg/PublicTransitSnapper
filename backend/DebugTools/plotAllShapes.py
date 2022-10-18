import matplotlib.pyplot as plt
import matplotlib as mpl
import geotiler
import pandas as pd


mpl.rcParams['agg.path.chunksize'] = 10000

file_name = "shapes_Freetown.png"
folder = r"../GTFS/Freiburg/VAG/gtfs-out"
# folder = r"../GTFS/Freiburg/VAG/gtfs-out"

# fix boundaries of map
limUpperX = 7.9171163513331  # max(x)
limLowerX = 7.759232104829365   # min(x)
limUpperY = 48.03258029439869  # max(y)
limLowerY = 47.96296726295266  # min(y)

x = []
y = []
polylines = []

df = pd.read_csv(folder + r"/shapes.txt", header=0)
num_rows = len(df)
current_shape_id = ""
current_shape_counter = -1
for i, row in df.iterrows():
    shape_id, lat, lon = row["shape_id"], float(row["shape_pt_lat"]), float(row["shape_pt_lon"])

    # filter points that are not within the map boundaries
    if not limLowerY < lat < limUpperY or not limLowerX < lon < limUpperX:
        continue

    if shape_id != current_shape_id:  # new shape
        polylines.append([(lon, lat)])
        current_shape_id = shape_id
        current_shape_counter += 1
    else:  # same shape
        polylines[current_shape_counter].append((lon, lat))  # geotiler uses (lon, lat), not (lat, lon)

    x.append(lon)
    y.append(lat)

    if i % 1000 == 0:
        print(f"{round(i / num_rows * 100, 2)}%")
print("100.0%")

# create map
print("Creating map...")
map_data = geotiler.Map(
    # extent=(limLowerX - paddingX, limLowerY - paddingY, limUpperX + paddingX, limUpperY + paddingY), zoom=16)
    extent=(limLowerX - 0.1, limLowerY - 0.1, limUpperX + 0.1, limUpperY + 0.1), zoom=14)
img = geotiler.render_map(map_data)

# plot image
print("Creating image...")
fig = plt.figure(figsize=(100, 100))
ax = plt.subplot(111)
ax.imshow(img)

# map gps points to image
print("Mapping GPS points to image...")
num_polylines = len(polylines)
for i, polyline in enumerate(polylines):
    image_points_lon = []
    image_points_lat = []
    for point in polyline:
        image_point = map_data.rev_geocode(point)
        image_points_lon.append(image_point[0])
        image_points_lat.append(image_point[1])
    ax.plot(image_points_lon, image_points_lat, 'r-', linewidth=5)  # draw polylines

    if i % 500 == 0:
        print(f"{round(i / num_polylines * 100, 2)}%")
print("100.0%")

print("Saving image...")
plt.axis('off')
plt.savefig(file_name, bbox_inches='tight', pad_inches=0)

print("Image saved.")
