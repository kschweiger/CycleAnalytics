import { EventMarker, reset_map, segment_adder_map, remove_last_marker_from_map, show_polyline } from './map_utils.js';

let map = segment_adder_map("map", []);

document.getElementById("Reset").onclick = function () {
  reset_map(map)
}

document.getElementById("show_customize_btn").onclick = function () {
  showSliders();
}

document.getElementById("remove_last_marker").onclick = function () {
  remove_last_marker_from_map(map);
}


export function add_marker(
  event_marker,
  draggable = false,
) {
  var marker = L.marker([event_marker.lat, event_marker.long], { icon: event_marker.icon, draggable: draggable });
  marker.addTo(map);
  if (!(event_marker.popup_text === "")) {
    marker.bindPopup(event_marker.popup_text);
  }
  return marker;
}

function showSliders() {
  var slidersDiv = document.getElementById("sliders");
  slidersDiv.classList.remove("visually-hidden");
  var customizeBtn = document.getElementById("show_customize_btn");
  customizeBtn.disabled = true;
}



export async function calc_route(csrf_token) {
  var transport_settings = {};
  var sliders = document.querySelectorAll('input[type="range"]');
  sliders.forEach(function (slider) {
    var sliderID = slider.id.replace("slider_", ""); // Remove the "slider_" prefix
    transport_settings[sliderID] = parseFloat(slider.value);
  });

  let waypoints = [];

  map.eachLayer(function (layer) {
    // Make a list of all Markers on the map. These will be sent to the endpoints
    // calcualting the route using a post request
    if (layer instanceof L.Marker) {
      waypoints.push([layer.getLatLng().lat, layer.getLatLng().lng]);
    }
    // Remove polylines from previous request
    else if (layer instanceof L.Polyline) {
      map.removeLayer(layer);
    }
  });

  // Reset the values in the from. Otherwise it can happen to carry over
  // data from previous routes
  document.getElementById("segment_latitudes").value = "";
  document.getElementById("segment_longitudes").value = "";
  document.getElementById("segment_elevations").value = "";

  // Reset the alert div
  document.getElementById("route_alert").className = "visually-hidden";
  document.getElementById("route_alert").innerHTML = "";

  if (waypoints.length < 2) {
    document.getElementById("route_alert").className = "alert alert-warning";
    document.getElementById("route_alert").innerHTML =
      "Place at least <span class='fw-bold'>two markers<span> on the map";
    return;
  }

  // Add a spinner to the button sending triggering the request
  document.getElementById("get_path_spinner").className =
    "spinner-border spinner-border-sm";

  let route = undefined;
  let profile = undefined;
  let elevations = undefined;
  const response = await fetch("/segments/calc-route", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": csrf_token,
    },
    body: JSON.stringify({
      waypoints: waypoints,
      transport_settings: transport_settings,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      route = data["route"];
      profile = data["profile"];
      elevations = data["elevations"];
    });

  // After post request
  // Remove the spinner
  document.getElementById("get_path_spinner").className = "";

  // Deal with the result of the post request
  if (!(route === undefined)) {
    show_polyline(map, route);
    let lats = [];
    let lngs = [];
    for (let point of route) {
      lats.push(point[0]);
      lngs.push(point[1]);
    }
    document.getElementById("segment_latitudes").value = lats.toString();
    document.getElementById("segment_longitudes").value = lngs.toString();
    if (!(elevations === null)) {
      document.getElementById("segment_elevations").value =
        elevations.toString();
    }
    document.getElementById("save_segmnet_btn").disabled = false;
    document.getElementById("segment_name").disabled = false;
    document.getElementById("segment_description").disabled = false;
    document.getElementById("segment_difficulty").disabled = false;
    document.getElementById("segment_type").disabled = false;
  }

  // Show bae64 encoded png if included in the response
  if (typeof profile === "string") {
    document.getElementById("profile_div").className = "";
    document
      .getElementById("profile_plot")
      .setAttribute("src", "data:image/png;base64," + profile);
  }
}
