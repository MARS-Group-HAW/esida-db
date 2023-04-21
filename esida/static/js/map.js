function load_data_for_layer(map, dl, layerControl) {
  map.fire('dataloading');

  $.getJSON(`/api/v1/parameter_data_map/${dl.id}/2023`, function(data) {

    var markers = new L.MarkerClusterGroup({ disableClusteringAtZoom: 19});
		var markersList = [];

    var m = L.geoJSON(data['geojson'], {
      style: {
        color: 'red'
      },
      onEachFeature: function (feature, layer) {
        var html = "";
        Object.keys(feature.properties).forEach(function(key) {
          var value = feature.properties[key];

          // ignore empty values (not all properties are set on each feature)
          // this reduces the visual space needed for the popup!
          if (value == null) {
            return;
          }

          // the values of same special keys can be enhanced with additional formatting
          if (key == 'wikidata') {
            value = `<a href="https://www.wikidata.org/wiki/${value}" target="_blank">${value}</a>`;
          } else if (key == 'nodes') {
            // usually a long list of OSM ids
            value = value.substring(0, 20) + "…";
          } else if (key == 'meteostat_id') {
            value = `<a href="https://meteostat.net/de/station/${value}" target="_blank">${value}</a>`
          }

          html += `<tr><th><code>${key}</code></th><td>${value}</td>`;
        });

        layer.bindPopup(`<table><tbody>${html}</tbody></table>`);
      }

    });

    markersList.push(m);
		markers.addLayer(m);

    map.addLayer(markers);

    if (layerControl) {
      layerControl.addOverlay(markers, dl.id);
    }

    map.fire('dataload');
  }).fail(function(data) {
    alert("Something went wrong during loading the data.");
    map.fire('dataload');
  });
}
