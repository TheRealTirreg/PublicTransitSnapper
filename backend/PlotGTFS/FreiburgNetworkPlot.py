# import networkx as nx
import peartree as pt
import matplotlib.pyplot as plt
# import geopandas as gpd
# from shapely.geometry import LineString
"""
graph = nx.DiGraph()
graph.add_edges_from([("root", "a"), ("a", "b"),
("a", "e"), ("b" ,"c"), ("b", "d"), ("d", "e")])
print(graph.nodes())
print(nx.shortest_path(graph, "root", "e"))
print(nx.is_directed(graph))
print(nx.is_directed_acyclic_graph(graph))
print(list(nx.topological_sort(graph)))
print(graph.in_edges("e"))
print(graph.out_degree("root"))
"""
path = 'vag_shapes.zip'
feed = pt.get_representative_feed(path)

start = 0  # 7*60*60
end = 24 * 60 * 60  # 10*60*60

G = pt.load_feed_as_graph(feed, start, end, use_multiprocessing=True)
"""
nx.draw(G, node_size = 1, width = 1)
ax = plt.gca()
plt.gca().invert_yaxis()
plt.gca().invert_xaxis()
ax.margins(0.20)
plt.axis("off")
plt.savefig('asdf.png', dpi = 1200)
"""
pt.generate_plot(G)
plt.savefig('FreiburgNetwork.png', dpi=300)
"""
http://kuanbutts.com/2020/08/25/simplified-map-matching/
rows = []
for node_from, node_to, edge in G.edges(data=True):
    if "geometry" in edge.keys():
        geometry = edge["geometry"]
    else:
        f = G.nodes[node_from]
        t = G.nodes[node_to]
        geometry = LineString([[f["x"], f["y"]], [t["x"], t["y"]]])
    base = {
        "from": node_from,
        "to": node_to,
        "id": edge["osmid"],
        "length": edge["length"],  # meters
        "geometry": geometry,
    }
    rows.append(base)
"""
