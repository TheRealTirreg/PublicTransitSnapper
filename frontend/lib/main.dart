/// Copyright 2022
/// Bachelor's thesis by Gerrit Freiwald and Robin Wu

import 'dart:async';
import 'dart:core';
import 'dart:math';
import 'package:flutter/services.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:tuple/tuple.dart';
import 'package:flutter/material.dart';
import 'package:location/location.dart';
import 'package:latlong2/latlong.dart';
import 'package:syncfusion_flutter_maps/maps.dart';
import 'package:marquee/marquee.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'connect_to_internet.dart' as cti;
import 'utilities.dart' as utils;
import 'sf_polyline.dart';
import 'custom_icons.dart';
import 'chat_message.dart';
import 'package:yaml/yaml.dart';

void main() async {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  // This widget is the root of our application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PublicTransitSnapper',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const MyHomePage(title: 'PublicTransitSnapper'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({Key? key, required this.title}) : super(key: key);

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  // header title
  late String _title;

  // load from config.yml
  String _ymlServerAddress = "";
  String _ymlServerPort = "";
  String _ymlProxyAddress = "";
  String _ymlProxyPort = "";

  // server address
  String _serverAddress = "";
  String _port = "";

  // start popup
  bool _launchPopUp = true;
  final Future<SharedPreferences> _prefs = SharedPreferences.getInstance();
  final ScrollController _serverConfigurationsScrollController =
    ScrollController();
  final GlobalKey<FormState> _userNameFormKey = GlobalKey<FormState>();

  // chat
  bool _showChat = false;
  int _userId = 0;
  double _serverStartTimestamp = 0;
  String _tripId = "";
  String _userName = "Max Mustermann";
  List<ChatMessage> _messages = [];

  // control chat messages
  TextEditingController sendMessageController = TextEditingController();

  // send back to backend
  String _shapeId = "";

  // location
  bool _hasReceivedGPSPoints = false;
  Location location = Location();
  final int locationUpdateInterval = 10000;  // update location every 10 seconds
  bool locationPermission = false;
  final List<Tuple2<LatLng, int>> _lastNCoordinates = <Tuple2<LatLng, int>>[];
  LatLng positionMarkerPosition = LatLng(0, 0);

  // navigate between widgets
  int _bottomNavigationBarCurrentIndex = 0;

  // Timer to fetch data from backend every minute
  Timer? timer;
  Timer? chatTimer;

  // Albums to connect to the backend
  Future<cti.Album>? _futureAlbum;
  Future<cti.ChangeVehicleAlbum>? _futureChangeVehicleAlbum;
  Future<cti.ChatAlbum>? _futureChatAlbum;
  Future<cti.ShapeAlbum>? _futureShapeAlbum;
  bool _updateTransferOptionsList = false;

  // sfMaps
  List<PolylineModel> polylines = [];
  List<MapMarker> mapMarkers = [];
  List<int> mapMarkerIndices = [];
  late MapShapeSource dataSource;
  late MapTileLayerController mapController;
  MapZoomPanBehavior zoomPanBehavior = MapZoomPanBehavior(
      zoomLevel: 12,
      focalLatLng: const MapLatLng(0, 0),
      minZoomLevel: 5,  // zoom out
      maxZoomLevel: 18,  // zoom in
      enableDoubleTapZooming: true,
      enableMouseWheelZooming: true,
      showToolbar: true,
      toolbarSettings: const MapToolbarSettings(
        position: MapToolbarPosition.topRight,
        iconColor: Colors.white,
        itemBackgroundColor: Colors.green,
        itemHoverColor: Colors.lightGreen,
      )
  );
  late MapLatLngBounds _zoomBounds;
  final double lineThickness = 4.0;
  bool lockCamera = false;
  bool drawRedLine = false;

  // route information
  String nextStop = "";
  String routeName = "";
  String routeType = "";
  String routeDest = "";
  String routeColor = "";
  List<List<String>> connections = [];
  DateTime connectionsFirstDepartureTimeDatetime =
    DateTime.fromMillisecondsSinceEpoch(0);
  bool isCurrentlyMatching = false;

  // ============================ init map =====================================
  void initMap() {
    print("Initializing map");
    // set true once the first gps point has been transmitted
    _hasReceivedGPSPoints = true;
    mapController = MapTileLayerController();
    zoomPanBehavior = MapZoomPanBehavior(
        zoomLevel: 12,
        focalLatLng: utils.convertLatLngToMapLatLng(
            _lastNCoordinates.last.item1),
        minZoomLevel: 5,  // zoom out
        maxZoomLevel: 18,  // zoom in
        enableDoubleTapZooming: true,
        enableMouseWheelZooming: true,
        showToolbar: true,
        toolbarSettings: const MapToolbarSettings(
          position: MapToolbarPosition.topRight,
          iconColor: Colors.white,
          itemBackgroundColor: Colors.green,
          itemHoverColor: Colors.lightGreen,
        )
    );
    _zoomBounds = MapLatLngBounds(
        utils.convertLatLngToMapLatLng(LatLng(
            _lastNCoordinates.last.item1.latitude + 0.05,
            _lastNCoordinates.last.item1.longitude - 0.05
        )),
        utils.convertLatLngToMapLatLng(LatLng(
            _lastNCoordinates.last.item1.latitude - 0.05,
            _lastNCoordinates.last.item1.longitude + 0.05
        ))
    );
  }

  // ============================ load config ==================================
  Future<void> getConfig() async {
    print("Getting config");

    // try loading the config
    try {
      final yamlString = await rootBundle.loadString('config.yml');
      final yaml = loadYaml(yamlString);
      _ymlServerAddress = yaml['SERVER_ADDRESS'].toString();
      _ymlServerPort = yaml['SERVER_PORT'].toString();
      _ymlProxyAddress = yaml['PROXY_ADDRESS'].toString();
      _ymlProxyPort = yaml['PROXY_PORT'].toString();
    } catch (_) {
      // if cannot be loaded, do nothing
      // it can still be typed into the boxes
    }
  }

  // =========================== init state ====================================
  @override
  void initState() {
    super.initState();

    // load config.yml
    getConfig();

    // get user_id for chatting
    loadUserId();

    // set default title
    _title = "Current vehicle";

    // enable location permission
    getLocationPermission();

    // try to collect data from the internet
    _futureAlbum = cti.createAlbum(
        [], _tripId, _shapeId, _serverAddress, _port);
    _futureChangeVehicleAlbum = cti.createChangeVehicleAlbum(
        "", "", "", _serverAddress, _port);
    _futureShapeAlbum = cti.createShapeAlbum(
        "", "", _serverAddress, _port);
    _futureChatAlbum = cti.createChatAlbum(
        true, _userId, _serverStartTimestamp, _tripId, _serverAddress, _port);

    // location settings. distanceFilter:
    // only updates location if minimum displacement of n=15 meters
    location.changeSettings(
        interval: locationUpdateInterval,
        accuracy: LocationAccuracy.high,
        distanceFilter: 15
    );

    // initialize _lastCoordinates
    _lastNCoordinates.add(Tuple2(LatLng(0, 0), 0));

    // sfMaps => polylines now has two entries
    // add the red line (own GPS points)
    polylines.add(PolylineModel(
        [const MapLatLng(0, 0)], Colors.red, lineThickness)
    );
    // add the purple line (own GPS points)
    polylines.add(PolylineModel(
        [const MapLatLng(0, 0)], Colors.purple, lineThickness)
    );

    // fetch changeVehicleAlbum every minute
    timer = Timer.periodic(const Duration(minutes: 1), (Timer t) {
      _futureChangeVehicleAlbum = cti.createChangeVehicleAlbum(
          nextStop,
          DateTime.now().millisecondsSinceEpoch.toString(),
          _tripId,
          _serverAddress,
          _port
      );

      if (mounted) setState(() {});
    });

    // fetch chat messages every 10 seconds
    // first starts after the seconds have expired
    chatTimer = Timer.periodic(
        const Duration(seconds: 10), (Timer t) {
      // just ask the backend if there are any new messages
      // (without sending a new message)
      _futureChatAlbum = cti.createChatAlbum(
          true, _userId, _serverStartTimestamp, _tripId, _serverAddress, _port);

      if (mounted) setState(() {});
    });

    // create location listener
    location.onLocationChanged.listen((LocationData currentLocation) {
      // if the position has changed, add new point to _lastNCoordinates and
      // polylines[0] (<= contains the red line (connected GPS points))
      if (currentLocation.latitude! != _lastNCoordinates.last.item1.latitude ||
          currentLocation.longitude! != _lastNCoordinates.last.item1.longitude){
        _lastNCoordinates.add(Tuple2(
            LatLng(currentLocation.latitude!, currentLocation.longitude!),
            currentLocation.time!.toInt()
        ));
        polylines[0].addPoint(MapLatLng(
            currentLocation.latitude!, currentLocation.longitude!));

        // send last 10 coordinates to backend
        List<String> lastTenGpsPoints = [];
        int lstlen = _lastNCoordinates.length;
        int delimiter = min(lstlen, 10);
        for (int i = 0; i < delimiter; i++) {
          double lat =
              _lastNCoordinates[lstlen - delimiter + i].item1.latitude;
          double lon =
              _lastNCoordinates[lstlen - delimiter + i].item1.longitude;
          int tim =
              _lastNCoordinates[lstlen - delimiter + i].item2;

          lastTenGpsPoints.add("$lat, $lon, $tim");
        }

        _futureAlbum = cti.createAlbum(
            lastTenGpsPoints, _tripId, _shapeId, _serverAddress, _port);
      }

      // initialize map once the first GPS point has been received
      if (!_hasReceivedGPSPoints) {
        initMap();
        _lastNCoordinates.removeAt(0);
        polylines[0].removeAtIndex(0);
      }

      setState(() {});
    });
  }

  // ========================== location permission ============================
  void getLocationPermission() async {
    // checks if location service is available,
    // then asks user for permission if needed
    bool serviceEnabled = await location.serviceEnabled();

    if (!serviceEnabled) {
      serviceEnabled = await location.requestService();

      if (!serviceEnabled) {
        locationPermission = false;
        return;  // service not enabled -> abort mission
      }
    }

    PermissionStatus hasPermission = await location.hasPermission();
    if (hasPermission == PermissionStatus.deniedForever) {
      print("Cannot get location permission. Try running the frontend"
          " in a secure environment (https)");
    }

    if (hasPermission == PermissionStatus.denied) {
      hasPermission = await location.requestPermission();

      if (hasPermission == PermissionStatus.granted) {
        locationPermission = true;
      } else {
        locationPermission = false;
      }
    } else {
      locationPermission = true;
    }
  }

  // ======================= server address query popup ========================
  Future<void> saveServerAddressAndPort(
      List<String> lastServerAddresses,
      List<String> lastPorts,
      SharedPreferences prefs) async {
    /// Storage location by platform
    /// Platform	  Location
    /// Android	    SharedPreferences
    /// iOS	        NSUserDefaults
    /// Linux	      In the XDG_DATA_HOME directory
    /// macOS	      NSUserDefaults
    /// Web	        LocalStorage
    /// Windows	    In the roaming AppData directory
    if (lastServerAddresses.contains(_serverAddress) &&
        _serverAddress.isNotEmpty && _port.isNotEmpty) {
      int idx = lastServerAddresses.indexOf(_serverAddress);
      lastServerAddresses.removeAt(idx);
      lastPorts.removeAt(idx);
    } else if (lastServerAddresses.length >= 3) {
      lastServerAddresses.removeAt(lastServerAddresses.length - 1);
      lastPorts.removeAt(lastPorts.length - 1);
    }
    lastServerAddresses.insert(0, _serverAddress);
    lastPorts.insert(0, _port);

    await prefs.setStringList("lastServerAddresses", lastServerAddresses);
    await prefs.setStringList("lastPorts", lastPorts);

    print("saved server address and port for next reboot");
  }

  Future<void> showServerConfigurationsQueryDialog() async {
    /// ask the user for the server address and the port
    /// If no userName has been given yet, also ask for the userName.
    // obtain information on recently used server configurations
    final SharedPreferences prefs = await _prefs;
    List<String> lastServerAddresses = prefs.getStringList(
        "lastServerAddresses") ?? [];
    List<String> lastPorts = prefs.getStringList("lastPorts") ?? [];


    // get userName if there is one already
    String userName = prefs.getString("userName") ?? "";

    // create the TextFormField for the userName
    TextEditingController userNameController = TextEditingController();
    if (userName.isNotEmpty) {
      userNameController.text = userName;
    }
    TextFormField userNameInputField =  TextFormField(
      controller: userNameController,
      decoration: const InputDecoration(hintText: "chat user name"),
      validator: (String? value) {
        return (value == null ||value.isEmpty) ?'Please enter a user name':null;
      },
    );

    print("addresses: $lastServerAddresses\nPorts: $lastPorts");

    // only show at most three server addresses
    if (lastServerAddresses.length >= 3) {
      // lastServerAddresses and lastPorts
      // should always have the same length here
      lastServerAddresses = lastServerAddresses.sublist(0, 3);
      lastPorts = lastPorts.sublist(0, 3);
    }

    // pre-set the text of the serverAddress
    // field and the port field if possible
    TextEditingController serverAddressController = TextEditingController();
    TextEditingController portController = TextEditingController();
    if (lastServerAddresses.isNotEmpty) {
      serverAddressController.text = lastServerAddresses.first;
    }
    if (lastPorts.isNotEmpty) {
      portController.text = lastPorts.first;
    }

    showDialog(
      context: context,
      builder: (_) {
        return AlertDialog(
          title: const Text("Connect to the server"),
          content: SizedBox(
            height: 300,
            width: 300,
            child: ListView(
              shrinkWrap: true,
              children: [
                Form(
                  key: _userNameFormKey,
                  child: userNameInputField,
                ),
                const Padding(padding: EdgeInsets.all(12.0)),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          serverAddressController.text = _ymlServerAddress;
                          portController.text = _ymlServerPort;

                          setState(() {});
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.cyan
                        ),
                        child: const Text("SERVER"),
                      ),
                    ),
                    const Padding(padding: EdgeInsets.all(6.0)),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          serverAddressController.text = _ymlProxyAddress;
                          portController.text = _ymlProxyPort;

                          setState(() {});
                        },
                        style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.cyan
                        ),
                        child: const Text("PROXY"),
                      ),
                    ),
                  ],
                ),
                TextFormField(
                  controller: serverAddressController,
                  decoration: const InputDecoration(
                      hintText: "server address (yourserver.com)"
                  ),
                ),
                TextFormField(
                  controller: portController,
                  decoration: const InputDecoration(
                      hintText: "port (default: 5000)"
                  ),
                ),
                Scrollbar(
                  controller: _serverConfigurationsScrollController,
                  child: ListView.separated(
                    physics: const ScrollPhysics(),
                    shrinkWrap: true,
                    scrollDirection: Axis.vertical,
                    itemBuilder: (BuildContext context, int index) {
                      return ListTile(
                        title: Text(
                            "${lastServerAddresses[index]}\n"
                            "Port: ${lastPorts[index]}"
                        ),
                        onTap: () {
                          serverAddressController.text =
                            lastServerAddresses[index];
                          portController.text = lastPorts[index];
                        },
                      );
                    },
                    separatorBuilder: (
                        BuildContext context,
                        int index) => const Divider(),
                    itemCount: lastServerAddresses.length
                  )
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                // if the userName field is empty, display error message
                if (_userNameFormKey.currentState!.validate()) {
                  _serverAddress = serverAddressController.text;
                  _port = portController.text;
                  _userName = userNameController.text;

                  // save data in shared_preferences
                  saveServerAddressAndPort(
                      lastServerAddresses, lastPorts, prefs);
                  saveUserName();

                  Navigator.pop(context);
                }

                setState(() {});
              },
              child: const Text("Confirm"),
            ),
          ],
        );
      },
      barrierDismissible: false,
    );
  }

  // ============================ save userName ================================
  Future<void> saveUserName() async {
    /// Storage location by platform
    /// Platform	  Location
    /// Android	    SharedPreferences
    /// iOS	        NSUserDefaults
    /// Linux	      In the XDG_DATA_HOME directory
    /// macOS	      NSUserDefaults
    /// Web	        LocalStorage
    /// Windows	    In the roaming AppData directory
    final SharedPreferences prefs = await _prefs;
    await prefs.setString("userName", _userName);
    print("saved user name");
  }

  // =========================== load & save userId ============================
  Future<void> loadUserId() async {
    /// Storage location by platform
    /// Platform	  Location
    /// Android	    SharedPreferences
    /// iOS	        NSUserDefaults
    /// Linux	      In the XDG_DATA_HOME directory
    /// macOS	      NSUserDefaults
    /// Web	        LocalStorage
    /// Windows	    In the roaming AppData directory
    final SharedPreferences prefs = await _prefs;
    _userId = prefs.getInt("userId+$_serverAddress+$_port") ?? 0;
    _serverStartTimestamp = prefs.getDouble(
        "timestamp+$_serverAddress+$_port") ?? 0;
  }

  Future<void> saveUserId(int userId, double serverTimestamp) async {
    /// saves userId to platform specific location
    final SharedPreferences prefs = await _prefs;
    await prefs.setInt("userId+$_serverAddress+$_port", userId);
    await prefs.setDouble("timestamp+$_serverAddress+$_port", serverTimestamp);
    _userId = userId;
    _serverStartTimestamp = serverTimestamp;
  }

  // ======================== process data from backend ========================
  Widget processDataFromBackend() {
    if (_serverAddress.isEmpty) {
      return const Text("Server address is empty!");
    }
    return FutureBuilder<cti.Album>(
      future: _futureAlbum,
      builder: (context, snapshot) {
        if (snapshot.hasData) {

          // get the tripId
          _tripId = snapshot.data!.tripId;

          // see if the shapeId has changed
          // If so, fetch a new shape from the backend
          if (snapshot.data!.shapeId != _shapeId) {
            _futureShapeAlbum = cti.createShapeAlbum(
              snapshot.data!.shapeId, _tripId, _serverAddress, _port);
            _shapeId = snapshot.data!.shapeId;
          }

          // Fetch the following information from backend:
          // If there is a new next stop on the line, change shown data in the
          // third tab of the app
          String newNextStop = snapshot.data!.nextStop;
          if (nextStop != newNextStop || _updateTransferOptionsList) {
            _futureChangeVehicleAlbum = cti.createChangeVehicleAlbum(
              newNextStop,
              DateTime.now().millisecondsSinceEpoch.toString(),
              _tripId,
              _serverAddress,
              _port
            );
            _updateTransferOptionsList = false;
          }
          if (newNextStop == "") {
            newNextStop = "next stop";
          }

          // get the route information
          nextStop = newNextStop;
          routeName = snapshot.data!.routeName;
          routeType = snapshot.data!.routeType;
          routeDest = snapshot.data!.routeDest;
          routeColor = snapshot.data!.routeColor;

          // Check if a path has been found:
          if (snapshot.data!.message == "Nothing to say") {
            isCurrentlyMatching = true;
            positionMarkerPosition = snapshot.data!.location;
          } else {
            isCurrentlyMatching = false;
            positionMarkerPosition = _lastNCoordinates.last.item1;
          }

        } else if (snapshot.hasError) {
          print("Error in processDataFromBackend: "
              "${snapshot.error},\n${snapshot.stackTrace}");
        }

        // show actual widget after passing it through the shape data fetcher
        return _processShapeDataFromBackend();
      },
    );
  }

  // =================== process shape data from backend =======================
  Widget _processShapeDataFromBackend() {
    return FutureBuilder<cti.ShapeAlbum>(
      future: _futureShapeAlbum,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          List<MapLatLng> polyline = snapshot.data!.shapePolyline;

          // skip if polyline too short
          if (polyline.length < 2) {
            _showChatOrNormalWidgets(_bottomNavigationBarCurrentIndex);
          }

          // create SF PolylineModel
          PolylineModel polylineModel = PolylineModel(
              polyline, utils.HexColor(routeColor), lineThickness
          );

          // add polyline model to polylines
          if (polylines.length == 1) {
            polylines.add(polylineModel);
          } else if (polylines.length == 2) {
            polylines[1] = polylineModel;
          }

          // convert stop positions to MapMarkers
          // and add them to the mapMarkers
          if (!isCurrentlyMatching) {
            mapMarkers = [];
          }
          else if (snapshot.data!.stops.isNotEmpty) {
            mapMarkers = [];
            double size = utils.calculateIconSize(zoomPanBehavior.zoomLevel);
            for (int i = 0; i < snapshot.data!.stops.length; i++) {
              mapMarkers.add(
                MapMarker(
                  latitude: snapshot.data!.stops[i].latitude,
                  longitude: snapshot.data!.stops[i].longitude,
                  iconType: MapIconType.circle,
                  iconColor: utils.HexColor(routeColor),
                  iconStrokeColor: Colors.black,
                  iconStrokeWidth: 2,
                  size: Size(size, size),
                )
              );
            }
          }

          // add marker with current transit icon
          mapMarkers.add(MapMarker(
            latitude: positionMarkerPosition.latitude,
            longitude: positionMarkerPosition.longitude,
            child: Container(
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.blue,
              ),
              child: Icon(
                _getCurrentTransitIcon(routeType: routeType).icon,
                color: Colors.white,
                size: utils.calculateIconSize(
                    zoomPanBehavior.zoomLevel,
                    isLocationIcon: true
                ),
              ),
            ),
          ));
          
          mapMarkerIndices = [for (int i = 0; i < mapMarkers.length; i++) i];

        } else if (snapshot.hasError) {
          print("Error in processShapeDataFromBackend: "
              "${snapshot.error},\n${snapshot.stackTrace}");
        }

        return _showChatOrNormalWidgets(_bottomNavigationBarCurrentIndex);
      }
    );
  }

  // ==================== process chat data from backend =======================
  Widget _processChatDataFromBackendChat() {
    // see if the server has sent any chat data
    return FutureBuilder<cti.ChatAlbum>(
        future: _futureChatAlbum,
        builder: (context, snapshot) {
          if (snapshot.hasData) {
            int userId = snapshot.data!.userId;
            double serverStartTimestamp = snapshot.data!.serverStartTimestamp;
            if (userId != _userId) {
              saveUserId(userId, serverStartTimestamp);
            }
            _messages = snapshot.data!.messages.reversed.toList();
          }
          else if (snapshot.hasError) {
            print("Error in processChatDataFromBackendChat: "
                "${snapshot.error},\n${snapshot.stackTrace}");
          }

          return _buildAnimatedChatContainer();
        }
    );
  }

  // =========================== Chat Container ================================
  Widget _showChatOrNormalWidgets(int index) {
    // when chat widget is shown, grey out background.
    // The map cannot be shown in the background due to a SfMaps error,
    // which has not been fixed yet in the current SfMaps version.
    if (_showChat) {
      return Stack(
        children: <Widget>[
          AbsorbPointer(
            child: Opacity(
              opacity: 0.7,
              child: Container(
                color: Colors.black54,
                // show greyed out in the background and don't show the map
                child: _choosePageToShow(index, false),
              ),
            ),
          ),
          _processChatDataFromBackendChat(),
        ],
      );
    }

    // if no chat
    return _choosePageToShow(index, true);
  }

  // =========================== show chat message =============================
  Widget _buildChatWidget(int index) {
    // displays the whole chat
    const double chatBubbleWidth = 250;

    return Container(
      padding: const EdgeInsets.only(left: 14, right: 14, top: 10, bottom: 10),
      // messages from the same user
      child: Align(  // if message was sent by this user, show on the right
        alignment: (  // else on the left
            _messages[index].userId == _userId ?
                                       Alignment.topRight:Alignment.topLeft
        ),
        child: Container(
          width: chatBubbleWidth,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            color: (  // messages from this user are blue
                _messages[index].userId == _userId ?
                                           Colors.blue[200]:Colors.grey.shade200
            ),
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _messages[index].messageContent,
                  style: const TextStyle(fontSize: 16),
                ),
              ),
              Row(
                children: [
                  Expanded(
                    flex: 1,
                    child: Text(
                      _messages[index].userName,
                      style: const TextStyle(fontSize: 12),
                    ),
                  ),
                  const Expanded(
                    flex: 2,
                    child: Text(""),
                  ),
                  Expanded(
                    flex: 1,
                    child: Align(
                      alignment: Alignment.centerRight,
                      child: Text(
                        _messages[index].timeSent,
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ================= build field to type chat messages in ====================
  Widget _buildEnterChatMessageBox() {
    return Align(
      alignment: Alignment.bottomLeft,
      child: Container(
        padding: const EdgeInsets.only(left: 10, bottom: 10, top: 10),
        height: 60,
        width: double.infinity,
        color: Colors.white,
        child: Row(
          children: <Widget>[
            const SizedBox(width: 15),
            Expanded(
              child: TextField(
                controller: sendMessageController,
                textAlign: TextAlign.left,
                decoration: const InputDecoration(
                  hintText: "Write message...",
                  hintStyle: TextStyle(color: Colors.black54),
                  border: InputBorder.none,
                ),
              ),
            ),
            const SizedBox(width: 15),
            FloatingActionButton(
              onPressed: () {  // send messages here
                if (sendMessageController.text.isEmpty) return;
                initializeDateFormatting();
                String timeSent = DateFormat("HH:mm").format(DateTime.now());
                _futureChatAlbum = cti.createChatAlbum(
                    false, // actually send a message (not just fetch)
                    _userId,
                    _serverStartTimestamp,
                    _tripId,
                    _serverAddress,
                    _port,
                    userName: _userName,
                    message: sendMessageController.text,
                    timeSent: timeSent
                );
                sendMessageController.text = "";  // clear TextField
                if (mounted) {
                  setState(() {});
                }
              },
              backgroundColor: Colors.blue,
              elevation: 0,
              child: const Icon(Icons.send,color: Colors.white,size: 18),
            ),
          ],
        ),
      ),
    );
  }

  // ======================== grey out background if chat ======================
  Widget _buildAnimatedChatContainer() {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      child: Column(
        children: <Widget>[
          Expanded(
            child: ListView.builder(
              reverse: true,
              itemCount: _messages.length,
              shrinkWrap: true,
              padding: const EdgeInsets.only(top: 10,bottom: 10),
              physics: const ScrollPhysics(),
              itemBuilder: (context, index) {
                return _buildChatWidget(index);
              },
            ),
          ),
          _buildEnterChatMessageBox(),
        ],
      ),
    );
  }

  // ============================= Front Page ==================================

  Widget _buildVehiclesPage() {
    if (nextStop == "next stop") {
      nextStop = "";
    }
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        _getCurrentVehicle(),
      ],
    );
  }

  Widget _getCurrentVehicle() {
    // displays the text for the front page
    if (routeName.isNotEmpty) {
      return Column(
        children: [
          Text(
            'You are currently in: ',
            style: Theme.of(context).textTheme.headline4,
            textAlign: TextAlign.center,
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: <Widget>[
              _getCurrentTransitIcon(routeType: routeType),
              Text(
                routeName,
                style: Theme
                    .of(context)
                    .textTheme
                    .headline4,
                textAlign: TextAlign.center,
              ),
            ],
          ),
          _getCurrentLine(),
          Text(
            "",
            style: Theme
                .of(context)
                .textTheme
                .headline4,
          ),
          Text(
            "Next Stop: ",
            style: Theme
                .of(context)
                .textTheme
                .headline4,
            textAlign: TextAlign.center,
          ),
          Text(
            nextStop,
            style: Theme
                .of(context)
                .textTheme
                .headline6,
            textAlign: TextAlign.center,
          ),
          Text(
            "",
            style: Theme
                .of(context)
                .textTheme
                .headline4,
          ),
        ],
      );
    }

    // if not in a vehicle:
    return Center(
      child: Text(
        'You are currently not matched to a vehicle.',
        style: Theme.of(context).textTheme.headline4,
        textAlign: TextAlign.center,
      ),
    );
  }

  Text _getCurrentLine() {
    String dest = "";
    if (routeDest != "") {
      dest = "To: $routeDest";
    }
    return Text(
      dest,
      style: Theme
        .of(context)
        .textTheme
        .headline6,
      textAlign: TextAlign.center,
    );
  }

  Icon _getCurrentTransitIcon(
      {String routeType = "", double? size = 56, Color color = Colors.black}) {
  /*
  Returns the route type as a string.

  According to the GTFS reference
      (https://developers.google.com/transit/gtfs/reference),
  these are the specified route types:

  0  - Tram, Streetcar, Light rail.
          Any light rail or street level system within a metropolitan area.
  1  - Subway, Metro. Any underground rail system within a metropolitan area.
  2  - Rail. Used for intercity or long-distance travel.
  3  - Bus. Used for short- and long-distance bus routes.
  4  - Ferry. Used for short- and long-distance boat service.
  5  - Cable tram. Used for street-level rail cars where the cable runs
          beneath the vehicle,
  e.g., cable car in San Francisco.
  6  - Aerial lift, suspended cable car (e.g., gondola lift, aerial tramway).
          Cable transport where cabins, cars, gondolas or open chairs
          are suspended by means of one or more cables.
  7  - Funicular. Any rail system designed for steep inclines.
  11 - Trolleybus. Electric buses that draw power from overhead wires
          using poles.
  12 - Monorail. Railway in which the track consists of a single rail or a beam.
  */
    switch (routeType) {
      // Tram
      case "0":
        return Icon(
          Icons.tram,
          size: size,
          color: color,
        );
      // Subway
      case "1":
        return Icon(
          Icons.directions_subway,
          size: size,
          color: color,
        );
      // Rail
      case "2":
        return Icon(
          Icons.train,
          size: size,
          color: color,
        );
      // Bus
      case "3":
        return Icon(
          Icons.directions_bus,
          size: size,
          color: color,
        );
      // Ferry
      case "4":
        return Icon(
          Icons.directions_ferry,
          size: size,
          color: color,
        );
      // Cable tram
      case "5":
        return Icon(
          Icons.tram,
          size: size,
          color: color,
        );
      // Aerial lift
      case "6":
        return Icon(
          CustomIcons.cable_car,
          size: size,
          color: color,
        );
      // Funicular
      case "7":
        return Icon(
          CustomIcons.funicular,
          size: size,
          color: color,
        );
      // Trolleybus
      case "11":
        return Icon(
          CustomIcons.trolleybus,
          size: size,
          color: color,
        );
      // Monorail
      case "12":
        return Icon(
          Icons.tram,
          size: size,
          color: color,
        );
      default:
        // not in a vehicle
        return Icon(
          Icons.not_interested,
          size: size,
          color: color,
        );
    }
  }

  // =========================== Map Page ======================================
  Widget _buildMapPage() {
    if (!_hasReceivedGPSPoints) {
      return const Center(
        child: Text("No GPS points received yet."),
      );
    }

    // build SFMap
    Widget map = _buildMap();

    return Stack(
      alignment: Alignment.bottomRight,
      children: [
        map,
        _buildFloatingActionButtonsOnMap(),
      ],
    );
  }

  List<MapPolyline> _getMapPolylines() {
    if (drawRedLine || polylines.length <= 1) {
      return List<MapPolyline>.generate(
        polylines.length,
            (int index) {
          return MapPolyline(
              points: polylines[index].points,
              color: polylines[index].color,
              width: polylines[index].width
          );
        },
      );
    }

    // if !drawRedLine:
    return [
      MapPolyline(
        points: polylines[1].points,
        color: polylines[1].color,
        width: polylines[1].width
      )
    ];
  }

  Widget _buildMap() {
    // update zoomPanBehaviour
    centerCameraToPredictedLocation();  // only centers if locking FAB active

    // As SfMaps cannot handle empty PolylineModels, remove them now
    polylines.removeWhere((polylineModel) => polylineModel.isEmpty());

    if (mapController.markersCount > 0) {
      mapController.clearMarkers();
    }
    for (int i = 0; i < mapMarkers.length; i++) {
      mapController.insertMarker(i);
    }

    mapController.updateMarkers(mapMarkerIndices);

    // Draw no line if there is no line to draw
    // OR if not matching and the red polyline should not be drawn
    if (polylines.isEmpty || (!drawRedLine && polylines.length == 1)) {
      return SfMaps(
        layers: [
          MapTileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            zoomPanBehavior: zoomPanBehavior,
            controller: mapController,
            initialMarkersCount: 1,
            markerBuilder: (BuildContext context, int index) {
              return mapMarkers[index];
            },
          ),
        ],
      );
    }

    // if there are lines:
    return SfMaps(
      layers: [
        MapTileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          sublayers: [
            MapPolylineLayer(
              polylines: _getMapPolylines().toSet(),
            ),
          ],
          zoomPanBehavior: zoomPanBehavior,
          controller: mapController,
          initialMarkersCount: mapMarkers.length,
          markerBuilder: (BuildContext context, int index) {
            return mapMarkers[index];
          },
        ),
      ],
    );
  }

  Widget _buildFloatingActionButtonsOnMap() {
    return Align(
      alignment: Alignment.bottomRight,
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: <Widget>[
            FloatingActionButton(
              onPressed: () {
                drawRedLine = !drawRedLine;
                setState(() {});
              },
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              tooltip: "Show GPS points",
              child: const Icon(Icons.not_listed_location),
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedDeleteFAB,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              tooltip: "Reset the latest coordinates (don't spam)",
              child: const Icon(Icons.sync),
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedLockFAB,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              tooltip: "Lock camera to current position",
              child: () {
                if (lockCamera) {
                  return const Icon(Icons.lock_outline);
                }
                return const Icon(Icons.lock_open_outlined);
              } (),
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedCenter,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              tooltip: "Move to current location",
              child: const Icon(Icons.my_location),
            ),
          ],
        ),
      ),
    );
  }

  // ======================== Floating Action Button ===========================
  /// deletes last coordinates and the polyline
  void onPressedDeleteFAB() {
    if (_lastNCoordinates.isNotEmpty) {
      _lastNCoordinates.removeRange(0, _lastNCoordinates.length - 1);
    }
    polylines[0].removeAll();
    setState(() {});
  }

  /// center the Map on last location
  void onPressedCenter() {
    if (_lastNCoordinates.isNotEmpty) {
      zoomPanBehavior.focalLatLng = utils.convertLatLngToMapLatLng(
          _lastNCoordinates.last.item1);
      if (zoomPanBehavior.zoomLevel >= 16 && zoomPanBehavior.zoomLevel < 18) {
        zoomPanBehavior.zoomLevel = 18;
      } else {
        zoomPanBehavior.zoomLevel = 16;
      }
    }
    setState(() {});
  }

  /// locks the map focus to the predicted position
  void onPressedLockFAB() {
    lockCamera = !lockCamera;
    setState(() {});
  }

  void centerCameraToPredictedLocation() {
    if (lockCamera) {
      // if not matching, center camera to current GPS position
      if (isCurrentlyMatching) {
        if (positionMarkerPosition != LatLng(0, 0)) {
          // try catch needed, because syncfusion has an error.
          try {
            zoomPanBehavior.focalLatLng = utils.convertLatLngToMapLatLng(
                positionMarkerPosition);
          } catch (error) {
            print("Error caught: Could not set zoomPanBehavior.focalLatLng: \n"
                "$error. Matching.");
          }
        }
      } else { // backend is not matching a path
        if (_lastNCoordinates.isNotEmpty) {
          try {
            zoomPanBehavior.focalLatLng = utils.convertLatLngToMapLatLng(
                _lastNCoordinates.last.item1);
          } catch (error) {
            print("Error caught: Could not set zoomPanBehavior.focalLatLng: \n"
                "$error. Not matching.");
          }
        }
      }
    }
  }

  // =========================== Connections Page ==============================
  /// only autoscroll text if the string is too long
  Widget _buildScrollingDestinationNameText(String destinationStation) {
    const double fontSize = 24;
    if (destinationStation.length * 10 > MediaQuery.of(
        context).size.width - 140) {
      return SizedBox(
        width: MediaQuery.of(context).size.width - 125,
        height: fontSize * 1.18,
        child: Marquee(
          scrollAxis: Axis.horizontal,
          text: "$destinationStation        ",
          crossAxisAlignment: CrossAxisAlignment.start,
          style: const TextStyle(fontSize: fontSize),
        ),
      );
    }

    return Text(destinationStation, style: const TextStyle(fontSize: fontSize));
  }

  Widget _buildChangeVehicleBox(List<String> connection) {
    // displays one line for the connections page
    final String routeName = connection[0];
    final String destinationStation = connection[1];
    final String vehicleType = connection[2];
    final String departureTime = connection[3];
    Color lineColor = utils.HexColor(connection[4]).withOpacity(1);
    Color textColor = utils.HexColor(connection[5]).withOpacity(1);

    return Padding(
      padding: const EdgeInsets.all(10.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget> [
              _buildScrollingDestinationNameText(destinationStation),
              Container(
                  margin: const EdgeInsets.fromLTRB(0, 3, 0, 0),
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    border: Border.all(),
                    borderRadius: const BorderRadius.all(Radius.circular(10)),
                    color: lineColor,
                  ),
                  child: Row(
                      mainAxisAlignment: MainAxisAlignment.start,
                      children: <Widget>[
                        _getCurrentTransitIcon(
                            routeType: vehicleType, size: 24, color: textColor
                        ),
                        Text(
                            routeName,
                            style: TextStyle(fontSize: 20, color: textColor)
                        ),
                      ],
                  ),
              ),
            ],
          ),
          Align(
              alignment: Alignment.centerRight,
              child: Text(departureTime, style: const TextStyle(fontSize: 20))
          ),
        ],
      ),
    );
  }

  Widget _buildScrollableWidget() {
    // builds the connections page
    return ListView.builder(
      padding: const EdgeInsets.all(16.0),
      itemCount: connections.length * 2,
      itemBuilder: (context, i) {
        if (i.isOdd) return const Divider();

        final index = i ~/ 2;  // floor division

        // fetch new data if the departure time (connections[index][3])
        // of the first transfer option on the list (i == 0) has passed
        if (i == 0 && DateTime.now().isAfter(
            connectionsFirstDepartureTimeDatetime)) {
          // data will be fetched the first time ones position changes
          _updateTransferOptionsList = true;
        }

        return _buildChangeVehicleBox(connections[index]);
      });
  }

  // Process data from change vehicle data
  FutureBuilder<cti.ChangeVehicleAlbum> processChangeVehicleDataFromBackend() {
    return FutureBuilder<cti.ChangeVehicleAlbum>(
        future: _futureChangeVehicleAlbum,
        builder: (context, snapshot) {
          if (snapshot.hasData) {
            connections = snapshot.data!.connections;
            connectionsFirstDepartureTimeDatetime = snapshot.data!.timestamp;
            return _buildScrollableWidget();
          }
          else if (snapshot.hasError && routeName.isNotEmpty) {
            print("Error bei processChangeVehicleDataFromBackend: "
                "${snapshot.error}");
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const CircularProgressIndicator(),
                Text("Error bei processChangeVehicleDataFromBackend: "
                    "${snapshot.error},\n ${snapshot.stackTrace}")
              ],
            );
          }
          else if (routeName.isEmpty) {
            return Text(
              "You are currently not matched to a vehicle.",
              style: Theme.of(context).textTheme.headline4,
              textAlign: TextAlign.center,
            );
          }

          return const CircularProgressIndicator();
        }
    );
  }

  // ========================= choose page to show =============================
  Widget _choosePageToShow(int index, bool showMap) {
    switch (index) {
      case 0:  // home page
        return _buildVehiclesPage();
      case 1:  // map widget
        if (showMap) return _buildMapPage();
        return const Center(child: Text(""));
      case 2:  // list of coordinates
        return processChangeVehicleDataFromBackend();
      default:  // not implemented
        return const Icon(Icons.all_inclusive, size: 150);
    }
  }

  // =========================== show settings =================================
  void _showSettings() {
    showServerConfigurationsQueryDialog();
  }

  // ============================== App Bar ====================================
  Widget _getAppBarTitle() {
    // scroll horizontally if not enough space
    if (_title.length * 10 > MediaQuery.of(context).size.width - 100) {
      return SizedBox(
        width: MediaQuery.of(context).size.width - 2,
        height: 40,
        child: Marquee(
          scrollAxis: Axis.horizontal,
          text: "$_title        ",
        ),
      );
    }

    // default
    return Align(
      alignment: Alignment.center,
        child: Text(_title)
    );
  }

  AppBar _getAppBar() {
    // refresh title on rebuild
    if (_bottomNavigationBarCurrentIndex == 2) {
      if (nextStop.isEmpty) {
        _title = "Possible transfer options at next stop";
      } else {
        _title = "Possible transfer options at $nextStop";
      }
    }
    else if (_bottomNavigationBarCurrentIndex == 1) {
      if (routeName.isEmpty) {
        _title = "You are not matched to a vehicle";
      } else {
        _title = "You are on route $routeName to $routeDest";
      }
    }

    return AppBar(
      centerTitle: true,
      title: _getAppBarTitle(),
      backgroundColor: Colors.cyan,
      actions: <Widget>[
        Padding(
          padding: const EdgeInsets.only(right: 3.0),
          child: IconButton(
              onPressed: () {
                _showChat = !_showChat;
                // fetch data from internet
                _futureChatAlbum = cti.createChatAlbum(
                    true,
                    _userId,
                    _serverStartTimestamp,
                    _tripId,
                    _serverAddress,
                    _port
                );
                setState(() {});
              },
              icon: const Icon(Icons.chat)
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(right: 10.0),
          child: IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettings,
          ),
        ),
      ],
    );
  }

  // =============================== build =====================================
  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_launchPopUp) {
        _launchPopUp = false;
        showServerConfigurationsQueryDialog();
      }
    });

    // This method is rerun every time setState is called.
    return Scaffold(
      appBar: _getAppBar(),
      body: Center(
        child: processDataFromBackend()
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _bottomNavigationBarCurrentIndex,
        fixedColor: Colors.cyan,
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(
              label: "Vehicle",
              tooltip: "What public vehicle am I in?",
              icon: Icon(Icons.directions_bus)
          ),
          BottomNavigationBarItem(
              label: "Map",
              tooltip: "Shows my position on the map",
              icon: Icon(Icons.map)
          ),
          BottomNavigationBarItem(
              label: "Connections",
              tooltip: "Connections at the next stop",
              icon: Icon(Icons.transfer_within_a_station),
          ),
        ],
        onTap: (int index) {
          setState(() {
            // show the page that was tapped on
            _bottomNavigationBarCurrentIndex = index;
            _updateTransferOptionsList = true;
            // set title of page
            switch (index) {
              case 0:
                {_title = "Current vehicle";}
                break;
              case 1:
                {_title = "Map";}
                break;
              case 2:
                {_title = "Possible transfer options at $nextStop";}
                break;
            }
          });
        },
      ),
    );
  }
}
