#!/bin/bash

#id="Bariadi"

#gdalwarp -of GTiff -cutline districts_valid.shp -crop_to_cutline -csql "SELECT * FROM districts_valid WHERE District_N = '$id'" ./data/worldpop_pop/tza_ppp_2020_UNadj.tiff output_clip_${id}.tif

clip_dir=./Districts

for shp in "$clip_dir"/*.shp
do
    filename=${shp##*/}
    basename="${filename%.shp}"
    outdir="./output/$basename/worldpop/"
    mkdir -p "$outdir"

    gdalwarp -of GTiff -cutline "$shp" -crop_to_cutline ./data/worldpop_pop/tza_ppp_2020_UNadj.tiff "$outdir/tza_ppp_2020_UNadj.tiff"
done