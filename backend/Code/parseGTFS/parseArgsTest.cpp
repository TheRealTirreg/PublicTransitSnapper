// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#include <gtest/gtest.h>
#include <string>
#include <tuple>
#include "./parseArgs.h"

using std::make_tuple;
using std::string;

// ___________________________________________________________________________
TEST(parseArgsTest, print_help_and_exit) {
    ::testing::FLAGS_gtest_death_test_style = "threadsafe";
    ASSERT_DEATH(print_help_and_exit(), "Usage: ");
}

// ___________________________________________________________________________
TEST(parseArgsTest, print_folder_usage) {
    {
        string gtfs_folder = "";
        string output_folder = "";
        testing::internal::CaptureStdout();
        print_folder_usage(gtfs_folder, output_folder);
        string output = testing::internal::GetCapturedStdout();
        ASSERT_EQ(output, "GTFS   folder: .\nOutput folder: .\n");
    }
    {
        string gtfs_folder = "test1";
        string output_folder = "test2";
        testing::internal::CaptureStdout();
        print_folder_usage(gtfs_folder, output_folder);
        string output = testing::internal::GetCapturedStdout();
        ASSERT_EQ(output, "GTFS   folder: test1\nOutput folder: test2\n");
    }
}

// ___________________________________________________________________________
TEST(parseArgsTest, check_gtfs_files_exist) {
    ::testing::FLAGS_gtest_death_test_style = "threadsafe";
    ASSERT_DEATH(check_gtfs_files_exist(""), "Error: ");
    ASSERT_EXIT({check_gtfs_files_exist("test_files/"); exit(EXIT_SUCCESS); },
                 ::testing::ExitedWithCode(0), "");
}

// ___________________________________________________________________________
TEST(parseArgsTest, add_slash) {
    ASSERT_EQ(add_slash(""), "");
    ASSERT_EQ(add_slash("test_files"), "test_files/");
    ASSERT_EQ(add_slash("test_files/"), "test_files/");
}

// ___________________________________________________________________________
TEST(parseArgsTest, check_folder_exists) {
    ::testing::FLAGS_gtest_death_test_style = "threadsafe";
    ASSERT_DEATH(check_folder_exists("", ""), "Error: ");
    ASSERT_DEATH(check_folder_exists("", "thisFolderDoesNotExist"), "Error: ");
    ASSERT_DEATH(check_folder_exists("test_files/", "thisFolderDoesNotExist"),
                 "Error: ");
    ASSERT_EXIT({check_folder_exists("test_files/", ""); exit(EXIT_SUCCESS); },
                 ::testing::ExitedWithCode(0), "");
}

// ___________________________________________________________________________
TEST(parseArgsTest, parse_arguments) {
    {
        int argc = 1;
        char* argv[1];
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Error: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 2;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("help")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Usage: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 2;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("-h")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Usage: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 2;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("thisFolderDoesNotExist")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Error: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 2;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("test_files")};
        testing::internal::CaptureStdout();
        ASSERT_EXIT({parse_arguments(argc, argv); exit(EXIT_SUCCESS); },
                    ::testing::ExitedWithCode(0), "");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 3;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("42"),
                        const_cast<char*> ("thisFolderDoesNotExist")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Usage: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 3;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("-o"),
                        const_cast<char*> ("test_files")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Error: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 4;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("42"), const_cast<char*> ("42"),
                        const_cast<char*> ("thisFolderDoesNotExist")};
        testing::internal::CaptureStdout();
        ASSERT_DEATH(parse_arguments(argc, argv), "Usage: ");
        string output = testing::internal::GetCapturedStdout();
    }
    {
        int argc = 4;
        char* argv[] = {const_cast<char*> ("coolProgrammName"),
                        const_cast<char*> ("test_files"),
                        const_cast<char*> ("-o"),
                        const_cast<char*> ("test_files/jsons")};
        testing::internal::CaptureStdout();
        ASSERT_EQ(parse_arguments(argc, argv),
                  make_tuple("test_files/", "test_files/jsons/"));
        string output = testing::internal::GetCapturedStdout();
    }
}
