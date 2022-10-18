# syntax=docker/dockerfile:1
FROM cirrusci/flutter:3.3.1

# Run flutter doctor
RUN flutter doctor

# Enable flutter web
RUN flutter config --enable-web

# Copy files to container and build
RUN mkdir /frontend/
COPY . /frontend/
WORKDIR /frontend/
RUN flutter pub get
RUN flutter build web
WORKDIR /frontend/build/web/

CMD ["python3", "-u", "-m", "http.server", "21698"]

# Commands for running frontend docker container
# docker build -t publictransitsnapper-frontend .
# docker run -p 21698:21698 publictransitsnapper-frontend
