import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:syncfusion_flutter_maps/maps.dart';

MapLatLng convertLatLngToMapLatLng(LatLng coords) {
  return MapLatLng(coords.latitude, coords.longitude);
}

List<MapLatLng> convertListOfLatLngToListMapLatLng(List<LatLng> lst) {
  List<MapLatLng> newlst = [];
  int len = lst.length;
  for (int i = 0; i < len; i++) {
    newlst.add(convertLatLngToMapLatLng(lst[i]));
  }
  return newlst;
}

/// converts a HH:mm string to a DateTime object using today's date
DateTime convertStringToDateTimeObject(String timeString) {
  List<String> splitString = timeString.split(":");
  int hour = int.parse(splitString[0]);
  int minute = int.parse(splitString[1]);
  DateTime now = DateTime.now();
  // nearly take the next minute to prolong showing public transit lines
  return DateTime(now.year, now.month, now.day, hour, minute, 59);
}

class HexColor extends Color {
  static int _getColorFromHex(String hexColor) {
    if (hexColor == "") {
      hexColor = "#FFFFFF";  // default color is white
    }
    hexColor = hexColor.toUpperCase().replaceAll("#", "");
    if (hexColor.length == 6) {
      hexColor = "FF" + hexColor;
    }
    return int.parse(hexColor, radix: 16);
  }

  HexColor(final String hexColor) : super(_getColorFromHex(hexColor));
}
