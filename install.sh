#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR > /dev/null

read -p "Enter project name (snake_cased): " project_name

echo "Creating .env files"
cp -i src/.env.example src/.env
cp -i .docker_env.example .env

echo "Updating project name"
sed -ie "s/YOUR_PROJECT_NAME/$project_name/g" src/settings.py
sed -ie "s/YOUR_PROJECT_NAME/$project_name/g" .env

read -p "Create new git repo? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing .git folder"
    rm -rf .git
    git init
fi

read -p "Clear README? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    dirname=${PWD##*/}
    echo -e "# $dirname\n" > README.md
    echo "Cleared README"
fi

echo "Installing pipenv dependencies"
pipenv install --dev --pre

echo "Setup finished, your project is ready!"
rm -f install.sh
popd > /dev/null
