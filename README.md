# scrapy-boilerplate

This is a boilerblape for new Scrapy projects.

*The project is a WIP, so expect major changes and additions (mostly latter).*

## Features

- Python 3.6+
- [Pipenv](https://github.com/pypa/pipenv) for dependency management
- SQLAlchemy ORM with alembic migrations
- RabbitMQ integrated via [pika](https://github.com/pika/pika/)
- single file for each class
- code generation scripts for classes: spiders, pipelines, etc. (see [this section](#code-generation))

## Installation

To create a new project using this boilerplate, you need to:

1. Clone the repository and change dir to `src`.
2. Edit `BOT_NAME` in `settings.py` to your project name.
3. Issue `pipenv install --dev --pre` to install dependencies from Pipfile.
4. Change git origin to your actual project repository: `git remote set-url origin {your-project-link-here}` **OR** just delete `.git` folder at the root of the project.
5. ???
6. PROFIT!

## Usage

The boilerplate comes with some pre-written classes and helper scripts and functions, which are described in this section.

### Code generation

There is a scrapy command to generate class files and automatically add imports ti `__init__` files. It can be used as follows:

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
