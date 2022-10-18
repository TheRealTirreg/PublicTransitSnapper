---
title: "Project Map Matching Mobile Phones to Public Transit Vehicles"
date: 2022-05-17T12:12:50+01:00
author: "Gerrit Freiwald and Robin Wu"
authorAvatar: "img/ada.jpg"
tags: ["map-matching", "GTFS", "public transit", "mobile phones", "flutter"]
categories: ["project"]
image: "img/freiburg-nahverkehr.jpg"
draft: true
---
Map matching can be used to match a given sequence of GPS points to a digital model of the real world.
'Traditional' map matching, like navigation systems for cars, uses a static map for the matching.
In contrast, when working with a public transit vehicle network, the 'map' contains the positions of each vehicle, which are highly dynamic.

# Content
1. [Introduction](#introduction)
2. [Backend](#backend)
    1. [Introduction to GTFS](#introduction-to-gtfs)
    2. [Map matching to a dynamic map](#map-matching-to-a-dynamic-map)
        1. [Markov Chain](#markov-chain)
        2. [Transition probability](#transition-probability)
        3. [Fast graph building](#fast-graph-building)
    3. [Flask as our API](#flask-as-our-api)
3. [Frontend](#frontend)
    1. [Flutter as our framework](#flutter-as-our-framework)
    2. [Content of the app](#content-of-the-app)
4. [Testing](#testing)
    1. [Selenium for manipulating a devices GPS location](#using-selenium-to-manipulate-a-devices-gps-location)
    2. [Generating fake GPS data](#generating-fake-gps-data)
5. [Installation](#installation)

# Introduction
Consider the following scenario: you are sitting in a public transit vehicle and you are interested in the available 
connections at the next stop, or the current delay of your vehicle, or you have changed your desired destination 
and want to calculate a new route, using the public transit vehicle you are currently in as a starting point. 
To do all this, your device has to know which vehicle it is currently travelling in. This is a map matching problem, 
but the "map" (the positions of all vehicles in the network) is not static, but highly dynamic. 
The goal of this project is to develop an app and a dynamic map matching backend which "snaps" the device to the most likely public transit vehicle.\
In this article, we are going to discuss our implementation of a dynamic map matcher and, 
next to an abstract about our frontend, a way to test code while working with GPS data and moving vehicles.

# Backend
## Introduction to GTFS
The network of public transit vehicles is typically described with the [GTFS standard](https://developers.google.com/transit/gtfs). 
This standard includes timetable and geographic data of each vehicle. 
It is split into multiple files in CSV format and is usually published by the respective transit agency. 
The GTFS standard also includes an extension for real time data. We will only use the static data for this project, 
but will look into real time data in the near future for increased accuracy.

The most important files for our application are the trips.txt, shapes.txt, stop.txt and stop_times.txt. 

**trips.txt**\
Every public transit vehicle route can have multiple trips. All trips are identified by a unique trip_id. A trip has a shape_id and references the service dates.

**shapes.txt**\
Every trip of a public transit vehicle follows a specific shape. 
For every shape_id there is a sequence of GPS points that describe the shape.

**stops.txt**\
It contains the GPS location and the name of each stop.

**stop_times.txt**\
This file contains arrival and departure times for every stop on each trip.

## Map matching to a dynamic map
The shapes that are used by the public transit vehicle network can be represented as a directed graph \\(G_{network}\\).
In this graph each GPS point of a shape is represented as a node and successive points in a shape are connected with a directed edge.
We get a list \\(C\\) of GPS points including timestamps from the mobile device.
Our goal is to match the GPS points of \\(C\\) to the most likely path in \\(G_{network}\\), that also fits to the given timestamps.

### Markov Chain
The map matching can be solved by using a [Markov Chain](https://en.wikipedia.org/wiki/Markov_chain).
We can model the Markov Chain by creating a directed graph \\(G_{markov}\\).
Each node represents a possible edge \\(e \in G_{network}\\) and the edges of \\(G_{markov}\\) contain the probability of a transition from one node to another \\(P_{transition}(e^1 \to e^2)\\).
We create a starting node, and then add all edges that are close to the first GPS point \\(c_1 \in C\\). 
Then, we add edges between the starting node and every node from the first GPS point \\(c_1\\). 
After that, we add all edges that are close to the second GPS point and connect these with the nodes of the previous GPS point. 
We repeat this for each GPS point in \\(C\\). In the end, we add an end node and connect it to the nodes of the last GPS point.
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/markov_chain.png" title="Markov Chain"></img>
If we assign meaningful transition probabilities to the edges in \\(G_{markov}\\), we can find the shortest path from the start node to the end node. 
This will give us edges that are on a path that fits best to the GPS points.
With this in mind, we do not really have probabilities, but instead those can be thought of as weights. 
We use [Djikstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra's_algorithm), which finds the shortest path by summing up all the weights on a path. 
As a consequence, if a path has higher probability, the weight needs to be smaller.
Note that the Djikstra's algorithm typically adds all the weights together, but probabilities are usually multiplied. 
This is why we use the logarithmic space for the probabilities. Hence, adding weights corresponds to multiplying the squared probabilities.

### Transition probability
The transition probability describes the likelihood of getting from one state in the Markov Chain to another.
As a reminder, the transition probability is the weight from a node \\(e^1\\) to one of its outgoing neighbors \\(e^2\\) in \\(G_{markov}\\).
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/transition.png" title="Transition"></img>
Firstly, each node represents an edge, and we want to include the length of the edge in the weight. 
The length can be calculated with the [great circle distance](https://en.wikipedia.org/wiki/Great-circle_distance) between the two end points of an edge.
Then, we try to find the shortest path from \\(e^1\\) to \\(e^2\\) within \\(G_{network}\\).
We add the lengths of the shortest path to the transition probability. 
Furthermore, we need to consider the direction of travel. This is important for shapes that are close to each other, but go in opposite directions.
Since we are getting all close edges within a 100 meters radius, the opposite direction is a possibility in the Markov Chain.
If we remember the order of the edges in a shape, we can check if the edges are in ascending order oder descending order.
Travelling in descending order means that we are travelling in the opposite direction of the shape. Thus, we penalize this direction.
In contrast, an ascending order corresponds to the correct direction, so we just set the penalty to 0.
\begin{align*}
    P_{transition}(e^1 \to e^2) &= ||e^1||_{great\\_circle} + ||e^2||_{great\\_circle}\newline
    &\phantom{\text{= }} + \text{len_shortest\_path}(e^1, e^2) + \text{direction\_penalty}(e^1, e^2)
\end{align*}
If there is no such direct path available, we penalize this path by adding a high weight.
This has the effect that this path can then still be matched if there is no other possibility. This can happen due to a transfer between vehicles.\
As the start and end nodes of \\(G_{markov}\\) do not represent edges, we need a different transition probability for those.
For the start node, we use the shortest great circle distance of the first GPS point to the first edge as weight.
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/transition_start.png" title="Transition from Start"></img>
In the same manner, we calculate the distance between the last edge to the last GPS point.
As a result, we get a shape where the start and end points are close to the GPS points.

### Fast graph building
In order to generate the most likely path, we need to quickly build a graph and also try to keep the graph as small as possible. 
We could just add all edges that are close to the GPS points, e.g. in a 100 meters radius, to our Markov Chain.
This works well in areas with little traffic and not many public transit routes. However, we run into performance issues in busy areas such as city centers. 
This is because calculating the shortest path takes much longer in a bigger Markov Chain graphs.
In order to mitigate this issue, we filter unnecessary nodes.\
Firstly, for every GPS point, we fetch all edges that are within a 100 meters radius. 
Then, we only consider those edges that have traffic of a public transit vehicle at the included timestamp.\
For that, we can pre-calculate the timeframe where a given vehicle is active on a particular edge. 
We can only fetch times for each stop of the vehicle from the GTFS data. Typically, there are multiple edges between the stops. 
Inorder to minimize the number of edges we get, we try to calculate an exact time frame for each edge between two stops.
The main difficulty in this approach is that the coordinates of a stop do not lie on the edges of a shape for a trip.
Thus, we need to split the shape at the stops. We can project every stop coordinate onto the shape line to find the closest edge. Then we can split the edge at these projected points.
As this calculation is computationally rather expensive, we can pre-calculate the split shapes for each trip and use them to calculate the time frame later.\
We only include the edge in \\(G_{markov}\\) if there is any traffic on the edge at the timestamp. 
With this approach we can greatly reduce the number of edges and therefore get results much faster.

## Flask as our API
Map matching is computationally expensive and requires a representation of the public transit network in memory.
Therefore, it is not feasible to calculate the Markov Chain on a mobile device such as a smartphone.
Instead, the mobile device continuously records GPS points with a corresponding timestamp. Then, these GPS points are sent to our API on a server.
The transit network is already loaded in memory on the server, so it can quickly calculate the map matching. 
After calculating a matched path on the server, we only need to return information for displaying the matched path to the mobile device.
All the requests and responses can be easily handled with [Flask](https://flask.palletsprojects.com/en/2.1.x/) as our API.
The framework we used for our app makes use of [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) to check if the API permits the actual request.
Not handling those on the server-side leads to errors. Luckily, there is an [extension](https://flask-cors.readthedocs.io/en/latest/) for Flask to handle these CORS requests.

# Frontend
## Flutter as our framework
In order to match a mobile phone to a public transit vehicle, we needed an interface for the user. 
As we could not decide whether to build a web-app or a mobile app, we chose to use [Flutter](https://flutter.dev) for our frontend.
Flutter is an open source framework developed by Google for building web-apps and apps for iOS or Android, all from a singe codebase.
The programming language used for Flutter apps is [Dart](https://dart.dev), which is designed and optimized for UI (Exactly what we needed!).

## Content of the app
There are three pages, all of which we can show using examples from the city of 
[Freiburg](https://de.wikipedia.org/wiki/Freiburg_im_Breisgau) with GTFS from the [Freiburger Verkehrs AG (VAG)](https://www.vag-freiburg.de/service-infos/downloads/gtfs-daten).\
The first page shows the public transit vehicle the user has been matched to, as well as the next stop.\
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/frontend_frontpage.png" title="frontpage" width="800"></img>
The second page shows the matched vehicle on a line in the color specified for the route in the GTFS data.\
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/frontend_map_hauptbahnhof.png" title="line 2 on the main station bridge" width="800"></img>
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/frontend_map_schwarzwaldstrasse.png" title="line 1 in the Schwarzwaldstraße" width="800"></img>
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/frontend_map_bus.png" title="a bus line" width="800"></img>
The third page shows the transfer possibilities at the next stop if the device has been matched to a trip.\
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/frontend_connections_page.png" title="connections page" width="800"></img>

# Testing
As it would be very exhausting and expensive to code on board of a bus or tram on a laptop, to see if the map matching algorithm actually works, we wrote a tool to simplify the task.

## Using selenium to manipulate a devices GPS location
In the chrome devtools, one can use the location sensor to manipulate one's position.\
<img src="/../../img/project-map-matching-mobile-phones-to-public-transit-vehicles/sensors_chrome.png" title="Sensors in Chrome Devtools" width="800"></img>
These sensors are also accessible via [selenium](https://www.selenium.dev/documentation/webdriver/bidirectional/chrome_devtools/), 
so we wrote a python script that takes in a list of GPS coordinates and updates the chrome sensor every other second.

## Generating fake GPS data
For every trip in the GTFS data, we know the exact shape it moves on. However, the GPS can be quite inaccurate. 
So, in order to simulate a device moving along a shape, we need to 'noisify' the polyline from the shape.\
First, we need to define an average public transit vehicle moving speed \\(v\\) in \\(\frac{m}{s}\\), 
a GPS signal frequency \\(p\\) in \\(\frac{1}{s}\\) and an average GPS accuracy \\(acc\\) in meters.\
Also, we can calculate the length \\(len\\) of the whole polyline and its parts \\(len_i\\) in meters by using the 
great circle distance for the GPS coordinates.\
Now, we can calculate the total time needed to travel along the polyline \\(t\\): $$t = \frac{len}{v}$$
The total number of GPS signals needed to simulate the whole trip is: $$numSignals = t \cdot p$$
And, as the simulated vehicle is moving with speed \\(v\\) and gets a signal every \\(\frac{1}{p}\\) seconds, 
the average travelling distance between two signals is: $$s = \frac{v}{p}$$

The next step is to generate points along the polyline.\
We generate these points for every signal by going along the polyline, one average travelling distance step \\(s\\) at a time.

As our Map Matching includes time, we need to annotate our test data with fitting timestamps.\
Calculating an estimated timestamp \\(t_{est}\\) for a GPS point can be done very similarly to checking whether a trip is active (see [fast graph building](#fast-graph-building)). 
We again match the stop coordinates to the edges of the selected shape. This splits the shape into segments. 
With the timeframe \\((t_{start}, t_{end})\\) of each segment we can project the generated GPS point to the shape. This gives us the segment the point was originally on. 
The length of the segment is \\(len_{segment}\\).
Then, we only need to project the point onto this segment and calculate the distance \\(dist_{proj}\\) to the start of this segment.
$$ t_{est} = t_{start} + (t_{end} - t_{start}) \cdot \frac{dist_{proj}}{len_{segment}} $$
With this, we get good timestamp estimates for every GPS point.

We can now 'noisify' the points along the line by adding a normally distributed deviation for each x and y with \\(\mu = 0\\) and \\(\sigma = acc\\).

Now, we have generated timed GPS points which can be used by our selenium script to simulate every trip from the GTFS files. 

# Installation
You can try everything out on your own by cloning our [GitHub repository](https://github.com/TheRealTirreg/PublicTransitSnapper/) and following the instructions in the README.md.
