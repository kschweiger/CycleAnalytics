# Docker setup and configuration

## Basic setup

Create a `secrets.env` file in this directory. It is not under version control and may be empty. It is intended to overwrite secrets set in a `.secrets.toml` file in the `conf` folder in the project root or replace it. For example, the database password can be set with `FLASK_database_password=XXX`

To start, build the container with `docker-compose`

```zsh
docker compose  build
```

It can then be run in production mode with

```zsh
docker-compose up
```

or in development mode with

```zsh
docker-compose -f docker-compose.yml -f docker-compose.dev.yml  up
```

from the project root directory. Ad the `-d` flag to run in the background.

The development mode, the application is launched in the flask debug mode and the project code is mounted. For example, this means that the servers restarts on file changes and **DEBUG** messages are shown.
Additionally a RedisInsight container is included in the compose. YOu can connect to the redis database under `redis` (host), `6379` (port) and `default` (user) under `http://localhost:8544`.

## Debugging in VSCode

Add a configuration to your `launch.json`

```json
{
  "name": "Python: Remote Attach",
  "type": "python",
  "request": "attach",
  "port": 10001,
  "host": "localhost",
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/usr/src/app/"
    }
  ]
}
```

Also use the the `docker-compose.debug.yml` file in the compose commmand.

Based on [this](https://blog.theodo.com/2020/05/debug-flask-vscode/) blog post.

