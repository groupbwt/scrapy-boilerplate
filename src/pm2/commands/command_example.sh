#!/bin/bash
DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd "$DIR"
pushd "../.."
exec poetry run scrapy
popd
