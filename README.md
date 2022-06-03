# Map Matching Mobile Phones to Public Transit Vehicles

This tool uses [GTFS](https://developers.google.com/transit/gtfs) data from cities to map-match a mobile phone to public transit vehicles.\
See this [blog post](https://ad-blog.informatik.uni-freiburg.de/post/project-map-matching-mobile-phones-to-public-transit-vehicles/) for more detailed information.

## Docker instructions for the backend
The first step is to set up the backend. Run the following commands in the backend folder.

docker command:

    docker build .
    docker run -v ./saved_dictionaries_freiburg:/code/saved_dictionaries_freiburg:ro -v ./GTFS:/code/GTFS:ro -p 5000:5000

run alternatively with docker compose:
    
    docker-compose build
    docker-compose up -d


## Get the app
As the app is a [Flutter](https://flutter.dev) app, it can be run as a mobile app on Android or iOS devices.
It should work on iOS in theory, but has not been tested due to a lack of iOS devices on our side.

Transfer the app-release.apk to your phone and install it.\
When starting the app for the first time, it should ask you to turn on GPS permissions.
If it doesn't, make sure to give the app those permissions in your phones settings.
Open the app and insert server address and port into the prompt.

## Test the map matching without having to get up
As is would be very exhausting and expensive to code on board of a bus or tram from a laptop, to see if the map matching algorithm actually works, we wrote a tool to simplify the task.\
Flutter apps can also be run as a web app, which comes in very handy: In the chrome devtools, one can use the location sensor to manipulate ones position. 
These sensors are also accessible via [selenium](https://www.selenium.dev/documentation/webdriver/bidirectional/chrome_devtools/), 
so we wrote a python script that takes in a list of GPS coordinates and updates the chrome sensor every other second.\
For every trip from the GTFS data, we know the exact shape it moves on. However, the GPS can be quite inaccurate. 
So, in order to simulate a device moving along a shape, we need to 'noisify' the polyline from the shape.\
Unfortunately, the current time of the browser cannot be changed. Therefore, we have to create a second API that annotates our request with timestamps and forwards this updated request to the backend.

backend/GPSTestdata.py does exactly that, as backend/ControlChromeDevTools.py starts a chrome instance showing the frontend.

### Installation
For the frontend, we use [Android Studio](https://developer.android.com/studio) and for the backend [PyCharm](https://www.jetbrains.com/de-de/pycharm/download/).
While we are certain there is another way to run the testing program, we recommend using Android Studio and PyCharm.

### Setting up Android Studio
Follow the [Flutter installation guide](https://docs.flutter.dev/get-started/install).\
After that, make sure to set the web port for the app:\
In Android Studio, click on "Run" in the task bar, then on "Edit Configurations" (somewhere in the middle).
Add `--web-port=21698` to the "Additional run args".

### Updating the config file
Update 'config.yml' in backend folder. Fill in the `SERVER-ADDRESS` and `SERVER-PORT` where the docker backend is running.
The other entries can be changed, but default values should work in most cases. 
`DEBUG-ADDRESS` and `DEBUG-PORT` are of our forwarding server.
`DEVTOOL-PORT` is the port that Chrome dev tool is running on, it must be the same as `--web-port=...`.

### Install dependencies
Go to the backend folder and run:
    
    pip install -r requirements.txt

### Starting the simulation
First, run the frontend (main.dart) using Chrome (web) in the top right corner of your screen in Android Studio.\
After some seconds, a Chrome window should open.

*After* the web app has been started (wait until it is running properly. You don't need to fill in the server address or the port yet), you can start the ControlChromeDevTools.py.\
Another Chrome window will open. In this one, you will need to set `localhost` as the server address  and `5000` as the port (or if changed `DEBUG-ADDRESS` and `DEBUG-PORT`).\
You can now use the app. See how the fake GPS positions are matched to a randomly chosen public transit vehicle. 
You can restart the ControlChromeDevTools.py to get a different random vehicle.
