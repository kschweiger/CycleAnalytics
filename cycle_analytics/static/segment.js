import { get_map_layer, add_marker_to_map, get_icon, PolyLineData } from './map_utils.js';

let points;
let markers = [];
let marker_indices = [];
let sliders = [];
let map;
let rangeMax;
// let sliderIndex = 0;
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
* @param {number} nPoints -
* @param {Array<number>} markerIndices -
*/
function initialize(div_id, line_data, nPoints, markerIndices) {
  map = L.map(div_id);
  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");
  rangeMax = nPoints;
  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };
  L.control.layers(baseMaps).addTo(map);

  let objects = [];

  objects.push(line_data.set_path_on_map(map));
  points = line_data.points;

  for (var idx of markerIndices) {
    initializeMarker(idx);
  }
}

/**
* Update the postion of a marker on the
* @param {number} idx
*/
function updateMarperPos(idx) {
  const value = document.getElementById('segment-slider-' + idx).value;
  const index = Math.floor(points.length * value / rangeMax);

  let currIndex = marker_indices[idx];
  if (index != currIndex) {
    currIndex = index;
    markers[idx].setLatLng(points[currIndex]);
  }

  marker_indices[idx] = currIndex;
  document.getElementById('save').disabled = true;
}

/**
* Add a new marker to the map and range slider to the page
* @param {number} startIdx -
*/
function initializeMarker(startIdx = 0) {
  let [lat, long] = points[startIdx];
  markers.push(
    add_marker_to_map(map, lat, long, get_icon("green", 0), "")
  )
  marker_indices.push(startIdx);
  addSlider(startIdx, true);
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
  document.getElementById('save').disabled = true;

}
/**
* @param {number} startValue - Set the start value of the slider
* @param {boolean} initial -
*/
function addSlider(startValue = 0, initial = false) {
  let sliderIndex = markers.length - 1;
  let sliderRowsContainer = document.getElementById('slider_rows');

  const newRow = document.createElement('div');
  newRow.className = 'row';
  newRow.innerHTML = `
      <div class="col">
        <input class="w-100" type="range" id="segment-slider-${sliderIndex}" min="0" max="${rangeMax}" value="${startValue}">
      </div>
    `;

  sliderRowsContainer.appendChild(newRow);
  if (sliderIndex > 0) {
    document.getElementById('remove_segment').disabled = false;
  }
  if (!initial) {
    document.getElementById('save').disabled = true;
  }
}


document.addEventListener('DOMContentLoaded', function () {
  const addSegmentButton = document.getElementById('add_segment');
  const rmSegmentButton = document.getElementById('remove_segment');
  const previewButton = document.getElementById('preview');
  const saveButton = document.getElementById('save');
  const sliderRowsContainer = document.getElementById('slider_rows');

  addSegmentButton.addEventListener('click', function () {
    initializeMarker();
    rmSegmentButton.disabled = false;
    document.getElementById('save').disabled = true;
  });
  rmSegmentButton.addEventListener("click", function () {
    const rows = sliderRowsContainer.getElementsByClassName('row');
    if (rows.length > 1) {  // Ensure we always keep at least one slider
      document.getElementById("save").disabled = true;
      sliderRowsContainer.removeChild(rows[rows.length - 1]);
      removeLastMarker();
      if (markers.length < 2) {
        rmSegmentButton.disabled = true;
      };
    } else {
      console.log("Cannot remove the last slider.");
      // Optionally, you can disable the remove button or show a message to the user
    }
  });

  previewButton.addEventListener("click", function () {
    console.log("Have marker indices " + marker_indices);
    document.getElementById("submit_indices").value = marker_indices;
    document.getElementById("submit_type").value = "preview";
    document.getElementById("segment_form").submit();
  });

  saveButton.addEventListener("click", function () {
    document.getElementById("submit_indices").value = marker_indices;
    document.getElementById("submit_type").value = "save";
    document.getElementById("segment_form").submit();
  });
});

export { initialize }
