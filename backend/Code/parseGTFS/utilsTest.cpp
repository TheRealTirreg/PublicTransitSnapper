// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#include <gtest/gtest.h>
#include <math.h>
#include <tuple>
#include "./utils.h"

using std::make_tuple;

// ___________________________________________________________________________
TEST(utilsTest, degrees_to_radians) {
    ASSERT_DOUBLE_EQ(degrees_to_radians(0), 0);
    ASSERT_DOUBLE_EQ(degrees_to_radians(90), M_PI/2);
    ASSERT_DOUBLE_EQ(degrees_to_radians(180), M_PI);
    ASSERT_DOUBLE_EQ(degrees_to_radians(270), M_PI*1.5);
    ASSERT_DOUBLE_EQ(degrees_to_radians(360), M_PI*2);
}

// ___________________________________________________________________________
TEST(utilsTest, great_circle_distance) {
    ASSERT_DOUBLE_EQ(great_circle_distance(0, 0, 0, 0), 0);
    ASSERT_NEAR(great_circle_distance(0, 0, 0, 1), 111194.925, 0.01);
    ASSERT_NEAR(great_circle_distance(0, 0, 0, -1), 111194.925, 0.01);
    {
        double lat1 = 48; double lon1 = 7;
        double lat2 = 48.00001; double lon2 = 7;
        ASSERT_NEAR(great_circle_distance(lat1, lon1, lat2, lon2),
                    1.111, 0.001);
        ASSERT_NEAR(great_circle_distance(make_tuple(lat1, lon1, lat2, lon2)),
                    1.111, 0.001);
    }
    {
        double lat1 = 48.009833; double lon1 = 7.782528;
        double lat2 = 47.009833; double lon2 = 6.782528;
        ASSERT_NEAR(great_circle_distance(lat1, lon1, lat2, lon2),
                    134182.004, 0.001);
        ASSERT_NEAR(great_circle_distance(make_tuple(lat1, lon1, lat2, lon2)),
                    134182.004, 0.001);
    }
}

// ___________________________________________________________________________
TEST(utilsTest, get_point_on_polyline) {
    {
        auto[pointX, pointY] = get_point_on_line(0, 0, 0, 0, 0, 0);
        ASSERT_DOUBLE_EQ(pointX, 0);
        ASSERT_DOUBLE_EQ(pointY, 0);
    }
    {
        auto[pointX, pointY] = get_point_on_line(0, 0, 0, 1, -1, -1);
        ASSERT_DOUBLE_EQ(pointX, 0);
        ASSERT_DOUBLE_EQ(pointY, 0);
    }
    {
        auto[pointX, pointY] = get_point_on_line(-1, 0, 2, 0, 3, 0);
        ASSERT_DOUBLE_EQ(pointX, 2);
        ASSERT_DOUBLE_EQ(pointY, 0);
    }
    {
        auto[pointX, pointY] = get_point_on_line(0, 0, 0, 1, 0.5, 0.5);
        ASSERT_DOUBLE_EQ(pointX, 0);
        ASSERT_DOUBLE_EQ(pointY, 0.5);
    }
    {
        auto[pointX, pointY] = get_point_on_line(5, 5, 10, 5, 6, 6);
        ASSERT_DOUBLE_EQ(pointX, 6);
        ASSERT_DOUBLE_EQ(pointY, 5);
    }
    {
        auto[pointX, pointY] = get_point_on_line(-1, -2, -5, -2, -3, -4);
        ASSERT_DOUBLE_EQ(pointX, -3);
        ASSERT_DOUBLE_EQ(pointY, -2);
    }
}

// ___________________________________________________________________________
TEST(utilsTest, distance_line_point) {
    ASSERT_DOUBLE_EQ(distance_line_point(0, 0, 0, 0, 0, 0), 0);
    ASSERT_NEAR(distance_line_point(0, 0, 0, 1, -1, -1), sqrt(2), 0.001);
    ASSERT_NEAR(distance_line_point(-1, 0, 2, 0, 3, 0), 1, 0.001);
    ASSERT_NEAR(distance_line_point(0, 0, 0, 1, 0.5, 0.5), 0.5, 0.001);
    ASSERT_NEAR(distance_line_point(5, 5, 10, 5, 6, 6), 1, 0.001);
    ASSERT_NEAR(distance_line_point(-1, -2, -5, -2, -3, -4), 2, 0.001);
}

// ___________________________________________________________________________
TEST(utilsTest, split_by_delimiter) {
    ASSERT_EQ(split_by_delimiter("", ":").size(), 0);
    ASSERT_EQ(split_by_delimiter("r", ":").size(), 1);
    ASSERT_EQ(split_by_delimiter("r:o", ":").size(), 2);
    ASSERT_EQ(split_by_delimiter("r:o:b", ":").size(), 3);
    ASSERT_EQ(split_by_delimiter("r::b", ":").size(), 3);
    ASSERT_EQ(split_by_delimiter("::", ":").size(), 3);
    ASSERT_EQ(split_by_delimiter("r:o:b", ":")[0], "r");
    ASSERT_EQ(split_by_delimiter("r:o:b", ":")[1], "o");
    ASSERT_EQ(split_by_delimiter("r:o:b", ":")[2], "b");
    ASSERT_EQ(split_by_delimiter("r::b", ":")[1], "");
    ASSERT_EQ(split_by_delimiter("::", ":")[0], "");
    ASSERT_EQ(split_by_delimiter("::", ":")[1], "");
    ASSERT_EQ(split_by_delimiter("::", ":")[2], "");
}

// ___________________________________________________________________________
TEST(utilsTest, convert_GTFS_date_to_string) {
    ::testing::FLAGS_gtest_death_test_style = "threadsafe";
    ASSERT_DEATH(convert_GTFS_date_to_string(""), "Invalid time format: ");
    ASSERT_DEATH(convert_GTFS_date_to_string("::"), "Invalid time format: ");
    ASSERT_DEATH(convert_GTFS_date_to_string(":12:"), "Invalid time format: ");
    ASSERT_EQ(convert_GTFS_date_to_string("00:00:00"),
              make_tuple("00:00:00", false));
    ASSERT_EQ(convert_GTFS_date_to_string("01:33:70"),
              make_tuple("01:33:70", false));
    ASSERT_EQ(convert_GTFS_date_to_string("42:42:42"),
              make_tuple("18:42:42", true));
    ASSERT_DEATH(convert_GTFS_date_to_string("69:42:42"), "overflow < 24 hrs");
}
