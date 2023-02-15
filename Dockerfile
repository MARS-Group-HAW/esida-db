FROM osgeo/gdal:ubuntu-small-3.6.2

# Installs pg_dump/pg_restore used for dumping/importing database backups
RUN apt-get install -y postgresql-client

# install pip and postgresql binaries so pycog2 will install
#
# python-rtree was NOT required building on Linux/GitLab CI. If it's missing
# during build on macOS/M1 the container won't run. Why? Probably due to
# arm64 emulation thins for the container?
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-rtree \
    libpq-dev \
    rsync \
    wget

RUN mkdir -p /app

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app

RUN pip install -e .
RUN export FLASK_APP=esida

EXPOSE 80

# parameter for ENTRYPOINT (i.e. docker run <image> <cmd> can be used to overwrite this)
#CMD ["gunicorn", "--bind", "0.0.0.0:80", "esida:app"]
CMD ["./entrypoint.sh"]
