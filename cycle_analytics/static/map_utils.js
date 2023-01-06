class EventMarker {
    constructor(lat, long, color, color_idx, text) {
        this.lat = lat;
        this.long = long;
        this.icon = get_icon(color, color_idx);
        this.popup_text = text
    }
}

function set_path_on_map(map, lats, longs) {
    const lat_points = lats.split(",");
    const long_points = longs.split(",");

    let points = [];

    for (let i = 0; i < lat_points.length; i++) {
        points.push([lat_points[i], long_points[i]])
    }

    var polyline = L.polyline([points], { color: '#0d6efd' }).addTo(map);
    // zoom the map to the polyline
    map.fitBounds(polyline.getBounds());
}

function get_map_layer() {
    return L.tileLayer('http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="http://cartodb.com/attributions">CartoDB</a>'
    });
}


function show_map_for_form(div_id, btn_id, height, view_lat, view_long, view_zoom) {
    document.getElementById(div_id).style = "height:" + height + "px"
    document.getElementById(div_id).className = "mt-2"

    document.getElementById(btn_id).setAttribute("disabled", true)

    let map = L.map(div_id).setView([view_lat, view_long], view_zoom);

    map.addLayer(get_map_layer());

    let popup = L.popup();
    function onMapClick(e) {
        popup
            .setLatLng(e.latlng)
            .setContent("You clicked the map at " + e.latlng.toString())
            .openOn(map);

        document.getElementById("latitude").value = e.latlng.lat;
        document.getElementById("longitude").value = e.latlng.lng;

    };

    map.on('click', onMapClick);
    return map;
}

function show_map_for_form_path(div_id, btn_id, height, lats, longs) {
    map = show_map_for_form(div_id, btn_id, height, 1, 1, 1);
    set_path_on_map(map, lats, longs);
    return map;
}

function get_base_icon() {
    return L.Icon.extend({
        options: {
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [0, -37]
        }
    });
}

function get_blue_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_blue_' + i + '.svg' })
    return icon
}

function get_red_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_red_' + i + '.svg' })
    return icon
}

function get_green_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_green_' + i + '.svg' })
    return icon
}

function get_pink_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_pink_' + i + '.svg' })
    return icon
}

function get_purple_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_purple_' + i + '.svg' })
    return icon
}

function get_teal_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_teal_' + i + '.svg' })
    return icon
}

function get_yellow_icon(i) {
    var LeafIcon = get_base_icon()
    var icon = new LeafIcon({ iconUrl: '/static/img/marker_yellow_' + i + '.svg' })
    return icon
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
    return icon
}

function add_marker_to_map(map, lat, long, icon, popup_text) {
    var marker = L.marker([lat, long], { icon: icon }).addTo(map);
    marker.bindPopup(popup_text);
    return marker
}



function show_map_with_markers(div_id, markers) {
    let map = L.map(div_id);
    map.addLayer(get_map_layer());

    let placed_markers = [];

    for (marker of markers) {
        placed_markers.push(add_marker_to_map(map, marker.lat, marker.long, marker.icon, marker.popup_text))
    }
    let group = new L.featureGroup(placed_markers);

    map.fitBounds(group.getBounds());
}