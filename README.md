# Cycle Analytics

App for tracking rides, managing goal, and events related to your cycling activities.


## Configuration

### Routing

Routing is done via the [`pyroutlib3`](https://github.com/MKuranowski/pyroutelib3) package, which uses _OpenStreepMap_ data. It uses weights to determine which type of paths to use for the route between nodes. These are set in the `default.routing` section in the [`settings.toml`](conf/settings.toml) configuration file. New default configuration can be added to the app by adding new sub dictionaries. The description if the path types can be found on the [OSM Wiki](https://wiki.openstreetmap.org/wiki/Map_features#Highway). The names under `Value` are used to specify the weights.