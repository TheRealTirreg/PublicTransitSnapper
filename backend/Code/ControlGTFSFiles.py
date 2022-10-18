"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
import os
import sys
from subprocess import Popen
from shutil import rmtree
import Utilities as Utils
from ParseConfig import get_city_config_attribute, is_city_in_city_config


# ------------------------------ Fetch GTFS, run pfaedle and create new saved_dictionaries --------------------------- #
def try_to_fetch_gtfs(city: str):
    """
    Fetches latest GTFS files.
    Will create shapes.txt if use_pfaedle is True.

    Input:
        use_pfaedle: https://github.com/ad-freiburg/pfaedle is a very handy tool which can be used to
                create GTFS shapes. Some cities do provide GTFS shapes, some don't.
                If use_pfaedle = True:
                    pfaedle will overwrite the existing shapes.
                Else:
                    No new shapes will be generated. Only the GTFS data will be fetched.
        path_to_gtfs: path where the GTFS files are saved. Changes from city to city!
        path_to_osm: path where the OSM files are saved. Changes from city to city!
        gtfs_link: link to the GTFS files.
        osm_link: link to the OSM files.
    """
    # see if the city has an entry in cities_config.yml
    # will raise an exception if not
    is_city_in_city_config(city)

    use_pfaedle: bool = get_city_config_attribute(city, "generate-new-shapes")
    gtfs_link = get_city_config_attribute(city, "GTFS-link")
    osm_link = get_city_config_attribute(city, "OSM-link")
    path_to_gtfs = "../" + get_city_config_attribute(city, "path-to-GTFS")
    path_to_osm = "../" + get_city_config_attribute(city, "path-to-OSM")

    # Assertions: args cannot be empty
    if use_pfaedle and (not path_to_osm or not osm_link or not path_to_gtfs or not gtfs_link):
        raise AssertionError("If 'use_pfaedle is active, "
                             "make sure to fill all the arguments when calling 'try_to_fetch_GTFS' function\n"
                             "You might want to try adjusting the cities_config.yml")
    elif not use_pfaedle and (not path_to_gtfs or not gtfs_link):
        raise AssertionError("Make sure to fill the arguments 'path_to_gtfs' and 'gtfs_link' "
                             "when calling 'try_to_fetch_GTFS' function with 'use_pfaedle=False'\n"
                             "You might want to try adjusting the cities_config.yml")

    # clear old gtfs-in folder
    if os.path.exists(path_to_gtfs + "/gtfs-in") and len(os.listdir(path_to_gtfs + "/gtfs-in")) > 0:
        print("Deleting old gtfs-in files", flush=True)
        rmtree(path_to_gtfs + "/gtfs-in")
        os.makedirs(path_to_gtfs + "/gtfs-in")
    elif not os.path.exists(path_to_gtfs + "/gtfs-in"):
        os.makedirs(path_to_gtfs + "/gtfs-in")

    # clear old gtfs-out folder
    if os.path.exists(path_to_gtfs + "/gtfs-out") and len(os.listdir(path_to_gtfs + "/gtfs-out")) > 0:
        print("Deleting old gtfs-out files", flush=True)
        rmtree(path_to_gtfs + "/gtfs-out")
        os.makedirs(path_to_gtfs + "/gtfs-out")
    elif not os.path.exists(path_to_gtfs + "/gtfs-out"):
        os.makedirs(path_to_gtfs + "/gtfs-out")

    # clear old OSM folder
    if os.path.exists(path_to_osm) and len(os.listdir(path_to_osm)) > 0:
        print("Deleting old OSM files", flush=True)
        rmtree(path_to_osm)
        os.makedirs(path_to_osm)
    elif not os.path.exists(path_to_osm):
        os.makedirs(path_to_osm)

    print("Downloading GTFS files...", flush=True)
    process_download_gtfs = Popen(["curl", gtfs_link,
                                  "-o", path_to_gtfs + r"/fetched_GTFS.zip"],
                                  stdout=sys.stdout, stderr=sys.stderr)
    process_download_gtfs.wait()

    print(f"Unzipping GTFS files to {path_to_gtfs + '/gtfs-in'}...", flush=True)
    process_unzip_gtfs = Popen(["unzip", path_to_gtfs + r"/fetched_GTFS.zip", "-d", path_to_gtfs + "/gtfs-in"],
                               stdout=sys.stdout, stderr=sys.stderr)
    process_unzip_gtfs.wait()

    # The switzerland GTFS use weird route_types that cannot be processed by pfaedle.
    # Therefore, we need to replace them.
    print("Replacing weird route types if needed", flush=True)
    Utils.replace_route_type(
        routes_file=path_to_gtfs + '/gtfs-in/routes.txt',
        what_to_replace=['1700', '1501'],
        replace_by=['1300', '700']
    )

    print("Removing .zip file", flush=True)
    if os.path.exists(path_to_gtfs + r"/fetched_GTFS.zip"):
        os.remove(path_to_gtfs + r"/fetched_GTFS.zip")

    if use_pfaedle:
        print("Fetching OSM data", flush=True)
        process_download_osm = Popen(["curl", osm_link,
                                     "-o", path_to_osm + r"/fetched_OSM.osm.bz2"],
                                     stdout=sys.stdout, stderr=sys.stderr)
        process_download_osm.wait()

        print(f"Unzipping OSM to {path_to_osm}...", flush=True)
        process_unzip_gtfs = Popen(["bunzip2", path_to_osm + r"/fetched_OSM.osm.bz2"],
                                   stdout=sys.stdout, stderr=sys.stderr)
        process_unzip_gtfs.wait()

        print("Starting pfaedle...", flush=True)
        print(f"OSM-path: {os.path.abspath(path_to_osm)}\n"
              f"GTFS-path: {os.path.abspath(path_to_gtfs)}", flush=True)

        # For pfaedle, "-x" will filter the input OSM file and output a new OSM file which contains exactly the
        # data needed to calculate the shapes for the input GTFS feed and the input configuration.
        # This can be used to avoid parsing (for example) the entire planet.osm on each run.
        # "-D" drops all existing shapes from /gtfs-in
        # "-i" announces the GTFS output path.
        # "-o" announces the output path for the new files.
        process_pfaedle = Popen(["pfaedle", "-D", "-x",
                                 path_to_osm + "/fetched_OSM.osm",
                                 "-i", path_to_gtfs + "/gtfs-in",
                                 "-o", path_to_gtfs + "/gtfs-out"],
                                stdout=sys.stdout, stderr=sys.stderr)

        # wait for pfaedle to finish
        process_pfaedle.wait()

    print("Done fetching new GTFS files.", flush=True)


if __name__ == '__main__':
    try_to_fetch_gtfs("Schweiz")
