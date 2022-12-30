function set_path_on_map(lats, longs) {
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