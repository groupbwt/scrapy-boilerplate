#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR > /dev/null

read -p "Enter project name (snake_cased): " project_name

echo "Creating .env files"
cp -i src/.env.example src/.env
cp -i .docker_env.example .env

echo "Updating project name"
sed -i "s/YOUR_PROJECT_NAME/$project_name/g" src/settings.py
sed -i "s/YOUR_PROJECT_NAME/$project_name/g" .env

read -p "Create new git repo? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing .git folder"
    rm -rf .git
    git init
fi

read -p "Delete README? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f README.md
    echo "Deleted README"
fi

echo "Installing pipenv dependencies"
pushd ./src > /dev/null
pipenv install --dev --pre
popd > /dev/null

read -p "Add pre-commit hooks? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
  pushd ./src > /dev/null
  PYTHON=$(pipenv --py)
  popd > /dev/null
  $PYTHON -m pre_commit install
fi

echo "Setup finished, your project is ready!"
rm -f install.sh
popd > /dev/null
