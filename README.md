# ESIDA DB Pipeline

## Initial setup


Cerate `docker-compose.yml`:

```
version: "3"

services:
  postgis:
    image: postgis/postgis
    restart: always
    environment:
      POSTGRES_DB: esida
      POSTGRES_USER: esida
      POSTGRES_PASSWORD: esida
      PGDATA: /var/lib/postgresql/data/pgdat
    ports:
      - 5432:5432
    volumes:
      - ./pgdata:/var/lib/postgresql/data
  esida:
    image: git.haw-hamburg.de:5005/mars/esida-db:latest
    restart: always
    environment:
      POSTGIS_HOST: postgis
      POSTGIS_DB: esida
      POSTGIS_USER: esida
      POSTGIS_PASS: esida
      POSTGIS_PORT: "5432"
      FLASK_BASIC_AUTH_FORCE: "False"
    ports:
      - 80:80
    volumes:
      - ./input:/app/input/data
      - ./output:/app/output
```

Boot it up with `docker-compose up -d` (you might need to log-in with your HAW-Account to access the registry).


After initial starting of the system, you need to-to the following steps. Either run them locally, or enter the docker container bash first.

    $ flask create-db # setup required database columns
    $ python esida-cli.py init # import region/district shape files into db

After that you can load the different parameters by key into the database. For example:

    $ python ./esida-cli.py param <key> extract # downloads files from source
    $ python ./esida-cli.py param <key> load # processes source and saves to databse

## Local development (docker)

Start PostGIS database via Docker Compose:

    $ docker-compose up -d  # starrting for the first time
    $ docker-compose start # after inital start has been done

Build Docker container containing the Python integration code and Flask Web-Frontend:

    $ docker build -t esida-db .

Run docker container locally:

    $ docker run -e -p 8080:80 esida-db

The database now runs at http://localhost:8080/ (but with no database)


## Local development (directly)

Stat the PostGIS database with docker-compose as shown above. Then install the dependencies:

- GDAL
- Python 3.9.x
- Python packages with `$ pip install -r requirements.txt`
- Make local ESIDA Python package: `$ pip install -e .`
- Make the Flask App know to the system: `$ export FLASK_APP=esida`
- Run gunicorn to serve flask App: `$ gunicorn --bind 0.0.0.0:80 esida:app --error-logfile - --reload`
- Page can now be access via http://localhost:8080/


## HAW ICC Deployment

Create Kubernetes space:

    $ kubectl apply -f ./k8s/space-esida.yaml

Access for further HAW users can be added with the `k8s/rolebinding.yaml`.

Create PersistentVolumeClaim's (PVC) for permanent storage independed of container life-cycle:

    $ kubectl apply -f ./k8s/pvc-postgis.yaml        # Storage of PostGis database
    $ kubectl apply -f ./k8s/pvc-esidadb-input.yaml  # Storage of input data of the pipeline
    $ kubectl apply -f ./k8s/pvc-esidadb-output.yaml # Storage of output files (per district files i.e.)

Create Service and Deployment for PostGIS database and ESIDA DB pipeline/flask app:


Login to the pods:

    $ kubectl exec -it <Name des Pods> -n <space-name> -- bash
    $ kubectl exec -it $(kubectl -n esida get pod | grep esida-db | awk '{ print $1 }') -n esida -- bash

Port forwarding to access pod:e

    $ kubectl port-forward <pod> -n esida 8432:80

    $ kubectl port-forward $(kubectl -n esida get pod | grep postgis | awk '{ print $1 }') -n esida 6432:5432


Delete something

    $ kubectl delete -f ./k8s/<file.yaml>

Debugging:

    $ kubectl describe pods -n esida # might hint deploymentment issues
