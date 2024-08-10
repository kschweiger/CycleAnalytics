# Cycle Analytics

App for tracking rides, managing goals, events, segments, and locations related to your cycling activities.

## Configuration

Various aspects of the tool can be configures with the [setting.toml](/conf/settings.toml) file. Create an additional file in the `conf/` folder called `.secrets.toml` for additional configuration like the database password. Typically it would look something like this:

```toml
dynaconf_merge = true

[default]
database_server = "XXX.XXX.XXX.XXX"
database_password = "..."
secret_key = "..."
```

The configuration is split into production/develop/testing evironment model. Most settings for the tool are done in the default evironments. If a setting is defined in the production/develop/testing evironments it overwrites the values in the default.

The following sections will outline some of the settings a used might change to adapt the tool to their usecasse

### Database

The values in `database_type`, `database_server`, `database_schema`, `database_user`, `database_port`, `database_name`, `database_password` need to be set and are combined into a SQLAlchemy database uri pointing to the database used as backend.

### Category values

The list defined in the `default.categorized_values` sections are used in various dropdowns and select fields all over the tools. If elements are added to the values in these list, they are added to the database when restarting the tool.

### Default values

The values set in the `default.defaults` section define default values used in dropdowns, select fields, or queries.

### Routing

Routing is done via the [`pyroutlib3`](https://github.com/MKuranowski/pyroutelib3) package, which uses _OpenStreepMap_ data. It uses weights to determine which type of paths to use for the route between nodes. These are set in the `default.routing` section in the [`settings.toml`](conf/settings.toml) configuration file. New default configuration can be added to the app by adding new sub dictionaries. The description if the path types can be found on the [OSM Wiki](https://wiki.openstreetmap.org/wiki/Map_features#Highway). The names under `Value` are used to specify the weights.

## Docker

The tool is intended to be run using the proved Docker files. Details are given in the [`docker/`](docker/README.md) directory and the compose configes files in the root directory. Currently this setup does not contain a Postgres container but it can be easily added in the [`docker-compose.yml`](docker-compose.yml) if required. The values set in the env files in the docker folder overwrite the values set in the files in the `conf/` directory. Similarly to the `.secrets.toml` docker-specific secrets can be defined in a `secrets.env` file inside the `docker/` directory. Use the

- `run-prod` (use code at build time),
- `run-dev` (mount current code and run flask app in dev mode), or
- `run-debug` (same a dev but also supports vscode debugger)

`make` commoands to run the tool after building the containers (e.g. with `make compose-build`)

## Development

Dependency management is done using `uv` (or `pip-tools`). Install `uv` in your venv and use the `uv-sync` make command to install the current dependencies.

Dependencies can be updated using the `uv-compile` make command.

Before running the app, take care of the settings described above. To run the app locally use something like this:

```bash
python -m flask --app cycle_analytics --debug run -p 7548
```

this will run on the local machine with a the default `SimpleCache` provided by flask.
