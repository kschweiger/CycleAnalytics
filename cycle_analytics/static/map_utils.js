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