#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR

echo "Enter project name (snake-cased): "
read project_name

echo "Updating project name"
sed -ie "s/YOUR_PROJECT_NAME/$project_name/g" src/settings.py

echo "Removing .git folder"
rm -rf .git

echo "Initializing empty git repo"
git init

echo "Creating .env file"
cp -i src/.env.example src/.env

echo ""
read -p "Clear README?[y/N] " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    dirname=${PWD##*/}
    echo "# $dirname\n" > README.md
    echo "Cleared README"
fi

echo "Setup finished, your project is ready"
rm -f install.sh
popd
