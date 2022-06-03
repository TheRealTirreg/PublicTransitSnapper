import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';

/// Album contains information on the current route
class Album {
  final String message;
  final List<List<LatLng>> edges;
  final List<LatLng> path;
  final String routeName;
  final String routeType;
  final String routeColor;
  final String nextStop;
  final String routeDest;
  final LatLng location;

  Album({
    required this.message,
    required this.edges,
    required this.path,
    required this.routeName,
    required this.routeType,
    required this.routeColor,
    required this.nextStop,
    required this.routeDest,
    required this.location,
  });

  /// Parse matched edges from json to dart
  factory Album.fromJson(Map<String, dynamic> json, {message = "Nothing to say"}) {
    /*print("Message: $message, edges: ${json['edges']}, path: ${json["path"]}, route name: ${json["route_name"]}, route type: ${json["route_type"]}");*/

    List<List<LatLng>> edges = [];
    // edges example: [[[lat0, lon0], [lat1, lon1]], repeat]
    for (int i = 0; i < json["edges"].length; i++) {
      edges.add([]);
      if (json["edges"][i].isNotEmpty) {
        for (int j = 0; j < 2; j++) {
          edges[i].add(LatLng(json["edges"][i][j][0], json["edges"][i][j][1]));
        }
      }
    }
    // print("Loop-edges: $edges");

    List<LatLng> path = [];
    // path example: [[lat0, lon0], [lat1, lon1], etc.]
    for (int i = 0; i < json["path"].length; i++) {
      if (json["path"].isNotEmpty) {
        path.add(LatLng(json["path"][i][0], json["path"][i][1]));
      }
    }
    // print("Loop-path: $path");
    // print("edges Type: ${edges.runtimeType}");
    // print("Path Type: ${path.runtimeType}");
    // print("LatLng of 'location':");
    // print(LatLng(json["location"][0], json["location"][1]));
    return Album(
      message: message,
      edges: edges,
      path: path,
      routeName: json['route_name'],
      routeType: json['route_type'],
      nextStop: json['next_stop'],
      routeDest: json['route_dest'],
      routeColor: json['route_color'],
      location: LatLng(json["location"][0], json["location"][1]),
    );
  }
}

/// Album for matched edges ("/json")
Future<Album> createAlbum(List<String> coords, String serverAddress, String port) async {
  // incorrect server address
  if (serverAddress == "" || port == "") {
    return Album(
      message: "Server address or port empty",
      edges: [[]],
      path: [],
      routeName: "",
      routeType: "",
      routeColor: "",
      nextStop: "",
      routeDest: "",
      location: LatLng(0, 0),
    );
  }

  print("$serverAddress:$port/json");

  final response = await http.post(
    Uri.parse("http://$serverAddress:$port/json"),
    headers: <String, String> {
      "Content-Type": 'application/json',
    },
    body : jsonEncode(<String, List<String>> {
      'coordinates' : coords,
    }),
  );

  if (response.statusCode == 200) {  // OK
    return Album.fromJson(json.decode(response.body));
  } else {
    return Album(
      message: "Error while fetching data: ${response.statusCode}",
      edges: [[]],
      path: [],
      routeName: "",
      routeType: "",
      routeColor: "",
      nextStop: "",
      routeDest: "",
      location: LatLng(0, 0),
    );
  }
}

/// Album for matched edges ("/json")
Future<Album> fetchAlbum(String serverAddress, String port) async {
  if (serverAddress == "" || port == "") {
    return Album(
        message: "server address or port empty",
        edges: [[]],
        path: [],
        routeName: "",
        routeType: "",
        routeColor: "",
        nextStop: "",
        routeDest: "",
        location: LatLng(0, 0),
    );
  }

  final response = await http.get(Uri.parse("http://$serverAddress:$port/json"));

  if (response.statusCode == 200) {
    return Album.fromJson(json.decode(response.body));
  } else {
    return Album(
      message: "Error while fetching data: ${response.statusCode}",
      edges: [[]],
      path: [],
      routeName: "",
      routeType: "",
      routeColor: "",
      nextStop: "",
      routeDest: "",
      location: LatLng(0, 0),
    );
  }
}


/// ------------------------- change vehicle Album -----------------------------
class ChangeVehicleAlbum {
  final List<List<String>> connections;
  final DateTime timestamp;

  ChangeVehicleAlbum({
    required this.connections,
    required this.timestamp  // holds the sent time from the server for the first trip on the connections list
  });

  factory ChangeVehicleAlbum.fromJson(Map<String, dynamic> json) {
    /// {
    ///   "0": ["3",                # <- route short name
    ///         "Munzinger Straße", # <- destination station name
    ///         "Tram",             # <- vehicle type
    ///         "1648734153",       # <- departure time
    ///         "646363",           # <- color in hex
    ///         "ffffff"],          # <- text color in hex
    ///   "1": ["4",
    ///         "Messe Freiburg",
    ///         "Tram",
    ///         "1645834153",
    ///         "13a538",
    ///         "000000"],
    ///   "length": 2
    /// }
    ///;

    if (json["length"].toInt() == 0) {
      return ChangeVehicleAlbum(connections:[], timestamp: DateTime.fromMillisecondsSinceEpoch(0));
    }

    // create dart compatible version of json
    List<List<String>> newConnections = [];
    DateTime firstDT = DateTime.fromMillisecondsSinceEpoch(json["0"][3]);

    for (int i = 0; i < json["length"].toInt(); i++) {
      List<dynamic> tup = json[i.toString()];
      DateTime dt = DateTime.fromMillisecondsSinceEpoch(tup[3]);
      initializeDateFormatting();
      String d24 = DateFormat("HH:mm").format(dt);
      List<String> newConnectionTup = [tup[0], tup[1], tup[2], d24, tup[4], tup[5]];
      newConnections.add(newConnectionTup);
    }

    return ChangeVehicleAlbum(connections: newConnections, timestamp: firstDT);
  }
}

/// Album for matched edges ("/json")
Future<ChangeVehicleAlbum> createChangeVehicleAlbum(String nextStopName, String userTime, String serverAddress, String port) async {
  if (serverAddress == "" || port == "") {
    print("server address or port empty while trying to fetch pubic transit vehicle connections");
    return ChangeVehicleAlbum(connections:[], timestamp: DateTime.fromMillisecondsSinceEpoch(0));
  }

  final response = await http.post(
    Uri.parse("http://$serverAddress:$port/connections"),
    headers: <String, String> {
      "Content-Type": 'application/json',
    },
    body : jsonEncode(<String, String> {
      'nextStopName' : nextStopName,
      'userTime' : userTime
    }),
  );

  if (response.statusCode == 200) {  // OK
    return ChangeVehicleAlbum.fromJson(json.decode(response.body));
  } else {
    return ChangeVehicleAlbum(connections:[], timestamp: DateTime.fromMillisecondsSinceEpoch(0));
  }
}
