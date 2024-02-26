# scrapy-boilerplate

This is a boilerplate for new Scrapy projects.

*The project is a WIP, so expect major changes and additions (mostly latter).
Master branch is to be considered as always ready to use, with major changes/features introduced in feature branches.*

## Features

- Python 3.11+
- [Poetry](https://github.com/python-poetry/poetry) for dependency management
- SQLAlchemy ORM with alembic migrations
- RabbitMQ integrated via [pika](https://github.com/pika/pika/)
- configuration via ENV variables and/or `.env` file
- single file for each class
- Docker-ready (see [here](#docker))
- PM2-ready
- supports single-IP/rotating proxy config out of the box (see [here](#proxy-middleware))

## Installation

### Python Quickstart Guide
To create and run a new Scrapy project using this boilerplate, you need to:

1. Clone the repository.
2. `cp .env.example .env`
3. No docker:
   1. Have the following prerequisites: python 3.11+, poetry, mysqlclient libraries, etc
   2. `cd src/python/src`
   3. `poetry install`
   4. `poetry shell`
   5. `scrapy`
4. Docker:
   1. Have the following prerequisites: docker, docker-compose
   2. `docker compose up -d database python`
   3. `docker compose exec python bash`
   4. `cd /var/app/python/src/`
   5. `poetry shell`
   6. `scrapy`

### Docker

The project includes Dockerfiles and docker-compose configuration for running your spiders in containers.

Also, a configuration for default RabbitMQ server is included.

Dockerfiles are located inside the `docker` subdirectory, and the `docker-compose.yml` - at the root of the project.

Docker-compose takes configuration values from ENV. Environment can also be provided by creating a `.env` file at the root of the project (see `.env.example` as a sample).

### Proxy middleware

A scrapy downloader middleware to use a proxy server is included in `src/middlewares/HttpProxyMiddleware.py` and is enabled by default. You can use it by providing proxy endpoint with the env variable (or in the `.env` file) `PROXY` in the format `host:port`. Proxy authentication can also be provided in the `PROXY_AUTH` variable, using the format `user:password`. If provided, it is encoded as a Basic HTTP Auth and put into `Proxy-Authorization` header.

A single-endpoint proxy is used by default, assuming usage of rotating proxies service. If you want to provide your own list of proxies, an external package has to be used, as this use-case is not yet covered by this boilerplate.

## File and folder structure

This boilerplate offers a more intuitive alternative to Scrapy's default project structure. Here, file/directory structure is more flattened and re-arranged a bit.

- All scrapy-related code is placed directly in `src/python/src` subdirectory (without any subdirs with project name, contrary to default).
- All scrapy classes (by default located in `items.py, middlewares.py, pipelines.py`) are converted to sub-modules, where each class is placed in its own separate file. Nothing else goes into those files.
- Configs in `scrapy.cfg` and `settings.py` are edited to correspond with these changes.
- Additional subdirectories are added to contain code, related to working with database (`src/python/src/database`), RabbitMQ (`src/python/src/rmq`)
