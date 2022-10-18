/// Copyright 2022
/// Bachelor's thesis by Gerrit Freiwald and Robin Wu

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';
import 'package:syncfusion_flutter_maps/maps.dart';
import 'chat_message.dart';
import 'utilities.dart';

/// Album contains information on the current route
class Album {
  final String message;
  final String routeName;
  final String routeType;
  final String routeColor;
  final String nextStop;
  final String routeDest;
  final LatLng location;
  final String tripId;
  final String shapeId;

  Album({
    required this.message,
    required this.routeName,
    required this.routeType,
    required this.routeColor,
    required this.nextStop,
    required this.routeDest,
    required this.location,
    required this.tripId,
    required this.shapeId,
  });

  /// Parse matched edges from json to dart
  factory Album.fromJson(Map<String, dynamic> json,
      {message = "Nothing to say"}) {
    print("nothing to say: ${json['route_name']}");
    if (json["route_name"] == "") {
      print("Message: No matching path found, location: ${json['location']}, "
          "route name: ${json["route_name"]}, "
          "route type: ${json["route_type"]}");

      return Album(
        message: "No matching path found",
        routeName: "",
        routeType: "",
        routeColor: "",
        nextStop: "",
        routeDest: "",
        location: LatLng(0, 0),
        tripId: "",
        shapeId: ""
      );
    }

    return Album(
      message: message,
      routeName: json['route_name'],
      routeType: json['route_type'],
      nextStop: json['next_stop'],
      routeDest: json['route_dest'],
      routeColor: json['route_color'],
      location: LatLng(
          json["location"][0].toDouble(),
          json["location"][1].toDouble()
      ),
      tripId: json['trip_id'],
      shapeId: json['shape_id'],
    );
  }
}

/// Album for matched edges ("/map-match")
Future<Album> createAlbum(List<String> coords, String tripId, String shapeId,
    String serverAddress, String port) async {
  /// creates an album after sending and receiving
  /// information related to the public transit vehicle matching
  // incorrect server address
  if (serverAddress == "" || port == "") {
    return Album(
      message: "Server address or port empty",
      routeName: "",
      routeType: "",
      routeColor: "",
      nextStop: "",
      routeDest: "",
      location: LatLng(0, 0),
      tripId: "",
      shapeId: "",
    );
  }

  final response = await http.post(
    Uri.parse(getUrl("map-match", serverAddress, port)),
    headers: <String, String> {
      "Content-Type": 'application/json',
    },
    body: jsonEncode(<String, dynamic>{
      'coordinates': coords,
      'trip_id': tripId,
      'shape_id': shapeId,
    }),
  );

  if (response.statusCode == 200) {  // OK
    return Album.fromJson(json.decode(response.body));
  } else {
    return Album(
      message: "Error while fetching data: ${response.statusCode}",
      routeName: "",
      routeType: "",
      routeColor: "",
      nextStop: "",
      routeDest: "",
      location: LatLng(0, 0),
      tripId: "",
      shapeId: "",
    );
  }
}


/// ------------------------- change vehicle Album -----------------------------
class ChangeVehicleAlbum {
  final List<List<String>> connections;
  final DateTime timestamp;

  ChangeVehicleAlbum({
    required this.connections,
    // timestamp holds the sent time from the server for the first trip
    // on the connections list
    required this.timestamp
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
      return ChangeVehicleAlbum(
          connections:[],
          timestamp: DateTime.fromMillisecondsSinceEpoch(0)
      );
    }

    // create dart compatible version of json
    List<List<String>> newConnections = [];
    DateTime firstDT = DateTime.fromMillisecondsSinceEpoch(json["0"][3]);

    for (int i = 0; i < json["length"].toInt(); i++) {
      List<dynamic> tup = json[i.toString()];
      DateTime dt = DateTime.fromMillisecondsSinceEpoch(tup[3]);
      initializeDateFormatting();
      String d24 = DateFormat("HH:mm").format(dt);
      List<String> newConnectionTup = [
        tup[0], tup[1], tup[2], d24, tup[4], tup[5]
      ];
      newConnections.add(newConnectionTup);
    }

    return ChangeVehicleAlbum(connections: newConnections, timestamp: firstDT);
  }
}

Future<ChangeVehicleAlbum> createChangeVehicleAlbum(
    String nextStopName,
    String userTime,
    String tripId,
    String serverAddress,
    String port) async {
  /// creates an album after sending and receiving
  /// information on the connections at the next stop
  if (serverAddress == "" || port == "") {
    print("server address or port empty while trying to "
        "fetch pubic transit vehicle connections");
    return ChangeVehicleAlbum(
        connections:[],
        timestamp: DateTime.fromMillisecondsSinceEpoch(0)
    );
  }

  if (tripId.isEmpty) {
    return ChangeVehicleAlbum(
        connections:[],
        timestamp: DateTime.fromMillisecondsSinceEpoch(0)
    );
  }

  final response = await http.post(
    Uri.parse(getUrl("connections", serverAddress, port)),
    headers: <String, String> {
      "Content-Type": 'application/json',
    },
    body: jsonEncode(<String, dynamic> {
      'next_stop_name': nextStopName,
      'user_time': userTime,
      'trip_id': tripId,
    }),
  );

  if (response.statusCode == 200) {  // OK
    return ChangeVehicleAlbum.fromJson(json.decode(response.body));
  } else {
    return ChangeVehicleAlbum(
        connections:[],
        timestamp: DateTime.fromMillisecondsSinceEpoch(0)
    );
  }
}


/// ------------------------------ Shape Album ---------------------------------
class ShapeAlbum {
  final List<MapLatLng> shapePolyline;
  final List<MapLatLng> stops;

  ShapeAlbum({
    required this.shapePolyline,
    required this.stops,
  });

  factory ShapeAlbum.fromJson(Map<String, dynamic> json) {
    /// json: [(lat0, lon0), (lat1, lon1), ...]

    if (json["polyline"].length < 2) {
      return ShapeAlbum(shapePolyline: [], stops: []);
    }

    List<MapLatLng> polyline = [MapLatLng(
        json["polyline"][0][0], json["polyline"][0][1]
    )];
    for (int i = 0; i < json["polyline"].length; i++) {
      polyline.add(MapLatLng(json["polyline"][i][0], json["polyline"][i][1]));
    }

    List<MapLatLng> stops = [];
    for (int i = 0; i < json["stops"].length; i++) {
      stops.add(MapLatLng(json["stops"][i][0], json["stops"][i][1]));
    }

    return ShapeAlbum(shapePolyline: polyline, stops: stops);
  }
}

Future<ShapeAlbum> createShapeAlbum(
    String shapeId,
    String tripId,
    String serverAddress,
    String port) async {
  /// creates an album after sending and receiving
  /// information on the shape of the current trip
  if (serverAddress == "" || port == "") {
    print("server address or port empty while trying to "
        "fetch a shape polyline");
    return ShapeAlbum(shapePolyline: [], stops: []);
  }

  if (shapeId.isEmpty || tripId.isEmpty) {
    return ShapeAlbum(shapePolyline: [], stops: []);
  }

  final response = await http.post(
    Uri.parse(getUrl("shapes", serverAddress, port)),
    headers: <String, String> {
      "Content-Type": 'application/json',
    },
    body: jsonEncode(<String, dynamic> {
      'shape_id' : shapeId,
      'trip_id' : tripId,
    }),
  );

  if (response.statusCode == 200) {  // OK
    return ShapeAlbum.fromJson(json.decode(response.body));
  } else {
    return ShapeAlbum(shapePolyline: [], stops: []);
  }
}


/// ------------------------------- chat Album ---------------------------------
class ChatAlbum {
  // one ChatMessage contains UserId, UserName, MessageText, timeSent
  final int userId;
  final double serverStartTimestamp;
  final List<ChatMessage> messages;

  ChatAlbum({
    required this.userId,
    required this.serverStartTimestamp,
    required this.messages,
  });

  factory ChatAlbum.fromJson(Map<String, dynamic> json) {
    // convert strings to ChatMessage objects
    List<ChatMessage> receivedMessages = [];
    for (int i = 0; i < json["messages"].length; i++) {
      receivedMessages.add(
        // json['messages'] = [
        //    ['user_id', 'user_name', 'message content', '22:42h']
        // ]
        ChatMessage(
            userId: json['messages'][i][0],
            userName: json['messages'][i][1],
            messageContent: json['messages'][i][2],
            timeSent: json['messages'][i][3]
        )
      );
    }

    return ChatAlbum(
      userId: json['user_id'],
      serverStartTimestamp: json['server_start_timestamp'],
      messages: receivedMessages,
    );
  }
}

Future<ChatAlbum> createChatAlbum(
    bool justFetchInfo,
    int userId,
    double serverStartTimestamp,
    String tripId,
    String serverAddress,
    String port,
    {String userName = "", String message = "", String timeSent = ""}) async {
  /// creates a ChatAlbum after sending and receiving
  /// information to and from the backend
  if (serverAddress == "" || port == "") {
    print("server address or port empty while trying to chat messages");
    return ChatAlbum(userId: 0, serverStartTimestamp: 0,  messages: []);
  }

  if (justFetchInfo) {
    print("fetching info: userId: $userId, serverStartTimestamp: "
        "$serverStartTimestamp, tripId: $tripId");
  } else {
    print("sending message: userId: $userId, serverStartTimestamp: "
        "$serverStartTimestamp, tripId: $tripId, userName: $userName, message: "
        "$message, timeSent: $timeSent");
  }

  // just fetch new chat messages without sending one
  http.Response response;
  if (justFetchInfo) {
    response = await http.post(
      Uri.parse(getUrl("chat", serverAddress, port)),
      headers: <String, String>{
        "Content-Type": 'application/json',
      },
      body: jsonEncode(<String, dynamic>{
        'just_fetch': true,
        'user_id': userId,
        'server_start_timestamp': serverStartTimestamp,
        'trip_id': tripId,
      }),
    );
  } else {  // actually sending a message
    response = await http.post(
      Uri.parse(getUrl("chat", serverAddress, port)),
      headers: <String, String> {
        "Content-Type": 'application/json',
      },
      body: jsonEncode(<String, dynamic> {
        'just_fetch': false,
        'user_id': userId,
        'server_start_timestamp': serverStartTimestamp,
        'user_name': userName,
        'message': message,
        'user_time': timeSent,
        'trip_id': tripId,
      }),
    );
  }

  if (response.statusCode == 200) {  // OK
    return ChatAlbum.fromJson(json.decode(response.body));
  } else {
    print("Error while trying to fetch chat messages: ${response.statusCode}");
    return ChatAlbum(userId: 0, serverStartTimestamp: 0, messages: []);
  }
}
