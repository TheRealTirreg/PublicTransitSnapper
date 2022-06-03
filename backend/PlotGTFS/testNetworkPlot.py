# https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler

x = []
y = []
locations = []

with open("testNetwork.txt") as file:
    start = True
    for i in file:
        if start:
            start = False
            continue
        information = i.rstrip().split(",")
        locations += [(float(information[2]), float(information[1]))]
        x += [float(information[2])]
        y += [float(information[1])]

lim_upper_x = max(x)
lim_lower_x = min(x)
lim_upper_y = max(y)
lim_lower_y = min(y)
padding_x = (lim_upper_x - lim_lower_x) * 0.25
padding_y = (lim_upper_y - lim_lower_y) * 0.25

map = geotiler.Map(extent=(
    lim_lower_x - padding_x, lim_lower_y - padding_y,
    lim_upper_x + padding_x, lim_upper_y + padding_y), zoom=16)
img = geotiler.render_map(map)

fig = plt.figure(figsize=(100, 100))
ax = plt.subplot(111)
ax.imshow(img)
xx, yy = zip(*(map.rev_geocode(point) for point in locations))
ax.scatter(xx, yy, s=5000, c='fuchsia')
plt.axis('off')
plt.savefig('testNetwork.png', bbox_inches='tight', pad_inches=0)
