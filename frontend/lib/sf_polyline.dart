/// Copyright 2022
/// Bachelor's thesis by Gerrit Freiwald and Robin Wu

import 'dart:ui';
import 'package:syncfusion_flutter_maps/maps.dart';

/// A simple Polyline (List of Points)
class PolylineModel {
  PolylineModel(this.points, this.color, this.width);
  final List<MapLatLng> points;
  final Color color;
  final double width;

  void addPoint(MapLatLng point) {
    points.add(point);
  }

  void removeAtIndex(int i) {
    points.removeAt(i);
  }

  void removeAll() {
    if (points.isNotEmpty) {
      points.removeRange(0, points.length - 1);
    }
  }

  bool isEmpty() {
    return points.isEmpty;
  }

  @override
  String toString() {
    return "PolylineModel(Points: $points, Color: $color, Line width: $width)";
  }
}
