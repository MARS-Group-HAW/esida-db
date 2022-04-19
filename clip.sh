#!/bin/bash

#id="Bariadi"

#gdalwarp -of GTiff -cutline districts_valid.shp -crop_to_cutline -csql "SELECT * FROM districts_valid WHERE District_N = '$id'" ./data/worldpop_pop/tza_ppp_2020_UNadj.tiff output_clip_${id}.tif

clip_dir=./input/shapes/Districts


# clip geotiffs
for shp in "$clip_dir"/*.shp
do
    filename=${shp##*/}
    basename="${filename%.shp}"

    tiffdirs=("worldpop_popc" "worldpop_pd" "worldpop_bsgme" "malaria" "worldpop_poverty")
    # loop over different geotiff features
    for tiff in "${tiffdirs[@]}"
    do
        outdir="./output/$basename/$tiff/"
        mkdir -p "$outdir"

        # loop over each file (i.e. different years) in each feature
        for tifffile in ./input/data/"$tiff"/*.{tiff,tif}; do
            outname=${tifffile##*/}

            # only clip if target file does not exist
            if [ ! -f "$outdir/$outname" ]; then
                gdalwarp -of GTiff -cutline "$shp" -crop_to_cutline "$tifffile" "$outdir/$outname"
            fi
        done
    done
done
