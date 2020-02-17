# scrapy-boilerplate

This is a boilerplate for new Scrapy projects.

*The project is a WIP, so expect major changes and additions (mostly latter).
Master branch is to be considered as always ready to use, with major changes/features introduced in feature branches.*

## Features

- Python 3.6+
- [Poetry](https://github.com/python-poetry/poetry) for dependency management
- SQLAlchemy ORM with alembic migrations
- RabbitMQ integrated via [pika](https://github.com/pika/pika/)
- configuration via ENV variables and/or `.env` file
- single file for each class
- code generation scripts for classes: spiders, pipelines, etc. (see [this section](#code-generation))
- [Black](https://github.com/psf/black) to ensure codestyle consistency (see [here](#black))
- Docker-ready (see [here](#docker))
- PM2-ready (see [here](#pm2))
- supports single-IP/rotating proxy config out of the box (see [here](#proxy-middleware))

## Installation

To create a new project using this boilerplate, you need to:

1. Clone the repository.
2. Run the installation script: `./install.sh`
3. ???
4. PROFIT!

## Usage

The boilerplate comes with some pre-written classes and helper scripts and functions, which are described in this section.

### Code generation

There is a scrapy command to generate class files and automatically add imports to `__init__` files.

The command is a part of a separate [package](https://github.com/KristobalJunta/scrapy-command-new). The repository contains code of the command and default tempaltes used for generation.

It can be used as follows:

```
scrapy new spider SampleSpider
```

The first argument (`spider`) is a type of class file to be generated, and can be one of the following:

- command
- extension
- item
- middleware
- model
- pipeline
- spider_middleware
- spider

The second argument is class name.

Also for `pipeline` and `spider` class an option `--rabbit` can be used to add RabbitMQ connection code to generated source.

Option `--item` is supported for generating pipelines, which adds an import and type-check for a provided item class to the resulting code.

### Docker

The project includes Dockerfiles and docker-compose configuration for running your spiders in containers.

Also, a configuration for default RabbitMQ server is included.

Dockerfiles are located inside the `docker` subdirectory, and the `docker-compose.yml` - at the root of the project. You might want to change the `CMD` of the scrapy container to something more relevant to your project. To do so, edit `docker/scrapy/Dockerfile`.

Docker-compose takes configuration values from ENV. Environment can also be provided by creating a `.env` file at the root of the project (see `.docker_env.example` as a sample). Creating of dotenv for docker is handled in the `install.sh` script by default.

### Black

Black is the uncompromising Python code formatter. It is used in thsi project to ensure code style consistensy in the least intrusive fashion.

Black is included in Pipfile dev-dependencies. A pre-commit hook for running autoformatting is also included, via [pre-commit](https://pre-commit.com) tool. It is installed automatically, if you run `install.sh`. Otherwise, to use it you need to run `pre-commit install` in the root project folder after installing pre-commit itself.

### PM2

This boilerplate contains a sample PM2 config file along with a bash startup script that sets up all the necessary environment to run scrapy with this process manager.

All you need to do, is copy/edit `src/pm2/commands/command_example.sh` and change the `exec` part to the command actually needed to be run, and then create `process.json` ecosystem file (based on `src/pm2/process.example.json`) to start the script.

Then, cd to `src/pm2` and run `pm2 start process.json`.

### Proxy middleware

A scrapy downloader middleware to use a proxy server is included in `src/middlewares/HttpProxyMiddleware.py` and is enabled by default. You can use it by providing proxy endpoint with the env variable (or in the `.env` file) `PROXY` in the format `host:port`. Proxy authentication can also be provided in the `PROXY_AUTH` variable, using the format `user:password`. If provided, it is encoded as a Basic HTTP Auth and put into `Proxy-Authorization` header.

A single-endpoint proxy is used by default, assuming usage of rotating proxies service. If you want to provide your own list of proxies, an external package has to be used, as this use-case is not yet covered by this boilerplate.

## File and folder structure

This boilerplate offers a more intuitive alternative to Scrapy's default project structure. Here, file/directory structure is more flattened and re-arranged a bit.

- All scrapy-related code is placed directly in `src` subdirectory (without any subdirs with project name, contrary to default).
- All scrapy classes (by default located in `items.py, middlewares.py, pipelines.py`) are converted to sub-modules, where each class is placed in its own separate file. Nothing else goes into those files. Helper functions/modules can be placed in the `helpers` module.
- Configs in `scrapy.cfg` and `settings.py` are edited to correspond with these changes.
- Additional subdirectories are added to contain code, related to working with database (`src/database`), RabbitMQ (`src/rabbitmq`), and also the accessory directory `src/_templates`, that contains templates for code generation (see ["new" command](#code-generation))
