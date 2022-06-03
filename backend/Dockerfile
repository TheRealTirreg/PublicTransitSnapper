# syntax=docker/dockerfile:1
FROM python:3.10.1-slim-buster
WORKDIR /code
ENV FLASK_APP=API.py
COPY requirements_docker.txt requirements.txt
RUN pip install -r requirements.txt
COPY *.py /code/
CMD ["flask", "run", "--host", "0.0.0.0"]
