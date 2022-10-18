#!/bin/bash

# start the API
python3 API.py &

# start the web app
python3 -u -m http.server --directory web 21698 &

# wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
