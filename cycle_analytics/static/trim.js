import { get_map_layer, add_marker_to_map, get_icon, PolyLineData } from './map_utils.js';

let points, startMarker, endMarker, currStartIndex, currEndIndex;

document.getElementById('start-slider').addEventListener('input', updateMap);
document.getElementById('end-slider').addEventListener('input', updateMap);

/**
 * Initialize the map with a ploy line for the trimming view
* @param {string} div_id - Id of the map div
* @param {PolyLineData} line_data - Object containing the Polyline to show on the map
*/
function initializeMap(div_id, line_data) {
  let map = L.map(div_id);
  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");

  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };
  L.control.layers(baseMaps).addTo(map);

  let objects = [];

  objects.push(line_data.set_path_on_map(map));
  points = line_data.points;
  startMarker = add_marker_to_map(map, line_data.lats[0], line_data.longs[0], get_icon("green", 0), "")
  endMarker = add_marker_to_map(map, line_data.lats[line_data.lats.length - 1], line_data.longs[line_data.longs.length - 1], get_icon("red", 0), "")
  currStartIndex = 0;
  currEndIndex = points.length - 1;
}

function updateMap() {
  const rangeMax = 1000;
  const startValue = document.getElementById('start-slider').value;
  const endValue = document.getElementById('end-slider').value;

  const startIndex = Math.floor(points.length * startValue / rangeMax);
  const endIndex = Math.min(Math.floor(points.length * endValue / rangeMax), points.length - 1);

  if (startIndex != currStartIndex) {
    currStartIndex = startIndex;
    startMarker.setLatLng(points[currStartIndex]);
  }

  if (endIndex != currEndIndex) {
    currEndIndex = endIndex;
    endMarker.setLatLng(points[currEndIndex]);
  }
  document.getElementById('start_idx').value = currStartIndex;
  document.getElementById('end_idx').value = currEndIndex;
}

export { initializeMap }
