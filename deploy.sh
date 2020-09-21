#!/bin/bash

# set variables
echo "$1"
echo "$2"
echo "$3"
release_dir="$1/releases/$2"
latest_release_dir="$1/latest";

# change current working dir to current release candidate dir
cd "$1/releases/$2"

# remove redundant files and dirs
rm -rf .git
rm -rf src/python/src/logs

# create symlinks for .env files and logs dir
# general .env
ln -s "$1/.env" .env
# python required (comment if redundant)
ln -s "$1/.env" src/python/src/.env
ln -s "$1/logs" src/python/src
# javascript required (comment if redundant)
ln -s "$1/.env" src/javascript/src/.env
ln -s "$1/logs" src/javascript/src

# install dependencies
# python
cd "$release_dir/src/python/src"
python3.8 -m poetry install
python3.8 -m poetry run alembic upgrade head
# javascript
cd "$release_dir/src/javascript/src"
npm install
npm run fbuild

# linking latest release
rm -rf "$latest_release_dir"
ln -s "$release_dir" "$latest_release_dir"

# remove old pm2 processes
pm2 stop "/$3_/" && pm2 delete "/$3_/"

# run pm2 processes
# python (comment if redundant)
cd "$release_dir/src/python/src"
pm2 start pm2.config.js
pm2 save
# javascript (comment if redundant)
cd "$release_dir/src/javascript/src"
pm2 start pm2.config.js
pm2 save

# cleanup (remove old releases)
cd "$1/releases"
pwd
rm -rf `ls -t | tail -n +4`

