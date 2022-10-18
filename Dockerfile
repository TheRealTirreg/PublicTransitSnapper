# syntax=docker/dockerfile:1
FROM debian:bullseye-slim AS builderB
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
COPY backend/Code/parseGTFS parseGTFS
RUN make -C parseGTFS install

FROM cirrusci/flutter:3.3.1 AS builderF

# Run flutter doctor
RUN flutter doctor

# Enable flutter web
RUN flutter config --enable-web

# Copy files to container and build
RUN mkdir /frontend/
COPY frontend /frontend/
WORKDIR /frontend/
# build flutter front end
RUN flutter build web
WORKDIR /frontend/build/web/

FROM python:3.10.1-slim-bullseye
WORKDIR /app

RUN apt-get update && \
	apt-get install -y unzip bzip2 curl

COPY --from=builderB /usr/local/etc/pfaedle /usr/local/etc/pfaedle
COPY --from=builderB /usr/local/bin/pfaedle /usr/local/bin/pfaedle
COPY --from=builderB /app/parseGTFS/parseGTFSMain /app/code/parseGTFS/parseGTFSMain
COPY --from=builderF /frontend/build/web /app/code/web

COPY backend/requirements_docker.txt .
RUN pip install -r requirements_docker.txt
COPY backend/cities_config.yml cities_config.yml
COPY backend/config.yml config.yml

WORKDIR /app/code
COPY backend/Code/*.py ./
COPY start_servers.sh .
RUN chmod +x start_servers.sh

CMD ./start_servers.sh

# Commands for running backend docker container
# docker build -t publictransitsnapper .
# docker run -it -v $PWD/backend/saved_dictionaries:/app/saved_dictionaries:rw -v $PWD/backend/GTFS:/app/GTFS:rw -p 5000:5000 -p 21698:21698 publictransitsnapper
