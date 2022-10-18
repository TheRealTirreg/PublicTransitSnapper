from csv import DictReader


def map_route_id_to_route_type(path):
    with open(path + "routes.txt", "r") as f:
        reader = DictReader(f)
        return {row["route_id"]: row["route_type"] for row in reader}


def count_route_types(path):
    with open(path + "trips.txt", "r") as f:
        reader = DictReader(f)
        route_id_to_route_type = map_route_id_to_route_type(path)
        route_types = [route_id_to_route_type[row["route_id"]] for row in reader]
        return {route_type: route_types.count(route_type) for route_type in set(route_types)}


if __name__ == '__main__':
    print(count_route_types("../GTFS/Schweiz/SBB/gtfs-out/"))
