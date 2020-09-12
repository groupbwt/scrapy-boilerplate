#!/bin/bash
set -eu
cd /var/app/python/src
poetry install
poetry run alembic upgrade head
pm2 status
# uncomment following line if pm2.config.js file existing in python/src dir and contain instructions
# to run worker processes. Or replace with required bash terminal instructions
#pm2 start pm2.config.js
python3
