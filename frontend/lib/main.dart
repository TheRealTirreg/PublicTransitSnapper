import 'dart:async';
import 'dart:core';
import 'dart:math';
import 'package:flutter/cupertino.dart';
import 'package:tuple/tuple.dart';
import 'package:flutter/material.dart';
import 'package:location/location.dart';
import 'package:latlong2/latlong.dart';
import 'package:syncfusion_flutter_maps/maps.dart';
import 'package:marquee/marquee.dart';
import 'connect_to_internet.dart' as cti;
import 'utilities.dart' as utils;
import 'sf_polyline.dart';
import 'custom_icons.dart';

void main() async {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Location gatherer',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const MyHomePage(title: 'We know where you live ^w^'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({Key? key, required this.title}) : super(key: key);

  // This widget is the home page of your application. It is stateful, meaning
  // that it has a State object (defined below) that contains fields that affect
  // how it looks.

  // This class is the configuration for the state. It holds the values (in this
  // case the title) provided by the parent (in this case the App widget) and
  // used by the build method of the State. Fields in a Widget subclass are
  // always marked "final".

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  // header title
  late String _title;

  // server address
  String _serverAddress = "";
  String _port = "";
  bool _launchPopUp = true;

  // location
  Location location = Location();
  final int locationUpdateInterval = 10000;  // update location every 10 seconds
  bool locationPermission = false;
  final List<Tuple2<LatLng, int>> _lastNCoordinates = <Tuple2<LatLng, int>>[];  // saves locations
  final LatLng freiburg = LatLng(47.997791, 7.842609);  // needed for the first zoom

  // widgets
  int _bottomNavigationBarCurrentIndex = 0;

  // Timer to fetch data from backend every minute
  Timer? timer;

  Future<cti.Album>? _futureAlbum;
  Future<cti.ChangeVehicleAlbum>? _futureChangeVehicleAlbum;
  bool _updateTransferOptionsList = false;

  // sfMaps
  List<PolylineModel> polylines = [];  // will always contain only 1 polyline
  late MapShapeSource dataSource;
  late MapTileLayerController mapController;
  late MapZoomPanBehavior zoomPanBehavior;
  final double lineThickness = 4.0;
  bool lockCamera = false;
  bool drawRedLine = false;

  // route information
  String nextStop = "";
  String routeName = "";
  String routeType = "";
  String routeDest = "";
  String routeColor = "";
  LatLng predictedLocation = LatLng(0, 0);
  List<List<String>> connections = [];
  DateTime connectionsFirstDepartureTimeDatetime = DateTime.fromMillisecondsSinceEpoch(0);

  // =========================== init state ====================================
  @override
  void initState() {
    super.initState();

    // set default title
    _title = "Current vehicle";

    // enable location permission
    getLocationPermission();

    // try to collect data from the internet
    _futureAlbum = cti.fetchAlbum(_serverAddress, _port);
    _futureChangeVehicleAlbum = cti.createChangeVehicleAlbum("", "", _serverAddress, _port);

    // location settings. distanceFilter: only updates location if minimum displacement of n=15 meters
    location.changeSettings(interval: locationUpdateInterval, accuracy: LocationAccuracy.high, distanceFilter: 15);  // todo set to 15m or so

    // initialize _lastCoordinates
    _lastNCoordinates.add(Tuple2(LatLng(0, 0), 0));

    // sfMaps => polylines now has two entries
    // add the red line (own GPS points)
    polylines.add(PolylineModel([const MapLatLng(0, 0)], Colors.red, lineThickness));
    // add the purple line (own GPS points)
    polylines.add(PolylineModel([const MapLatLng(0, 0)], Colors.purple, lineThickness));

    mapController = MapTileLayerController();

    zoomPanBehavior = MapZoomPanBehavior(
      zoomLevel: 12,
      focalLatLng: utils.convertLatLngToMapLatLng(freiburg),
      minZoomLevel: 5,  // zoom out
      maxZoomLevel: 18,  // zoom in
      enableDoubleTapZooming: true,
      showToolbar: true,
      toolbarSettings: const MapToolbarSettings(
        position: MapToolbarPosition.topRight,
        iconColor: Colors.white,
        itemBackgroundColor: Colors.green,
        itemHoverColor: Colors.lightGreen,
      )
    );

    // fetch changeVehicleAlbum every minute
    timer = Timer.periodic(const Duration(minutes: 1), (Timer t) {
      cti.createChangeVehicleAlbum(nextStop, DateTime.now().millisecondsSinceEpoch.toString(), _serverAddress, _port);
      setState(() {});
    });

    // create location listener
    location.onLocationChanged.listen((LocationData currentLocation) {
      // if the position has changed, add new point to _lastNCoordinates and polylines[0] (<= contains the red line (connected GPS points))
      if (currentLocation.latitude! != _lastNCoordinates.last.item1.latitude || currentLocation.longitude! != _lastNCoordinates.last.item1.longitude) {
        _lastNCoordinates.add(Tuple2(LatLng(currentLocation.latitude!, currentLocation.longitude!), currentLocation.time!.toInt()));
        polylines[0].addPoint(MapLatLng(currentLocation.latitude!, currentLocation.longitude!));

        // send last 10 coordinates to backend
        List<String> lastTenGpsPoints = [];
        int lstlen = _lastNCoordinates.length;
        int delimiter = min(lstlen, 10);
        for (int i = 0; i < delimiter; i++) {
          double lat = _lastNCoordinates[lstlen - delimiter + i].item1.latitude;
          double lon = _lastNCoordinates[lstlen - delimiter + i].item1.longitude;
          int tim = _lastNCoordinates[lstlen - delimiter + i].item2;
          lastTenGpsPoints.add("$lat, $lon, $tim");
        }

        _futureAlbum = cti.createAlbum(lastTenGpsPoints, _serverAddress, _port);
      }

      // remove first placeholder coordinates (only needed once)
      if (_lastNCoordinates[0].item1 == LatLng(0, 0) && polylines[0].points[0] == const MapLatLng(0, 0)) {
        _lastNCoordinates.removeAt(0);
        polylines[0].removeAtIndex(0);
      }

      setState(() {});
    });
  }

  // ========================== location permission ============================

  void getLocationPermission() async {
    bool serviceEnabled = await location.serviceEnabled();

    if (!serviceEnabled) {
      serviceEnabled = await location.requestService();

      if (!serviceEnabled) {
        locationPermission = false;
        return;  // service not enabled -> abort mission
      }
    }

    PermissionStatus _hasPermission = await location.hasPermission();

    if (_hasPermission == PermissionStatus.denied) {
      _hasPermission = await location.requestPermission();


      if (_hasPermission == PermissionStatus.granted) {
        locationPermission = true;
      } else {
        locationPermission = false;
      }
    } else {
      locationPermission = true;
    }
  }

  // ======================= server address query popup ========================

  showServerAddressQueryDialog() {
    /// ask the user for the server address and the port
    showDialog(
        context: context,
        builder: (_) {
          TextEditingController serverAddressController = TextEditingController();
          TextEditingController portController = TextEditingController();
          return AlertDialog(
            title: const Text("Connect to the server"),
            content: SizedBox(
              height: 300,
              width: 300,
              child: ListView(
                shrinkWrap: true,
                children: [
                  const Text(
                      "When using the mobile app, write the server address where the backend is running.\n"
                      "When testing with ControlChromeDevTools, write http://localhost."
                  ),
                  TextFormField(
                    controller: serverAddressController,
                    decoration: const InputDecoration(hintText: "server address, e.g.: yourserver.com"),
                  ),
                  TextFormField(
                    controller: portController,
                    decoration: const InputDecoration(hintText: "port, default: 5000"),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () {
                    _serverAddress = serverAddressController.text;
                    _port = portController.text;
                    Navigator.pop(context);
                  },
                  child: const Text("Confirm"),
              ),
            ],
          );
        }
    );
  }

  // ======================== process data from backend ========================

  FutureBuilder<cti.Album> processDataFromBackend() {
    return FutureBuilder<cti.Album>(
      future: _futureAlbum,
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          // Fetch the following information from backend:
          // If there is a new next stop on the line, change shown data in the
          // third tab of the app
          String newNextStop = snapshot.data!.nextStop;
          if (nextStop != newNextStop || _updateTransferOptionsList) {
            _futureChangeVehicleAlbum = cti.createChangeVehicleAlbum(
                newNextStop,
                DateTime.now().millisecondsSinceEpoch.toString(),
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
          predictedLocation = snapshot.data!.location;

          // add calculated path by HMM to polylines as a matched (old purple) polyline
          if (polylines.length > 1) {
            polylines[1] = PolylineModel(utils.convertListOfLatLngToListMapLatLng(snapshot.data!.path), utils.HexColor(routeColor), lineThickness);
          } else {
            polylines.add(PolylineModel(utils.convertListOfLatLngToListMapLatLng(snapshot.data!.path), utils.HexColor(routeColor), lineThickness));
          }

        } else if (snapshot.hasError) {
          print("Error in processDataFromBackend: ${snapshot.error}");
        }

        // show actual widget
        return _choosePageToShow(_bottomNavigationBarCurrentIndex);
      },
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
        Text(
          'You are currently in: ',
          style: Theme.of(context).textTheme.headline4,
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            _getCurrentTransitIcon(),
            Text(
                routeName,
                style: Theme
                .of(context)
                .textTheme
                .headline4,
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
        ),
        Text(
          nextStop,
          style: Theme
              .of(context)
              .textTheme
              .headline6,
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

  Text _getCurrentLine() {
    String dest = "";
    if (routeDest != "") {
      dest = "To: " + routeDest;
    }
    return Text(
      dest,
      style: Theme
        .of(context)
        .textTheme
        .headline6,
    );  // TODO: if (in_line) {..}
  }

  Icon _getCurrentTransitIcon({String type = "", double? size = 56, Color color = Colors.black}) {
    if (type == "") {
      type = routeType;
    }

    switch (type) {
      case "Tram":
        return Icon(
          Icons.tram,
          size: size,
          color: color,
        );
      case "Metro":
        return Icon(
          Icons.subway,
          size: size,
          color: color,
        );
      case "Train":
        return Icon(
          Icons.train,
          size: size,
          color: color,
        );
      case "Bus":
        return Icon(
          Icons.directions_bus,
          size: size,
          color: color,
        );
      case "Ferry":
        return Icon(
          Icons.directions_ferry,
          size: size,
          color: color,
        );
      case "Cable tram":
        return Icon(
          Icons.tram,
          size: size,
          color: color,
        );
      case "Gondola":
        return Icon(
          CustomIcons.cable_car,
          size: size,
          color: color,
        );
      case "Funicular":
        return Icon(
          CustomIcons.funicular,
          size: size,
          color: color,
        );
      case "Trolleybus":
        return Icon(
          CustomIcons.trolleybus,
          size: size,
          color: color,
        );
      case "Monorail":
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
    Widget map = _buildMap();

    // Update the map markers
    // There is currently only one marker (the vehicle icon for the user position).
    mapController.updateMarkers([0]);
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

    if (polylines.length < 2) {
      return SfMaps(
          layers: [
            MapTileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              zoomPanBehavior: zoomPanBehavior,
              controller: mapController,
              initialMarkersCount: 1,
              markerBuilder: (BuildContext context, int index) {
                return MapMarker(
                  latitude: _lastNCoordinates.last.item1.latitude,
                  longitude: _lastNCoordinates.last.item1.longitude,
                  alignment: Alignment.bottomRight,
                  child: Icon(
                    _getCurrentTransitIcon().icon,
                    color: Colors.red,
                    size: 20,
                  ),
                );
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
          initialMarkersCount: 1,
          markerBuilder: (BuildContext context, int index) {
            return MapMarker(
              latitude: polylines[1].points.last.latitude,
              longitude: polylines[1].points.last.longitude,
              child: Container(
                alignment: Alignment.center,
                child: Icon(
                  _getCurrentTransitIcon().icon,
                  color: Colors.red,
                  size: 20,
                ),
              ),
            );
          },
          controller: mapController,
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
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              child: const Icon(Icons.ramen_dining),
              tooltip: "DEBUG hide the red line",
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedDeleteFAB,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              child: const Icon(Icons.sync),
              tooltip: "Reset the latest coordinates",
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedLockFAB,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              child: () {
                if (lockCamera) {
                  return const Icon(Icons.lock_outline);
                }
                return const Icon(Icons.lock_open_outlined);
              }(),
              tooltip: "Lock camera to current position",
            ),
            const Padding(padding: EdgeInsets.all(6.0)),
            FloatingActionButton(
              onPressed: onPressedCenter,
              mini: true,
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
              child: const Icon(Icons.my_location),
              tooltip: "Move to current location",
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
      _lastNCoordinates.removeRange(0, _lastNCoordinates.length - 1); // TODO sinnvoll?
    }
    polylines[0].removeAll();
    setState(() {});
  }

  /// center the Map on last location
  void onPressedCenter() {
    if (_lastNCoordinates.isNotEmpty) {
      zoomPanBehavior.focalLatLng = utils.convertLatLngToMapLatLng(_lastNCoordinates.last.item1);
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
      if (predictedLocation != LatLng(0, 0)) {
        // try catch needed, because syncfusion has an error.
        try {
          zoomPanBehavior.focalLatLng = utils.convertLatLngToMapLatLng(predictedLocation);
        } catch (error) {
          print("Error caught: Could not set zoomPanBehavior.focalLatLng: \n$error}");
        }
      }
    }
  }

  // =========================== Connections Page ==============================

  /// only autoscroll text if the string is too long
  Widget _buildScrollingDestinationNameText(String destinationStation) {
    const double fontSize = 24;
    if (destinationStation.length * 10 > MediaQuery.of(context).size.width - 140) {
      return SizedBox(
        width: MediaQuery.of(context).size.width - 125,
        height: fontSize * 1.18,
        child: Marquee(
          scrollAxis: Axis.horizontal,
          text: destinationStation + "        ",
          crossAxisAlignment: CrossAxisAlignment.start,
          style: const TextStyle(fontSize: fontSize),
        ),
      );
    }

    return Text(destinationStation, style: const TextStyle(fontSize: fontSize));
  }

  Widget _buildChangeVehicleBox(List<String> connection) {
    final String routeName = connection[0];
    final String destinationStation = connection[1];
    final String vehicleType = connection[2];
    final String departureTime = connection[3];
    final Color lineColor = utils.HexColor(connection[4]);
    final Color textColor = utils.HexColor(connection[5]);

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
                        _getCurrentTransitIcon(type: vehicleType, size: 24, color: textColor),
                        Text(routeName, style: TextStyle(fontSize: 20, color: textColor)),
                      ],
                  ),
              ),
            ],
          ),
          Align(alignment: Alignment.centerRight, child: Text(departureTime, style: const TextStyle(fontSize: 20))),
        ],
      ),
    );
  }

  Widget _buildScrollableWidget() {
    return ListView.builder(
        padding: const EdgeInsets.all(16.0),  // Rand zwischen Zeilen
        itemCount: connections.length * 2,
        itemBuilder: (context, i) {
          if (i.isOdd) return const Divider();

          final index = i ~/ 2;  // Ganzzahlige Division

          // fetch new data if the departure time (connections[index][3]) of the first transfer option on the list (i == 0) has passed

          if (i == 0 && DateTime.now().isAfter(connectionsFirstDepartureTimeDatetime)) {
            _updateTransferOptionsList = true;  // data will be fetched the first time ones position changes
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
          else if (snapshot.hasError) {
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

          return const CircularProgressIndicator();
        }
    );
  }

  // ========================= choose page to show =============================

  Widget _choosePageToShow(int index) {
    switch (index) {
      case 0:  // home page
        return _buildVehiclesPage();
      case 1:  // map widget
        return _buildMapPage();
      case 2:  // list of coordinates
        return processChangeVehicleDataFromBackend();  // old: _buildCoordinates();
      default:  // not implemented
        return const Icon(Icons.all_inclusive, size: 150);
    }
  }

  // =============================== build =====================================

  AppBar _getAppBar() {
    // refresh title on rebuild
    if (_bottomNavigationBarCurrentIndex == 2) {
      _title = "Possible transfer options at $nextStop";
    }

    if (_title.length * 10 > MediaQuery.of(context).size.width - 2) {
      return AppBar(
        centerTitle: true,
        title: SizedBox(
          width: MediaQuery.of(context).size.width - 2,
          height: 40,
          child: Marquee(
            scrollAxis: Axis.horizontal,
            text: _title + "        ",
          ),
        ),
      );
    }
    else {
      return AppBar(
        centerTitle: true,
        title: Text(_title),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_launchPopUp) {
        _launchPopUp = false;
        showServerAddressQueryDialog();
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
        fixedColor: Colors.teal,
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
