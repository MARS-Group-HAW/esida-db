#!/bin/sh

marsdir=ESIDADarEsSalaam/ESIDADarEsSalaam_MACOSX

# check if MARS folder is setup wirh resources and config
if [ ! -d "$DIRECTORY" ]; then
    unzip ESIDADarEsSalaam_MACOSX.zip
    mkdir -p "$marsdir/resources"
    rsync -a resources/ "$marsdir/resources"
    cp config.json "$marsdir"
fi

# run simulation
cd "$marsdir" || exit
./ESIDADarEsSalaamBox
