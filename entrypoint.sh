#!/bin/bash


# Merge/copy local saved data into actual data directory.
# Some data sources are stored locally in the git repo due to complicated/
# unreliable downloads of the source.
# trailing slash is required!
rsync -a input/data.local/ input/data/

# make sure log ouptut directory exits
mkdir -p output/.logs

# start gunicorn
gunicorn --bind 0.0.0.0:80 esida:app --timeout 0
