import { get_map_layer, add_marker_to_map, get_icon, PolyLineData } from './map_utils.js';

let points;
let markers = [];
let marker_indices = [];
let sliders = [];
let map;

Function.prototype.partial = function (...args) {
  const fn = this;
  return function (...restArgs) {
    return fn.apply(this, args.concat(restArgs));
  };
};

/**
 * Initialize the map with a ploy line for the trimming view
* @param {string} div_id - Id of the map div
* @param {PolyLineData} line_data - Object containing the Polyline to show on the map
*/
function initializeMap(div_id, line_data) {
  map = L.map(div_id);
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

  initializeMarker();

}

/**
* Update the postion of a marker on the
* @param {number} idx
*/
function updateMarperPos(idx) {
  const rangeMax = 1000;
  const value = document.getElementById('segment-slider-' + idx).value;
  const index = Math.floor(points.length * value / rangeMax);

  let currIndex = marker_indices[idx];
  if (index != currIndex) {
    currIndex = index;
    markers[idx].setLatLng(points[currIndex]);
  }

  marker_indices[idx] = currIndex;
}


/**
* Add a new marker to the map and range slider to the page
*/
function initializeMarker() {
  let [lat, long] = points[0];
  markers.push(
    add_marker_to_map(map, lat, long, get_icon("green", 0), "")
  )
  marker_indices.push(0);
  sliders.push(
    document.getElementById('segment-slider-' + (markers.length - 1))
  );
  sliders[markers.length - 1].addEventListener('input', updateMarperPos.partial(markers.length - 1));

}

function removeLastMarker() {
  let marker = markers.pop();
  marker_indices.pop();
  sliders.pop();
  map.removeLayer(marker);

}


document.addEventListener('DOMContentLoaded', function () {
  const addSegmentButton = document.getElementById('add_segment');
  const rmSegmentButton = document.getElementById('remove_segment');
  const sliderRowsContainer = document.getElementById('slider_rows');
  let sliderIndex = 0;

  addSegmentButton.addEventListener('click', function () {
    sliderIndex++;

    const newRow = document.createElement('div');
    newRow.className = 'row';
    newRow.innerHTML = `
      <div class="col">
        <input class="w-100" type="range" id="segment-slider-${sliderIndex}" min="0" max="1000" value="0">
      </div>
    `;

    sliderRowsContainer.appendChild(newRow);
    initializeMarker();
    rmSegmentButton.disabled = false;
  });
  rmSegmentButton.addEventListener("click", function () {
    const rows = sliderRowsContainer.getElementsByClassName('row');
    if (rows.length > 1) {  // Ensure we always keep at least one slider
      sliderRowsContainer.removeChild(rows[rows.length - 1]);
      removeLastMarker();
      sliderIndex--;  // Decrement the slider index
      if (sliderIndex == 0) {
        rmSegmentButton.disabled = true;
      };
    } else {
      console.log("Cannot remove the last slider.");
      // Optionally, you can disable the remove button or show a message to the user
    }
  });

});

export { initializeMap }
