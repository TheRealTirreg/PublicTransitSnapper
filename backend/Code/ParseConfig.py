"""
Copyright 2022
Bachelor's thesis by Gerrit Freiwald and Robin Wu
"""
from yaml import safe_load, YAMLError
from typing import Union


def get_config(file_name: str = r"../config.yml", dev_tools: bool = False) -> dict:
    """
    Gets settings from the config.yml file.

    Below are the available settings with default values.
    config_all settings are always needed.
    config_api only needed when running the flask api.
    config_dev only needed when controlling chrome with mock gps data.
    """
    # values to check, if they do not exist, but are needed, use given default values
    config_all = {"CITY": "Freiburg", "PREFER_LAST_TRIP": False, "BASELINE": False, "BASELINE_HMM": False,
                  "TIME_AFTER": False, "SLACK": 0.2, "EARLINESS": 1, "DELAY": 5}
    config_api = {"UPDATE_DICTS": True, "USE_GTFS_RT": False, "UPDATE_GTFS": False, "UPDATE_GTFS_ON_STARTUP": False,
                  "UPDATE_TIME": "00:00:00", "UPDATE_FREQUENCY": 7, "DEBUG": False}
    config_dev = {"SERVER_ADDRESS": "localhost", "SERVER_PORT": 5000,
                  "PROXY_ADDRESS": "localhost", "PROXY_PORT": 5001,
                  "DEVTOOL_PORT": 21698, "NEW_GTFS": True}

    config = {}
    try:
        with open(file_name, "r") as stream:
            try:
                config = safe_load(stream)
            except YAMLError as e:
                print(e)
    except FileNotFoundError as e:
        print(e)
        print("Error while reading config file %s, using default config" % file_name)

    def check_config(config_check: dict):
        nonlocal config
        for param, default in config_check.items():
            if param not in config:
                config[param] = default
                print(f"{param} not found in config file, using default value {default}")

    # config that are always needed
    check_config(config_all)

    # config for api run
    if not dev_tools:
        check_config(config_api)

    # config for dev tools run
    if dev_tools:
        check_config(config_dev)

    return config


def get_credentials(params: list, file_name: str = "../credentials.yml") -> dict:
    """
    Read API key from credentials.yml
    """
    with open(file_name, "r") as f:
        try:
            credentials = safe_load(f)
            if not params:
                raise ValueError("No parameters given")
            found_error = False
            for param in params:
                if param not in credentials:
                    print(f"{param} not found in config file, please check {file_name}")
                    found_error = True
                if found_error:
                    raise ValueError("Missing above config parameters")
        except (YAMLError, ValueError) as e:
            print(e)
            exit(1)
    return credentials


def get_city_config(
        city: str, params: list = None, gtfs_rt: bool = False, file_name: str = "../cities_config.yml") -> dict:
    """
    Gets the config parameters from cities_config.yml file.
    Either use the given parameters or only check the once given in params.
    If using given parameters, specify gtfs_rt to True if you want to use gtfs_rt, feed.
    """
    config_all = ["generate-new-shapes", "path-to-GTFS", "path-to-OSM", "GTFS-link", "OSM-link", "timezone"]
    config_rt = ["GTFS-RT-feed"]
    config_rt_opt = ["RT-API-key", "RT-UPDATE-PERIOD"]

    config = {}
    try:
        with open(file_name, "r") as stream:
            try:
                yml = safe_load(stream)
            except YAMLError as e:
                print(e)
            try:
                config = yml[city]
            except KeyError:
                raise ValueError(f"{city} is not in cities_config.yml.")
    except FileNotFoundError as e:
        print(e)
        print("Error while reading config file %s" % file_name)

    # config that are always needed
    to_check = params if params else (config_all + config_rt if gtfs_rt else config_all)

    try:
        found_error = False

        for param in to_check:
            if param not in config:
                print(f"{param} not found in config file, please check {file_name}")
                found_error = True

        if found_error:
            raise ValueError("Missing above config parameters")

        # additionally check if api key is provided for gtfs_rt
        if gtfs_rt:
            config["API-key"] = True
            for param in config_rt_opt:
                if param not in config:
                    config["API-key"] = False

    except ValueError as e:
        print(e)
        exit(1)

    return config


# ------------------------------------------ Read cities_config.yml -------------------------------------------------- #
def is_city_in_city_config(city: str) -> bool:
    """
    Checks whether the given string is in cities_config.yml
    """
    with open("../cities_config.yml", "r") as stream:
        try:
            cities_config_dct = safe_load(stream)
            if city not in cities_config_dct:
                raise YAMLError(f"{city} is not in cities_config.yml."
                                f"Try changing the cities_config.yml accordingly.")
            return True
        except YAMLError as e:
            raise e


def get_city_config_attribute(city: str, city_attribute: str) -> Union[str, bool]:
    """
    Returns a path like 'GTFS/Freiburg/VAG' when city == 'Freiburg'

    Input:
        city: e.g.: 'Freiburg', see cities_config.yml.
        city_attribute: must be one of the following:
            ['generate-new-shapes', 'path-to-GTFS', 'path-to-OSM', 'GTFS-link', 'OSM-link']
            (see cities_config.yml file for more information)

    Example cites_config_dct:
    {
        'Freiburg':
        {
            'generate-new-shapes': True,
            'path-to-GTFS': 'GTFS/Freiburg/VAG',
            'path-to-OSM': 'GTFS/Freiburg/OSM',
            'GTFS-link': 'https://www.vag-freiburg.de/fileadmin/gtfs/VAGFR.zip',
            'OSM-link': 'http://download.geofabrik.de/europe/germany/baden-wuerttemberg/freiburg-regbez-latest.osm.bz2'
        },
        'Hamburg':
        {
            'generate-new-shapes': True,
            'path-to-GTFS': 'GTFS/Hamburg/HVV',
            'path-to-OSM': 'GTFS/Hamburg/OSM',
            'GTFS-link': 'https://daten.transparenz.hamburg.de/Dataport.HmbTG.ZS.Webservice.GetRessource100/
                GetRessource100.svc/40c90bad-79e6-4f03-ac33-8f1f7095f7a1/Upload__HVV_Rohdaten_GTFS_Fpl_20220408.zip',
            'OSM-link': 'https://download.geofabrik.de/europe/germany/hamburg-latest.osm.bz2'
        },
        'Schweiz': {
            'generate-new-shapes': True,
            'path-to-GTFS': 'GTFS/Schweiz/SBB',
            'path-to-OSM': 'GTFS/Schweiz/OSM',
            'GTFS-link': 'https://www.avv-augsburg.de/fileadmin/user_upload/OpenData/GTFS_AVV.zip',
            'OSM-link': 'https://download.geofabrik.de/europe/switzerland-latest.osm.bz2'
        }
    }
    """
    with open("../cities_config.yml", "r") as stream:
        try:
            cities_config_dct = safe_load(stream)
            if city not in cities_config_dct:
                raise YAMLError("")

            if city_attribute not in cities_config_dct[city]:
                raise YAMLError(f"{city} does not have a '{city_attribute}' attribute! "
                                f"Try changing the cities_config.yml accordingly.")
            return cities_config_dct[city][city_attribute]

        except YAMLError as e:
            raise e


if __name__ == '__main__':
    print(get_city_config("Schweiz", gtfs_rt=True))
    """
    print(get_config())
    print(get_config(dev_tools=True))
    print(get_config("thisFileDoesNotExists.yml"))
    """
