FROM osgeo/gdal:ubuntu-small-3.4.2

# install pip and postgresql binaries so pycog2 will install
RUN apt-get update && apt-get install -y \
    python3-pip \
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
