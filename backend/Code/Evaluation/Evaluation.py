# Evaluate the performance of map matching
# write the generated files to a folder, so that results can be reproduced
# or used with different parameters
from datetime import datetime
from os.path import isfile
from pickle import load, dump
from time import monotonic
from multiprocessing import Pool, current_process, cpu_count
from random import shuffle
from itertools import repeat
from EvaluationDataset import get_trip_infos, GenerationDataSet


import sys
import os.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from GPSTestdata import generate_noisified_stops_data
from MapMatcher import NetworkOfRoutes
from GTFSContainer import GTFSContainer
from ParseConfig import get_config, get_city_config

# default parameters can be changed here
AVG_SPEED = 14
SIGNAL_EVERY_N_SECONDS = 5
AVG_GPS_ACCURACY_IN_METERS = 16
# generate a now mock dataset
NEW_MOCK_DATA = False
# update the GTFS needed for generating mock data
# needs to be new, for new GTFS data set
NEW_GTFS = False
DATE = datetime(2022, 9, 14, 0, 0)
NUM_STOPS = 4
POINTS_PER_TEST = 10
# new mock data needs to be generated to add noise
ADD_TIME_NOISE = False
TIME_STOP_NOISE = 60
TIME_POSITION_NOISE = 30


def get_random_batches(test_data, num_batches):
    shuffled = test_data.copy()
    shuffle(shuffled)
    return [shuffled[i::num_batches] for i in range(num_batches)]


def gen_mock_data_multiprocess(city, path_to_gtfs, path_to_saved, num_processes=cpu_count()):
    dates_data, tws, map_hash = list(get_trip_infos(city, path_to_gtfs, path_to_saved, NEW_GTFS))
    split_data = zip(get_random_batches(list(dates_data.items()), num_processes), repeat(tws), repeat(map_hash))
    with Pool(processes=num_processes) as pool:
        result = pool.map(gen_mock_data, split_data)

        test_data = []
        for tests in result:
            test_data.extend(tests)

    return test_data


def gen_mock_data(trips_dates):
    trips_to_generate, trips_with_stops, map_hash = trips_dates
    path_to_gtfs = get_paths_tz(get_config(file_name="../../config.yml")["CITY"])[0]
    gen_dataset = GenerationDataSet(path_to_gtfs)
    ret = []

    num_test = len(trips_to_generate)
    print(f"Starting {current_process().name} with {num_test} tests")
    num_test_modulo = num_test // 10
    for i, (trip_id, trip_info) in enumerate(trips_to_generate):
        active_weekdays = trip_info[1]
        extra_dates = trip_info[3]
        removed_dates = trip_info[4]

        # check if the trip is active on the given date
        if (DATE.weekday() in active_weekdays and DATE.date() not in removed_dates) or DATE.date() in extra_dates:
            trip_segments = map_hash[trips_with_stops[trip_id][0]][1]
            test_data_trip = generate_noisified_stops_data(
                gen_dataset, trip_id, trip_segments, NUM_STOPS, POINTS_PER_TEST,
                AVG_SPEED, SIGNAL_EVERY_N_SECONDS, AVG_GPS_ACCURACY_IN_METERS, DATE,
                add_noise=ADD_TIME_NOISE, noise_stop=TIME_STOP_NOISE, noise_point=TIME_POSITION_NOISE)

            if test_data_trip:
                ret.append((trip_id, test_data_trip))

        # debug:
        if not i % num_test_modulo:
            time = datetime.now().time()
            percentage = round(i / num_test * 100, 3)
            name = current_process().name
            print(f"{str(time)} {percentage}%\tof tests generated {name}", flush=True)

    return ret


def read_mock_data(city, path_to_gtfs, path_to_saved, new_mock_data: bool = False, num_processes=cpu_count()):
    file_name = city + r".pkl"
    if isfile(file_name) and not new_mock_data:
        with open(file_name, "rb")as f:
            mock_data = load(f)
    else:
        mock_data = gen_mock_data_multiprocess(city, path_to_gtfs, path_to_saved, num_processes)
        with open(file_name, "wb") as f:
            dump(mock_data, f)
    print("Finished generating mock data.\n\n\n\n")
    return mock_data


def gen_network(path_to_gtfs, path_saved, timezone, config):

    gtfs_container = GTFSContainer(
        path_gtfs=path_to_gtfs, path_saved_dictionaries=path_saved, update_dicts=config["UPDATE_DICTS"], verbose=False)

    return NetworkOfRoutes(
        gtfs_container, print_time=False, prefer_last_trip=config["PREFER_LAST_TRIP"],
        baseline=config["BASELINE"], baseline_hmm=config["BASELINE_HMM"], time_after=config["TIME_AFTER"], slack=config["SLACK"],
        earliness=config["EARLINESS"], delay=config["DELAY"], timezone=timezone)


def get_paths_tz(city):
    city_config = get_city_config(city, file_name="../../cities_config.yml")
    read_path = "../../" + city_config["path-to-GTFS"] + "/gtfs-out/"
    save_path = "../../saved_dictionaries/" + city + "/"
    tz = city_config["timezone"]
    return read_path, save_path, tz


def evaluate(test_data):
    """
    run the evaluation, no realtime data for now
    """
    num_test = len(test_data)
    print(f"Starting {current_process().name} with {num_test} tests")

    config = get_config(file_name="../../config.yml")
    network = gen_network(*get_paths_tz(config["CITY"]), config)

    evaluation_accuracy = []
    evaluation_time = []
    evaluation_map = []

    num_test_modulo = num_test // 10
    for i, (correct_trip_id, test_instances) in enumerate(test_data):
        accuracy_trip = 0
        matched_trip_ids = []
        matched_evaluation_times = []
        num_evaluated = 0
        for correct_points, trip_gps_points in test_instances:
            route = list(map(lambda x: (x[0][0], x[0][1], x[1] // 1000), trip_gps_points))

            start_time = monotonic()
            most_likely_dict = network.find_route_name(route, dist=0.1)
            end_time = monotonic()

            matched_trip_id = most_likely_dict["trip_id"]
            run_time = end_time - start_time
            evaluation_time.append(run_time)

            matched_trip_ids.append(matched_trip_id)
            matched_evaluation_times.append(run_time)

            num_evaluated += 1
            if matched_trip_id == correct_trip_id:
                accuracy_trip += 1

        # debug:
        if not i % num_test_modulo:
            time = datetime.now().time()
            percentage = round(i / num_test * 100, 3)
            name = current_process().name
            print(f"{str(time)} {percentage}%\tof tests done {name}", flush=True)

        if num_evaluated == 0:
            print(f"no evaluation for trip {correct_trip_id}", flush=True)
            continue

        accuracy = accuracy_trip / num_evaluated
        evaluation_accuracy.append(accuracy)
        evaluation_map.append((correct_trip_id, accuracy, matched_trip_ids,
                               matched_evaluation_times))

    return evaluation_accuracy, evaluation_time, evaluation_map


def run_evaluation_multiprocess(num_processes=cpu_count()):
    city = get_config(file_name="../../config.yml")["CITY"]
    test_data = read_mock_data(city, *get_paths_tz(city)[:2], NEW_MOCK_DATA, num_processes)

    split_shuffled = get_random_batches(test_data, num_processes)

    with Pool(processes=num_processes) as pool:
        result = pool.map(evaluate, split_shuffled)

        all_accuracy, all_time, all_dist, all_map = [], [], [], []
        for eval_accuracy, eval_time, eval_map in result:
            all_accuracy.extend(eval_accuracy)
            all_time.extend(eval_time)
            all_map.extend(eval_map)

    with open(city + "TimeEvaluation.txt", "w") as time_file:
        time_file.write(str(all_time))
        time_file.close()
    with open(city + "AccuracyEvaluation.txt", "w") as accuracy_file:
        accuracy_file.write(str(all_accuracy))
        accuracy_file.close()
    with open(city + "MapEvaluation.txt", "w") as map_file:
        map_file.write(str(all_map))
        map_file.close()

    calc_averages(city)


def calc_averages(city):
    with open(city + "AccuracyEvaluation.txt", "r") as f:
        accuracies = f.read()
        acc_lst = eval(accuracies)
        no_zero = list(filter(lambda x: x != 0, acc_lst))

        avg_acc = sum(acc_lst) / len(acc_lst)
        avg_acc_nz = sum(no_zero) / len(no_zero)

    with open(city + "TimeEvaluation.txt", "r") as f:
        times = f.read()
        tim_lst = eval(times)
        avg_tim = sum(tim_lst) / len(tim_lst)

    with open(city + "Evaluation.txt", "w") as avgs:
        avgs.write("Averages:\n")
        avgs.write("Accuracy: " + str(avg_acc) + "\n")
        avgs.write("Accuracy_nz: " + str(avg_acc_nz) + "\n")
        avgs.write("Time: " + str(avg_tim) + "\n")
        avgs.close()


if __name__ == '__main__':
    # insert number of processes as argument
    run_evaluation_multiprocess(cpu_count() // 2)
