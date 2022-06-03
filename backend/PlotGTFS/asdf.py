#https://stackoverflow.com/questions/28476117/easy-openstreetmap-tile-displaying-for-python
import matplotlib.pyplot as plt
import geotiler

x = []
y = []
locations = []

with open("line4.bak") as file:
    for i in file:
        information = i.rstrip().split(",")
        locations += [(float(information[3]), float(information[2]))]
        x += [float(information[3])]
        y += [float(information[2])]

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
xx, yy = zip(*(map.rev_geocode(point) for point in locations))
ax.scatter(xx, yy, s = 50, c = 'r')
plt.axis('off')
plt.savefig('asdf.png', bbox_inches='tight', pad_inches=0)
