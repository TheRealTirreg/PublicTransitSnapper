/// Copyright 2022
/// Bachelor's thesis by Gerrit Freiwald and Robin Wu

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
  // able to read a hex color and display it
  static int _getColorFromHex(String hexColor) {
    if (hexColor == "") {
      hexColor = "#26ABFF";  // default color is sky blue
    }
    hexColor = hexColor.toUpperCase().replaceAll("#", "");
    if (hexColor.length == 6) {
      hexColor = "FF$hexColor";
    }
    return int.parse(hexColor, radix: 16);
  }

  HexColor(final String hexColor) : super(_getColorFromHex(hexColor));
}

String getUrl(String endpoint, String serverAddress, String port) {
  if (serverAddress.startsWith("https://")) {
    return "$serverAddress/$endpoint";
  } else {
    return "http://$serverAddress:$port/$endpoint";
  }
}

double calculateIconSize(zoom, {isLocationIcon = false}) {
  /// zoomed in => bigger icon
  /// zoomed out => smaller icon
  /// zoom -> return
  ///   18 -> 16
  ///   16 -> 14
  ///   14 -> 11
  ///   12 -> 6
  ///   10 -> 1
  ///  <10 -> 0
  if (!isLocationIcon) {
    if (zoom < 10) return 1;
    if (zoom >= 18) return 16;
    if (zoom > 16) return 14;
    if (zoom > 15) return 11;
    if (zoom > 14) return 8;
    if (zoom > 13) return 5;
    if (zoom > 12) return 2;
    if (zoom >= 10) return 1;
    return 1;
  }

  // if location icon:
  if (zoom > 14) return 24;
  return 18;
}
