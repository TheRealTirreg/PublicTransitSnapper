# PublicTransitSnapper: Dynamic Map-Matching To Public Transit Vehicles

This tool uses [GTFS](https://developers.google.com/transit/gtfs) data 
from cities to match a mobile phone to public transit vehicles.\
It consists of a backend and a frontend.
The backend calculates the public transit vehicle matching and other relevant information.
The frontend displays whether the user is 'snapped' to a public transit vehicle or not, as well as other features.

As is would be very exhausting and expensive to code on board of a bus or tram from a laptop, 
to see if the map matching algorithm actually works, we wrote a tool to simplify the task.\
Flutter apps can also be run as a web app, which comes in very handy: In the chrome devtools, 
one can use the location sensor to manipulate ones position. 
These sensors are also accessible via 
[selenium](https://www.selenium.dev/documentation/webdriver/bidirectional/chrome_devtools/), 
so we wrote a test tool that takes in a list of GPS coordinates and updates the chrome sensor every other second.\
For every trip from the GTFS data, we know the exact shape it moves on. However, the GPS can be quite inaccurate. 
So, in order to simulate a device moving along a shape, we need to 'noisify' the polyline from the shape.\
Unfortunately, the current time of the browser cannot be changed. 
Therefore, we have to create a proxy server that changes the timestamps of our request 
and forwards this updated request to the backend.

# Content
1. [Configuration](#configuration)
   1. [Backend Configuration](#backend-configuration)
      1. [General Configuration](#general-configuration)
      2. [Choosing the GTFS Dataset](#choosing-the-gtfs-dataset)
      3. [Automatically Fetching Few GTFS](#automatically-fetching-few-gtfs)
      4. [GTFS Realtime](#gtfs-realtime)
   2. [Frontend Configuration](#frontend-configuration)
   3. [Test Tool Configuration](#test-tool-configuration)
2. [Setup](#setup)
   1. [Run Both the Backend and the Frontend](#1-run-both-the-backend-and-the-frontend)
   2. [Run Only the Backend](#2-run-only-the-backend)
       1. [Run as a docker container](#21-run-as-a-docker-container)
       2. [Run Manually](#22-run-manually)
   3. [Run only the frontend web app](#3-run-only-the-frontend-web-app)
       1. [Run as a docker container](#31-run-as-a-docker-container)
       2. [Build Manually](#32-build-manually)
   4. [Run only the frontend mobile app](#3-run-only-the-frontend-web-app)
      1. [Run with pre-built APK](#41-run-with-pre-built-apk)
      2. [Build Manually](#42-build-manually)
   5. [Setup Test Tool](#5-setup-test-tool)
3. [Backend File Structure](#backend-file-structure)

# Configuration
## Backend Configuration
### General Configuration
The `config.yml` in the backend folder contains options for the backend.
Most importantly, set the `CITY` to the desired city.
You can manually put the GTFS data set into the desired folder.
Alternatively enable `UPDATE_GTFS`, which pulls the GTFS from the link provided in `cities_config.yml`.
Every city you use needs to be specified in the `cities_config.yml`.
See the files for detailed explanation of entries needed.

When starting the backend for the first time you need to set `UPDATE_DICTS`.
If you did not manually put the GTFS data in the folder set `UPDATE_GTFS_ON_STARTUP` to True, to fetch the GTFS data.

### Choosing the GTFS Dataset
In `cities_config.yml`, you can enter information on the GTFS files you want to use.
Follow the instructions in the file to add another city.
Make sure to choose the city in the `config.yml` afterwards.

### Automatically Fetching Few GTFS
We wrote a tool that can fetch new GTFS data on a regular basis. If the public transit agency updates their GTFS dataset
on the same link, you can choose the `UPDATE_GTFS` option in the `config.yml` file.
Also adjust the `UPDATE_GTFS_ON_STARTUP`, `UPDATE_TIME` and `UPDATE_FREQUENCY` parameters accordingly.

Our tool will fetch the latest GTFS dataset at `UPDATE_TIME` (!UTC!) every `UPDATE_FREQUENCY` days,
temporarily take down the API, and then start with the new GTFS dataset.

Some agencies (like the HVV for Hamburg, Germany) do not provide static links for their GTFS data.
They publish their updated datasets under a new link. Before using `UPDATE_GTFS`, make sure that your agency
provides their GTFS updates under the same link. Otherwise, a manual restart is needed.

### GTFS Realtime
GTFS Realtime is also supported. In this case, enable `USE_GTFS_RT` in `config.yml`.
Additional entries are needed in `cities_config.yml`.
Since every public transit agency provides the feed in different ways, we cannot implement a version that works for all.
A function for fetching might need to be implemented in `Code/FetchRealtimeUpdate.py`.
Implement a function and add to `map_city_to_getter_function`.
If your city works with one of our implemented getter functions, 
you still need to add it to `map_city_to_getter_function`.
Sometimes an API-Key is needed. Create a `credentials.yml` insert API-KEY-NAME: "API-KEY" into the file.
In `cities_config.yml` you can reference the API-KEY-NAME.

## Frontend Configuration
For easy testing, the frontend prompts for server address and port on startup.
Alternatively, in the frontend folder, you will find a `config.yml` file. 
Fill the `SERVER_ADDRESS` and the `SERVER_PORT` so they match to the backend config.
This determines the addresses and ports that appear when pressing the `SERVER`
and `PROXY` buttons when starting the app.

## Test Tool Configuration
The test tool creates a proxy server that forwards the requests to the backend.
Update `config.yml` in the backend folder. 
Fill in the `SERVER_ADDRESS` and `SERVER_PORT` where the backend is running.
The frontend web app should be running on localhost:`DEVTOOL_PORT`.

Insert `PROXY_ADDRESS` and `PROXY_PORT` for the forwarding server.

You can change the `PROXY_ADDRESS` and `PROXY_PORT` in the frontend `config.yml` as well. 
The values can be selected on frontend startup with the `PROXY` button. 

# Setup
We provide different methods to set up the project.
1. Run both the backend and frontend web app.
2. Run only the backend. This can be used if you only want to use the mobile app.
3. Run only the frontend web app. Needs a running backend.
4. Run only the mobile app. Needs a running backend.

Moreover, we provide a tool for testing without sitting in a public transit vehicle.
5. Setup test tool.

When using the web app, use a chromium based browser (e.g. Chrome, Vivaldi, Opera, Edge, ...).
Others may not display everything correctly.

## 1. Run Both the Backend and the Frontend
### With Dockerfile
The `Dockerfile` is in the root folder. Run the following commands.

    docker build -t publictransitsnapper .
    docker run -it -v $PWD/backend/saved_dictionaries:/app/saved_dictionaries:rw -v $PWD/backend/GTFS:/app/GTFS:rw -p 5000:5000 -p 21698:21698 publictransitsnapper

### With Docker Compose
The `docker-compose.yml` is in the root folder. Run the following commands.

    docker-compose build
    docker-compose up

## 2. Run Only the Backend
The backend can either be run as a Docker container or manually.

### 2.1 Run as a docker container
### With Dockerfile
The `Dockerfile` in the backend folder. Run the following commands in the backend folder.

    docker build -t publictransitsnapper .
    docker run -v $PWD/saved_dictionaries:/app/saved_dictionaries:rw -v $PWD/GTFS:/app/GTFS:rw -p 5000:5000 publictransitsnapper-backend

### With Docker Compose
Use the `docker-compose.yml` in the backend folder. Run the following commands.
    
        docker-compose build
        docker-compose up

### 2.2 Run Manually
The backend can also be run on a linux computer.
Change into the backend directory and run the following commands.

1. Install [pfaedle](https://github.com/ad-freiburg/pfaedle)
2. Install dependencies:


    apt install clang, make, libgtest-dev, unzip, bzip2 and curl
    pip install -r requirements_docker.txt
3. Install parser for GTFS files:


    make -C Code/parseGTFS install
4. Start the server:

    
    python3 Code/API.py

## 3. Run only the frontend web app
### 3.1 Run as a docker container
### With Dockerfile
Use the `Dockerfile` in the frontend folder. Run the following commands in the frontend folder.

    docker build -t publictransitsnapper-frontend .
    docker run -p 21698:21698 publictransitsnapper-frontend

### With Docker Compose
Use the `docker-compose.yml` in the frontend folder. Run the following commands in the frontend folder.

        docker-compose build
        docker-compose up

### 3.2 Build Manually
Follow the [Flutter installation guide](https://docs.flutter.dev/get-started/install).
Once installed, run the following commands in the frontend folder.

    flutter build web


## 4. Run only the frontend mobile app
### 4.1 Run with pre-built APK
As the app is a [Flutter](https://flutter.dev) app, it can be run as a mobile app on Android or iOS devices.
It should work on iOS in theory, but has not been tested due to a lack of iOS devices on our side.
Currently, we only support Android 10+.

Transfer the `app-release.apk` to your phone and install it.\
When starting the app for the first time, it should ask you to turn on GPS permissions.
If it doesn't, make sure to give the app those permissions in your phones settings.
Open the app and insert username, server address and port into the prompt.

### 4.2 Build Manually
Follow the [Flutter installation guide](https://docs.flutter.dev/get-started/install).
Once installed, run the following command in the frontend folder.

    flutter build apk

## 5. Setup Test Tool
Install the [Google Chrome](https://www.google.com/chrome/) browser.

Run the web app locally on your machine.
Make sure to run the web app on the `DEVTOOL-PORT` in the backend `config.yml`.

In backend/Code run:
    
    pip install -r requirements.txt
    python3 ControlChromeDevTools.py

# Backend File Structure
The backend has four folders:

The `Code` folder contains all Python and C++ code files.

The `Code/Evaluation` folder contains the evaluation scripts. They are not production ready.
You may need to follow the [Run Manually](#22-run-manually) setup instructions.

The `DebugTools` folder contains tools we wrote and used for debugging purposes. 
For example, we wrote a tool to draw a shape given a GTFS trip_id or a shape_id. 
Another tool fetches all relevant information on one trip_id. 
Another tool filters a GTFS dataset to remove all routes of a given agency and their references.
All these tools are experimental and to be used at one's own risk.
These are not production ready.

The `GTFS` folder contains raw GTFS files, OSM (OpenStreetMaps) files, 
as well as files with shapes generated by [pfaedle](https://github.com/ad-freiburg/pfaedle).
The subdirectories within the GTFS folder are generated when 
starting the backend server with the GTFS dataset specified in the `config.yml`.

The `saved_dictionaries` folder contains files generated by the GTFSparser (which can be found in the `Code` folder).
These files are being preprocessed once a new GTFS dataset has been pulled. 
The Python part of the backend then uses the preprocessed files to generate the internal data structures.
