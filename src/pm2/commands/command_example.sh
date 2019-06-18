#!/bin/bash
DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd "$DIR"
pushd "../.."
export PIPENV_VENV_IN_PROJECT=1
exec pipenv run scrapy
popd
