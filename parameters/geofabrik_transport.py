import geopandas

from esida.geofabrik_parameter import GeofabrikParameter

class geofabrik_transport(GeofabrikParameter):

    def load(self, shapes=None, save_output=False):
        gdf = geopandas.read_file(self.get_data_path() / 'gis_osm_transport_free_1.shp')

        if shapes is None:
            shapes = self._get_shapes_from_db()

        for shape in shapes:
            aoi_gdf = gdf[gdf.within(shape['geometry'])].reset_index(drop=True)

            stats = aoi_gdf['fclass'].value_counts().to_dict()

            row = {
                'year': 2022,
                'shape_id': shape['id']
            }

            large = 0

            for key, value in stats.items():
                row[f"{self.parameter_id}_{key}"] = value

                if key in ['bus_station', 'railway_station', 'airport']:
                    large += value

            row[f"{self.parameter_id}"] = large

            self.rows.append(row)

        self.save()
