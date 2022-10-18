# syntax=docker/dockerfile:1
FROM debian:bullseye-slim AS builder
WORKDIR /app

RUN apt-get update && \
	apt-get install -y clang cmake make git zlib1g-dev libgtest-dev

# install pfaedle for generating shapesfile
RUN git clone --recurse-submodules https://github.com/ad-freiburg/pfaedle pfaedle && \
    cd pfaedle && \
	mkdir build && \
	cd build && \
	cmake .. && \
	make -j && \
	make install

# install parseGTFS for generating precomputed data
COPY /Code/parseGTFS parseGTFS
RUN make -C parseGTFS install

FROM python:3.10.1-slim-bullseye
WORKDIR /app

RUN apt-get update && \
	apt-get install -y unzip bzip2 curl

COPY --from=builder /usr/local/etc/pfaedle /usr/local/etc/pfaedle
COPY --from=builder /usr/local/bin/pfaedle /usr/local/bin/pfaedle
COPY --from=builder /app/parseGTFS/parseGTFSMain /app/code/parseGTFS/parseGTFSMain

COPY requirements_docker.txt .
RUN pip install -r requirements_docker.txt
COPY cities_config.yml cities_config.yml
COPY config.yml config.yml
# COPY GTFS GTFS # uncomment if you don't use volumes
# COPY saved_dictionaries saved_dictionaries # uncomment if you don't use volumes

WORKDIR /app/code
COPY /Code/*.py ./

CMD ["python3", "API.py"]

# Commands for running backend docker container
# docker build -t publictransitsnapper-backend .
# docker run -v $PWD/saved_dictionaries:/app/saved_dictionaries:rw -v $PWD/GTFS:/app/GTFS:rw -p 5000:5000 publictransitsnapper-backend
