class EventMarker {
  constructor(lat, long, color, color_idx, text) {
    this.lat = lat;
    this.long = long;
    this.icon = get_icon(color, color_idx);
    this.popup_text = text;
  }
}

function show_polyline(map, points, color = "#20c997") {
  var polyline = L.polyline([points], { color: color }).addTo(map);

  map.fitBounds(polyline.getBounds());

  return polyline;
}

class PolyLineData {
  constructor(lats, longs, color) {
    this.lats = lats;
    this.longs = longs;
    this.color = color;
  }

  set_path_on_map(map) {
    let points = [];

    for (let i = 0; i < this.lats.length; i++) {
      points.push([this.lats[i], this.longs[i]]);
    }

    return show_polyline(map, points, this.color);
  }
}

function set_path_on_map(map, lats, longs, color = "#20c997") {
  const lat_points = lats.split(",");
  const long_points = longs.split(",");

  let points = [];

  for (let i = 0; i < lat_points.length; i++) {
    points.push([lat_points[i], long_points[i]]);
  }

  return show_polyline(map, points, (color = color));
}

function get_map_layer(type) {
  if (type == "carto") {
    return L.tileLayer(
      "http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      {
        attribution:
          '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
      },
    );
  } else if (type == "opencycle") {
    return L.tileLayer("https://tile.thunderforest.com/cycle/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://www.thunderforest.com">Thunderforest</a>',
    });
  } else {
    return L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
  }
}

function show_map_for_form(
  div_id,
  btn_id,
  height,
  view_lat,
  view_long,
  view_zoom,
  markers,
) {
  document.getElementById(div_id).style = "height:" + height + "px";
  document.getElementById(div_id).className = "mt-2";

  if (btn_id) {
    document.getElementById(btn_id).setAttribute("disabled", true);
  }

  let map = L.map(div_id).setView([view_lat, view_long], view_zoom);

  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");

  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };
  L.control.layers(baseMaps).addTo(map);

  let placed_markers = [];

  for (let marker of markers) {
    placed_markers.push(
      add_marker_to_map(
        map,
        marker.lat,
        marker.long,
        marker.icon,
        marker.popup_text,
      ),
    );
  }

  console.log(placed_markers);
  let group = new L.featureGroup(placed_markers);

  let popup = L.popup();
  function onMapClick(e) {
    popup
      .setLatLng(e.latlng)
      .setContent("You clicked the map at " + e.latlng.toString())
      .openOn(map);

    document.getElementById("latitude").value = e.latlng.lat;
    document.getElementById("longitude").value = e.latlng.lng;
  }

  map.on("click", onMapClick);
  return map;
}

function show_map_for_form_path(div_id, btn_id, height, lats, longs) {
  map = show_map_for_form(div_id, btn_id, height, 1, 1, 1, []);
  set_path_on_map(map, lats, longs);
  return map;
}

function show_map_with_path_and_markers(div_id, line_datas, markers) {
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

  for (let line_data of line_datas) {
    objects.push(line_data.set_path_on_map(map));
  }

  for (let marker of markers) {
    objects.push(
      add_marker_to_map(
        map,
        marker.lat,
        marker.long,
        marker.icon,
        marker.popup_text,
      ),
    );
  }
}

function get_base_icon() {
  return L.Icon.extend({
    options: {
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [0, -37],
    },
  });
}

function get_blue_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({ iconUrl: "/static/img/marker_blue_" + i + ".svg" });
  return icon;
}

function get_red_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({ iconUrl: "/static/img/marker_red_" + i + ".svg" });
  return icon;
}

function get_green_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({
    iconUrl: "/static/img/marker_green_" + i + ".svg",
  });
  return icon;
}

function get_pink_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({ iconUrl: "/static/img/marker_pink_" + i + ".svg" });
  return icon;
}

function get_purple_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({
    iconUrl: "/static/img/marker_purple_" + i + ".svg",
  });
  return icon;
}

function get_teal_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({ iconUrl: "/static/img/marker_teal_" + i + ".svg" });
  return icon;
}

function get_yellow_icon(i) {
  var LeafIcon = get_base_icon();
  var icon = new LeafIcon({
    iconUrl: "/static/img/marker_yellow_" + i + ".svg",
  });
  return icon;
}

function get_icon(color, color_idx) {
  switch (color) {
    case "blue":
      icon = get_blue_icon(color_idx);
      break;
    case "red":
      icon = get_red_icon(color_idx);
      break;
    case "green":
      icon = get_green_icon(color_idx);
      break;
    case "pink":
      icon = get_pink_icon(color_idx);
      break;
    case "purple":
      icon = get_purple_icon(color_idx);
      break;
    case "teal":
      icon = get_teal_icon(color_idx);
      break;
    default:
      icon = get_yellow_icon(color_idx);
  }
  return icon;
}

function add_marker_to_map(
  map,
  lat,
  long,
  icon,
  popup_text,
  draggable = false,
) {
  var marker = L.marker([lat, long], { icon: icon, draggable: draggable });
  marker.addTo(map);
  if (!(popup_text === "")) {
    marker.bindPopup(popup_text);
  }
  return marker;
}

function show_map_with_markers(div_id, markers) {
  let map = L.map(div_id);

  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");

  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };
  L.control.layers(baseMaps).addTo(map);

  let placed_markers = [];

  for (let marker of markers) {
    placed_markers.push(
      add_marker_to_map(
        map,
        marker.lat,
        marker.long,
        marker.icon,
        marker.popup_text,
      ),
    );
  }

  let group = new L.featureGroup(placed_markers);

  map.fitBounds(group.getBounds());
}

function segment_adder_map(div_id, markers) {
  let map = L.map(div_id).setView([48.02, 10.2], 7);

  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");
  let cycle = get_map_layer("opencycle");
  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };

  L.control.layers(baseMaps).addTo(map);

  function onMapClick(e) {
    add_marker_to_map(
      map,
      e.latlng.lat,
      e.latlng.lng,
      get_icon("green", 0),
      "Marker @ " + e.latlng.lat + " / " + e.latlng.lng,
      (draggable = true),
    );
  }
  map.on("click", onMapClick);

  let placed_markers = [];

  for (let marker of markers) {
    placed_markers.push(
      add_marker_to_map(
        map,
        marker.lat,
        marker.long,
        marker.icon,
        marker.popup_text,
      ),
    );
  }

  let group = new L.featureGroup(placed_markers);

  return map;
}

async function calc_route(csrf_token, map) {
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
    for (point of route) {
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

function remove_last_marker_from_map(map) {
  let n_markers = 0;
  map.eachLayer(function (layer) {
    // Make a list of all Markers on the map. These will be sent to the endpoints
    // calcualting the route using a post request
    if (layer instanceof L.Marker) {
      n_markers += 1;
    }
  });

  // Reset the alert div
  document.getElementById("route_alert").className = "visually-hidden";
  document.getElementById("route_alert").innerHTML = "";

  if (n_markers == 0) {
    document.getElementById("route_alert").className = "alert alert-warning";
    document.getElementById("route_alert").innerHTML =
      "No markers on map to remove";
    return;
  }

  let count = 0;
  map.eachLayer(function (layer) {
    // Make a list of all Markers on the map. These will be sent to the endpoints
    // calcualting the route using a post request
    if (layer instanceof L.Marker) {
      if (count == n_markers - 1) {
        map.removeLayer(layer);
      } else {
        count += 1;
      }
    }
  });
}

function reset_map(map) {
  map.eachLayer(function (layer) {
    if (layer instanceof L.Marker) {
      if (layer.options.draggable) {
        map.removeLayer(layer);
      }
    } else if (layer instanceof L.Polyline) {
      map.removeLayer(layer);
    }
  });
  document.getElementById("save_segmnet_btn").disabled = true;
  document.getElementById("segment_name").disabled = true;
  document.getElementById("segment_description").disabled = true;

  document.getElementById("profile_div").className = "visually-hidden";
  document.getElementById("profile_plot").setAttribute("src", "");
}

function segment_map(div_id, csrf_token, markers) {
  let map = L.map(div_id).setView([47.598342, 7.759027], 12);

  let carto = get_map_layer("carto");
  let osm = get_map_layer("osm");
  map.addLayer(carto);

  var baseMaps = {
    "Carto (Light)": carto,
    OpenStreetMap: osm,
  };

  let segments_on_map = [];

  L.control.layers(baseMaps).addTo(map);
  function on_map_zoom(e) {
    const curr_bounds = map.getBounds();
    const north_east = curr_bounds.getNorthEast();
    const south_west = curr_bounds.getSouthWest();
    fetch("/segments/segments-in-bounds", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token,
      },
      body: JSON.stringify({
        ids_on_map: segments_on_map,
        ne_latitude: north_east.lat,
        ne_longitude: north_east.lng,
        sw_latitude: south_west.lat,
        sw_longitude: south_west.lng,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        for (segment of data["segments"]) {
          segments_on_map.push(segment["segment_id"]);
          var polyline = L.polyline([segment["points"]], {
            color: segment["color"],
          }).addTo(map);
          polyline.bindPopup(
            `<span class="fw-bold">${segment["name"]}</span>:
                     ${segment["type"]} - ${segment["difficulty"]} <br>
                    <a href="${segment["url"]}">More info</a>`,
          );
        }
      });
  }
  on_map_zoom();

  let placed_markers = [];

  for (let marker of markers) {
    placed_markers.push(
      add_marker_to_map(
        map,
        marker.lat,
        marker.long,
        marker.icon,
        marker.popup_text,
      ),
    );
  }

  let group = new L.featureGroup(placed_markers);

  map.on("zoomend", on_map_zoom);
  map.on("moveend", on_map_zoom);
}

