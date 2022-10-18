// Copyright 2022
// Bachelor's thesis by Gerrit Freiwald and Robin Wu

#ifndef PARSEARGS_H_
#define PARSEARGS_H_

#include <string>
#include <tuple>

using std::string;
using std::tuple;

// print usage and exit
void print_help_and_exit();

// print folder that will be used for input gtfs and output json files
void print_folder_usage(
    const string& gtfs_folder_name, const string& output_folder_name);

// check if all necessary gtfs files exist in given folder
void check_gtfs_files_exist(const string& folder_name);

// add slash to folder name if not empty
const string add_slash(const string& folder_name);

// check if given folders exist and if all gtfs are avaliable
void check_folder_exists(
    const string& gtfs_folder_name, const string& output_folder_name);

// parse command line arguments, get folder for gtfs and output files
const tuple<string, string> parse_arguments(int argc, char** argv);

#endif  // PARSEARGS_H_
