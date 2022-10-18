import os
import docker
from subprocess import Popen, PIPE
from shutil import rmtree


def get_gtfs_freiburg():
    """
    Fetches latest VAG GTFS files from "https://www.vag-freiburg.de/fileadmin/gtfs/VAGFR.zip"
    """
    # delete old gtfs-in files
    print("deleting old gtfs-in files")
    gtfs_in_path = r"./GTFS/Freiburg/VAG/gtfs-in"
    if os.path.exists(gtfs_in_path):
        rmtree(gtfs_in_path)
        os.makedirs(gtfs_in_path)
 
    # download and drop files into temp folder
    # wget https://www.vag-freiburg.de/fileadmin/gtfs/VAGFR.zip && unzip VAGFR.zip -d r"GTFS/Freiburg/VAG/gtfs-in"
    print("downloading gtfs files from VAG page")
    process = Popen(["wget", "https://www.vag-freiburg.de/fileadmin/gtfs/VAGFR.zip", "GTFS/Freiburg/VAG"
                     "&&", "unzip", r"GTFS/Freiburg/VAG/VAGFR.zip", "-d", gtfs_in_path],
                    stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    print(stdout)
    print("==================== Errors: ======================")
    print(stderr)

    # remove .zip file
    print("removing .zip file")
    if os.path.exists(r"GTFS/Freiburg/VAG/VAGFR.zip"):
        os.remove(r"GTFS/Freiburg/VAG/VAGFR.zip")


def call_pfaedle_freiburg():
    """
    -x will filter the input OSM file and output a new OSM file which contains
      exactly the data needed to calculate the shapes for the input GTFS feed and the input configuration
      This can be used to avoid parsing (for example) the entire planet.osm on each run.

    "Freiburg/OSM/freiburg-regbez-latest.osm" is the area around Freiburg from OpenStreetMaps
    "Freiburg/VAG/gtfs-in" contains the GTFS files from Freiburg VAG

    -o describes the output directory for the GTFS files with the calculated shapes
    """
    # todo remove old code
    # process = Popen(["pfaedle", "-x",
    #                             r"Freiburg/OSM/freiburg-regbez-latest.osm", r"Freiburg/VAG/gtfs-in",
    #                             r"-o Freiburg/VAG/gtfs-out"],
    #                            stdout=PIPE, stderr=PIPE)
    # stdout, stderr = process.communicate()
    # print(stdout)
    # print("=================== ERRORS: ====================")
    # print(stderr)
    client = docker.from_env()
    client.containers.run("adfreiburg/pfaedle:latest", "", detach=True)
    # docker run -i --rm
    # --volume /mnt/g/Code/Bachelorprojekt_duckdns/bachelorprojekt_robin_gerrit/GTFS/Freiburg/OSM:/OSM
    # --volume /mnt/g/Code/Bachelorprojekt_duckdns/bachelorprojekt_robin_gerrit/GTFS/Freiburg/VAG:/VAG
    # adfreiburg/pfaedle -x /OSM/freiburg-regbez-latest.osm -i /VAG/gtfs-in -o /VAG/gtfs-out


if __name__ == '__main__':
    get_gtfs_freiburg()
